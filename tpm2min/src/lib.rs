//! `tpm2min` — a dependency-free, `no_std`, `forbid(unsafe_code)` library that
//! marshals and parses a minimal set of TPM 2.0 commands as raw byte buffers
//! in the TPM 2.0 Library Specification wire format
//! (Part 3 "Commands" for command/response layout, Part 2 "Structures" for
//! the data types).  The resulting buffers can be handed directly to
//! `EFI_TCG2_PROTOCOL.SubmitCommand()` from a UEFI unikernel, or to a swtpm
//! TCP socket for testing.
//!
//! Supported commands:
//!
//! | Command              | Builder                           | Parser                     |
//! |----------------------|-----------------------------------|----------------------------|
//! | `TPM2_Startup`       | [`cmd::startup`]                  | [`rsp::startup`]           |
//! | `TPM2_PCR_Read`      | [`cmd::pcr_read`]                 | [`rsp::pcr_read`]          |
//! | `TPM2_PCR_Extend`    | [`cmd::pcr_extend_sha256`]        | [`rsp::pcr_extend`]        |
//! | `TPM2_CreatePrimary` | [`cmd::create_primary_ecc_p256`]  | [`rsp::create_primary`]    |
//! | `TPM2_Quote`         | [`cmd::quote`]                    | [`rsp::quote`]             |
//! | `TPM2_FlushContext`  | [`cmd::flush_context`]            | [`rsp::flush_context`]     |
//!
//! Plus: [`rsp::attest`] (TPMS_ATTEST parser), [`rsp::ecc_public`]
//! (TPMT_PUBLIC parser for ECC keys), [`pcr::composite_sha256`] (PCR
//! composite digest), a small [`sha256`] implementation, and [`der`]
//! helpers that turn the TPM's ECC point / (r,s) signature into the DER
//! structures OpenSSL expects.
//!
//! Everything works on caller-provided `&mut [u8]` buffers or fixed-size
//! `[u8; N]` structs — no heap allocation anywhere.
//!
//! # Wire-format conventions (Part 1 §18, Part 3 §5)
//!
//! * All integers are big-endian.
//! * `TPM2B_*` = `UINT16 size` followed by `size` bytes.
//! * `TPML_*`  = `UINT32 count` followed by `count` elements.
//! * A command is `tag(2) commandSize(4) commandCode(4) [handles] [authorizationSize(4) authArea] [parameters]`.
//! * A response is `tag(2) responseSize(4) responseCode(4) [handles] [parameterSize(4)] [parameters] [authArea]`.
//!   When `responseCode != TPM_RC_SUCCESS` the response is exactly the 10-byte header
//!   with `tag = TPM_ST_NO_SESSIONS`.

#![no_std]
#![forbid(unsafe_code)]
#![deny(missing_docs)]
#![warn(clippy::all)]

pub mod cmd;
pub mod consts;
pub mod der;
pub mod error;
pub mod pcr;
pub mod rsp;
pub mod sha256;
pub mod wire;

pub use error::Error;
pub use pcr::{PcrSelection, PcrSelectionList};
pub use wire::{Reader, Tpm2b, Writer};

/// Result alias used throughout the crate.
pub type Result<T> = core::result::Result<T, Error>;

/// Recommended size of a command buffer: all commands this crate builds fit
/// comfortably (the largest, `TPM2_Quote` with a 64-byte qualifying data and
/// 8 PCR banks, is far below 256 bytes).
pub const COMMAND_BUFFER_SIZE: usize = 512;

/// Recommended size of a response buffer.  `MAX_COMMAND_SIZE`/`MAX_RESPONSE_SIZE`
/// of real TPMs is typically 4096 (Part 2 §A.3), and `TPM2_CreatePrimary`
/// responses carry a `TPM2B_CREATION_DATA` that can approach 1 KiB.
pub const RESPONSE_BUFFER_SIZE: usize = 4096;
