"""Dark Remnant-style theme for ttk + dark replacements for messagebox/simpledialog.

The dialog functions keep the tkinter API (showinfo/showerror/askyesno/askstring/askfloat),
so the GUI can use them as drop-in replacements.
"""
import os
import sys
import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont

from .i18n import t

# --- palette -----------------------------------------------------------------
BG = "#0c0a09"        # window
PANEL = "#141110"     # tables, cards
PANEL2 = "#1b1714"    # alternate rows, buttons
RAISED = "#26201c"    # hover
FIELD = "#0f0d0b"     # entries
BORDER = "#2f2622"
TEXT = "#ddd2c3"      # bone
MUTED = "#8d8178"
DIM = "#5c534d"
RED = "#8f1a14"       # blood red
RED_HI = "#b8261d"
RED_GLOW = "#e0473b"
RED_DK = "#3e0d0a"    # selection

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
FONTS_DIR = os.path.join(ASSETS, "fonts")

FONT = ("Segoe UI", 10)
FONT_M = ("Segoe UI", 10)
FONT_B = ("Segoe UI Semibold", 10)
FONT_H = ("Segoe UI Semibold", 16)
FONT_SUB = ("Segoe UI", 9)
FONT_INFO = ("Segoe UI", 11)
FONT_TAB = ("Segoe UI Semibold", 10)

_images = {}


def register_fonts():
    """Make the bundled Montserrat (SIL OFL) available to this process only (Windows).
    Elsewhere the font is used if it is installed."""
    if sys.platform != "win32" or not os.path.isdir(FONTS_DIR):
        return
    try:
        import ctypes
        add = ctypes.windll.gdi32.AddFontResourceExW
        for n in os.listdir(FONTS_DIR):
            if n.lower().endswith(".ttf"):
                add(os.path.join(FONTS_DIR, n), 0x10, 0)  # FR_PRIVATE
    except Exception:
        pass


def _resolve_fonts(root):
    global FONT, FONT_M, FONT_B, FONT_H, FONT_SUB, FONT_INFO, FONT_TAB
    try:
        fam = set(tkfont.families(root))
    except Exception:
        fam = set()
    if "Montserrat" not in fam:
        return False
    semi = "Montserrat SemiBold" if "Montserrat SemiBold" in fam else None
    med = "Montserrat Medium" if "Montserrat Medium" in fam else None
    FONT = ("Montserrat", 9)
    FONT_M = (med, 9) if med else ("Montserrat", 9)
    FONT_B = (semi, 9) if semi else ("Montserrat", 9, "bold")
    FONT_TAB = (semi, 9) if semi else ("Montserrat", 9, "bold")
    FONT_H = ("Montserrat", 16, "bold")
    FONT_SUB = ("Montserrat", 8)
    FONT_INFO = ("Montserrat", 10)
    return True


def image(name):
    """PhotoImage from assets/<name>.png (cached; None if missing)."""
    if name in _images:
        return _images[name]
    p = os.path.join(ASSETS, name + ".png")
    img = None
    if os.path.exists(p):
        try:
            img = tk.PhotoImage(file=p)
        except tk.TclError:
            img = None
    _images[name] = img
    return img


def tab_image(name):
    """Image spec for a notebook tab: muted icon, bone-coloured when selected."""
    a, b = image("tab_" + name), image("tab_%s_on" % name)
    if a is None:
        return None
    return (a, "selected", b) if b is not None else a


def section(parent, text):
    """Section title with an ornamental divider:  TITLE  ◆─────────"""
    f = ttk.Frame(parent)
    ttk.Label(f, text=text, style="Section.TLabel").pack(side="left")
    c = tk.Canvas(f, height=10, bg=BG, highlightthickness=0, bd=0)
    c.pack(side="left", fill="x", expand=True, padx=(10, 0))

    def draw(_e=None):
        c.delete("all")
        w = c.winfo_width()
        c.create_polygon(4, 5, 8, 1, 12, 5, 8, 9, fill=RED_HI, outline="")
        c.create_line(16, 5, max(16, w - 2), 5, fill=BORDER)
    c.bind("<Configure>", draw)
    return f


def card(parent, style="Info.TLabel", **label_kw):
    """Panel with a crimson accent bar on the left. Returns (frame, label)."""
    f = tk.Frame(parent, bg=PANEL)
    tk.Frame(f, bg=RED_HI, width=3).pack(side="left", fill="y")
    lbl = ttk.Label(f, style=style, **label_kw)
    lbl.pack(side="left", fill="both", expand=True)
    return f, lbl


def apply(root):
    _resolve_fonts(root)
    root.configure(bg=BG)
    s = ttk.Style(root)
    s.theme_use("clam")
    s.configure(".", background=BG, foreground=TEXT, fieldbackground=FIELD, bordercolor=BORDER,
                lightcolor=BORDER, darkcolor=BORDER, troughcolor=BG, focuscolor=RED,
                selectbackground=RED_DK, selectforeground=TEXT, insertcolor=TEXT, font=FONT)
    s.map(".", foreground=[("disabled", DIM)])

    s.configure("TFrame", background=BG)
    s.configure("Panel.TFrame", background=PANEL)
    s.configure("Accent.TFrame", background=RED)
    s.configure("TLabel", background=BG, foreground=TEXT)
    s.configure("Muted.TLabel", foreground=MUTED, font=FONT_SUB)
    s.configure("Warn.TLabel", foreground=RED_GLOW, font=FONT_SUB)
    s.configure("Section.TLabel", foreground=TEXT, font=FONT_B)
    s.configure("Title.TLabel", foreground=TEXT, font=FONT_H)
    s.configure("Brand.TLabel", foreground=RED_GLOW, font=FONT_H)
    s.configure("Info.TLabel", background=PANEL, foreground=TEXT, font=FONT_INFO, padding=(14, 10))
    s.configure("Status.TLabel", background=PANEL, foreground=MUTED, font=FONT_SUB, padding=(10, 4))
    s.configure("Dirty.TLabel", background=PANEL, foreground=RED_GLOW, font=FONT_SUB, padding=(10, 4))

    # buttons
    s.configure("TButton", background=PANEL2, foreground=TEXT, bordercolor=BORDER, lightcolor=PANEL2,
                darkcolor=PANEL2, focusthickness=0, padding=(12, 5), relief="flat", font=FONT_M)
    s.map("TButton",
          background=[("pressed", RED_DK), ("active", RAISED), ("disabled", PANEL)],
          bordercolor=[("active", RED), ("focus", RED)],
          lightcolor=[("active", RAISED)], darkcolor=[("active", RAISED)])
    s.configure("Accent.TButton", background=RED, foreground="#fff4ec", bordercolor=RED_HI,
                lightcolor=RED, darkcolor=RED, font=FONT_B)
    s.map("Accent.TButton",
          background=[("pressed", RED_DK), ("active", RED_HI)],
          lightcolor=[("active", RED_HI)], darkcolor=[("active", RED_HI)],
          bordercolor=[("active", RED_GLOW)])

    # notebook
    s.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(0, 4, 0, 0))
    s.configure("TNotebook.Tab", background=BG, foreground=MUTED, padding=(16, 7), bordercolor=BG,
                lightcolor=BG, darkcolor=BG, font=FONT_TAB)
    s.map("TNotebook.Tab",
          background=[("selected", PANEL2), ("active", PANEL)],
          foreground=[("selected", TEXT), ("active", TEXT), ("disabled", DIM)],
          lightcolor=[("selected", RED_HI)],
          bordercolor=[("selected", BORDER)])

    # tables
    s.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXT, bordercolor=BORDER,
                lightcolor=PANEL, darkcolor=PANEL, rowheight=26, font=FONT)
    s.map("Treeview", background=[("selected", RED_DK)], foreground=[("selected", "#fff4ec")])
    s.configure("Treeview.Heading", background=PANEL2, foreground=MUTED, bordercolor=BORDER,
                lightcolor=PANEL2, darkcolor=PANEL2, relief="flat", font=FONT_B, padding=(6, 5))
    s.map("Treeview.Heading", background=[("active", RAISED)], foreground=[("active", TEXT)])
    s.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])  # no inner border

    # inputs
    s.configure("TEntry", fieldbackground=FIELD, foreground=TEXT, bordercolor=BORDER, lightcolor=FIELD,
                darkcolor=FIELD, insertcolor=TEXT, padding=(6, 4))
    s.map("TEntry", bordercolor=[("focus", RED_HI)], lightcolor=[("focus", RED)])
    s.configure("TCombobox", fieldbackground=FIELD, background=PANEL2, foreground=TEXT, arrowcolor=MUTED,
                bordercolor=BORDER, lightcolor=FIELD, darkcolor=FIELD, padding=(6, 3))
    s.map("TCombobox",
          fieldbackground=[("readonly", FIELD)], selectbackground=[("readonly", FIELD)],
          selectforeground=[("readonly", TEXT)], foreground=[("readonly", TEXT)],
          background=[("active", RAISED)], arrowcolor=[("active", RED_GLOW)],
          bordercolor=[("focus", RED_HI), ("active", RED)])
    root.option_add("*TCombobox*Listbox.background", PANEL)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", RED_DK)
    root.option_add("*TCombobox*Listbox.selectForeground", "#fff4ec")
    root.option_add("*TCombobox*Listbox.font", FONT)
    root.option_add("*TCombobox*Listbox.borderWidth", 0)

    s.configure("TRadiobutton", background=BG, foreground=TEXT, indicatorcolor=FIELD,
                indicatorbackground=FIELD, indicatorforeground=RED_GLOW, upperbordercolor=BORDER,
                lowerbordercolor=BORDER, bordercolor=BORDER, focusthickness=0, padding=(2, 3))
    s.map("TRadiobutton",
          indicatorcolor=[("selected", RED_HI), ("active", RAISED)],
          indicatorbackground=[("selected", RED_HI), ("active", RAISED)],
          upperbordercolor=[("selected", RED_GLOW)], lowerbordercolor=[("selected", RED_GLOW)],
          background=[("active", BG)], foreground=[("active", TEXT)])

    s.configure("TCheckbutton", background=BG, foreground=TEXT, indicatorcolor=FIELD,
                indicatorbackground=FIELD, indicatorforeground="#fff4ec", upperbordercolor=BORDER,
                lowerbordercolor=BORDER, bordercolor=BORDER, focusthickness=0, padding=(2, 3))
    s.map("TCheckbutton",
          indicatorcolor=[("selected", RED_HI), ("active", RAISED)],
          indicatorbackground=[("selected", RED_HI), ("active", RAISED)],
          upperbordercolor=[("selected", RED_GLOW)], lowerbordercolor=[("selected", RED_GLOW)],
          background=[("active", BG)], foreground=[("active", TEXT)])

    for orient in ("Vertical", "Horizontal"):
        s.configure("%s.TScrollbar" % orient, background=PANEL2, troughcolor=PANEL, bordercolor=PANEL,
                    lightcolor=PANEL2, darkcolor=PANEL2, arrowcolor=MUTED, gripcount=0)
        s.map("%s.TScrollbar" % orient, background=[("active", RED_DK), ("pressed", RED)],
              arrowcolor=[("active", TEXT)])
    return s


def dark_titlebar(win):
    """Windows 10 20H1+/11: dark title bar, Win11: blood-red window border."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
        dwm = ctypes.windll.dwmapi
        on = ctypes.c_int(1)
        if dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(on), ctypes.sizeof(on)) != 0:
            dwm.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(on), ctypes.sizeof(on))

        def colorref(h):
            h = h.lstrip("#")
            return ctypes.c_int(int(h[0:2], 16) | int(h[2:4], 16) << 8 | int(h[4:6], 16) << 16)
        for attr, col in ((35, BG), (34, RED), (36, TEXT)):  # caption, border, caption text
            c = colorref(col)
            dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(c), ctypes.sizeof(c))
    except Exception:
        pass


# --- dialogs -------------------------------------------------------------------

class _Dialog(tk.Toplevel):
    def __init__(self, parent, title, message, kind="info", entry=None, buttons=(("OK", True),),
                 validate=None):
        parent = parent or tk._default_root
        super().__init__(parent)
        self.withdraw()
        self.title(title)
        self.configure(bg=BG)
        self.resizable(False, False)
        self.transient(parent)
        self.result = None
        self._validate = validate

        tk.Frame(self, bg=RED if kind != "error" else RED_GLOW, height=3).pack(fill="x")
        body = ttk.Frame(self, padding=(20, 16, 20, 8))
        body.pack(fill="both", expand=True)
        glyph = {"info": "◆", "error": "✕", "question": "?", "input": "✎"}.get(kind, "◆")
        tk.Label(body, text=glyph, bg=BG, fg=RED_GLOW, font=(FONT_H[0], 17, "bold")).grid(
            row=0, column=0, sticky="n", padx=(0, 14))
        ttk.Label(body, text=title, style="Section.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Label(body, text=message, wraplength=440, justify="left").grid(row=1, column=1, sticky="w",
                                                                           pady=(4, 0))
        self.var = None
        self.err = None
        if entry is not None:
            self.var = tk.StringVar(value=entry)
            e = ttk.Entry(body, textvariable=self.var, width=36)
            e.grid(row=2, column=1, sticky="we", pady=(12, 0))
            self.err = ttk.Label(body, text="", style="Warn.TLabel")
            self.err.grid(row=3, column=1, sticky="w", pady=(4, 0))
            e.focus_set()
            e.select_range(0, "end")
            e.icursor("end")
        bar = ttk.Frame(self, padding=(20, 6, 20, 16))
        bar.pack(fill="x")
        first = None
        for i, (label, value) in enumerate(reversed(buttons)):
            b = ttk.Button(bar, text=label, style="Accent.TButton" if i == 0 else "TButton",
                           command=lambda v=value: self._done(v))
            b.pack(side="right", padx=(8, 0))
            if i == 0:
                first = b
        if entry is None and first is not None:
            first.focus_set()
        self.bind("<Return>", lambda e: self._done(buttons[-1][1]))
        self.bind("<Escape>", lambda e: self._done(buttons[0][1] if len(buttons) > 1 else buttons[-1][1]))
        self.protocol("WM_DELETE_WINDOW", lambda: self._done(None if entry is not None else
                                                             (buttons[0][1] if len(buttons) > 1 else True)))
        self.update_idletasks()
        try:
            x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_reqwidth()) // 2
            y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_reqheight()) // 3
            self.geometry("+%d+%d" % (max(x, 0), max(y, 0)))
        except Exception:
            pass
        self.deiconify()
        dark_titlebar(self)
        self.grab_set()
        self.wait_window(self)

    def _done(self, value):
        if self.var is not None and value is True:
            text = self.var.get()
            if self._validate is not None:
                ok, res = self._validate(text)
                if not ok:
                    self.err.config(text=res)
                    return
                self.result = res
            else:
                self.result = text
        elif self.var is not None:
            self.result = None
        else:
            self.result = value
        self.grab_release()
        self.destroy()


def showinfo(title, message, parent=None, **_):
    _Dialog(parent, title, message, "info")


def showerror(title, message, parent=None, **_):
    _Dialog(parent, title, message, "error")


def askyesno(title, message, parent=None, **_):
    return bool(_Dialog(parent, title, message, "question", buttons=((t("no"), False), (t("yes"), True))).result)


def askstring(title, prompt, initialvalue="", parent=None, **_):
    return _Dialog(parent, title, prompt, "input", entry=initialvalue or "",
                   buttons=((t("cancel"), False), ("OK", True))).result


def askint(title, prompt, initialvalue=0, lo=None, hi=None, parent=None):
    def val(s):
        try:
            v = int(s.strip().replace(" ", "").replace("_", ""))
        except ValueError:
            return False, t("need_int")
        if (lo is not None and v < lo) or (hi is not None and v > hi):
            return False, t("range", lo, hi)
        return True, v
    return _Dialog(parent, title, prompt, "input", entry=str(initialvalue),
                   buttons=((t("cancel"), False), ("OK", True)), validate=val).result


def askfloat(title, prompt, initialvalue=None, parent=None, **_):
    def val(s):
        try:
            return True, float(s.strip().replace(",", "."))
        except ValueError:
            return False, t("need_num")
    return _Dialog(parent, title, prompt, "input", entry="" if initialvalue is None else repr(initialvalue),
                   buttons=((t("cancel"), False), ("OK", True)), validate=val).result
