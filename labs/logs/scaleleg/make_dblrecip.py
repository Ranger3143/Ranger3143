#!/usr/bin/env python3
"""Make bitnet2b_dblrecip/MODEL.SAF from bitnet2b_fixed/MODEL.SAF.

Every per-tensor weight scale scalar (F32, shape [1], name ending '_scale') is replaced by
f32(1.0 / f32(1.0 / s)), both divisions rounded to float32 (numpy float32 arithmetic).
Source file is only READ; the output is a byte copy with the 4-byte scale slots overwritten.
Run with: python3 -I make_dblrecip.py SRC_MODEL.SAF DST_MODEL.SAF [AS_SHIPPED_MODEL.SAF]
No timing is measured or reported.
"""
import hashlib, json, os, shutil, struct, sys
import numpy as np

SRC, DST = sys.argv[1], sys.argv[2]
SHIPPED = sys.argv[3] if len(sys.argv) > 3 else None
OUTDIR = os.path.dirname(os.path.dirname(os.path.abspath(DST)))  # stats land one level above the output dir

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(1 << 24)
            if not b:
                break
            h.update(b)
    return h.hexdigest()

def read_header(path):
    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        raw = f.read(n)
    return n, raw, json.loads(raw)

assert os.path.abspath(SRC) != os.path.abspath(DST)
assert not os.path.exists(DST), "refusing to overwrite existing output"

n, hdr_raw, hdr = read_header(SRC)
base = 8 + n
slots = []
for name, t in hdr.items():
    if name == "__metadata__" or not name.endswith("_scale"):
        continue
    assert t["dtype"] == "F32" and t["shape"] == [1], (name, t)
    s0, s1 = t["data_offsets"]
    assert s1 - s0 == 4, (name, t)
    slots.append((name, base + s0))
slots.sort(key=lambda x: x[1])
assert len(slots) == 210, len(slots)
offs = [o for _, o in slots]
assert len(set(offs)) == 210 and all(offs[i] + 4 <= offs[i + 1] for i in range(209))
print("scale tensors found:", len(slots))

with open(SRC, "rb") as f:
    olds = []
    for name, off in slots:
        f.seek(off)
        olds.append(f.read(4))
old = np.frombuffer(b"".join(olds), dtype="<f4").copy()
assert np.all(np.isfinite(old)) and np.all(old > 0), "non-finite or non-positive scale"

one = np.float32(1.0)
recip = (one / old).astype(np.float32)          # float32 division, rounded to f32
new = (one / recip).astype(np.float32)          # float32 division, rounded to f32
assert recip.dtype == np.float32 and new.dtype == np.float32

# cross-check: f32 division == f64 division rounded to f32 (should always hold) and as-shipped scales
recip_via_f64 = (1.0 / old.astype(np.float64)).astype(np.float32)
print("recip f32-div == f64-div-then-round:", bool(np.array_equal(recip.view(np.uint32), recip_via_f64.view(np.uint32))))
shipped_match = None
if SHIPPED:
    _, _, sh = read_header(SHIPPED)
    sn = struct.unpack("<Q", open(SHIPPED, "rb").read(8))[0]
    vals = []
    with open(SHIPPED, "rb") as f:
        for name, _ in slots:
            t = sh[name]
            assert t["dtype"] == "F32" and t["shape"] == [1]
            f.seek(8 + sn + t["data_offsets"][0])
            vals.append(f.read(4))
    shipped = np.frombuffer(b"".join(vals), dtype="<f4")
    shipped_match = bool(np.array_equal(shipped.view(np.uint32), recip.view(np.uint32)))
    print("as-shipped (reciprocal) artifact scales bit-equal to f32(1/s):", shipped_match)
    back = (one / shipped).astype(np.float32)
    print("f32(1/shipped) bit-equal to new:", bool(np.array_equal(back.view(np.uint32), new.view(np.uint32))))

# copy, then patch the 210 slots in the COPY
shutil.copyfile(SRC, DST)
with open(DST, "r+b") as f:
    for (name, off), v in zip(slots, new):
        f.seek(off)
        f.write(struct.pack("<f", float(v)))
    f.flush()
    os.fsync(f.fileno())

# stats
changed_written = len(slots)
differs = old.view(np.uint32) != new.view(np.uint32)
nd = int(differs.sum())
absd = np.abs(new.astype(np.float64) - old.astype(np.float64))
reld = absd / np.abs(old.astype(np.float64))
ulp = np.abs(new.view(np.int32).astype(np.int64) - old.view(np.int32).astype(np.int64))
print(f"scales rewritten: {changed_written}")
print(f"scales whose f32 value differs after round trip: {nd}")
print(f"max abs change: {absd.max():.9e}  (at {slots[int(absd.argmax())][0]})")
print(f"max rel change: {reld.max():.9e}  (at {slots[int(reld.argmax())][0]})")
print(f"max change in ulps: {int(ulp.max())}; count by ulps: {dict(zip(*[x.tolist() for x in np.unique(ulp, return_counts=True)]))}")
print(f"scale value range (old): min {old.min():.9g} max {old.max():.9g}")

# verify: bytes outside the 210 slots identical, header identical
with open(SRC, "rb") as a, open(DST, "rb") as b:
    A = a.read(); B = b.read()
assert len(A) == len(B), (len(A), len(B))
assert A[:base] == B[:base], "header region differs"
mask = np.ones(len(A), dtype=bool)
for _, off in slots:
    mask[off:off + 4] = False
Aa = np.frombuffer(A, dtype=np.uint8); Bb = np.frombuffer(B, dtype=np.uint8)
outside_equal = bool(np.array_equal(Aa[mask], Bb[mask]))
diff_idx = np.nonzero(Aa != Bb)[0]
inside_slots = set()
for _, off in slots:
    inside_slots.update(range(off, off + 4))
all_diffs_in_slots = all(int(i) in inside_slots for i in diff_idx)
nbytes_diff = int(diff_idx.size)
# in-slot values exactly as intended
got = np.frombuffer(b"".join(B[o:o + 4] for _, o in slots), dtype="<f4")
slots_as_intended = bool(np.array_equal(got.view(np.uint32), new.view(np.uint32)))
header_json_equal = json.loads(B[8:base]) == hdr
print("header bytes (8-byte length + JSON) identical:", A[:base] == B[:base], "| header JSON equal:", header_json_equal)
print("all bytes outside the 210 scale slots identical:", outside_equal, "| total differing bytes:", nbytes_diff)
print("every differing byte lies inside a scale slot:", all_diffs_in_slots)
print("slot contents == intended new values:", slots_as_intended)
assert outside_equal and all_diffs_in_slots and slots_as_intended and header_json_equal

src_sha = sha256(SRC); dst_sha = sha256(DST)
print("src sha256:", src_sha)
print("dst sha256:", dst_sha)

stats = {
    "n_scale_tensors": len(slots), "n_rewritten": changed_written, "n_value_differs": nd,
    "max_abs_change": float(absd.max()), "max_rel_change": float(reld.max()),
    "max_ulp_change": int(ulp.max()),
    "ulp_histogram": {str(k): int(v) for k, v in zip(*np.unique(ulp, return_counts=True))},
    "scale_min": float(old.min()), "scale_max": float(old.max()),
    "src_sha256": src_sha, "dst_sha256": dst_sha, "bytes_differing": nbytes_diff,
    "shipped_reciprocal_scales_bit_equal_f32_1_over_s": shipped_match,
    "header_identical": True, "outside_slots_identical": outside_equal,
}
with open(os.path.join(OUTDIR, "scale_stats.json"), "w") as f:
    json.dump(stats, f, indent=2)
with open(os.path.join(OUTDIR, "scales.tsv"), "w") as f:
    f.write("tensor\tabs_offset\told_f32_hex\tnew_f32_hex\told\tnew\tdiffers\n")
    for (name, off), o, nw in zip(slots, old, new):
        f.write(f"{name}\t{off}\t{o.view(np.uint32):08x}\t{nw.view(np.uint32):08x}\t{float(o):.9g}\t{float(nw):.9g}\t{int(o.view(np.uint32) != nw.view(np.uint32))}\n")
