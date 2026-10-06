//! Big-endian cursors over caller-provided byte slices, plus a fixed-capacity
//! `TPM2B` container.  (Part 1 §18 "Command/response marshalling": all
//! integers are big-endian; `TPM2B_*` is `UINT16 size` + bytes.)

use crate::{Error, Result};
use core::fmt;

/// Write cursor over a `&mut [u8]`.
pub struct Writer<'a> {
    buf: &'a mut [u8],
    pos: usize,
}

impl<'a> Writer<'a> {
    /// Start writing at the beginning of `buf`.
    pub fn new(buf: &'a mut [u8]) -> Self {
        Self { buf, pos: 0 }
    }

    /// Number of bytes written so far.
    pub fn position(&self) -> usize {
        self.pos
    }

    /// Bytes written so far.
    pub fn written(&self) -> &[u8] {
        &self.buf[..self.pos]
    }

    /// Append raw bytes.
    pub fn put_bytes(&mut self, b: &[u8]) -> Result<()> {
        let end = self.pos.checked_add(b.len()).ok_or(Error::BufferTooSmall)?;
        let dst = self
            .buf
            .get_mut(self.pos..end)
            .ok_or(Error::BufferTooSmall)?;
        dst.copy_from_slice(b);
        self.pos = end;
        Ok(())
    }

    /// Append a `UINT8`.
    pub fn put_u8(&mut self, v: u8) -> Result<()> {
        self.put_bytes(&[v])
    }

    /// Append a big-endian `UINT16`.
    pub fn put_u16(&mut self, v: u16) -> Result<()> {
        self.put_bytes(&v.to_be_bytes())
    }

    /// Append a big-endian `UINT32`.
    pub fn put_u32(&mut self, v: u32) -> Result<()> {
        self.put_bytes(&v.to_be_bytes())
    }

    /// Append a big-endian `UINT64`.
    pub fn put_u64(&mut self, v: u64) -> Result<()> {
        self.put_bytes(&v.to_be_bytes())
    }

    /// Append a `TPM2B_*`: `UINT16 size` followed by the bytes.
    pub fn put_2b(&mut self, b: &[u8]) -> Result<()> {
        let n = u16::try_from(b.len()).map_err(|_| Error::TooLarge)?;
        self.put_u16(n)?;
        self.put_bytes(b)
    }

    /// Overwrite a previously written big-endian `UINT32` at offset `at`
    /// (used to back-patch `commandSize`).
    pub fn patch_u32(&mut self, at: usize, v: u32) -> Result<()> {
        let end = at.checked_add(4).ok_or(Error::BufferTooSmall)?;
        if end > self.pos {
            return Err(Error::BufferTooSmall);
        }
        self.buf[at..end].copy_from_slice(&v.to_be_bytes());
        Ok(())
    }

    /// Finish and return the number of bytes written.
    pub fn finish(self) -> usize {
        self.pos
    }
}

/// Read cursor over a `&[u8]`.
#[derive(Clone)]
pub struct Reader<'a> {
    buf: &'a [u8],
    pos: usize,
}

impl<'a> Reader<'a> {
    /// Start reading at the beginning of `buf`.
    pub fn new(buf: &'a [u8]) -> Self {
        Self { buf, pos: 0 }
    }

    /// Current offset.
    pub fn position(&self) -> usize {
        self.pos
    }

    /// Bytes left.
    pub fn remaining(&self) -> usize {
        self.buf.len() - self.pos
    }

    /// `true` when all bytes have been consumed.
    pub fn is_empty(&self) -> bool {
        self.remaining() == 0
    }

    /// Take `n` raw bytes.
    pub fn take(&mut self, n: usize) -> Result<&'a [u8]> {
        let end = self.pos.checked_add(n).ok_or(Error::Truncated)?;
        let s = self.buf.get(self.pos..end).ok_or(Error::Truncated)?;
        self.pos = end;
        Ok(s)
    }

    /// Read a `UINT8`.
    pub fn u8(&mut self) -> Result<u8> {
        Ok(self.take(1)?[0])
    }

    /// Read a big-endian `UINT16`.
    pub fn u16(&mut self) -> Result<u16> {
        let b = self.take(2)?;
        Ok(u16::from_be_bytes([b[0], b[1]]))
    }

    /// Read a big-endian `UINT32`.
    pub fn u32(&mut self) -> Result<u32> {
        let b = self.take(4)?;
        Ok(u32::from_be_bytes([b[0], b[1], b[2], b[3]]))
    }

    /// Read a big-endian `UINT64`.
    pub fn u64(&mut self) -> Result<u64> {
        let b = self.take(8)?;
        let mut a = [0u8; 8];
        a.copy_from_slice(b);
        Ok(u64::from_be_bytes(a))
    }

    /// Read a `TPM2B_*` and return its payload.
    pub fn take_2b(&mut self) -> Result<&'a [u8]> {
        let n = self.u16()? as usize;
        self.take(n)
    }

    /// Read a `TPM2B_*` into a fixed-capacity [`Tpm2b`].
    pub fn read_2b<const N: usize>(&mut self) -> Result<Tpm2b<N>> {
        Tpm2b::from_slice(self.take_2b()?)
    }

    /// Fail with [`Error::SizeMismatch`] unless everything was consumed.
    pub fn expect_end(&self) -> Result<()> {
        if self.is_empty() {
            Ok(())
        } else {
            Err(Error::SizeMismatch)
        }
    }
}

/// A `TPM2B_*` sized buffer with fixed capacity `N` (no heap).
#[derive(Clone, Copy)]
pub struct Tpm2b<const N: usize> {
    len: usize,
    buf: [u8; N],
}

impl<const N: usize> Tpm2b<N> {
    /// Maximum payload length.
    pub const CAPACITY: usize = N;

    /// An empty buffer (`size = 0`).
    pub const fn empty() -> Self {
        Self {
            len: 0,
            buf: [0u8; N],
        }
    }

    /// Copy `s` in; fails with [`Error::TooLarge`] if it does not fit.
    pub fn from_slice(s: &[u8]) -> Result<Self> {
        if s.len() > N {
            return Err(Error::TooLarge);
        }
        let mut t = Self::empty();
        t.buf[..s.len()].copy_from_slice(s);
        t.len = s.len();
        Ok(t)
    }

    /// Payload bytes.
    pub fn as_slice(&self) -> &[u8] {
        &self.buf[..self.len]
    }

    /// Payload length.
    pub fn len(&self) -> usize {
        self.len
    }

    /// `true` when `size == 0`.
    pub fn is_empty(&self) -> bool {
        self.len == 0
    }

    /// Marshal as `UINT16 size || payload`.
    pub fn marshal(&self, w: &mut Writer<'_>) -> Result<()> {
        w.put_2b(self.as_slice())
    }
}

impl<const N: usize> Default for Tpm2b<N> {
    fn default() -> Self {
        Self::empty()
    }
}

impl<const N: usize> PartialEq for Tpm2b<N> {
    fn eq(&self, other: &Self) -> bool {
        self.as_slice() == other.as_slice()
    }
}
impl<const N: usize> Eq for Tpm2b<N> {}

impl<const N: usize> fmt::Debug for Tpm2b<N> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "Tpm2b<{}>[{}]=", N, self.len)?;
        for b in self.as_slice() {
            write!(f, "{b:02x}")?;
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn writer_roundtrip() {
        let mut buf = [0u8; 32];
        let mut w = Writer::new(&mut buf);
        w.put_u8(0xAA).unwrap();
        w.put_u16(0x1122).unwrap();
        w.put_u32(0x3344_5566).unwrap();
        w.put_u64(0x0102_0304_0506_0708).unwrap();
        w.put_2b(&[9, 8, 7]).unwrap();
        let n = w.finish();
        assert_eq!(n, 1 + 2 + 4 + 8 + 2 + 3);
        assert_eq!(
            &buf[..n],
            &[0xAA, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 1, 2, 3, 4, 5, 6, 7, 8, 0, 3, 9, 8, 7]
        );
        let mut r = Reader::new(&buf[..n]);
        assert_eq!(r.u8().unwrap(), 0xAA);
        assert_eq!(r.u16().unwrap(), 0x1122);
        assert_eq!(r.u32().unwrap(), 0x3344_5566);
        assert_eq!(r.u64().unwrap(), 0x0102_0304_0506_0708);
        assert_eq!(r.take_2b().unwrap(), &[9, 8, 7]);
        assert!(r.expect_end().is_ok());
        assert_eq!(r.u8(), Err(Error::Truncated));
    }

    #[test]
    fn writer_overflow() {
        let mut buf = [0u8; 3];
        let mut w = Writer::new(&mut buf);
        assert_eq!(w.put_u32(1), Err(Error::BufferTooSmall));
        assert_eq!(w.position(), 0);
    }

    #[test]
    fn tpm2b_capacity() {
        assert!(Tpm2b::<4>::from_slice(&[1, 2, 3, 4, 5]).is_err());
        let t = Tpm2b::<4>::from_slice(&[1, 2]).unwrap();
        assert_eq!(t.as_slice(), &[1, 2]);
        assert_eq!(t, Tpm2b::<4>::from_slice(&[1, 2]).unwrap());
    }
}
