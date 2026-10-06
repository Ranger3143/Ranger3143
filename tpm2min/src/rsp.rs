//! Response parsers.  Every parser takes the complete response buffer (exactly
//! `responseSize` bytes) and returns typed, fixed-size results.
//!
//! Response header (Part 1 §18.10 / Part 3 §5.4):
//!
//! ```text
//! offset  size  field
//! 0       2     TPM_ST tag           (0x8001 / 0x8002; always 0x8001 on error)
//! 2       4     UINT32 responseSize  (total bytes incl. header)
//! 6       4     TPM_RC responseCode  (0 = success)
//! 10      ...   [handles] [UINT32 parameterSize] [parameters] [TPMS_AUTH_RESPONSE...]
//! ```
//!
//! `TPMS_AUTH_RESPONSE` (Part 2 §10.13.3) for a password session:
//! `TPM2B_NONCE nonce (0000) | TPMA_SESSION (01 or 00) | TPM2B_AUTH hmac (0000)`.

use crate::consts::*;
use crate::pcr::PcrSelectionList;
use crate::{Error, Reader, Result, Tpm2b};

/// Capacity reserved for a `TPMT_PUBLIC` body.  ECC P-256 is 88 bytes;
/// RSA-2048 would be ~314 — we leave room for either.
pub const MAX_PUBLIC_SIZE: usize = 384;
/// Capacity reserved for a `TPMS_ATTEST` body (a 2-PCR SHA-256 quote is 145 bytes).
pub const MAX_ATTEST_SIZE: usize = 512;
/// Capacity reserved for a `TPM2B_NAME` (`UINT16 alg || digest`, <= 66 bytes).
pub const MAX_NAME_SIZE: usize = 68;
/// Capacity reserved for a marshalled `TPMT_SIGNATURE` (ECDSA P-256 is 72 bytes).
pub const MAX_SIGNATURE_SIZE: usize = 80;

/// Parsed response header.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ResponseHeader {
    /// `TPM_ST` tag.
    pub tag: u16,
    /// `responseSize`.
    pub size: u32,
    /// `TPM_RC` response code (0 on success).
    pub rc: u32,
}

/// Parse and sanity-check the 10-byte header.  Does *not* fail on `rc != 0`.
pub fn header(rsp: &[u8]) -> Result<ResponseHeader> {
    let mut r = Reader::new(rsp);
    let tag = r.u16()?;
    let size = r.u32()?;
    let rc = r.u32()?;
    if tag != TPM_ST_NO_SESSIONS && tag != TPM_ST_SESSIONS {
        return Err(Error::BadTag(tag));
    }
    if size as usize != rsp.len() {
        return Err(if (size as usize) > rsp.len() {
            Error::Truncated
        } else {
            Error::SizeMismatch
        });
    }
    Ok(ResponseHeader { tag, size, rc })
}

/// Parse the header, fail with [`Error::TpmRc`] on a non-zero response code,
/// check the tag matches `sessions`, and return a reader positioned after the
/// header.
fn open(rsp: &[u8], sessions: bool) -> Result<Reader<'_>> {
    let h = header(rsp)?;
    if h.rc != TPM_RC_SUCCESS {
        return Err(Error::TpmRc(h.rc));
    }
    let want = if sessions {
        TPM_ST_SESSIONS
    } else {
        TPM_ST_NO_SESSIONS
    };
    if h.tag != want {
        return Err(Error::BadTag(h.tag));
    }
    let mut r = Reader::new(rsp);
    r.take(RESPONSE_HEADER_SIZE)?;
    Ok(r)
}

/// Consume one `TPMS_AUTH_RESPONSE` and require end of buffer.
fn password_auth_response_and_end(r: &mut Reader<'_>) -> Result<()> {
    let _nonce = r.take_2b()?;
    let _attrs = r.u8()?;
    let _hmac = r.take_2b()?;
    r.expect_end()
}

/// `TPM2_Startup` response: header only.  Returns `Err(TpmRc(0x100))`
/// (`TPM_RC_INITIALIZE`) if the TPM was already started — callers may treat
/// that as success.
pub fn startup(rsp: &[u8]) -> Result<()> {
    open(rsp, false)?.expect_end()
}

/// `TPM2_FlushContext` response: header only.
pub fn flush_context(rsp: &[u8]) -> Result<()> {
    open(rsp, false)?.expect_end()
}

/// `TPM2_PCR_Extend` response: `parameterSize = 0` then the auth response.
pub fn pcr_extend(rsp: &[u8]) -> Result<()> {
    let mut r = open(rsp, true)?;
    if r.u32()? != 0 {
        return Err(Error::SizeMismatch);
    }
    password_auth_response_and_end(&mut r)
}

/// Result of `TPM2_PCR_Read` (Part 3 §22.4.2).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct PcrReadResult {
    /// `pcrUpdateCounter`.
    pub update_counter: u32,
    /// `pcrSelectionOut` — the PCRs actually returned (may be fewer than asked).
    pub selection: PcrSelectionList,
    /// Number of digests in `digests`.
    pub count: usize,
    /// `pcrValues` — in selection order.
    pub digests: [Tpm2b<MAX_DIGEST_SIZE>; PCR_READ_MAX_DIGESTS],
}

impl PcrReadResult {
    /// The returned digests.
    pub fn values(&self) -> &[Tpm2b<MAX_DIGEST_SIZE>] {
        &self.digests[..self.count]
    }

    /// Copy digest `i` into a 32-byte array (fails unless it is 32 bytes long).
    pub fn sha256_value(&self, i: usize) -> Result<[u8; 32]> {
        let d = self
            .digests
            .get(i)
            .filter(|_| i < self.count)
            .ok_or(Error::Malformed)?;
        let mut out = [0u8; 32];
        if d.len() != 32 {
            return Err(Error::Malformed);
        }
        out.copy_from_slice(d.as_slice());
        Ok(out)
    }
}

/// `TPM2_PCR_Read` response:
///
/// ```text
/// header (8001)
/// UINT32 pcrUpdateCounter
/// TPML_PCR_SELECTION pcrSelectionOut
/// TPML_DIGEST pcrValues: UINT32 count, TPM2B_DIGEST digests[count]
/// ```
pub fn pcr_read(rsp: &[u8]) -> Result<PcrReadResult> {
    let mut r = open(rsp, false)?;
    let update_counter = r.u32()?;
    let selection = PcrSelectionList::unmarshal(&mut r)?;
    let count = r.u32()? as usize;
    if count > PCR_READ_MAX_DIGESTS {
        return Err(Error::TooLarge);
    }
    let mut digests = [Tpm2b::<MAX_DIGEST_SIZE>::empty(); PCR_READ_MAX_DIGESTS];
    for d in digests.iter_mut().take(count) {
        *d = r.read_2b()?;
    }
    r.expect_end()?;
    if selection.total_pcrs() != count {
        return Err(Error::SizeMismatch);
    }
    Ok(PcrReadResult {
        update_counter,
        selection,
        count,
        digests,
    })
}

/// Result of `TPM2_CreatePrimary` (Part 3 §24.1.2).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct CreatePrimaryResult {
    /// `objectHandle` — the transient handle (0x80xxxxxx).
    pub handle: u32,
    /// `outPublic.publicArea` — the raw `TPMT_PUBLIC` bytes (the `TPM2B_PUBLIC`
    /// is `UINT16 size || these bytes`).
    pub public: Tpm2b<MAX_PUBLIC_SIZE>,
    /// `creationHash`.
    pub creation_hash: Tpm2b<MAX_DIGEST_SIZE>,
    /// `name` — `UINT16 nameAlg || H_nameAlg(publicArea)`.
    pub name: Tpm2b<MAX_NAME_SIZE>,
}

/// `TPM2_CreatePrimary` response:
///
/// ```text
/// header (8002)
/// TPM_HANDLE objectHandle
/// UINT32 parameterSize
/// TPM2B_PUBLIC outPublic
/// TPM2B_CREATION_DATA creationData
/// TPM2B_DIGEST creationHash
/// TPMT_TK_CREATION creationTicket { TPM_ST tag=8021, TPMI_RH_HIERARCHY, TPM2B_DIGEST }
/// TPM2B_NAME name
/// TPMS_AUTH_RESPONSE
/// ```
pub fn create_primary(rsp: &[u8]) -> Result<CreatePrimaryResult> {
    let mut r = open(rsp, true)?;
    let handle = r.u32()?;
    let param_size = r.u32()? as usize;
    let start = r.position();
    let public = r.read_2b::<MAX_PUBLIC_SIZE>()?;
    let _creation_data = r.take_2b()?;
    let creation_hash = r.read_2b::<MAX_DIGEST_SIZE>()?;
    let tk_tag = r.u16()?;
    if tk_tag != TPM_ST_CREATION {
        return Err(Error::Malformed);
    }
    let _tk_hierarchy = r.u32()?;
    let _tk_digest = r.take_2b()?;
    let name = r.read_2b::<MAX_NAME_SIZE>()?;
    if r.position() - start != param_size {
        return Err(Error::SizeMismatch);
    }
    password_auth_response_and_end(&mut r)?;
    Ok(CreatePrimaryResult {
        handle,
        public,
        creation_hash,
        name,
    })
}

/// The interesting fields of an ECC `TPMT_PUBLIC` (Part 2 §12.2.4).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct EccPublic {
    /// `nameAlg`.
    pub name_alg: u16,
    /// `objectAttributes`.
    pub attributes: u32,
    /// `parameters.symmetric.algorithm`.
    pub symmetric: u16,
    /// `parameters.scheme.scheme` (`TPM_ALG_ECDSA` or `TPM_ALG_NULL`).
    pub scheme: u16,
    /// `parameters.scheme.details.hashAlg` (0 when `scheme == TPM_ALG_NULL`).
    pub scheme_hash: u16,
    /// `parameters.curveID`.
    pub curve: u16,
    /// `unique.x`, left-padded to 32 bytes.
    pub x: [u8; 32],
    /// `unique.y`, left-padded to 32 bytes.
    pub y: [u8; 32],
}

fn coord32(b: &[u8]) -> Result<[u8; 32]> {
    if b.len() > 32 {
        return Err(Error::Malformed);
    }
    let mut out = [0u8; 32];
    out[32 - b.len()..].copy_from_slice(b);
    Ok(out)
}

/// Parse an ECC `TPMT_PUBLIC` body (as returned in [`CreatePrimaryResult::public`]):
///
/// ```text
/// TPMI_ALG_PUBLIC type (must be 0023 ECC)
/// TPMI_ALG_HASH nameAlg
/// TPMA_OBJECT objectAttributes
/// TPM2B_DIGEST authPolicy
/// TPMS_ECC_PARMS { TPMT_SYM_DEF_OBJECT symmetric (alg [+ keyBits + mode if != NULL]),
///                  TPMT_ECC_SCHEME scheme (alg [+ hashAlg if != NULL]),
///                  TPMI_ECC_CURVE curveID,
///                  TPMT_KDF_SCHEME kdf (alg [+ hashAlg if != NULL]) }
/// TPMS_ECC_POINT unique { TPM2B_ECC_PARAMETER x, TPM2B_ECC_PARAMETER y }
/// ```
pub fn ecc_public(tpmt_public: &[u8]) -> Result<EccPublic> {
    let mut r = Reader::new(tpmt_public);
    let ty = r.u16()?;
    if ty != TPM_ALG_ECC {
        return Err(Error::Unsupported(ty));
    }
    let name_alg = r.u16()?;
    let attributes = r.u32()?;
    let _auth_policy = r.take_2b()?;
    let symmetric = r.u16()?;
    if symmetric != TPM_ALG_NULL {
        let _key_bits = r.u16()?;
        let _mode = r.u16()?;
    }
    let scheme = r.u16()?;
    let scheme_hash = if scheme != TPM_ALG_NULL { r.u16()? } else { 0 };
    let curve = r.u16()?;
    let kdf = r.u16()?;
    if kdf != TPM_ALG_NULL {
        let _kdf_hash = r.u16()?;
    }
    let x = coord32(r.take_2b()?)?;
    let y = coord32(r.take_2b()?)?;
    r.expect_end()?;
    Ok(EccPublic {
        name_alg,
        attributes,
        symmetric,
        scheme,
        scheme_hash,
        curve,
        x,
        y,
    })
}

/// `TPMS_SIGNATURE_ECDSA` (Part 2 §11.3.3) with P-256-sized scalars.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct EcdsaSignature {
    /// `hash` — the hash algorithm used over the attestation (`TPM_ALG_SHA256`).
    pub hash_alg: u16,
    /// `signatureR`, left-padded to 32 bytes.
    pub r: [u8; 32],
    /// `signatureS`, left-padded to 32 bytes.
    pub s: [u8; 32],
}

/// Result of `TPM2_Quote` (Part 3 §18.4.2).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct QuoteResult {
    /// `quoted.attestationData` — the raw `TPMS_ATTEST` bytes that are signed
    /// (the `TPM2B_ATTEST` is `UINT16 size || these bytes`).
    pub attest: Tpm2b<MAX_ATTEST_SIZE>,
    /// Decoded `signature`.
    pub signature: EcdsaSignature,
    /// The marshalled `TPMT_SIGNATURE` exactly as received (what
    /// `tpm2_quote -s` writes and `tpm2_checkquote -s` reads).
    pub signature_raw: Tpm2b<MAX_SIGNATURE_SIZE>,
}

/// `TPM2_Quote` response:
///
/// ```text
/// header (8002)
/// UINT32 parameterSize
/// TPM2B_ATTEST quoted
/// TPMT_SIGNATURE signature { TPMI_ALG_SIG_SCHEME sigAlg = 0018 (ECDSA),
///                            TPMS_SIGNATURE_ECDSA { TPMI_ALG_HASH hash,
///                                                   TPM2B_ECC_PARAMETER r,
///                                                   TPM2B_ECC_PARAMETER s } }
/// TPMS_AUTH_RESPONSE
/// ```
pub fn quote(rsp: &[u8]) -> Result<QuoteResult> {
    let mut r = open(rsp, true)?;
    let param_size = r.u32()? as usize;
    let start = r.position();
    let attest = r.read_2b::<MAX_ATTEST_SIZE>()?;
    let sig_start = r.position();
    let sig_alg = r.u16()?;
    if sig_alg != TPM_ALG_ECDSA {
        return Err(Error::Unsupported(sig_alg));
    }
    let hash_alg = r.u16()?;
    let rr = coord32(r.take_2b()?)?;
    let ss = coord32(r.take_2b()?)?;
    let sig_end = r.position();
    if sig_end - start != param_size {
        return Err(Error::SizeMismatch);
    }
    let signature_raw = Tpm2b::from_slice(&rsp[sig_start..sig_end])?;
    password_auth_response_and_end(&mut r)?;
    Ok(QuoteResult {
        attest,
        signature: EcdsaSignature {
            hash_alg,
            r: rr,
            s: ss,
        },
        signature_raw,
    })
}

/// `TPMS_CLOCK_INFO` (Part 2 §10.11.1).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ClockInfo {
    /// `clock` (ms).
    pub clock: u64,
    /// `resetCount`.
    pub reset_count: u32,
    /// `restartCount`.
    pub restart_count: u32,
    /// `safe`.
    pub safe: bool,
}

/// `TPMS_QUOTE_INFO` (Part 2 §10.12.1).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct QuoteInfo {
    /// `pcrSelect` — the PCRs covered by the quote.
    pub pcr_select: PcrSelectionList,
    /// `pcrDigest` — hash of the selected PCR values in selection order.
    pub pcr_digest: Tpm2b<MAX_DIGEST_SIZE>,
}

/// Parsed `TPMS_ATTEST` for a quote (Part 2 §10.12.8).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Attest {
    /// `magic` — must be [`TPM_GENERATED_VALUE`] (checked).
    pub magic: u32,
    /// `type` — must be [`TPM_ST_ATTEST_QUOTE`] (checked).
    pub attest_type: u16,
    /// `qualifiedSigner` — qualified name of the signing key.
    pub qualified_signer: Tpm2b<MAX_NAME_SIZE>,
    /// `extraData` — echoes the `qualifyingData` passed to `TPM2_Quote`.
    pub extra_data: Tpm2b<MAX_DIGEST_SIZE>,
    /// `clockInfo`.
    pub clock_info: ClockInfo,
    /// `firmwareVersion`.
    pub firmware_version: u64,
    /// `attested.quote`.
    pub quote: QuoteInfo,
}

/// Parse a `TPMS_ATTEST` produced by `TPM2_Quote`:
///
/// ```text
/// TPM_GENERATED magic            = ff544347
/// TPMI_ST_ATTEST type            = 8018 (TPM_ST_ATTEST_QUOTE)
/// TPM2B_NAME qualifiedSigner
/// TPM2B_DATA extraData
/// TPMS_CLOCK_INFO clockInfo      { UINT64 clock, UINT32 resetCount, UINT32 restartCount, TPMI_YES_NO safe }
/// UINT64 firmwareVersion
/// TPMS_QUOTE_INFO attested.quote { TPML_PCR_SELECTION pcrSelect, TPM2B_DIGEST pcrDigest }
/// ```
pub fn attest(bytes: &[u8]) -> Result<Attest> {
    let mut r = Reader::new(bytes);
    let magic = r.u32()?;
    if magic != TPM_GENERATED_VALUE {
        return Err(Error::Malformed);
    }
    let attest_type = r.u16()?;
    if attest_type != TPM_ST_ATTEST_QUOTE {
        return Err(Error::Unsupported(attest_type));
    }
    let qualified_signer = r.read_2b()?;
    let extra_data = r.read_2b()?;
    let clock = r.u64()?;
    let reset_count = r.u32()?;
    let restart_count = r.u32()?;
    let safe = match r.u8()? {
        0 => false,
        1 => true,
        _ => return Err(Error::Malformed),
    };
    let firmware_version = r.u64()?;
    let pcr_select = PcrSelectionList::unmarshal(&mut r)?;
    let pcr_digest = r.read_2b()?;
    r.expect_end()?;
    Ok(Attest {
        magic,
        attest_type,
        qualified_signer,
        extra_data,
        clock_info: ClockInfo {
            clock,
            reset_count,
            restart_count,
            safe,
        },
        firmware_version,
        quote: QuoteInfo {
            pcr_select,
            pcr_digest,
        },
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::pcr::PcrSelection;
    use crate::Writer;

    fn rsp(tag: u16, rc: u32, body: &[u8]) -> ([u8; 1024], usize) {
        let mut b = [0u8; 1024];
        let n = {
            let mut w = Writer::new(&mut b);
            w.put_u16(tag).unwrap();
            w.put_u32((10 + body.len()) as u32).unwrap();
            w.put_u32(rc).unwrap();
            w.put_bytes(body).unwrap();
            w.finish()
        };
        (b, n)
    }

    const AUTH_RSP: [u8; 5] = [0, 0, 0x01, 0, 0];

    #[test]
    fn error_code_is_reported_not_parsed() {
        // TPM_RC_FAILURE = 0x101; error responses carry tag 8001 and are 10 bytes.
        let (b, n) = rsp(TPM_ST_NO_SESSIONS, 0x101, &[]);
        assert_eq!(pcr_read(&b[..n]), Err(Error::TpmRc(0x101)));
        assert_eq!(create_primary(&b[..n]), Err(Error::TpmRc(0x101)));
        assert_eq!(quote(&b[..n]), Err(Error::TpmRc(0x101)));
        assert_eq!(pcr_extend(&b[..n]), Err(Error::TpmRc(0x101)));
        assert_eq!(flush_context(&b[..n]), Err(Error::TpmRc(0x101)));
        // TPM_RC_INITIALIZE on a second Startup
        let (b, n) = rsp(TPM_ST_NO_SESSIONS, TPM_RC_INITIALIZE, &[]);
        assert_eq!(startup(&b[..n]), Err(Error::TpmRc(0x100)));
    }

    #[test]
    fn header_checks() {
        assert_eq!(header(&[0x80, 0x01, 0, 0]), Err(Error::Truncated));
        // size says 12 but only 10 present
        assert_eq!(
            header(&[0x80, 0x01, 0, 0, 0, 12, 0, 0, 0, 0]),
            Err(Error::Truncated)
        );
        // size says 10 but 11 present
        assert_eq!(
            header(&[0x80, 0x01, 0, 0, 0, 10, 0, 0, 0, 0, 0]),
            Err(Error::SizeMismatch)
        );
        assert_eq!(
            header(&[0x12, 0x34, 0, 0, 0, 10, 0, 0, 0, 0]),
            Err(Error::BadTag(0x1234))
        );
        let ok = header(&[0x80, 0x01, 0, 0, 0, 10, 0, 0, 0, 0]).unwrap();
        assert_eq!(
            ok,
            ResponseHeader {
                tag: 0x8001,
                size: 10,
                rc: 0
            }
        );
        assert!(startup(&[0x80, 0x01, 0, 0, 0, 10, 0, 0, 0, 0]).is_ok());
    }

    #[test]
    fn wrong_tag_for_command_is_rejected() {
        // PCR_Read must come back with 8001; a sessions tag is wrong.
        let (b, n) = rsp(TPM_ST_SESSIONS, 0, &[0, 0, 0, 1]);
        assert_eq!(pcr_read(&b[..n]), Err(Error::BadTag(0x8002)));
    }

    #[test]
    fn pcr_read_parses_two_sha256_values() {
        let mut body = [0u8; 256];
        let n = {
            let mut w = Writer::new(&mut body);
            w.put_u32(7).unwrap(); // pcrUpdateCounter
            PcrSelectionList::single(PcrSelection::sha256(&[4, 12]))
                .marshal(&mut w)
                .unwrap();
            w.put_u32(2).unwrap();
            w.put_2b(&[0xAA; 32]).unwrap();
            w.put_2b(&[0xBB; 32]).unwrap();
            w.finish()
        };
        let (b, len) = rsp(TPM_ST_NO_SESSIONS, 0, &body[..n]);
        let res = pcr_read(&b[..len]).unwrap();
        assert_eq!(res.update_counter, 7);
        assert_eq!(res.count, 2);
        assert_eq!(res.sha256_value(0).unwrap(), [0xAA; 32]);
        assert_eq!(res.sha256_value(1).unwrap(), [0xBB; 32]);
        assert!(res.sha256_value(2).is_err());
        assert_eq!(res.selection.as_slice()[0].count(), 2);
        // truncated: drop the last byte
        assert_eq!(pcr_read(&b[..len - 1]), Err(Error::Truncated));
    }

    #[test]
    fn pcr_extend_response() {
        let mut body = [0u8; 16];
        body[..4].copy_from_slice(&[0, 0, 0, 0]);
        body[4..9].copy_from_slice(&AUTH_RSP);
        let (b, n) = rsp(TPM_ST_SESSIONS, 0, &body[..9]);
        assert!(pcr_extend(&b[..n]).is_ok());
    }

    /// Build an 88-byte ECC P-256 TPMT_PUBLIC with the given point.
    fn ecc_tpmt_public(x: &[u8; 32], y: &[u8; 32]) -> [u8; 88] {
        let mut p = [0u8; 88];
        p[..20].copy_from_slice(&crate::cmd::ECC_P256_SIGNING_TEMPLATE[..20]);
        p[20..22].copy_from_slice(&[0, 32]);
        p[22..54].copy_from_slice(x);
        p[54..56].copy_from_slice(&[0, 32]);
        p[56..88].copy_from_slice(y);
        p
    }

    #[test]
    fn ecc_public_parses_point() {
        let x: [u8; 32] = core::array::from_fn(|i| i as u8);
        let y: [u8; 32] = core::array::from_fn(|i| 0xff - i as u8);
        let p = ecc_tpmt_public(&x, &y);
        let e = ecc_public(&p).unwrap();
        assert_eq!(e.name_alg, TPM_ALG_SHA256);
        assert_eq!(e.attributes, SIGNING_KEY_ATTRIBUTES);
        assert_eq!(e.symmetric, TPM_ALG_NULL);
        assert_eq!(e.scheme, TPM_ALG_ECDSA);
        assert_eq!(e.scheme_hash, TPM_ALG_SHA256);
        assert_eq!(e.curve, TPM_ECC_NIST_P256);
        assert_eq!(e.x, x);
        assert_eq!(e.y, y);
        // RSA type is rejected
        let mut rsa = p;
        rsa[1] = 0x01;
        assert_eq!(ecc_public(&rsa), Err(Error::Unsupported(TPM_ALG_RSA)));
    }

    #[test]
    fn create_primary_response() {
        let x = [0x11u8; 32];
        let y = [0x22u8; 32];
        let pubarea = ecc_tpmt_public(&x, &y);
        let mut params = [0u8; 512];
        let plen = {
            let mut w = Writer::new(&mut params);
            w.put_2b(&pubarea).unwrap(); // outPublic
            w.put_2b(&[0x33; 40]).unwrap(); // creationData (opaque here)
            w.put_2b(&[0x44; 32]).unwrap(); // creationHash
            w.put_u16(TPM_ST_CREATION).unwrap(); // ticket
            w.put_u32(TPM_RH_OWNER).unwrap();
            w.put_2b(&[0x55; 32]).unwrap();
            w.put_2b(&[0x00, 0x0B, 0x66, 0x66]).unwrap(); // name (short, fine for the test)
            w.finish()
        };
        let mut body = [0u8; 600];
        let blen = {
            let mut w = Writer::new(&mut body);
            w.put_u32(0x8000_0002).unwrap(); // objectHandle
            w.put_u32(plen as u32).unwrap(); // parameterSize
            w.put_bytes(&params[..plen]).unwrap();
            w.put_bytes(&AUTH_RSP).unwrap();
            w.finish()
        };
        let (b, n) = rsp(TPM_ST_SESSIONS, 0, &body[..blen]);
        let res = create_primary(&b[..n]).unwrap();
        assert_eq!(res.handle, 0x8000_0002);
        assert_eq!(res.public.as_slice(), &pubarea[..]);
        assert_eq!(res.creation_hash.as_slice(), &[0x44; 32]);
        assert_eq!(res.name.as_slice(), &[0x00, 0x0B, 0x66, 0x66]);
        assert_eq!(ecc_public(res.public.as_slice()).unwrap().x, x);

        // wrong parameterSize is caught
        let mut bad = b;
        bad[14..18].copy_from_slice(&((plen + 1) as u32).to_be_bytes());
        assert_eq!(create_primary(&bad[..n]), Err(Error::SizeMismatch));
    }

    fn sample_attest(extra: &[u8], pcr_digest: &[u8; 32]) -> ([u8; 256], usize) {
        let mut a = [0u8; 256];
        let n = {
            let mut w = Writer::new(&mut a);
            w.put_u32(TPM_GENERATED_VALUE).unwrap();
            w.put_u16(TPM_ST_ATTEST_QUOTE).unwrap();
            // qualifiedSigner: UINT16 nameAlg || 32-byte digest = 34 bytes (realistic size)
            let mut qn = [0x77u8; 34];
            qn[0] = 0x00;
            qn[1] = 0x0B;
            w.put_2b(&qn).unwrap();
            w.put_2b(extra).unwrap();
            w.put_u64(123_456).unwrap(); // clock
            w.put_u32(3).unwrap(); // resetCount
            w.put_u32(4).unwrap(); // restartCount
            w.put_u8(1).unwrap(); // safe
            w.put_u64(0x2020_0000_0000_0001).unwrap(); // firmwareVersion
            PcrSelectionList::single(PcrSelection::sha256(&[4, 12]))
                .marshal(&mut w)
                .unwrap();
            w.put_2b(pcr_digest).unwrap();
            w.finish()
        };
        (a, n)
    }

    #[test]
    fn attest_parses_and_validates() {
        let extra = [0xEEu8; 32];
        let pd = [0xDDu8; 32];
        let (a, n) = sample_attest(&extra, &pd);
        assert_eq!(n, 145);
        let at = attest(&a[..n]).unwrap();
        assert_eq!(at.magic, TPM_GENERATED_VALUE);
        assert_eq!(at.attest_type, TPM_ST_ATTEST_QUOTE);
        assert_eq!(at.extra_data.as_slice(), &extra);
        assert_eq!(at.quote.pcr_digest.as_slice(), &pd);
        assert_eq!(
            at.clock_info,
            ClockInfo {
                clock: 123_456,
                reset_count: 3,
                restart_count: 4,
                safe: true
            }
        );
        assert_eq!(at.firmware_version, 0x2020_0000_0000_0001);
        assert!(at.quote.pcr_select.as_slice()[0].is_selected(12));

        let mut bad_magic = a;
        bad_magic[0] = 0x00;
        assert_eq!(attest(&bad_magic[..n]), Err(Error::Malformed));
        let mut bad_type = a;
        bad_type[5] = 0x17; // TPM_ST_ATTEST_CERTIFY
        assert_eq!(attest(&bad_type[..n]), Err(Error::Unsupported(0x8017)));
        assert_eq!(attest(&a[..n - 1]), Err(Error::Truncated));
    }

    #[test]
    fn quote_response() {
        let (a, alen) = sample_attest(&[0xEE; 32], &[0xDD; 32]);
        let r = [0x9Au8; 32];
        let s = [0x3Cu8; 32];
        let mut params = [0u8; 512];
        let plen = {
            let mut w = Writer::new(&mut params);
            w.put_2b(&a[..alen]).unwrap(); // quoted
            w.put_u16(TPM_ALG_ECDSA).unwrap();
            w.put_u16(TPM_ALG_SHA256).unwrap();
            w.put_2b(&r).unwrap();
            w.put_2b(&s).unwrap();
            w.finish()
        };
        let mut body = [0u8; 600];
        let blen = {
            let mut w = Writer::new(&mut body);
            w.put_u32(plen as u32).unwrap();
            w.put_bytes(&params[..plen]).unwrap();
            w.put_bytes(&AUTH_RSP).unwrap();
            w.finish()
        };
        let (b, n) = rsp(TPM_ST_SESSIONS, 0, &body[..blen]);
        let q = quote(&b[..n]).unwrap();
        assert_eq!(q.attest.as_slice(), &a[..alen]);
        assert_eq!(q.signature.hash_alg, TPM_ALG_SHA256);
        assert_eq!(q.signature.r, r);
        assert_eq!(q.signature.s, s);
        assert_eq!(q.signature_raw.len(), 72);
        assert_eq!(&q.signature_raw.as_slice()[..4], &[0, 0x18, 0, 0x0b]);
        assert_eq!(q.signature_raw.as_slice(), &params[2 + alen..plen]);

        // an RSA signature is rejected as unsupported
        let mut rsa = b;
        rsa[10 + 4 + 2 + alen + 1] = 0x14; // TPM_ALG_RSASSA
        assert_eq!(quote(&rsa[..n]), Err(Error::Unsupported(0x0014)));
    }
}
