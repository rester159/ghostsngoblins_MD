"""ring_cmp.py <arc state> <port rom> <port ram>: the two games' terrain rings byte for byte (arcade bg RAM $2800
tiles / $2C00 attributes; port $FF0000 / $FF0400; both cell (col & 31) << 5 | ((row ^ 15) & 31), rows counted up),
all 1,024 cells, and how many differ as a floor to Arthur's probe (the port's rule, $860C: no
floor when attribute & $C0, else the height table $14A6E by tile; the arcade's probe $8CA7 agrees with it cell for
cell, terrain_probe.py). Prints the differing cells as world column / row (from the cameras). Fixed 80."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'arcade'))
from gng import GnG
g = GnG(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'rom')); g.load(sys.argv[1]); am = g.mem
ROM = open(sys.argv[2], 'rb').read(); raw = open(sys.argv[3], 'rb').read()
RAM = bytes(raw[i ^ 1] for i in range(len(raw)))
acx, acy = am[0x9C] << 8 | am[0x9D], am[0x9E] << 8 | am[0x9F]
pcx = RAM[0x9100] << 8 | RAM[0x9101]; pcy = RAM[0x9102] << 8 | RAM[0x9103]
H = ROM[0x14A6E:0x14A6E + 256]
floor = lambda t, a: not (a & 0xC0) and H[t] != 0
bad = []; fbad = 0
for i in range(1024):
    at, aa = am[0x2800 + i], am[0x2C00 + i]
    pt, pa = RAM[i], RAM[0x400 + i]
    if (at, aa) != (pt, pa):
        # the world cell: column with these low 5 bits nearest the camera's, row likewise
        c5, r5 = i >> 5, (i & 31) ^ 15
        c = acx // 16 - 8 + ((c5 - (acx // 16 - 8)) & 31); r = acy // 16 - 8 + ((r5 - (acy // 16 - 8)) & 31)
        f = floor(at, aa) != floor(pt, pa) or (floor(at, aa) and H[at] != H[pt])
        fbad += f
        bad.append((c, r, at, aa, pt, pa, f))
print('camera arcade %d,%d port %d,%d: %d of 1024 cells differ, %d as a floor' % (acx, acy, pcx, pcy, len(bad), fbad))
for c, r, at, aa, pt, pa, f in sorted(bad)[:int(os.environ.get('SHOW', '12'))]:
    print('  col %d row %d arcade %02X/%02X port %02X/%02X%s' % (c, r, at, aa, pt, pa, ' floor' if f else ''))
