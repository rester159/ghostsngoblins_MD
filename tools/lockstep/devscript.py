import sys
s, p = int(sys.argv[1]), int(sys.argv[2]); extra = sys.argv[3] if len(sys.argv) > 3 else ''
D = 40                              # boot menu: ARCADE first, so Down before A
ev = ['%d-%d:20' % (580 + D, 583 + D), '%d-%d:100' % (600 + D, 605 + D)]; f = 640 + D
for b in (0x10, 0x20, 0x10, 0x20, 0x40, 0x80, 0x40, 0x80): ev.append('%d-%d:%x' % (f, f + 3, b)); f += 10
ev.append('%d-%d:100' % (740 + D, 745 + D)); f = 780 + D
def tap(b):
    global f; ev.append('%d-%d:%x' % (f, f + 3, b)); f += 10
for _ in range(s - 1): tap(0x80)
tap(0x20); tap(0x20); tap(0x80); tap(0x20); tap(0x20)
for _ in range(p): tap(0x80)
tap(0x20); tap(0x20); ev.append('%d-%d:100' % (f + 10, f + 15))
if extra: ev.append(extra)
print(','.join(ev))
