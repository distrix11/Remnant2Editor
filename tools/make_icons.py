"""Generates the editor's own icons (original artwork, part of this project, MIT).
Needs Pillow:  pip install pillow   ->   python tools/make_icons.py
Output: r2save/assets/*.png
"""
import math
import os

from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "r2save", "assets")
S = 8          # supersampling factor
BASE = 20      # tab icon size
MUTED = (141, 129, 120, 255)
BONE = (221, 210, 195, 255)
RED = (184, 38, 29, 255)
GLOW = (224, 71, 59, 255)


def canvas(size):
    img = Image.new("RGBA", (size * S, size * S), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def P(*pts):
    return [(x * S, y * S) for x, y in pts]


def line(d, pts, col, w=1.6, closed=False):
    pts = P(*pts)
    if closed:
        pts = pts + [pts[0]]
    d.line(pts, fill=col, width=int(w * S), joint="curve")
    r = w * S / 2
    for x, y in pts:
        d.ellipse([x - r, y - r, x + r, y + r], fill=col)


def finish(img, size, name):
    img = img.resize((size, size), Image.LANCZOS)
    img.save(os.path.join(OUT, name))


# --- tab icons: each draws on a 20x20 grid -----------------------------------------

def ic_character(d, c):
    d.ellipse(P((6.6, 2.6), (13.4, 9.4)), outline=c, width=int(1.6 * S))
    d.arc(P((3, 11), (17, 25)), 200, 340, fill=c, width=int(1.6 * S))
    line(d, [(4.2, 16.8), (4.2, 17.6)], c)
    line(d, [(15.8, 16.8), (15.8, 17.6)], c)


def ic_resources(d, c):
    top, mid, bot = (10, 2.2), 7.0, (10, 17.8)
    hexa = [top, (15, mid), (15, 13), bot, (5, 13), (5, mid)]
    line(d, hexa, c, closed=True)
    line(d, [(5, mid), (10, 9.6), (15, mid)], c, 1.2)
    line(d, [(10, 9.6), bot], c, 1.2)


def ic_inventory(d, c):
    d.rounded_rectangle(P((4, 6.5), (16, 17.5)), radius=2.4 * S, outline=c, width=int(1.6 * S))
    d.arc(P((7, 2.6), (13, 9)), 180, 360, fill=c, width=int(1.5 * S))
    line(d, [(4.4, 10.6), (15.6, 10.6)], c, 1.3)
    d.rectangle(P((8.6, 9.6), (11.4, 12.4)), fill=c)


def ic_traits(d, c):
    for i, h in enumerate((4.5, 7.5, 10.5)):
        x = 3.4 + i * 4.6
        d.rectangle(P((x, 17.4 - h), (x + 2.6, 17.4)), fill=c)
    cx, cy, r = 15.6, 3.2, 2.0
    d.polygon(P((cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)), fill=c)


def ic_add(d, c):
    line(d, [(10, 2), (18, 10), (10, 18), (2, 10)], c, closed=True)
    line(d, [(10, 6.8), (10, 13.2)], c)
    line(d, [(6.8, 10), (13.2, 10)], c)


def ic_teleport(d, c):
    line(d, [(8, 17), (8.6, 5), (10, 2.4), (11.4, 5), (12, 17)], c, 1.5, closed=True)
    d.arc(P((2.4, 8.4), (17.6, 14.6)), 200, 340, fill=c, width=int(1.4 * S))
    d.arc(P((2.4, 8.4), (17.6, 14.6)), 20, 160, fill=c, width=int(1.4 * S))
    line(d, [(5, 18), (15, 18)], c, 1.4)


def ic_analysis(d, c):
    pts = []
    for i in range(0, 181, 10):
        a = math.radians(i)
        pts.append((10 - 8 * math.cos(a), 10 - 5.4 * math.sin(a)))
    for i in range(0, 181, 10):
        a = math.radians(i)
        pts.append((10 + 8 * math.cos(a), 10 + 5.4 * math.sin(a)))
    line(d, pts, c, 1.5, closed=True)
    d.ellipse(P((7.2, 7.2), (12.8, 12.8)), outline=c, width=int(1.5 * S))
    d.ellipse(P((9, 9), (11, 11)), fill=c)


def ic_raw(d, c):
    line(d, [(7, 2.8), (5, 4), (5, 8.6), (2.6, 10), (5, 11.4), (5, 16), (7, 17.2)], c, 1.5)
    line(d, [(13, 2.8), (15, 4), (15, 8.6), (17.4, 10), (15, 11.4), (15, 16), (13, 17.2)], c, 1.5)
    for y in (7, 10, 13):
        d.ellipse(P((9.1, y - 0.9), (10.9, y + 0.9)), fill=c)


TABS = {
    "character": ic_character, "resources": ic_resources, "inventory": ic_inventory, "traits": ic_traits,
    "add": ic_add, "teleport": ic_teleport, "analysis": ic_analysis, "raw": ic_raw,
}


def emblem(size):
    """Crimson crystal sigil used in the header and as the window icon."""
    img, d = canvas(size)
    u = size / 36.0
    cx = cy = 18 * u

    def Q(*pts):
        return [(x * u * S, y * u * S) for x, y in pts]
    d.polygon(Q((18, 1.5), (34.5, 18), (18, 34.5), (1.5, 18)), outline=RED, width=int(max(1.4, 1.6 * u) * S))
    d.polygon(Q((18, 6.5), (29.5, 18), (18, 29.5), (6.5, 18)), fill=(62, 13, 10, 255))
    d.polygon(Q((18, 9), (27, 18), (18, 27), (9, 18)), fill=RED)
    d.polygon(Q((18, 9), (27, 18), (18, 18)), fill=GLOW)
    d.polygon(Q((18, 13.5), (22.5, 18), (18, 22.5), (13.5, 18)), fill=(255, 214, 200, 255))
    return img


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, fn in TABS.items():
        for suffix, col in (("", MUTED), ("_on", BONE)):
            img, d = canvas(BASE)
            fn(d, col)
            finish(img, BASE, "tab_%s%s.png" % (name, suffix))
    for size in (36, 64):
        finish(emblem(size), size, "emblem_%d.png" % size)
    print("icons written to", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
