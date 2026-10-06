//! Error type.

use core::fmt;

/// Errors produced by the builders and parsers.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Error {
    /// The caller-provided output buffer is too small for the command.
    BufferTooSmall,
    /// The response buffer ended before the structure was complete.
    Truncated,
    /// The TPM returned a non-zero `TPM_RC` (Part 2 §6.6).  The raw code is
    /// carried verbatim (e.g. `0x100` = `TPM_RC_INITIALIZE`).
    TpmRc(u32),
    /// Response `tag` was not `TPM_ST_NO_SESSIONS`/`TPM_ST_SESSIONS` or did not
    /// match what the command used.
    BadTag(u16),
    /// A length field (responseSize, parameterSize, TPM2B size, ...) does not
    /// agree with the bytes actually present.
    SizeMismatch,
    /// A field has a value this crate does not handle (e.g. an RSA key where
    /// an ECC key was expected).  Carries the offending 16-bit value.
    Unsupported(u16),
    /// A value exceeds the fixed-size storage this crate reserves for it
    /// (e.g. more PCR selections than `MAX_PCR_SELECTIONS`).
    TooLarge,
    /// A structural invariant was violated (bad magic, wrong attestation type,
    /// a point coordinate longer than the curve size, ...).
    Malformed,
}

impl Error {
    /// The raw `TPM_RC` if this is [`Error::TpmRc`].
    pub fn rc(&self) -> Option<u32> {
        match self {
            Error::TpmRc(rc) => Some(*rc),
            _ => None,
        }
    }

    /// `true` for the warning-class codes that mean "resend the identical
    /// command": `TPM_RC_RETRY`, `TPM_RC_YIELDED`, `TPM_RC_NV_RATE`,
    /// `TPM_RC_NV_UNAVAILABLE` (Part 2 §6.6.3, warning codes).  A transport
    /// should bound the number of resends.
    pub fn is_retryable(&self) -> bool {
        matches!(
            self,
            Error::TpmRc(crate::consts::TPM_RC_RETRY)
                | Error::TpmRc(crate::consts::TPM_RC_YIELDED)
                | Error::TpmRc(crate::consts::TPM_RC_NV_RATE)
                | Error::TpmRc(crate::consts::TPM_RC_NV_UNAVAILABLE)
        )
    }
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Error::BufferTooSmall => f.write_str("output buffer too small"),
            Error::Truncated => f.write_str("response truncated"),
            Error::TpmRc(rc) => write!(f, "TPM returned TPM_RC 0x{rc:03x}"),
            Error::BadTag(tag) => write!(f, "unexpected response tag 0x{tag:04x}"),
            Error::SizeMismatch => f.write_str("length field disagrees with payload"),
            Error::Unsupported(v) => write!(f, "unsupported value 0x{v:04x}"),
            Error::TooLarge => f.write_str("value exceeds fixed-size storage"),
            Error::Malformed => f.write_str("malformed structure"),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn retryable_classification() {
        assert!(Error::TpmRc(0x922).is_retryable()); // TPM_RC_RETRY
        assert!(Error::TpmRc(0x908).is_retryable()); // TPM_RC_YIELDED
        assert!(Error::TpmRc(0x920).is_retryable()); // TPM_RC_NV_RATE
        assert!(!Error::TpmRc(0x100).is_retryable()); // TPM_RC_INITIALIZE
        assert!(!Error::TpmRc(0x1c4).is_retryable()); // format-1 TPM_RC_VALUE
        assert!(!Error::Truncated.is_retryable());
        assert_eq!(Error::TpmRc(0x922).rc(), Some(0x922));
        assert_eq!(Error::Malformed.rc(), None);
    }
}
