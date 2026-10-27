"""restart_entry.py <in.bin> <out.bin> <entry hex 8> [stage index, default 4]: a test copy of the port ROM whose
checkpoint-0 restart entry for that stage index (table $1040CC, 4 bytes each) is replaced, for a life start anywhere
(the arcade's: arc_restart.py). Entry: $4000 | screen y << 5 | screen x, then x and y in the screen (the arcade's
first byte $40; the port's has it clear), e.g. 40DB6050 = stage 5's room top floor at x 7008, y 1616."""
import sys
d = bytearray(open(sys.argv[1], 'rb').read())
e = bytes.fromhex(sys.argv[3]); e = bytes([e[0] & 0x3F]) + e[1:]
i = int(sys.argv[4]) if len(sys.argv) > 4 else 4
d[0x1040CC + 4 * i:0x1040CC + 4 * i + 4] = e
open(sys.argv[2], 'wb').write(d)
