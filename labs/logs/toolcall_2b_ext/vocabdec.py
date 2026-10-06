"""vocabdec.py - Python port of AegisTokenizer::new + ::decode (aegis-core/src/tokenizer.rs)
for decoding the `toks=` id lists in AEGIS-TRACE receipts back to text.
Validated against the Rust decode by tests in analyze_ext.py (decoded step text must
contain the receipt's own recorded tool call `in=` for every receipt with a tool call)."""
import struct

def load_vocab(path):
    b = open(path, "rb").read()
    magic, n = struct.unpack_from("<II", b, 0)
    assert magic == 0x564F4341, "bad vocab magic"
    off = 8
    toks = []
    for _ in range(n):
        (ln,) = struct.unpack_from("<H", b, off); off += 2
        toks.append(b[off:off+ln].decode("utf-8")); off += ln
    return toks

def decode(vocab, ids):
    buf = bytearray()
    for i in ids:
        if i < len(vocab):
            for ch in vocab[i]:
                u = ord(ch)
                if u < 256:
                    buf.append(u)
                else:
                    o = u - 256
                    if o <= 32: buf.append(o)
                    elif 33 <= o <= 66: buf.append(o - 33 + 127)
                    elif o == 67: buf.append(173)
                    else: buf.append(ord("?"))
    return buf.decode("utf-8", "replace")
