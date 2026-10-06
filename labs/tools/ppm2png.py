#!/usr/bin/env python3
"""Convert a binary PPM (P6) screendump to PNG with stdlib only (zlib)."""
import struct, sys, zlib
def read_ppm(p):
    d = open(p, 'rb').read()
    parts = []; i = 0
    while len(parts) < 4:
        while d[i:i+1].isspace(): i += 1
        if d[i:i+1] == b'#':
            while d[i:i+1] not in (b'\n', b''): i += 1
            continue
        j = i
        while not d[j:j+1].isspace(): j += 1
        parts.append(d[i:j]); i = j
    i += 1
    assert parts[0] == b'P6', parts[0]
    w, h, mx = int(parts[1]), int(parts[2]), int(parts[3])
    return w, h, d[i:i+w*h*3]
def write_png(p, w, h, rgb):
    raw = b''.join(b'\x00' + rgb[y*w*3:(y+1)*w*3] for y in range(h))
    def chunk(t, b): return struct.pack('>I', len(b)) + t + b + struct.pack('>I', zlib.crc32(t + b) & 0xffffffff)
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b'')
    open(p, 'wb').write(png)
w, h, rgb = read_ppm(sys.argv[1]); write_png(sys.argv[2], w, h, rgb); print(f'{sys.argv[2]} {w}x{h}')
