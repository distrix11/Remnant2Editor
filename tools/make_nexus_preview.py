"""Renders the Nexus Mods images in the style of the startup splash.

Needs Pillow:  pip install pillow   ->   python tools/make_nexus_preview.py [output folder]
Writes (default folder: dist/, not committed):
  nexus_header.png   1300x372  mod page header
  nexus_preview.png  1920x1080 main image / thumbnail (16:9)
and docs/header.png (the same header, for the GitHub README). No version number on the images.
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

FONTS = os.path.join(ROOT, "r2save", "assets", "fonts")
SS = 3                       # supersampling for smooth lines

BG = (12, 10, 9)
PANEL2 = (27, 23, 20)
BORDER = (47, 38, 34)
TEXT = (221, 210, 195)
MUTED = (141, 129, 120)
RED = (143, 26, 20)
RED_HI = (184, 38, 29)
RED_GLOW = (224, 71, 59)
RED_DK = (62, 13, 10)
CORE = (255, 214, 200)

FEATURES = ["Resources", "Items", "Archetypes", "Teleport", "World stones", "Blood Moon", "Loot analysis"]
# no version number on the images: they must not go stale with every release
SUB = "Free & open source   ·   English / Русский"


def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, "Montserrat-%s.ttf" % name), int(size * SS))


def fit(d, text, name, size, max_w):
    """Largest font (starting at `size`) in which `text` is at most max_w wide (all values in output px)."""
    while size > 8:
        f = font(name, size)
        if d.textlength(text, font=f) <= max_w * SS:
            return f
        size -= 1
    return font(name, size)


def mix(a, b, p):
    return tuple(int(x + (y - x) * p) for x, y in zip(a, b))


def diamond(cx, cy, r, ang):
    return [(cx + r * math.cos(ang + k * math.pi / 2), cy + r * math.sin(ang + k * math.pi / 2)) for k in range(4)]


def spaced_width(d, text, fnt, spacing):
    return sum(d.textlength(ch, font=fnt) for ch in text) + spacing * SS * (len(text) - 1)


def spaced(d, x, y, text, fnt, fill, spacing):
    """Text starting at x with extra letter spacing (like the splash's 'S A V E  E D I T O R')."""
    for ch in text:
        d.text((x, y), ch, font=fnt, fill=fill)
        x += d.textlength(ch, font=fnt) + spacing * SS


def background(w, h, gx, gy, glow_r):
    """Dark canvas with a soft crimson glow at (gx, gy), a faint diamond texture and the red top bar."""
    img = Image.new("RGB", (w, h), BG)
    glow = Image.new("RGB", (w, h), BG)
    gd = ImageDraw.Draw(glow)
    for k, col in ((1.0, (40, 11, 9)), (0.68, (70, 16, 12)), (0.4, (105, 22, 16))):
        r = glow_r * k
        gd.ellipse([gx - r, gy - r * 0.8, gx + r, gy + r * 0.8], fill=col)
    glow = glow.filter(ImageFilter.GaussianBlur(glow_r / 4))
    img = Image.blend(img, glow, 0.9)
    d = ImageDraw.Draw(img)
    step = int(h / 12)
    for row, y in enumerate(range(0, h, step)):
        for x in range((row % 2) * step // 2, w, step):
            d.polygon(diamond(x, y, max(2, step / 30), math.pi / 4), fill=(22, 18, 16))
    d.rectangle([0, 0, w, max(4 * SS, h // 135)], fill=RED)
    d.rectangle([0, 0, w - 1, h - 1], outline=BORDER, width=2 * SS)
    return img, d


def emblem(d, cx, cy, size, rings=True):
    """The editor's sigil (geometry of tools/make_icons.py on a 36-unit grid) inside the splash's turning frames."""
    if rings:
        for k, ang, col, wid in ((0.66, 0.55, RED_GLOW, 1.0), (0.82, 0.85, RED_HI, 0.85),
                                 (0.98, 1.15, mix(RED_DK, RED, 0.7), 0.7)):
            pts = diamond(cx, cy, size * k / 2, ang)     # radius: k of half the size, so the frames fit
            d.line(pts + [pts[0]], fill=col, width=max(SS, int(size / 110 * wid)), joint="curve")
    u = size / 36.0
    ox, oy = cx - 18 * u, cy - 18 * u

    def Q(*pts):
        return [(ox + x * u, oy + y * u) for x, y in pts]
    inner = size * 0.52 / 36.0   # the sigil is about half of the ring size
    ox, oy, u = cx - 18 * inner, cy - 18 * inner, inner
    d.polygon(Q((18, 1.5), (34.5, 18), (18, 34.5), (1.5, 18)), outline=RED_HI, width=max(SS, int(1.6 * u)))
    d.polygon(Q((18, 6.5), (29.5, 18), (18, 29.5), (6.5, 18)), fill=RED_DK)
    d.polygon(Q((18, 9), (27, 18), (18, 27), (9, 18)), fill=RED_HI)
    d.polygon(Q((18, 9), (27, 18), (18, 18)), fill=RED_GLOW)
    d.polygon(Q((18, 13.5), (22.5, 18), (18, 22.5), (13.5, 18)), fill=CORE)


def loading_bar(d, x0, x1, y, h):
    d.rectangle([x0, y, x1, y + h], fill=PANEL2)
    d.rectangle([x0, y, x1, y + h], fill=RED_HI)
    a = x0 + (x1 - x0) * 0.58
    d.rectangle([a, y, a + (x1 - x0) * 0.11, y + h], fill=RED_GLOW)


def header(out):
    """1300x372: emblem on the left, title block on the right."""
    sub = SUB
    W, H = 1300, 372
    w, h = W * SS, H * SS
    ex, ey = 310 * SS, 190 * SS
    img, d = background(w, h, ex + 140 * SS, ey, 520 * SS)
    emblem(d, ex, ey, 356 * SS)

    x0, x1 = 560 * SS, 1210 * SS
    f_title = fit(d, "REMNANT II", "Bold", 96, (x1 - x0) / SS)
    d.text((x0, 62 * SS), "REMNANT II", font=f_title, fill=RED_GLOW)
    f_sub = font("Medium", 25)
    sp = 14
    spaced(d, x0 + 4 * SS, 184 * SS, "SAVE EDITOR", f_sub, MUTED, sp)
    loading_bar(d, x0 + 4 * SS, x1, 236 * SS, 4 * SS)
    feats = "  ·  ".join(FEATURES)
    f_feat = fit(d, feats, "Medium", 19, (x1 - x0) / SS - 4)
    d.text((x0 + 4 * SS, 258 * SS), feats, font=f_feat, fill=TEXT)
    f_small = fit(d, sub, "Regular", 17, (x1 - x0) / SS - 4)
    d.text((x0 + 4 * SS, 296 * SS), sub, font=f_small, fill=MUTED)
    save(img, (W, H), out)


def preview(out):
    """1920x1080: everything centred, like the splash window."""
    W, H = 1920, 1080
    w, h = W * SS, H * SS
    cx, cy = w // 2, 365 * SS
    img, d = background(w, h, cx, cy, 560 * SS)
    emblem(d, cx, cy, 640 * SS)
    f_title = font("Bold", 132)
    tw = d.textlength("REMNANT II", font=f_title)
    d.text((w / 2 - tw / 2, 660 * SS), "REMNANT II", font=f_title, fill=RED_GLOW)
    f_sub = font("Medium", 40)
    sw = spaced_width(d, "SAVE EDITOR", f_sub, 20)
    spaced(d, w / 2 - sw / 2, 820 * SS, "SAVE EDITOR", f_sub, MUTED, 20)
    loading_bar(d, 560 * SS, w - 560 * SS, 905 * SS, 6 * SS)
    feats = "  ·  ".join(FEATURES)
    f_feat = font("Medium", 27)
    fw = d.textlength(feats, font=f_feat)
    d.text((w / 2 - fw / 2, 945 * SS), feats, font=f_feat, fill=TEXT)
    f_small = font("Regular", 24)
    sw = d.textlength(SUB, font=f_small)
    d.text((w / 2 - sw / 2, 995 * SS), SUB, font=f_small, fill=MUTED)
    save(img, (W, H), out)


def save(img, size, out):
    img = img.resize(size, Image.LANCZOS)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    img.save(out, optimize=True)
    print("written", os.path.abspath(out), img.size)


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "dist")
    header(os.path.join(folder, "nexus_header.png"))
    header(os.path.join(ROOT, "docs", "header.png"))
    preview(os.path.join(folder, "nexus_preview.png"))


if __name__ == "__main__":
    main()
