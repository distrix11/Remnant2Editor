"""Small animations for the Tk GUI: startup splash, tab underline that glides, content that slides in.

Tk has no per-widget transparency, so everything here is drawn on a Canvas or done with geometry / window alpha.
All of it can be switched off in the ? window ("animations": false in settings.json); the GUI then behaves exactly
as before.
"""
import math
import time
import tkinter as tk

from .. import settings
from .. import theme
from ..i18n import t

FRAME_MS = 15


def enabled():
    return settings.get("animations") is not False


def ease_out(p):
    """Cubic ease-out: fast start, soft landing."""
    p = min(max(p, 0.0), 1.0)
    return 1 - (1 - p) ** 3


def _mix(c1, c2, p):
    """Colour between c1 and c2 ('#rrggbb'), p in 0..1."""
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(x + (y - x) * min(max(p, 0.0), 1.0)) for x, y in zip(a, b))


def animate(widget, ms, step, done=None):
    """Call step(eased progress 0..1) every frame for `ms` milliseconds, then done()."""
    start = time.perf_counter()

    def tick():
        try:
            if not widget.winfo_exists():
                return
        except tk.TclError:
            return
        p = (time.perf_counter() - start) * 1000.0 / ms
        step(ease_out(p))
        if p < 1:
            widget.after(FRAME_MS, tick)
        elif done is not None:
            done()
    tick()


def fade_in(win, ms=220):
    """Window opacity 0 -> 1 (Windows / macOS; elsewhere it simply appears)."""
    try:
        win.attributes("-alpha", 0.0)
    except tk.TclError:
        return
    animate(win, ms, lambda p: win.attributes("-alpha", p))


# --- splash ------------------------------------------------------------------------------------------------------

class Splash(tk.Toplevel):
    """Borderless startup window: the emblem with a pulsing, slowly turning diamond frame, the title, and a
    progress bar that eases towards the real loading steps (step()), then fades out (finish())."""

    W, H = 460, 290

    def __init__(self, master, version):
        super().__init__(master)
        self.withdraw()
        self.overrideredirect(True)
        self.configure(bg=theme.BORDER)
        try:
            self.attributes("-topmost", True)
        except tk.TclError:
            pass
        s = max(1.0, master.winfo_fpixels("1i") / 96.0)
        self.s = s
        w, h = int(self.W * s), int(self.H * s)
        self.w, self.h = w, h
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2 - int(40 * s)
        self.geometry("%dx%d+%d+%d" % (w, h, x, y))
        c = tk.Canvas(self, width=w - 2, height=h - 2, bg=theme.BG, highlightthickness=0, bd=0)
        c.pack(padx=1, pady=1)
        self.c = c
        cx, cy = w // 2, int(96 * s)
        self.cx, self.cy = cx, cy
        c.create_rectangle(0, 0, w, int(3 * s), fill=theme.RED, outline="")
        # glow diamonds (redrawn every frame) under the emblem
        self.rings = [c.create_polygon(0, 0, 0, 0, 0, 0, outline="", fill="", width=max(1, int(s)))
                      for _ in range(3)]
        em = theme.image("emblem_64")
        if em is not None:
            self.em = c.create_image(cx, cy, image=em)
        c.create_text(cx, int(166 * s), text="REMNANT II", fill=theme.RED_GLOW, font=(theme.FONT_H[0], 18, "bold"))
        c.create_text(cx, int(190 * s), text="S A V E    E D I T O R", fill=theme.MUTED, font=theme.FONT_SUB)
        self.bx0, self.bx1 = int(60 * s), w - int(60 * s)
        self.by = int(228 * s)
        bh = max(3, int(4 * s))
        c.create_rectangle(self.bx0, self.by, self.bx1, self.by + bh, fill=theme.PANEL2, outline="")
        self.bar = c.create_rectangle(self.bx0, self.by, self.bx0, self.by + bh, fill=theme.RED_HI, outline="")
        self.shine = c.create_rectangle(0, self.by, 0, self.by + bh, fill=theme.RED_GLOW, outline="")
        self.status = c.create_text(self.bx0, self.by + int(20 * s), anchor="w", text="", fill=theme.MUTED,
                                    font=theme.FONT_SUB)
        c.create_text(self.bx1, self.by + int(20 * s), anchor="e", text="v" + version, fill=theme.DIM,
                      font=theme.FONT_SUB)
        self.shown = 0.0       # drawn progress (eases towards target)
        self.target = 0.0
        self.t0 = time.perf_counter()
        self._closing = False
        self.deiconify()
        try:
            self.attributes("-alpha", 0.0)
        except tk.TclError:
            pass
        self._tick()
        self.update()

    def _tick(self):
        if not self.winfo_exists():
            return
        now = time.perf_counter() - self.t0
        c, s = self.c, self.s
        try:                   # fade in over the first 0.25 s
            if not self._closing:
                self.attributes("-alpha", min(1.0, now / 0.25))
        except tk.TclError:
            pass
        # diamonds: breathe in size, turn slowly, glow from dark red to bright red
        for i, ring in enumerate(self.rings):
            phase = now * 2.2 - i * 0.7
            r = (46 + i * 9 + 3 * math.sin(phase)) * s
            ang = now * 0.6 + i * 0.35
            pts = []
            for k in range(4):
                a = ang + k * math.pi / 2
                pts += [self.cx + r * math.cos(a), self.cy + r * math.sin(a)]
            glow = (math.sin(phase) + 1) / 2
            col = _mix(theme.RED_DK, theme.RED_GLOW if i == 0 else theme.RED, glow * (1 - i * 0.3))
            c.coords(ring, *pts)
            c.itemconfigure(ring, outline=col)
        # progress bar eases towards the target, a highlight runs along the filled part
        self.shown += (self.target - self.shown) * 0.18
        x = self.bx0 + (self.bx1 - self.bx0) * self.shown
        c.coords(self.bar, self.bx0, self.by, x, c.coords(self.bar)[3])
        span = max(1.0, x - self.bx0)
        sx = self.bx0 + (now * 260 * s) % (span + 60 * s) - 30 * s
        c.coords(self.shine, max(self.bx0, sx), self.by, min(x, sx + 30 * s), c.coords(self.bar)[3])
        self.after(FRAME_MS, self._tick)

    def step(self, progress, text):
        """A loading step: move the bar to `progress` (0..1) and show what is being done. Pumps the event loop so
        the animation keeps running between the (blocking) loading steps."""
        self.target = max(self.target, progress)
        self.c.itemconfigure(self.status, text=text)
        self.update()

    def finish(self, done, min_total=1.1):
        """Fill the bar, keep the splash up at least `min_total` seconds in total, fade out, then done()."""
        self.step(1.0, t("sp_ready"))

        def wait():
            if time.perf_counter() - self.t0 < min_total or self.shown < 0.985:
                self.after(FRAME_MS, wait)
                return
            self._closing = True
            done()

            def out(p):
                try:
                    self.attributes("-alpha", 1 - p)
                except tk.TclError:
                    pass
            animate(self, 200, out, self.destroy)
        wait()


# --- tabs -----------------------------------------------------------------------------------------------------

class TabMotion:
    """A red underline that glides to the selected tab, and the page content that slides in from the right."""

    def __init__(self, nb):
        self.nb = nb
        self.bar = tk.Frame(nb, bg=theme.RED_HI, height=2, bd=0, highlightthickness=0)
        self._x = None            # current (x0, x1) of the underline
        self._job = 0
        nb.bind("<Configure>", lambda e: nb.after_idle(self.snap), add="+")

    def _tab_span(self, index):
        """Pixel range of tab `index` in the tab row (ttk has no bbox for tabs: probe with index('@x,y'))."""
        nb = self.nb
        y = self._row_y()
        if y is None:
            return None
        xs = []
        step = 3
        for x in range(0, nb.winfo_width(), step):
            try:
                if nb.index("@%d,%d" % (x, y)) == index:
                    xs.append(x)
            except tk.TclError:
                pass
        return (xs[0], xs[-1] + step) if xs else None

    def _row_y(self):
        """y in the middle of the tab row, and remember its bottom for the underline."""
        nb = self.nb
        x = 6
        top = bottom = None
        for y in range(0, min(120, nb.winfo_height())):
            try:
                nb.index("@%d,%d" % (x, y))
                hit = True
            except tk.TclError:
                hit = False
            if hit and top is None:
                top = y
            if hit:
                bottom = y
            elif top is not None:
                break
        if top is None:
            return None
        self._bottom = bottom
        return (top + bottom) // 2

    def snap(self):
        """Put the underline under the selected tab without animation (startup, resize, language switch)."""
        try:
            span = self._tab_span(self.nb.index("current"))
        except tk.TclError:
            return
        if span is None:
            return
        self._x = span
        self.bar.place(x=span[0], y=self._bottom - 1, width=span[1] - span[0], height=2)

    def changed(self, page=None):
        """The selected tab changed: glide the underline, slide the page content in."""
        if not enabled():
            self.snap()
            return
        try:
            span = self._tab_span(self.nb.index("current"))
        except tk.TclError:
            return
        if span is None:
            return
        if self._x is None:
            self.snap()
        else:
            (a0, a1), (b0, b1) = self._x, span
            self._job += 1
            job = self._job

            def glide(p):
                if job != self._job:
                    return
                x0, x1 = a0 + (b0 - a0) * p, a1 + (b1 - a1) * p
                self.bar.place(x=int(x0), y=self._bottom - 1, width=max(2, int(x1 - x0)), height=2)
            animate(self.bar, 220, glide)
            self._x = span
        if page is not None:
            slide_in(page)


def slide_in(page, dist=26, ms=200):
    """Content of a notebook page moves in from the right by `dist` px (animated left padding)."""
    try:
        pad = [int(str(v)) for v in str(page.cget("padding")).split()] or [4, 12, 4, 4]
    except (tk.TclError, ValueError):
        return
    while len(pad) < 4:
        pad.append(pad[-1])
    base = pad[0]
    rest = pad[1:]
    if getattr(page, "_sliding", False):
        return
    page._sliding = True

    def step(p):
        page.configure(padding=[int(base + dist * (1 - p))] + rest)

    def done():
        page.configure(padding=[base] + rest)
        page._sliding = False
    animate(page, ms, step, done)
