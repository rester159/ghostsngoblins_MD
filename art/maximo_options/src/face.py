"""Hand-drawn Maximo face stamps, placed relative to each frame's eye pixel.
Columns i = -2..5 (i>0 = toward the nose); rows start one above the eye row.
'.' keeps the frame's pixel. Keeps Arthur's brow (444) and eye (F D E)."""
ARMOR_FACE=[  # i: -2 -1 0 1 2 3 4 5
".444CA1.",    # ey-1  brow, forehead
".FDECCA1",    # ey    eye, cheek, nose bump juts out
".ACCCC1.",    # ey+1  under the nose
".ACAAC1.",    # ey+2  mouth line
"..ACC1..",    # ey+3  chin
"..111...",    # ey+4  outline under chin
]
BOXER_FACE=[
".444CA1.",
".FDECCA1",
".ACCCC1.",
".ACAAC1.",
".AACCA1.",
"..AAA...",
]
def stamp(g, ey, ex, d, rows):
    for r,row in enumerate(rows):
        y=ey-1+r
        for j,ch in enumerate(row):
            if ch=='.': continue
            x=ex+d*(j-2)
            if 0<=y<32 and 0<=x<32: g[y][x]=int(ch,16)
