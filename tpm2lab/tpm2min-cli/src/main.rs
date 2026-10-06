//! `tpm2min-cli`: drives the `tpm2min` builders/parsers against a `swtpm`
//! TCP data channel, dumps every artefact to files, and verifies the quote
//! (a) with tpm2-tools (`tpm2_checkquote`), (b) with OpenSSL over our own
//! DER encodings, and (c) with an independent Python verifier.
//!
//! Only the std library is used here; all TPM byte handling is `tpm2min`.

use std::fmt::Write as _;
use std::fs;
use std::io::{self, Read, Write};
use std::net::TcpStream;
use std::path::{Path, PathBuf};
use std::process::Command;

use tpm2min::cmd::{self, SigScheme};
use tpm2min::consts::*;
use tpm2min::pcr::{composite_sha256, PcrSelection, PcrSelectionList};
use tpm2min::sha256::Sha256;
use tpm2min::{der, rsp, Error, COMMAND_BUFFER_SIZE, RESPONSE_BUFFER_SIZE};

// --------------------------------------------------------------------------
// small helpers
// --------------------------------------------------------------------------

fn hex(b: &[u8]) -> String {
    let mut s = String::with_capacity(b.len() * 2);
    for x in b {
        let _ = write!(s, "{x:02x}");
    }
    s
}

fn base64(b: &[u8]) -> String {
    const T: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut out = String::new();
    for chunk in b.chunks(3) {
        let n = chunk.len();
        let v = (u32::from(chunk[0]) << 16)
            | (u32::from(*chunk.get(1).unwrap_or(&0)) << 8)
            | u32::from(*chunk.get(2).unwrap_or(&0));
        out.push(T[((v >> 18) & 63) as usize] as char);
        out.push(T[((v >> 12) & 63) as usize] as char);
        out.push(if n > 1 { T[((v >> 6) & 63) as usize] as char } else { '=' });
        out.push(if n > 2 { T[(v & 63) as usize] as char } else { '=' });
    }
    out
}

fn pem(label: &str, der: &[u8]) -> String {
    let b64 = base64(der);
    let mut s = format!("-----BEGIN {label}-----\n");
    for line in b64.as_bytes().chunks(64) {
        s.push_str(std::str::from_utf8(line).unwrap());
        s.push('\n');
    }
    let _ = writeln!(s, "-----END {label}-----");
    s
}

#[derive(Default)]
struct Checks {
    items: Vec<(String, bool, String)>,
}

impl Checks {
    fn add(&mut self, name: &str, pass: bool, detail: impl Into<String>) {
        let detail = detail.into();
        println!("[{}] {name}{}", if pass { "PASS" } else { "FAIL" }, if detail.is_empty() { String::new() } else { format!(" — {detail}") });
        self.items.push((name.to_string(), pass, detail));
    }
    fn all_pass(&self) -> bool {
        self.items.iter().all(|(_, p, _)| *p)
    }
    fn render(&self) -> String {
        let mut s = String::new();
        for (name, pass, detail) in &self.items {
            let _ = writeln!(s, "{} {}{}", if *pass { "PASS" } else { "FAIL" }, name, if detail.is_empty() { String::new() } else { format!(" -- {detail}") });
        }
        let _ = writeln!(s, "overall: {}", if self.all_pass() { "PASS" } else { "FAIL" });
        s
    }
}

// --------------------------------------------------------------------------
// swtpm TCP data channel: raw TPM command stream (same framing as the
// tpm2-tss `swtpm` TCTI: write command bytes, read `responseSize` bytes).
// --------------------------------------------------------------------------

struct Tpm {
    stream: TcpStream,
    log: String,
    retries: usize,
}

impl Tpm {
    fn connect(host: &str, port: u16) -> io::Result<Self> {
        let stream = TcpStream::connect((host, port))?;
        stream.set_nodelay(true)?;
        Ok(Self { stream, log: String::new(), retries: 0 })
    }

    fn transceive_once(&mut self, name: &str, command: &[u8], response: &mut [u8]) -> io::Result<usize> {
        let _ = writeln!(self.log, "{name} cmd ({} bytes): {}", command.len(), hex(command));
        self.stream.write_all(command)?;
        self.stream.read_exact(&mut response[..RESPONSE_HEADER_SIZE])?;
        let size = u32::from_be_bytes([response[2], response[3], response[4], response[5]]) as usize;
        if !(RESPONSE_HEADER_SIZE..=response.len()).contains(&size) {
            return Err(io::Error::new(io::ErrorKind::InvalidData, format!("bad responseSize {size}")));
        }
        self.stream.read_exact(&mut response[RESPONSE_HEADER_SIZE..size])?;
        let _ = writeln!(self.log, "{name} rsp ({size} bytes): {}", hex(&response[..size]));
        Ok(size)
    }

    /// Send a command; on a warning-class `TPM_RC_RETRY`/`YIELDED`/`NV_RATE`
    /// response resend the identical command (bounded).  This mirrors what the
    /// Linux `tpm_transmit()` and tpm2-tss ESAPI do; libtpms returns
    /// `TPM_RC_RETRY` once for the first clock/NV-touching command after startup.
    fn transceive(&mut self, name: &str, command: &[u8], response: &mut [u8]) -> io::Result<usize> {
        const MAX_RETRIES: usize = 5;
        let mut attempt = 0;
        loop {
            let size = self.transceive_once(name, command, response)?;
            let rc = u32::from_be_bytes([response[6], response[7], response[8], response[9]]);
            if Error::TpmRc(rc).is_retryable() && attempt < MAX_RETRIES {
                attempt += 1;
                println!("  {name}: TPM_RC 0x{rc:03x} (retryable warning) -> resending identical command (attempt {attempt})");
                let _ = writeln!(self.log, "{name}: rc 0x{rc:03x} is retryable, resending (attempt {attempt})");
                std::thread::sleep(std::time::Duration::from_millis(20));
                continue;
            }
            self.retries += attempt;
            return Ok(size);
        }
    }
}

// --------------------------------------------------------------------------
// external tool runner
// --------------------------------------------------------------------------

struct Tools {
    log: String,
    cwd: PathBuf,
}

impl Tools {
    fn run(&mut self, program: &str, args: &[&str]) -> (bool, String) {
        let cmdline = std::iter::once(program.to_string()).chain(args.iter().map(|a| a.to_string())).collect::<Vec<_>>().join(" ");
        println!("$ {cmdline}");
        let out = Command::new(program).args(args).current_dir(&self.cwd).output();
        match out {
            Ok(o) => {
                let text = format!("{}{}", String::from_utf8_lossy(&o.stdout), String::from_utf8_lossy(&o.stderr));
                for line in text.lines() {
                    println!("  | {line}");
                }
                let _ = writeln!(self.log, "$ {cmdline}\n{text}(exit {})\n", o.status);
                (o.status.success(), text)
            }
            Err(e) => {
                println!("  ! failed to spawn: {e}");
                let _ = writeln!(self.log, "$ {cmdline}\n! spawn error: {e}\n");
                (false, format!("spawn error: {e}"))
            }
        }
    }
}

fn pcrread_values(text: &str) -> Vec<(u8, String)> {
    // lines look like "    4 : 0x3D45..."  (tpm2_pcrread 5.x yaml)
    let mut v = Vec::new();
    for line in text.lines() {
        if let Some((l, r)) = line.split_once(':') {
            if let Ok(idx) = l.trim().parse::<u8>() {
                let r = r.trim().trim_start_matches("0x").to_ascii_lowercase();
                if !r.is_empty() && r.chars().all(|c| c.is_ascii_hexdigit()) {
                    v.push((idx, r));
                }
            }
        }
    }
    v
}

// --------------------------------------------------------------------------
// main flow
// --------------------------------------------------------------------------

struct Opts {
    host: String,
    port: u16,
    out: PathBuf,
    scheme: SigScheme,
    skip_tools: bool,
    verify_py: Option<PathBuf>,
}

fn parse_opts() -> Opts {
    let mut o = Opts { host: "127.0.0.1".into(), port: 2321, out: PathBuf::from("out"), scheme: SigScheme::Null, skip_tools: false, verify_py: None };
    let mut it = std::env::args().skip(1);
    while let Some(a) = it.next() {
        match a.as_str() {
            "--host" => o.host = it.next().expect("--host value"),
            "--port" => o.port = it.next().expect("--port value").parse().expect("port"),
            "--out" => o.out = PathBuf::from(it.next().expect("--out value")),
            "--scheme" => {
                o.scheme = match it.next().expect("--scheme value").as_str() {
                    "null" => SigScheme::Null,
                    "ecdsa" => SigScheme::EcdsaSha256,
                    other => panic!("unknown scheme {other}"),
                }
            }
            "--skip-tools" => o.skip_tools = true,
            "--verify-py" => o.verify_py = Some(PathBuf::from(it.next().expect("--verify-py value"))),
            "-h" | "--help" => {
                println!("tpm2min-cli [--host H] [--port P] [--out DIR] [--scheme null|ecdsa] [--skip-tools] [--verify-py script.py]");
                std::process::exit(0);
            }
            other => panic!("unknown argument {other}"),
        }
    }
    o
}

fn save(dir: &Path, name: &str, data: &[u8]) {
    fs::write(dir.join(name), data).unwrap_or_else(|e| panic!("write {name}: {e}"));
}

fn main() {
    let opts = parse_opts();
    fs::create_dir_all(&opts.out).expect("create out dir");
    let out = opts.out.canonicalize().expect("canonicalize out dir");
    let tcti = format!("swtpm:host={},port={}", opts.host, opts.port);
    let mut checks = Checks::default();

    let mut tpm = Tpm::connect(&opts.host, opts.port).unwrap_or_else(|e| {
        eprintln!("cannot connect to swtpm at {}:{}: {e}", opts.host, opts.port);
        std::process::exit(2);
    });
    let mut cbuf = [0u8; COMMAND_BUFFER_SIZE];
    let mut rbuf = [0u8; RESPONSE_BUFFER_SIZE];

    // ---- 1. TPM2_Startup(TPM_SU_CLEAR) -----------------------------------
    let n = cmd::startup(&mut cbuf, TPM_SU_CLEAR).unwrap();
    let m = tpm.transceive("TPM2_Startup", &cbuf[..n], &mut rbuf).expect("io");
    match rsp::startup(&rbuf[..m]) {
        Ok(()) => checks.add("TPM2_Startup(CLEAR)", true, "rc=0 (TPM was not started yet)"),
        Err(Error::TpmRc(TPM_RC_INITIALIZE)) => checks.add("TPM2_Startup(CLEAR)", true, "rc=0x100 TPM_RC_INITIALIZE: already started by swtpm --flags startup-clear (expected)"),
        Err(e) => checks.add("TPM2_Startup(CLEAR)", false, format!("{e}")),
    }

    // ---- 2. TPM2_PCR_Extend(12, sha256("AEGIS-TEST")) ------------------------
    let extend_digest = Sha256::digest(b"AEGIS-TEST");
    println!("sha256(\"AEGIS-TEST\") = {}", hex(&extend_digest));
    let n = cmd::pcr_extend_sha256(&mut cbuf, 12, &extend_digest).unwrap();
    let m = tpm.transceive("TPM2_PCR_Extend", &cbuf[..n], &mut rbuf).expect("io");
    match rsp::pcr_extend(&rbuf[..m]) {
        Ok(()) => checks.add("TPM2_PCR_Extend PCR12 <- sha256(AEGIS-TEST)", true, ""),
        Err(e) => checks.add("TPM2_PCR_Extend PCR12", false, format!("{e}")),
    }

    // ---- 3. TPM2_PCR_Read(sha256:4,12) ------------------------------------------
    let selection = PcrSelectionList::single(PcrSelection::sha256(&[4, 12]));
    let n = cmd::pcr_read(&mut cbuf, &selection).unwrap();
    let m = tpm.transceive("TPM2_PCR_Read", &cbuf[..n], &mut rbuf).expect("io");
    let pcrs = rsp::pcr_read(&rbuf[..m]).unwrap_or_else(|e| panic!("PCR_Read failed: {e}"));
    let pcr4 = pcrs.sha256_value(0).expect("pcr4");
    let pcr12 = pcrs.sha256_value(1).expect("pcr12");
    println!("pcrUpdateCounter = {}", pcrs.update_counter);
    println!("PCR[4]  (sha256) = {}", hex(&pcr4));
    println!("PCR[12] (sha256) = {}", hex(&pcr12));
    checks.add("TPM2_PCR_Read returned 2 digests for sha256:4,12", pcrs.count == 2 && pcrs.selection == selection, format!("count={}", pcrs.count));
    // PCR 12 was all-zero at reset, so after one extend it must equal SHA256(0^32 || digest)
    let mut cat = [0u8; 64];
    cat[32..].copy_from_slice(&extend_digest);
    let expected_pcr12 = Sha256::digest(&cat);
    checks.add("PCR12 == SHA256(0x00*32 || sha256(AEGIS-TEST)) (fresh TPM state)", pcr12 == expected_pcr12, if pcr12 == expected_pcr12 { String::new() } else { "PCR12 was not pristine before the extend; the quote still covers whatever value it has".to_string() });
    save(&out, "pcr4.hex", hex(&pcr4).as_bytes());
    save(&out, "pcr12.hex", hex(&pcr12).as_bytes());
    save(&out, "pcrs.txt", format!("sha256:\n  4 : 0x{}\n  12: 0x{}\n", hex(&pcr4).to_uppercase(), hex(&pcr12).to_uppercase()).as_bytes());

    // ---- 4. TPM2_CreatePrimary(TPM_RH_OWNER, ECC P-256 ECDSA/SHA256) ----------
    let n = cmd::create_primary_ecc_p256(&mut cbuf, TPM_RH_OWNER).unwrap();
    let m = tpm.transceive("TPM2_CreatePrimary", &cbuf[..n], &mut rbuf).expect("io");
    let key = rsp::create_primary(&rbuf[..m]).unwrap_or_else(|e| panic!("CreatePrimary failed: {e}"));
    let public = rsp::ecc_public(key.public.as_slice()).unwrap_or_else(|e| panic!("TPMT_PUBLIC parse: {e}"));
    let handle = key.handle;
    let mut tpm2b_public = Vec::with_capacity(2 + key.public.len());
    tpm2b_public.extend_from_slice(&(key.public.len() as u16).to_be_bytes());
    tpm2b_public.extend_from_slice(key.public.as_slice());
    println!("objectHandle      = 0x{handle:08x}");
    println!("TPM2B_PUBLIC      = {}", hex(&tpm2b_public));
    println!("  nameAlg=0x{:04x} attrs=0x{:08x} curve=0x{:04x} scheme=0x{:04x}/0x{:04x}", public.name_alg, public.attributes, public.curve, public.scheme, public.scheme_hash);
    println!("  x = {}", hex(&public.x));
    println!("  y = {}", hex(&public.y));
    println!("name              = {}", hex(key.name.as_slice()));
    checks.add("CreatePrimary handle is transient", handle & 0xff00_0000 == TRANSIENT_FIRST, format!("0x{handle:08x}"));
    checks.add("outPublic echoes template (ECC/P-256/ECDSA-SHA256/attrs 0x00050072)", public.curve == TPM_ECC_NIST_P256 && public.scheme == TPM_ALG_ECDSA && public.scheme_hash == TPM_ALG_SHA256 && public.attributes == SIGNING_KEY_ATTRIBUTES && public.name_alg == TPM_ALG_SHA256, "");
    // Name = nameAlg || H(TPMT_PUBLIC)   (Part 1 §16 "Names")
    let mut want_name = vec![0x00, 0x0B];
    want_name.extend_from_slice(&Sha256::digest(key.public.as_slice()));
    checks.add("name == 0x000B || SHA256(TPMT_PUBLIC)", key.name.as_slice() == want_name.as_slice(), "");
    let spki = der::p256_spki(&public.x, &public.y);
    let pub_pem = pem("PUBLIC KEY", &spki);
    save(&out, "pub_tpm2b.bin", &tpm2b_public);
    save(&out, "pub_tpm2b.hex", hex(&tpm2b_public).as_bytes());
    save(&out, "pub_xy.hex", format!("x={}\ny={}\n", hex(&public.x), hex(&public.y)).as_bytes());
    save(&out, "pub.der", &spki);
    save(&out, "pub.pem", pub_pem.as_bytes());
    save(&out, "name.hex", hex(key.name.as_slice()).as_bytes());

    // ---- 5. TPM2_Quote --------------------------------------------------------------
    let qualifying = Sha256::digest(b"receipt-chain-test");
    println!("qualifyingData = sha256(\"receipt-chain-test\") = {}", hex(&qualifying));
    let n = cmd::quote(&mut cbuf, handle, &qualifying, opts.scheme, &selection).unwrap();
    let m = tpm.transceive("TPM2_Quote", &cbuf[..n], &mut rbuf).expect("io");
    let q = rsp::quote(&rbuf[..m]).unwrap_or_else(|e| panic!("Quote failed: {e}"));
    let attest_bytes = q.attest.as_slice().to_vec();
    let mut tpm2b_attest = Vec::new();
    tpm2b_attest.extend_from_slice(&(attest_bytes.len() as u16).to_be_bytes());
    tpm2b_attest.extend_from_slice(&attest_bytes);
    let mut rs = Vec::with_capacity(64);
    rs.extend_from_slice(&q.signature.r);
    rs.extend_from_slice(&q.signature.s);
    let mut sig_der = [0u8; der::ECDSA_P256_DER_MAX];
    let sig_der_len = der::ecdsa_signature(&q.signature.r, &q.signature.s, &mut sig_der).unwrap();
    println!("TPM2B_ATTEST      = {}", hex(&tpm2b_attest));
    println!("TPMS_ATTEST       = {}", hex(&attest_bytes));
    println!("TPMT_SIGNATURE    = {}", hex(q.signature_raw.as_slice()));
    println!("signature r||s    = {}", hex(&rs));
    println!("signature DER     = {}", hex(&sig_der[..sig_der_len]));
    save(&out, "quote_tpm2b_attest.hex", hex(&tpm2b_attest).as_bytes());
    save(&out, "attest.bin", &attest_bytes);
    save(&out, "attest.hex", hex(&attest_bytes).as_bytes());
    save(&out, "sig_tss.bin", q.signature_raw.as_slice());
    save(&out, "sig_rs.hex", hex(&rs).as_bytes());
    save(&out, "sig.der", &sig_der[..sig_der_len]);
    save(&out, "qualifying.bin", &qualifying);
    save(&out, "qualifying.hex", hex(&qualifying).as_bytes());
    checks.add("Quote signature is ECDSA/SHA256", q.signature.hash_alg == TPM_ALG_SHA256, "");
    println!("retryable-warning resends so far: {}", tpm.retries);

    // ---- 6. local verification of TPMS_ATTEST ------------------------------------
    let at = rsp::attest(&attest_bytes).unwrap_or_else(|e| panic!("attest parse: {e}"));
    checks.add("attest.magic == 0xff544347 && type == TPM_ST_ATTEST_QUOTE", at.magic == TPM_GENERATED_VALUE && at.attest_type == TPM_ST_ATTEST_QUOTE, "");
    checks.add("attest.extraData == qualifyingData", at.extra_data.as_slice() == qualifying, "");
    checks.add("attest.pcrSelect == sha256:4,12", at.quote.pcr_select == selection, "");
    let composite = composite_sha256(&[pcr4, pcr12]);
    checks.add("attest.pcrDigest == SHA256(PCR4 || PCR12)", at.quote.pcr_digest.as_slice() == composite, format!("pcrDigest={}", hex(at.quote.pcr_digest.as_slice())));
    // qualifiedSigner = nameAlg || H(QN_parent || Name), QN of a hierarchy is its handle (Part 1 §26.5)
    let mut qn_in = TPM_RH_OWNER.to_be_bytes().to_vec();
    qn_in.extend_from_slice(key.name.as_slice());
    let mut want_qn = vec![0x00, 0x0B];
    want_qn.extend_from_slice(&Sha256::digest(&qn_in));
    checks.add("attest.qualifiedSigner == 0x000B || SHA256(TPM_RH_OWNER || name)", at.qualified_signer.as_slice() == want_qn.as_slice(), "");
    println!("clockInfo: clock={}ms resetCount={} restartCount={} safe={} firmwareVersion=0x{:016x}", at.clock_info.clock, at.clock_info.reset_count, at.clock_info.restart_count, at.clock_info.safe, at.firmware_version);
    save(&out, "attest_parsed.txt", format!("magic=0x{:08x}\ntype=0x{:04x}\nqualifiedSigner={}\nextraData={}\nclock={}\nresetCount={}\nrestartCount={}\nsafe={}\nfirmwareVersion=0x{:016x}\npcrSelect=sha256:{:?}\npcrDigest={}\n", at.magic, at.attest_type, hex(at.qualified_signer.as_slice()), hex(at.extra_data.as_slice()), at.clock_info.clock, at.clock_info.reset_count, at.clock_info.restart_count, at.clock_info.safe, at.firmware_version, at.quote.pcr_select.as_slice()[0].indices().collect::<Vec<_>>(), hex(at.quote.pcr_digest.as_slice())).as_bytes());

    // Give the data channel back to swtpm before tpm2-tools connect to it.
    let mut tpm_log = std::mem::take(&mut tpm.log);
    drop(tpm);

    // ---- 7. external verification -----------------------------------------------------
    let mut tools = Tools { log: String::new(), cwd: out.clone() };
    if !opts.skip_tools {
        // (i) tpm2-tools: pcr file from the same TPM, public key via tpm2_readpublic, tpm2_checkquote
        let (ok, text) = tools.run("tpm2_pcrread", &["-T", &tcti, "-o", "pcr.bin", "sha256:4,12"]);
        let vals = pcrread_values(&text);
        let tools_pcr4 = vals.iter().find(|(i, _)| *i == 4).map(|(_, v)| v.clone()).unwrap_or_default();
        let tools_pcr12 = vals.iter().find(|(i, _)| *i == 12).map(|(_, v)| v.clone()).unwrap_or_default();
        checks.add("tpm2_pcrread values == our TPM2_PCR_Read values", ok && tools_pcr4 == hex(&pcr4) && tools_pcr12 == hex(&pcr12), "");

        let handle_str = format!("0x{handle:08x}");
        let (ok_pem, _) = tools.run("tpm2_readpublic", &["-T", &tcti, "-c", &handle_str, "-f", "pem", "-o", "pub_tools.pem"]);
        let tools_pem = fs::read_to_string(out.join("pub_tools.pem")).unwrap_or_default();
        checks.add("tpm2_readpublic -f pem == our DER->PEM of (x,y)", ok_pem && tools_pem.trim() == pub_pem.trim(), "");
        let (ok_bin, _) = tools.run("tpm2_readpublic", &["-T", &tcti, "-c", &handle_str, "-o", "pub_tools.tpm2b"]);
        let tools_tpm2b = fs::read(out.join("pub_tools.tpm2b")).unwrap_or_default();
        checks.add("tpm2_readpublic -o (TPM2B_PUBLIC) == our raw TPM2B_PUBLIC bytes", ok_bin && tools_tpm2b == tpm2b_public, format!("{} bytes", tools_tpm2b.len()));

        let qhex = hex(&qualifying);
        let (ok, text) = tools.run("tpm2_checkquote", &["-u", "pub.pem", "-g", "sha256", "-m", "attest.bin", "-s", "sig_tss.bin", "-f", "pcr.bin", "-l", "sha256:4,12", "-q", &qhex]);
        checks.add("tpm2_checkquote (our pub.pem, attest.bin, sig_tss.bin, pcr.bin)", ok, text.lines().last().unwrap_or("").to_string());
        let (ok, _) = tools.run("tpm2_checkquote", &["-u", "pub_tools.pem", "-g", "sha256", "-m", "attest.bin", "-s", "sig_tss.bin", "-f", "pcr.bin", "-l", "sha256:4,12", "-q", &qhex]);
        checks.add("tpm2_checkquote with tpm2_readpublic's PEM", ok, "");
        // negative control: wrong qualifying data must be rejected
        let wrong_q = hex(&Sha256::digest(b"wrong"));
        let (ok, _) = tools.run("tpm2_checkquote", &["-u", "pub.pem", "-g", "sha256", "-m", "attest.bin", "-s", "sig_tss.bin", "-f", "pcr.bin", "-l", "sha256:4,12", "-q", &wrong_q]);
        checks.add("tpm2_checkquote rejects wrong qualifying data (negative control)", !ok, "");

        // (ii) OpenSSL: ECDSA-P256 over SHA256(TPMS_ATTEST) with our DER (r,s)
        let (ok, text) = tools.run("openssl", &["dgst", "-sha256", "-verify", "pub.pem", "-signature", "sig.der", "attest.bin"]);
        checks.add("openssl dgst -sha256 -verify pub.pem -signature sig.der attest.bin", ok && text.contains("Verified OK"), text.trim().to_string());
        let mut tampered = attest_bytes.clone();
        tampered[attest_bytes.len() - 1] ^= 0x01; // flip a bit in pcrDigest
        save(&out, "attest_tampered.bin", &tampered);
        let (ok, text) = tools.run("openssl", &["dgst", "-sha256", "-verify", "pub.pem", "-signature", "sig.der", "attest_tampered.bin"]);
        checks.add("openssl rejects tampered attest (negative control)", !ok && text.contains("Verification failure"), text.trim().to_string());
        let (ok, text) = tools.run("openssl", &["ec", "-pubin", "-in", "pub.pem", "-noout", "-text"]);
        checks.add("openssl parses pub.pem as P-256 public key", ok && text.contains("prime256v1"), "");

        // (iii) Python verifier (independent parser + cryptography), run with -I
        if let Some(py) = &opts.verify_py {
            let py = py.canonicalize().expect("verify script path");
            let (ok, text) = tools.run("python3", &["-I", py.to_str().unwrap(), "pub.pem", "attest.bin", "sig_rs.hex", "qualifying.hex", "pcr4.hex", "pcr12.hex", "name.hex"]);
            checks.add("python3 verify_quote.py (independent parser + cryptography ECDSA)", ok, text.lines().last().unwrap_or("").to_string());
        }
    }

    // ---- 8. TPM2_FlushContext --------------------------------------------------------------
    let mut tpm = Tpm::connect(&opts.host, opts.port).expect("reconnect");
    let n = cmd::flush_context(&mut cbuf, handle).unwrap();
    let m = tpm.transceive("TPM2_FlushContext", &cbuf[..n], &mut rbuf).expect("io");
    match rsp::flush_context(&rbuf[..m]) {
        Ok(()) => checks.add("TPM2_FlushContext(handle)", true, format!("0x{handle:08x}")),
        Err(e) => checks.add("TPM2_FlushContext(handle)", false, format!("{e}")),
    }
    // flushing again must fail (TPM_RC_HANDLE | RC_FMT1 | handle#1 = 0x18b)
    let m = tpm.transceive("TPM2_FlushContext(again)", &cbuf[..n], &mut rbuf).expect("io");
    let again = rsp::flush_context(&rbuf[..m]);
    checks.add("second FlushContext fails (handle gone)", matches!(again, Err(Error::TpmRc(_))), format!("{again:?}"));
    tpm_log.push_str(&tpm.log);
    drop(tpm);

    // ---- summary ----------------------------------------------------------------------------------
    save(&out, "tpm_commands.log", tpm_log.as_bytes());
    save(&out, "tools.log", tools.log.as_bytes());
    let summary = checks.render();
    save(&out, "verify_summary.txt", summary.as_bytes());
    println!("\n==== SUMMARY ====\n{summary}");
    if !checks.all_pass() {
        std::process::exit(1);
    }
}
