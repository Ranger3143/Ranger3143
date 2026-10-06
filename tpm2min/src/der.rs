//! Tiny DER helpers so the TPM's raw ECC material can be handed to OpenSSL:
//!
//! * [`p256_spki`]: `SubjectPublicKeyInfo` (RFC 5480) for an uncompressed
//!   P-256 point — `openssl ec -pubin -inform DER` / `-verify pub.pem`.
//! * [`ecdsa_signature`]: `ECDSA-Sig-Value ::= SEQUENCE { r INTEGER, s INTEGER }`
//!   (RFC 3279 §2.2.3) from the TPM's fixed-width `r`, `s`.

use crate::{Error, Result, Writer};

/// Length of a P-256 `SubjectPublicKeyInfo` DER encoding.
pub const P256_SPKI_LEN: usize = 91;

/// Upper bound of [`ecdsa_signature`] output (2 + 2×(2+33)).
pub const ECDSA_P256_DER_MAX: usize = 72;

/// `SEQUENCE { SEQUENCE { id-ecPublicKey, secp256r1 }, BIT STRING 0x00 || 0x04 || x || y }`
const P256_SPKI_PREFIX: [u8; 26] = [
    0x30, 0x59, // SEQUENCE, 89 bytes
    0x30, 0x13, // SEQUENCE, 19 bytes (AlgorithmIdentifier)
    0x06, 0x07, 0x2a, 0x86, 0x48, 0xce, 0x3d, 0x02, 0x01, // OID 1.2.840.10045.2.1 ecPublicKey
    0x06, 0x08, 0x2a, 0x86, 0x48, 0xce, 0x3d, 0x03, 0x01,
    0x07, // OID 1.2.840.10045.3.1.7 prime256v1
    0x03, 0x42, 0x00, // BIT STRING, 66 bytes, 0 unused bits
];

/// DER `SubjectPublicKeyInfo` for the P-256 point `(x, y)`.
pub fn p256_spki(x: &[u8; 32], y: &[u8; 32]) -> [u8; P256_SPKI_LEN] {
    let mut out = [0u8; P256_SPKI_LEN];
    out[..26].copy_from_slice(&P256_SPKI_PREFIX);
    out[26] = 0x04; // uncompressed point
    out[27..59].copy_from_slice(x);
    out[59..].copy_from_slice(y);
    out
}

fn der_uint(w: &mut Writer<'_>, v: &[u8; 32]) -> Result<()> {
    // strip leading zero bytes (keep at least one)
    let first = v.iter().position(|&b| b != 0).unwrap_or(31);
    let body = &v[first..];
    let pad = body[0] & 0x80 != 0;
    w.put_u8(0x02)?;
    w.put_u8((body.len() + usize::from(pad)) as u8)?;
    if pad {
        w.put_u8(0)?;
    }
    w.put_bytes(body)
}

/// DER-encode `(r, s)` as `ECDSA-Sig-Value`; returns the encoded length.
pub fn ecdsa_signature(r: &[u8; 32], s: &[u8; 32], out: &mut [u8]) -> Result<usize> {
    let mut body = [0u8; ECDSA_P256_DER_MAX];
    let body_len = {
        let mut w = Writer::new(&mut body);
        der_uint(&mut w, r)?;
        der_uint(&mut w, s)?;
        w.finish()
    };
    let mut w = Writer::new(out);
    w.put_u8(0x30)?;
    w.put_u8(u8::try_from(body_len).map_err(|_| Error::TooLarge)?)?;
    w.put_bytes(&body[..body_len])?;
    Ok(w.finish())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn spki_layout() {
        let x = [0x11u8; 32];
        let y = [0x22u8; 32];
        let d = p256_spki(&x, &y);
        assert_eq!(d[0], 0x30);
        assert_eq!(d[1] as usize, P256_SPKI_LEN - 2);
        assert_eq!(d[26], 0x04);
        assert_eq!(&d[27..59], &x);
        assert_eq!(&d[59..], &y);
    }

    #[test]
    fn sig_der_high_bit_padding_and_zero_stripping() {
        let mut r = [0u8; 32];
        r[0] = 0x80; // high bit set -> needs 0x00 pad -> 33-byte INTEGER
        let mut s = [0u8; 32];
        s[31] = 0x01; // leading zeros stripped -> 1-byte INTEGER
        let mut out = [0u8; ECDSA_P256_DER_MAX];
        let n = ecdsa_signature(&r, &s, &mut out).unwrap();
        // 30 len | 02 21 00 80 00.. | 02 01 01
        assert_eq!(n, 2 + 2 + 33 + 2 + 1);
        assert_eq!(out[0], 0x30);
        assert_eq!(out[1] as usize, n - 2);
        assert_eq!(&out[2..5], &[0x02, 0x21, 0x00]);
        assert_eq!(out[5], 0x80);
        assert_eq!(&out[n - 3..n], &[0x02, 0x01, 0x01]);
    }

    #[test]
    fn sig_der_all_zero_scalar_encodes_single_zero_byte() {
        let r = [0u8; 32];
        let s = [0x7fu8; 32];
        let mut out = [0u8; ECDSA_P256_DER_MAX];
        let n = ecdsa_signature(&r, &s, &mut out).unwrap();
        assert_eq!(&out[2..5], &[0x02, 0x01, 0x00]);
        assert_eq!(n, 2 + 3 + 2 + 32);
    }
}
