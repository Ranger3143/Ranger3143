//! PCR selection structures and the PCR composite digest.
//!
//! * `TPMS_PCR_SELECTION` (Part 2 §10.6.2):
//!   `TPMI_ALG_HASH hash (UINT16) | UINT8 sizeofSelect | BYTE pcrSelect[sizeofSelect]`
//!   where PCR *i* is selected when `pcrSelect[i / 8] & (1 << (i % 8))` is set.
//! * `TPML_PCR_SELECTION` (Part 2 §10.9.7):
//!   `UINT32 count | TPMS_PCR_SELECTION pcrSelections[count]`.
//! * PCR composite / `pcrDigest` (Part 3 §18.4 `TPM2_Quote`, Part 1 §17.7):
//!   the digest, using the signing scheme's hash, of the concatenation of the
//!   selected PCR values in selection order (bank order, then ascending PCR index).

use crate::consts::{PCR_SELECT_MAX, PCR_SELECT_MIN, TPM_ALG_SHA256};
use crate::sha256::Sha256;
use crate::{Error, Reader, Result, Writer};

/// One `TPMS_PCR_SELECTION` (one hash bank).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct PcrSelection {
    /// `TPM_ALG_ID` of the bank (e.g. [`TPM_ALG_SHA256`]).
    pub hash: u16,
    /// `sizeofSelect`, 1..=4.  Builders use 3 (24 PCRs).
    pub size_of_select: u8,
    /// `pcrSelect` bitmap; only the first `size_of_select` bytes are meaningful.
    pub select: [u8; PCR_SELECT_MAX],
}

impl PcrSelection {
    /// Empty selection for `hash` with `sizeofSelect = 3`.
    pub const fn new(hash: u16) -> Self {
        Self {
            hash,
            size_of_select: PCR_SELECT_MIN as u8,
            select: [0u8; PCR_SELECT_MAX],
        }
    }

    /// SHA-256 bank selecting the given PCR indices (const-evaluable).
    pub const fn sha256(pcrs: &[u8]) -> Self {
        let mut s = Self::new(TPM_ALG_SHA256);
        let mut i = 0;
        while i < pcrs.len() {
            s = s.with_pcr(pcrs[i]);
            i += 1;
        }
        s
    }

    /// Add PCR `pcr` to the selection (silently ignores indices >= 32).
    pub const fn with_pcr(mut self, pcr: u8) -> Self {
        let byte = (pcr / 8) as usize;
        if byte < PCR_SELECT_MAX {
            self.select[byte] |= 1 << (pcr % 8);
            if byte + 1 > self.size_of_select as usize {
                self.size_of_select = (byte + 1) as u8;
            }
        }
        self
    }

    /// Whether PCR `pcr` is selected.
    pub fn is_selected(&self, pcr: u8) -> bool {
        let byte = (pcr / 8) as usize;
        byte < self.size_of_select as usize && self.select[byte] & (1 << (pcr % 8)) != 0
    }

    /// Number of selected PCRs.
    pub fn count(&self) -> usize {
        self.select[..self.size_of_select as usize]
            .iter()
            .map(|b| b.count_ones() as usize)
            .sum()
    }

    /// Selected PCR indices in ascending order (the order the TPM uses when
    /// returning values and when computing the composite digest).
    pub fn indices(&self) -> impl Iterator<Item = u8> + '_ {
        (0..(self.size_of_select as u32 * 8) as u8).filter(move |&i| self.is_selected(i))
    }

    /// Marshal as `TPMS_PCR_SELECTION`.
    pub fn marshal(&self, w: &mut Writer<'_>) -> Result<()> {
        w.put_u16(self.hash)?;
        w.put_u8(self.size_of_select)?;
        w.put_bytes(&self.select[..self.size_of_select as usize])
    }

    /// Unmarshal a `TPMS_PCR_SELECTION`.
    pub fn unmarshal(r: &mut Reader<'_>) -> Result<Self> {
        let hash = r.u16()?;
        let size_of_select = r.u8()?;
        if size_of_select as usize > PCR_SELECT_MAX {
            return Err(Error::TooLarge);
        }
        let bytes = r.take(size_of_select as usize)?;
        let mut select = [0u8; PCR_SELECT_MAX];
        select[..bytes.len()].copy_from_slice(bytes);
        Ok(Self {
            hash,
            size_of_select,
            select,
        })
    }
}

/// Maximum number of banks stored in a [`PcrSelectionList`] (`HASH_COUNT` of
/// real TPMs is typically 2..4).
pub const MAX_PCR_SELECTIONS: usize = 8;

/// A `TPML_PCR_SELECTION` with fixed capacity.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct PcrSelectionList {
    count: usize,
    items: [PcrSelection; MAX_PCR_SELECTIONS],
}

impl Default for PcrSelectionList {
    fn default() -> Self {
        Self::new()
    }
}

impl PcrSelectionList {
    /// Empty list (`count = 0`).
    pub const fn new() -> Self {
        Self {
            count: 0,
            items: [PcrSelection::new(0); MAX_PCR_SELECTIONS],
        }
    }

    /// List containing a single bank.
    pub const fn single(sel: PcrSelection) -> Self {
        let mut l = Self::new();
        l.items[0] = sel;
        l.count = 1;
        l
    }

    /// Append a bank.
    pub fn push(&mut self, sel: PcrSelection) -> Result<()> {
        if self.count >= MAX_PCR_SELECTIONS {
            return Err(Error::TooLarge);
        }
        self.items[self.count] = sel;
        self.count += 1;
        Ok(())
    }

    /// The banks.
    pub fn as_slice(&self) -> &[PcrSelection] {
        &self.items[..self.count]
    }

    /// Number of banks.
    pub fn len(&self) -> usize {
        self.count
    }

    /// `true` when `count == 0`.
    pub fn is_empty(&self) -> bool {
        self.count == 0
    }

    /// Total number of selected PCRs across all banks.
    pub fn total_pcrs(&self) -> usize {
        self.as_slice().iter().map(PcrSelection::count).sum()
    }

    /// Marshal as `TPML_PCR_SELECTION`.
    pub fn marshal(&self, w: &mut Writer<'_>) -> Result<()> {
        w.put_u32(self.count as u32)?;
        for s in self.as_slice() {
            s.marshal(w)?;
        }
        Ok(())
    }

    /// Unmarshal a `TPML_PCR_SELECTION`.
    pub fn unmarshal(r: &mut Reader<'_>) -> Result<Self> {
        let count = r.u32()? as usize;
        if count > MAX_PCR_SELECTIONS {
            return Err(Error::TooLarge);
        }
        let mut l = Self::new();
        for _ in 0..count {
            l.push(PcrSelection::unmarshal(r)?)?;
        }
        Ok(l)
    }
}

/// PCR composite digest for a SHA-256 quote: `SHA-256(pcr[0] || pcr[1] || ...)`
/// with the values given in selection order.  This is what `TPM2_Quote`
/// places in `TPMS_QUOTE_INFO.pcrDigest` (Part 3 §18.4.1).
pub fn composite_sha256(values: &[[u8; 32]]) -> [u8; 32] {
    let mut h = Sha256::new();
    for v in values {
        h.update(v);
    }
    h.finalize()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn selection_bytes_sha256_4_12() {
        // PCR 4  -> byte 0, bit 4 -> 0x10
        // PCR 12 -> byte 1, bit 4 -> 0x10
        let s = PcrSelection::sha256(&[4, 12]);
        let mut buf = [0u8; 16];
        let mut w = Writer::new(&mut buf);
        s.marshal(&mut w).unwrap();
        let n = w.finish();
        assert_eq!(&buf[..n], &[0x00, 0x0B, 0x03, 0x10, 0x10, 0x00]);
        assert_eq!(s.count(), 2);
        let idx: [u8; 2] = {
            let mut it = s.indices();
            let a = it.next().unwrap();
            let b = it.next().unwrap();
            assert!(it.next().is_none());
            [a, b]
        };
        assert_eq!(idx, [4, 12]);
    }

    #[test]
    fn selection_list_marshal_unmarshal() {
        let list = PcrSelectionList::single(PcrSelection::sha256(&[0, 7, 23]));
        let mut buf = [0u8; 16];
        let mut w = Writer::new(&mut buf);
        list.marshal(&mut w).unwrap();
        let n = w.finish();
        assert_eq!(&buf[..n], &[0, 0, 0, 1, 0x00, 0x0B, 0x03, 0x81, 0x00, 0x80]);
        let back = PcrSelectionList::unmarshal(&mut Reader::new(&buf[..n])).unwrap();
        assert_eq!(back, list);
        assert_eq!(back.total_pcrs(), 3);
    }

    #[test]
    fn composite_is_plain_concatenation_hash() {
        let a = [0x11u8; 32];
        let b = [0x22u8; 32];
        let mut cat = [0u8; 64];
        cat[..32].copy_from_slice(&a);
        cat[32..].copy_from_slice(&b);
        assert_eq!(composite_sha256(&[a, b]), Sha256::digest(&cat));
    }
}
