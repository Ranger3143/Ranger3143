//! Command builders.  Every function writes a complete command into `out`
//! and returns the number of bytes written (= `commandSize`).
//!
//! Common header (Part 1 §18.9 / Part 3 §5.2 "Command Header"):
//!
//! ```text
//! offset  size  field
//! 0       2     TPMI_ST_COMMAND_TAG tag     (0x8001 no sessions / 0x8002 sessions)
//! 2       4     UINT32 commandSize           (total bytes incl. header)
//! 6       4     TPM_CC commandCode
//! 10      ...   handles, [authorizationSize + authorization area], parameters
//! ```
//!
//! Password authorization area (Part 1 §19.4 / Part 3 §5.3 "Authorization
//! Area"), one `TPMS_AUTH_COMMAND` (Part 2 §10.13.2) for the `TPM_RS_PW`
//! pseudo-session with an empty password:
//!
//! ```text
//! UINT32 authorizationSize          = 9
//! TPMI_SH_AUTH_SESSION sessionHandle = 0x40000009 (TPM_RS_PW)
//! TPM2B_NONCE nonce                  = 0000        (empty)
//! TPMA_SESSION sessionAttributes     = 01          (continueSession)
//! TPM2B_AUTH hmac                    = 0000        (empty password)
//! ```

use crate::consts::*;
use crate::pcr::PcrSelectionList;
use crate::{Error, Result, Writer};

/// Exact byte count of `TPM2_Startup`.
pub const STARTUP_LEN: usize = 12;
/// Exact byte count of `TPM2_FlushContext`.
pub const FLUSH_CONTEXT_LEN: usize = 14;
/// Exact byte count of `TPM2_PCR_Extend` for one SHA-256 digest.
pub const PCR_EXTEND_SHA256_LEN: usize = 65;
/// Exact byte count of `TPM2_CreatePrimary` with the fixed ECC template.
pub const CREATE_PRIMARY_ECC_P256_LEN: usize = 65;

/// Signature scheme passed to `TPM2_Quote` as `inScheme` (`TPMT_SIG_SCHEME`,
/// Part 2 §11.2.1.5).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SigScheme {
    /// `TPM_ALG_NULL` — use the scheme baked into the signing key.  Marshals as
    /// a bare `UINT16 0x0010` (no `details`).
    Null,
    /// `TPM_ALG_ECDSA` with `TPMS_SCHEME_HASH hashAlg = TPM_ALG_SHA256`.
    /// Marshals as `0018 000B`.
    EcdsaSha256,
}

impl SigScheme {
    fn marshal(self, w: &mut Writer<'_>) -> Result<()> {
        match self {
            SigScheme::Null => w.put_u16(TPM_ALG_NULL),
            SigScheme::EcdsaSha256 => {
                w.put_u16(TPM_ALG_ECDSA)?;
                w.put_u16(TPM_ALG_SHA256)
            }
        }
    }
}

fn begin<'a>(out: &'a mut [u8], tag: u16, cc: u32) -> Result<Writer<'a>> {
    let mut w = Writer::new(out);
    w.put_u16(tag)?;
    w.put_u32(0)?; // commandSize, patched in `end`
    w.put_u32(cc)?;
    Ok(w)
}

fn end(mut w: Writer<'_>) -> Result<usize> {
    let n = w.position();
    w.patch_u32(2, u32::try_from(n).map_err(|_| Error::TooLarge)?)?;
    Ok(w.finish())
}

/// Write `authorizationSize` + one password (`TPM_RS_PW`) `TPMS_AUTH_COMMAND`.
pub fn password_auth_area(w: &mut Writer<'_>, password: &[u8]) -> Result<()> {
    let auth_len = 4 + 2 + 1 + 2 + password.len();
    w.put_u32(u32::try_from(auth_len).map_err(|_| Error::TooLarge)?)?;
    w.put_u32(TPM_RS_PW)?;
    w.put_u16(0)?; // nonce
    w.put_u8(TPMA_SESSION_CONTINUE_SESSION)?;
    w.put_2b(password)
}

/// `TPM2_Startup` (Part 3 §9.3).
///
/// ```text
/// 8001 | 0000000c | 00000144 | TPM_SU startupType (UINT16)
/// ```
pub fn startup(out: &mut [u8], startup_type: u16) -> Result<usize> {
    let mut w = begin(out, TPM_ST_NO_SESSIONS, TPM_CC_STARTUP)?;
    w.put_u16(startup_type)?;
    end(w)
}

/// `TPM2_PCR_Read` (Part 3 §22.4).
///
/// ```text
/// 8001 | size | 0000017e | TPML_PCR_SELECTION pcrSelectionIn
/// ```
/// For `sha256:4,12`: `8001 00000014 0000017e 00000001 000b 03 10 10 00`.
pub fn pcr_read(out: &mut [u8], selection: &PcrSelectionList) -> Result<usize> {
    let mut w = begin(out, TPM_ST_NO_SESSIONS, TPM_CC_PCR_READ)?;
    selection.marshal(&mut w)?;
    end(w)
}

/// `TPM2_PCR_Extend` (Part 3 §22.2) of one SHA-256 digest into `pcr_index`
/// with an empty password session.
///
/// ```text
/// 8002 | size=0x41 | 00000182
/// TPMI_DH_PCR pcrHandle (UINT32 = pcr index)
/// authorizationSize=00000009, auth area 40000009 0000 01 0000
/// TPML_DIGEST_VALUES digests: UINT32 count=1,
///     TPMT_HA { TPMI_ALG_HASH hashAlg=000b, BYTE digest[32] }
/// ```
pub fn pcr_extend_sha256(out: &mut [u8], pcr_index: u32, digest: &[u8; 32]) -> Result<usize> {
    let mut w = begin(out, TPM_ST_SESSIONS, TPM_CC_PCR_EXTEND)?;
    w.put_u32(pcr_index)?;
    password_auth_area(&mut w, &[])?;
    w.put_u32(1)?; // TPML_DIGEST_VALUES.count
    w.put_u16(TPM_ALG_SHA256)?; // TPMT_HA.hashAlg
    w.put_bytes(digest)?; // TPMT_HA.digest (TPMU_HA, sized by hashAlg)
    end(w)
}

/// The fixed `TPMT_PUBLIC` template (Part 2 §12.2.4) used by
/// [`create_primary_ecc_p256`]: ECC P-256, ECDSA/SHA-256, restricted signing
/// key, `fixedTPM | fixedParent | sensitiveDataOrigin | userWithAuth |
/// restricted | sign`, empty `authPolicy`, empty `unique` point.
///
/// ```text
/// 0023        TPMI_ALG_PUBLIC   type         = TPM_ALG_ECC
/// 000b        TPMI_ALG_HASH     nameAlg      = TPM_ALG_SHA256
/// 00050072    TPMA_OBJECT       objectAttributes
/// 0000        TPM2B_DIGEST      authPolicy   (empty)
/// -- TPMS_ECC_PARMS parameters (Part 2 §12.2.3.6) --
/// 0010        TPMT_SYM_DEF_OBJECT symmetric  = TPM_ALG_NULL (no keyBits/mode)
/// 0018 000b   TPMT_ECC_SCHEME     scheme     = ECDSA, hashAlg SHA256
/// 0003        TPMI_ECC_CURVE      curveID    = TPM_ECC_NIST_P256
/// 0010        TPMT_KDF_SCHEME     kdf        = TPM_ALG_NULL
/// -- TPMS_ECC_POINT unique --
/// 0000        TPM2B_ECC_PARAMETER x (empty)
/// 0000        TPM2B_ECC_PARAMETER y (empty)
/// ```
pub const ECC_P256_SIGNING_TEMPLATE: [u8; 24] = [
    0x00, 0x23, // type = ECC
    0x00, 0x0B, // nameAlg = SHA256
    0x00, 0x05, 0x00, 0x72, // objectAttributes
    0x00, 0x00, // authPolicy
    0x00, 0x10, // symmetric = NULL
    0x00, 0x18, 0x00, 0x0B, // scheme = ECDSA / SHA256
    0x00, 0x03, // curveID = NIST P-256
    0x00, 0x10, // kdf = NULL
    0x00, 0x00, // unique.x
    0x00, 0x00, // unique.y
];

/// Write the `TPMT_PUBLIC` body of [`ECC_P256_SIGNING_TEMPLATE`] field by field
/// (kept separate so the unit test can compare it to the hand-written bytes).
pub fn write_ecc_p256_signing_template(w: &mut Writer<'_>) -> Result<()> {
    w.put_u16(TPM_ALG_ECC)?;
    w.put_u16(TPM_ALG_SHA256)?;
    w.put_u32(SIGNING_KEY_ATTRIBUTES)?;
    w.put_2b(&[])?; // authPolicy
    w.put_u16(TPM_ALG_NULL)?; // symmetric
    w.put_u16(TPM_ALG_ECDSA)?; // scheme.scheme
    w.put_u16(TPM_ALG_SHA256)?; // scheme.details.hashAlg
    w.put_u16(TPM_ECC_NIST_P256)?; // curveID
    w.put_u16(TPM_ALG_NULL)?; // kdf
    w.put_2b(&[])?; // unique.x
    w.put_2b(&[]) // unique.y
}

/// `TPM2_CreatePrimary` (Part 3 §24.1) under `hierarchy` (normally
/// [`TPM_RH_OWNER`]) with the fixed ECC P-256 signing template and empty
/// hierarchy password.
///
/// ```text
/// 8002 | size=0x41 | 00000131
/// TPMI_RH_HIERARCHY primaryHandle          40000001
/// authorizationSize + password auth area   00000009 40000009 0000 01 0000
/// TPM2B_SENSITIVE_CREATE inSensitive       0004 { TPM2B_AUTH userAuth 0000, TPM2B_SENSITIVE_DATA data 0000 }
/// TPM2B_PUBLIC inPublic                    0018 + ECC_P256_SIGNING_TEMPLATE (24 bytes)
/// TPM2B_DATA outsideInfo                   0000
/// TPML_PCR_SELECTION creationPCR           00000000
/// ```
pub fn create_primary_ecc_p256(out: &mut [u8], hierarchy: u32) -> Result<usize> {
    let mut w = begin(out, TPM_ST_SESSIONS, TPM_CC_CREATE_PRIMARY)?;
    w.put_u32(hierarchy)?;
    password_auth_area(&mut w, &[])?;
    // TPM2B_SENSITIVE_CREATE
    w.put_u16(4)?;
    w.put_2b(&[])?; // userAuth
    w.put_2b(&[])?; // data
                    // TPM2B_PUBLIC
    w.put_u16(ECC_P256_SIGNING_TEMPLATE.len() as u16)?;
    write_ecc_p256_signing_template(&mut w)?;
    // outsideInfo, creationPCR
    w.put_2b(&[])?;
    w.put_u32(0)?;
    end(w)
}

/// `TPM2_Quote` (Part 3 §18.4) with an empty password session on `sign_handle`.
///
/// ```text
/// 8002 | size | 00000158
/// TPMI_DH_OBJECT signHandle
/// authorizationSize + password auth area   00000009 40000009 0000 01 0000
/// TPM2B_DATA qualifyingData                 UINT16 size + bytes (<= 64)
/// TPMT_SIG_SCHEME inScheme                  0010  |  0018 000b
/// TPML_PCR_SELECTION PCRselect
/// ```
pub fn quote(
    out: &mut [u8],
    sign_handle: u32,
    qualifying_data: &[u8],
    scheme: SigScheme,
    selection: &PcrSelectionList,
) -> Result<usize> {
    if qualifying_data.len() > MAX_DIGEST_SIZE {
        // TPM2B_DATA is bounded by sizeof(TPMT_HA) (Part 2 §10.4.3).
        return Err(Error::TooLarge);
    }
    let mut w = begin(out, TPM_ST_SESSIONS, TPM_CC_QUOTE)?;
    w.put_u32(sign_handle)?;
    password_auth_area(&mut w, &[])?;
    w.put_2b(qualifying_data)?;
    scheme.marshal(&mut w)?;
    selection.marshal(&mut w)?;
    end(w)
}

/// `TPM2_FlushContext` (Part 3 §28.4).
///
/// ```text
/// 8001 | 0000000e | 00000165 | TPMI_DH_CONTEXT flushHandle (UINT32)
/// ```
pub fn flush_context(out: &mut [u8], handle: u32) -> Result<usize> {
    let mut w = begin(out, TPM_ST_NO_SESSIONS, TPM_CC_FLUSH_CONTEXT)?;
    w.put_u32(handle)?;
    end(w)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::pcr::PcrSelection;

    const PW_AUTH: [u8; 13] = [
        0x00, 0x00, 0x00, 0x09, // authorizationSize
        0x40, 0x00, 0x00, 0x09, // TPM_RS_PW
        0x00, 0x00, // nonce
        0x01, // continueSession
        0x00, 0x00, // hmac
    ];

    #[test]
    fn startup_clear_bytes() {
        let mut b = [0u8; 64];
        let n = startup(&mut b, TPM_SU_CLEAR).unwrap();
        assert_eq!(n, STARTUP_LEN);
        assert_eq!(
            &b[..n],
            &[0x80, 0x01, 0, 0, 0, 0x0c, 0, 0, 0x01, 0x44, 0x00, 0x00]
        );
    }

    #[test]
    fn flush_context_bytes() {
        let mut b = [0u8; 64];
        let n = flush_context(&mut b, 0x8000_0001).unwrap();
        assert_eq!(n, FLUSH_CONTEXT_LEN);
        assert_eq!(
            &b[..n],
            &[0x80, 0x01, 0, 0, 0, 0x0e, 0, 0, 0x01, 0x65, 0x80, 0x00, 0x00, 0x01]
        );
    }

    #[test]
    fn pcr_read_sha256_4_12_bytes() {
        let mut b = [0u8; 64];
        let sel = PcrSelectionList::single(PcrSelection::sha256(&[4, 12]));
        let n = pcr_read(&mut b, &sel).unwrap();
        assert_eq!(
            &b[..n],
            &[
                0x80, 0x01, 0x00, 0x00, 0x00, 0x14, 0x00, 0x00, 0x01, 0x7e, // header
                0x00, 0x00, 0x00, 0x01, // count
                0x00, 0x0b, 0x03, 0x10, 0x10, 0x00 // sha256, 3, bitmap
            ]
        );
    }

    #[test]
    fn pcr_extend_bytes() {
        let mut b = [0u8; 128];
        let d: [u8; 32] = core::array::from_fn(|i| i as u8);
        let n = pcr_extend_sha256(&mut b, 12, &d).unwrap();
        assert_eq!(n, PCR_EXTEND_SHA256_LEN);
        let mut want = [0u8; PCR_EXTEND_SHA256_LEN];
        want[..10].copy_from_slice(&[0x80, 0x02, 0, 0, 0, 0x41, 0, 0, 0x01, 0x82]);
        want[10..14].copy_from_slice(&[0, 0, 0, 12]);
        want[14..27].copy_from_slice(&PW_AUTH);
        want[27..31].copy_from_slice(&[0, 0, 0, 1]);
        want[31..33].copy_from_slice(&[0x00, 0x0b]);
        want[33..65].copy_from_slice(&d);
        assert_eq!(&b[..n], &want[..]);
    }

    #[test]
    fn template_matches_handwritten_bytes() {
        let mut b = [0u8; 64];
        let mut w = Writer::new(&mut b);
        write_ecc_p256_signing_template(&mut w).unwrap();
        let n = w.finish();
        assert_eq!(&b[..n], &ECC_P256_SIGNING_TEMPLATE[..]);
        assert_eq!(SIGNING_KEY_ATTRIBUTES, 0x0005_0072);
    }

    #[test]
    fn create_primary_bytes() {
        let mut b = [0u8; 128];
        let n = create_primary_ecc_p256(&mut b, TPM_RH_OWNER).unwrap();
        assert_eq!(n, CREATE_PRIMARY_ECC_P256_LEN);
        let mut want = [0u8; CREATE_PRIMARY_ECC_P256_LEN];
        want[..10].copy_from_slice(&[0x80, 0x02, 0, 0, 0, 0x41, 0, 0, 0x01, 0x31]);
        want[10..14].copy_from_slice(&[0x40, 0, 0, 0x01]); // TPM_RH_OWNER
        want[14..27].copy_from_slice(&PW_AUTH);
        want[27..33].copy_from_slice(&[0, 4, 0, 0, 0, 0]); // inSensitive
        want[33..35].copy_from_slice(&[0, 0x18]); // inPublic.size
        want[35..59].copy_from_slice(&ECC_P256_SIGNING_TEMPLATE);
        want[59..61].copy_from_slice(&[0, 0]); // outsideInfo
        want[61..65].copy_from_slice(&[0, 0, 0, 0]); // creationPCR
        assert_eq!(&b[..n], &want[..]);
    }

    #[test]
    fn quote_bytes_null_scheme() {
        let mut b = [0u8; 128];
        let qd = [0xA5u8; 32];
        let sel = PcrSelectionList::single(PcrSelection::sha256(&[4, 12]));
        let n = quote(&mut b, 0x8000_0000, &qd, SigScheme::Null, &sel).unwrap();
        assert_eq!(n, 73);
        let mut want = [0u8; 73];
        want[..10].copy_from_slice(&[0x80, 0x02, 0, 0, 0, 0x49, 0, 0, 0x01, 0x58]);
        want[10..14].copy_from_slice(&[0x80, 0, 0, 0]);
        want[14..27].copy_from_slice(&PW_AUTH);
        want[27..29].copy_from_slice(&[0, 0x20]);
        want[29..61].copy_from_slice(&qd);
        want[61..63].copy_from_slice(&[0, 0x10]); // TPM_ALG_NULL
        want[63..73].copy_from_slice(&[0, 0, 0, 1, 0, 0x0b, 3, 0x10, 0x10, 0]);
        assert_eq!(&b[..n], &want[..]);
    }

    #[test]
    fn quote_bytes_ecdsa_scheme() {
        let mut b = [0u8; 128];
        let qd = [0u8; 32];
        let sel = PcrSelectionList::single(PcrSelection::sha256(&[4, 12]));
        let n = quote(&mut b, 0x8000_0000, &qd, SigScheme::EcdsaSha256, &sel).unwrap();
        assert_eq!(n, 75);
        assert_eq!(&b[2..6], &[0, 0, 0, 0x4b]);
        assert_eq!(&b[61..65], &[0, 0x18, 0, 0x0b]);
    }

    #[test]
    fn quote_rejects_oversized_qualifying_data() {
        let mut b = [0u8; 256];
        let sel = PcrSelectionList::single(PcrSelection::sha256(&[4]));
        assert_eq!(
            quote(&mut b, 0x8000_0000, &[0u8; 65], SigScheme::Null, &sel),
            Err(Error::TooLarge)
        );
    }

    #[test]
    fn small_buffer_is_rejected_cleanly() {
        let mut b = [0u8; 20];
        assert_eq!(
            create_primary_ecc_p256(&mut b, TPM_RH_OWNER),
            Err(Error::BufferTooSmall)
        );
    }
}
