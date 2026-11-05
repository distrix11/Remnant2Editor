"""Tkinter GUI for the Remnant 2 save editor (standard library only)."""
import datetime
import os
import sys
import time
import traceback
import tkinter as tk
from tkinter import ttk, filedialog

from . import theme
from . import i18n
from .i18n import t

from .core import SaveFile, ByteProp, SaveFormatError
from .nav import walk, fmt_value
from .profile import Profile, CURRENCIES, ARCHETYPE_MAX_XP
from .storage import default_save_dirs, game_running, list_backups, restore, save_dir_of
from .world import WorldSave, is_world_save, point_hint, quest_id_of
from .doc import Doc, StaleFileError
from .itemdb import db, ADD_RULES, world_label, localized
from .analyzer import analyze

# dark dialogs with the tkinter messagebox/simpledialog API
messagebox = theme
simpledialog = theme

TITLE = "Remnant 2 Save Editor"
RAW_LIMIT = 3000
TAB_ADD = 4
TAB_TP = 5
TAB_AN = 6
TAB_RAW = 7
PROFILE_TABS = (0, 1, 2, 3, 4)
ALL = "__all__"

_INT_TYPES = {
    "IntProperty": (-2**31, 2**31 - 1), "Int16Property": (-2**15, 2**15 - 1),
    "Int64Property": (-2**63, 2**63 - 1), "UInt16Property": (0, 2**16 - 1),
    "UInt32Property": (0, 2**32 - 1), "UInt64Property": (0, 2**64 - 1),
    "BoolProperty": (0, 1),
}


def _ask_int(parent, title, prompt, initial, lo, hi):
    return theme.askint(title, "%s\n(%d … %d)" % (prompt, lo, hi), initial, lo, hi, parent=parent)


def _fmt_local(ts):
    return datetime.datetime.fromtimestamp(ts).strftime("%d.%m.%Y %H:%M:%S")


class Table(ttk.Frame):
    """Treeview + scrollbar with sortable columns. tree=True shows a first tree column."""

    def __init__(self, master, columns, widths, height=8, tree=None):
        super().__init__(master)
        cols = [c for c, _ in columns]
        self.tv = ttk.Treeview(self, columns=cols, show="tree headings" if tree else "headings",
                               height=height, selectmode="browse")
        if tree:
            label, w = tree
            self.tv.heading("#0", text=label)
            self.tv.column("#0", width=w, stretch=True)
        for (cid, label), w in zip(columns, widths):
            self.tv.heading(cid, text=label, command=(lambda c=cid: self.sort(c)) if not tree else "")
            anchor = "e" if w < 0 else "w"
            self.tv.column(cid, width=abs(w), anchor=anchor, stretch=(w > 200))
        sb = ttk.Scrollbar(self, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=sb.set)
        self.tv.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.tv.tag_configure("odd", background=theme.PANEL2)
        self.tv.tag_configure("muted", foreground=theme.MUTED)
        self.tv.tag_configure("miss", foreground=theme.RED_GLOW)
        self.tv.tag_configure("cur", foreground="#fff4ec")
        self._rev = {}

    def clear(self):
        self.tv.delete(*self.tv.get_children())

    def add(self, iid, values, tags=()):
        odd = len(self.tv.get_children()) % 2
        self.tv.insert("", "end", iid=str(iid), values=values, tags=(("odd",) if odd else ()) + tuple(tags))

    def selected(self):
        s = self.tv.selection()
        return s[0] if s else None

    def select(self, iid):
        iid = str(iid)
        if self.tv.exists(iid):
            self.tv.selection_set(iid)
            self.tv.see(iid)

    def sort(self, col):
        rev = self._rev.get(col, False)
        rows = [(self.tv.set(k, col), k) for k in self.tv.get_children("")]

        def key(x):
            v = x[0].lstrip("x+▶ ").replace(" ", "")
            try:
                return (0, float(v), "")
            except ValueError:
                return (1, 0.0, x[0].lower())
        rows.sort(key=key, reverse=rev)
        for i, (_, k) in enumerate(rows):
            self.tv.move(k, "", i)
            tags = [tg for tg in self.tv.item(k, "tags") if tg != "odd"]
            self.tv.item(k, tags=(["odd"] if i % 2 else []) + tags)
        self._rev[col] = not rev


class DarkWindow(tk.Toplevel):
    def __init__(self, master, title, size="820x480"):
        super().__init__(master)
        self.withdraw()
        self.title(title)
        self.configure(bg=theme.BG)
        self.transient(master)
        self.geometry(size)
        tk.Frame(self, bg=theme.RED, height=3).pack(fill="x")
        self.body = ttk.Frame(self, padding=14)
        self.body.pack(fill="both", expand=True)
        self.bind("<Escape>", lambda e: self.destroy())
        try:
            x = master.winfo_rootx() + 60
            y = master.winfo_rooty() + 60
            self.geometry("+%d+%d" % (x, y))
        except Exception:
            pass
        self.deiconify()
        theme.dark_titlebar(self)
        self.grab_set()


class App(tk.Tk):
    def __init__(self, path=None):
        theme.register_fonts()
        super().__init__()
        i18n.load_lang()
        self.title(TITLE)
        self.geometry("1140x740")
        self.minsize(860, 560)
        self.pd = None           # Doc: profile.sav
        self.wd = None           # Doc: save_N.sav
        self.log = []            # [(doc, description)] in order, for undo / change list
        self.prof = None
        self.ws = None
        self.char = None
        self._chars = []
        self._raw_rows = []
        self._raw_src = "p"
        self._inv_items = {}
        self._cat_value = ALL
        self._tp_rows = []
        self._tp_world = None
        self._tp_focus_zone = None
        self._an_world = None
        self._an_rows = {}
        self._cat_rows = []
        self._last_focus_check = 0.0
        theme.apply(self)
        emblem = theme.image("emblem_64")
        if emblem is not None:
            self.iconphoto(True, emblem)
        self._build()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.bind("<FocusIn>", self._on_focus, add="+")
        self.bind_all("<Control-z>", lambda e: self.undo_last())
        self.bind_all("<Control-s>", lambda e: self.save())
        if path is None:
            path = self._default_profile()
        if path:
            self.after(50, lambda: self.load(path))

    # ------------------------------------------------------------------ docs
    def docs(self):
        return [d for d in (self.pd, self.wd) if d is not None]

    @property
    def main_doc(self):
        return self.pd or self.wd

    @property
    def dirty(self):
        return any(d.dirty for d in self.docs())

    def _rewrap(self):
        """Rebuild the high level wrappers after a doc's SaveFile was replaced."""
        slot = self.char.slot if self.char is not None else None
        self.prof = None
        if self.pd is not None and self.pd.sf.is_profile:
            self.prof = Profile(self.pd.sf)
            self._chars = self.prof.characters()
            self.char = None
            if self._chars:
                want = slot if slot is not None else self.prof.active_slot
                self.char = next((c for c in self._chars if c.slot == want), self._chars[0])
        else:
            self._chars, self.char = [], None
        self.ws = WorldSave(self.wd.sf) if self.wd is not None else None

    def _edit(self, doc, desc, fn):
        """Run fn() as one undoable change of doc. desc may be a callable taking fn's result."""
        before = doc.snapshot()
        try:
            res = fn()
        except (ValueError, SaveFormatError) as e:
            doc.restore(before)
            self._rewrap()
            self.refresh()
            messagebox.showerror(TITLE, str(e))
            return None
        text = desc(res) if callable(desc) else desc
        doc.push(text, before)
        self.log.append((doc, text))
        self.refresh()
        self.set_status("● %s — %s" % (text, t("unsaved")), dirty=True)
        return res

    def undo_last(self):
        if not self.log:
            self.set_status(t("nothing_to_undo"))
            return
        doc, _ = self.log.pop()
        text = doc.undo()
        self._rewrap()
        self.refresh()
        self.set_status(t("undone", text), dirty=self.dirty)

    def undo_all(self):
        while self.log:
            doc, _ = self.log.pop()
            doc.undo()
        self._rewrap()
        self.refresh()
        self.set_status(t("undone", "*"))

    # ------------------------------------------------------------------ layout
    def _build(self):
        head = ttk.Frame(self, padding=(14, 10, 14, 6))
        head.pack(fill="x")
        em = theme.image("emblem_36")
        if em is not None:
            ttk.Label(head, image=em).pack(side="left", padx=(0, 10))
        ttk.Label(head, text="REMNANT", style="Brand.TLabel").pack(side="left")
        ttk.Label(head, text=" II", style="Title.TLabel").pack(side="left")
        ttk.Label(head, text="   " + "  ".join("SAVE EDITOR".split(" ")).replace("", " ").strip(),
                  style="Muted.TLabel").pack(side="left", padx=(10, 0), pady=(6, 0))
        langs = ttk.Frame(head)
        langs.pack(side="right")
        for code in reversed(i18n.LANGS):
            ttk.Button(langs, text=code.upper(), width=4,
                       style="Accent.TButton" if code == i18n.get_lang() else "TButton",
                       command=lambda c=code: self.switch_lang(c)).pack(side="right", padx=(4, 0))
        self.file_lbl = ttk.Label(head, text=self.main_doc.path if self.main_doc else t("no_file"),
                                  style="Muted.TLabel")
        self.file_lbl.pack(side="right", pady=(6, 0), padx=(0, 14))
        tk.Frame(self, bg=theme.RED, height=2).pack(fill="x", padx=14)
        bar = ttk.Frame(self, padding=(14, 10, 14, 6))
        bar.pack(fill="x")
        ttk.Button(bar, text=t("open"), command=self.open_dialog).pack(side="left")
        ttk.Button(bar, text=t("reload"), command=self.reload).pack(side="left", padx=(6, 0))
        self.save_btn = ttk.Button(bar, text=t("save"), style="Accent.TButton", command=self.save)
        self.save_btn.pack(side="left", padx=(6, 0))
        self.changes_btn = ttk.Button(bar, text=t("changes", 0), command=self.show_changes)
        self.changes_btn.pack(side="left", padx=(6, 0))
        ttk.Button(bar, text=t("undo"), command=self.undo_last).pack(side="left", padx=(6, 0))
        ttk.Button(bar, text=t("backups"), command=self.show_backups).pack(side="left", padx=(6, 0))
        ttk.Label(bar, text=t("character")).pack(side="left", padx=(18, 4))
        self.char_cb = ttk.Combobox(bar, state="readonly", width=34)
        self.char_cb.pack(side="left")
        self.char_cb.bind("<<ComboboxSelected>>", self._on_char)

        self.status = ttk.Label(self, text="", style="Status.TLabel", anchor="w")
        self.status.pack(side="bottom", fill="x")
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=14, pady=(0, 8))
        self.nb.bind("<<NotebookTabChanged>>", self._on_tab)
        self._tab_overview()
        self._tab_currency()
        self._tab_inventory()
        self._tab_traits()
        self._tab_add()
        self._tab_teleport()
        self._tab_analysis()
        self._tab_raw()

    def _frame(self, title, icon=None):
        f = ttk.Frame(self.nb, padding=(4, 12, 4, 4))
        img = theme.tab_image(icon) if icon else None
        if img is not None:
            self.nb.add(f, text=" " + title, image=img, compound="left")
        else:
            self.nb.add(f, text=title)
        return f

    def _tab_overview(self):
        f = self._frame(t("tab_char"), "character")
        card, self.ov_lbl = theme.card(f, text="", justify="left")
        card.pack(anchor="w", fill="x")
        theme.section(f, t("archetypes_hdr")).pack(fill="x", pady=(14, 6))
        self.arch_t = Table(f, [("name", t("col_arch")), ("level", t("col_level")), ("xp", "XP"),
                                ("slot", t("col_equipped"))], [220, -80, -100, 120])
        self.arch_t.pack(fill="both", expand=True)
        b = ttk.Frame(f)
        b.pack(anchor="w", pady=(6, 0))
        ttk.Button(b, text=t("set_xp"), command=self.arch_set_xp).pack(side="left")
        ttk.Button(b, text=t("max_level"), command=lambda: self.arch_set_xp(ARCHETYPE_MAX_XP)).pack(
            side="left", padx=6)
        ttk.Label(f, style="Muted.TLabel", text=t("arch_note")).pack(anchor="w", pady=(8, 0))
        self.arch_t.tv.bind("<Double-1>", lambda e: self.arch_set_xp())

    def _tab_currency(self):
        f = self._frame(t("tab_res"), "resources")
        self.cur_t = Table(f, [("name", t("col_res")), ("qty", t("col_qty"))], [320, -140])
        self.cur_t.pack(fill="both", expand=True)
        b = ttk.Frame(f)
        b.pack(anchor="w", pady=(6, 0))
        ttk.Button(b, text=t("edit"), command=self.cur_edit).pack(side="left")
        ttk.Label(f, style="Muted.TLabel", text=t("res_note")).pack(anchor="w", pady=(8, 0))
        self.cur_t.tv.bind("<Double-1>", lambda e: self.cur_edit())

    def _tab_inventory(self):
        f = self._frame(t("tab_inv"), "inventory")
        top = ttk.Frame(f)
        top.pack(fill="x", pady=(0, 6))
        ttk.Label(top, text=t("search")).pack(side="left")
        self.inv_q = tk.StringVar()
        ttk.Entry(top, textvariable=self.inv_q, width=30).pack(side="left", padx=4)
        self.inv_q.trace_add("write", lambda *a: self.fill_inventory())
        ttk.Label(top, text=t("category")).pack(side="left", padx=(12, 4))
        self.inv_cat = ttk.Combobox(top, state="readonly", width=20)
        self.inv_cat.pack(side="left")
        self.inv_cat.bind("<<ComboboxSelected>>", self._on_cat)
        self.inv_count = ttk.Label(top, text="", style="Muted.TLabel")
        self.inv_count.pack(side="left", padx=12)
        self.inv_t = Table(f, [("name", t("col_item")), ("cat", t("col_cat")), ("type", t("col_type")),
                               ("qty", t("col_qty_s")), ("lvl", t("col_level")), ("id", "ID")],
                           [300, 130, 200, -80, -70, -60])
        self.inv_t.pack(fill="both", expand=True)
        b = ttk.Frame(f)
        b.pack(anchor="w", pady=(6, 0))
        ttk.Button(b, text=t("qty_btn"), command=self.inv_qty).pack(side="left")
        ttk.Button(b, text=t("level_btn"), command=self.inv_level).pack(side="left", padx=6)
        self.inv_path = ttk.Label(f, text="", style="Muted.TLabel")
        self.inv_path.pack(anchor="w", pady=(6, 0))
        self.inv_t.tv.bind("<<TreeviewSelect>>", self._inv_sel)
        self.inv_t.tv.bind("<Double-1>", lambda e: self.inv_dbl())

    def _tab_traits(self):
        f = self._frame(t("tab_traits"), "traits")
        self.tr_t = Table(f, [("name", t("col_trait")), ("kind", t("col_kind")), ("lvl", t("col_level"))],
                          [300, 140, -80])
        self.tr_t.pack(fill="both", expand=True)
        b = ttk.Frame(f)
        b.pack(anchor="w", pady=(6, 0))
        ttk.Button(b, text=t("trait_level_btn"), command=self.trait_level).pack(side="left")
        ttk.Label(f, style="Muted.TLabel", text=t("traits_note"), wraplength=1000).pack(anchor="w", pady=(8, 0))
        self.tr_t.tv.bind("<Double-1>", lambda e: self.trait_level())

    def _tab_add(self):
        f = self._frame(t("tab_add"), "add")
        top = ttk.Frame(f)
        top.pack(fill="x", pady=(0, 6))
        ttk.Label(top, text=t("search")).pack(side="left")
        self.cat_q = tk.StringVar()
        ttk.Entry(top, textvariable=self.cat_q, width=28).pack(side="left", padx=4)
        self.cat_q.trace_add("write", lambda *a: self.fill_catalog())
        ttk.Label(top, text=t("item_type")).pack(side="left", padx=(12, 4))
        self.cat_type = ttk.Combobox(top, state="readonly", width=16)
        self._cat_types = [ALL] + sorted(ADD_RULES)
        self.cat_type["values"] = [t("all")] + [t("itype_" + k) for k in self._cat_types[1:]]
        self.cat_type.current(0)
        self.cat_type.pack(side="left")
        self.cat_type.bind("<<ComboboxSelected>>", lambda e: self.fill_catalog())
        self.cat_hide = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text=t("hide_owned"), variable=self.cat_hide,
                        command=self.fill_catalog).pack(side="left", padx=(14, 0))
        self.cat_count = ttk.Label(top, text="", style="Muted.TLabel")
        self.cat_count.pack(side="left", padx=12)
        self.cat_t = Table(f, [("name", t("col_item")), ("type", t("col_type_s")), ("world", t("col_world")),
                               ("have", t("col_have"))], [320, 130, 220, -70], height=7)
        self.cat_t.pack(fill="both", expand=True)
        self.cat_note = ttk.Label(f, text="", style="Muted.TLabel", wraplength=1050, justify="left")
        self.cat_note.pack(anchor="w", pady=(4, 0))
        r = ttk.Frame(f)
        r.pack(anchor="w", pady=6)
        ttk.Label(r, text=t("quantity")).pack(side="left")
        self.cat_qty = tk.StringVar(value="1")
        ttk.Entry(r, textvariable=self.cat_qty, width=8).pack(side="left", padx=4)
        ttk.Button(r, text=t("add_selected"), style="Accent.TButton", command=self.add_from_catalog).pack(
            side="left", padx=(8, 0))
        ttk.Label(f, text=t("catalog_note"), style="Muted.TLabel", wraplength=1050).pack(anchor="w")
        self.cat_t.tv.bind("<<TreeviewSelect>>", self._cat_sel)
        self.cat_t.tv.bind("<Double-1>", lambda e: self.add_from_catalog())

        theme.section(f, t("manual_hdr")).pack(fill="x", pady=(8, 4))
        m = ttk.Frame(f)
        m.pack(fill="x")
        self.add_path = tk.StringVar()
        ttk.Entry(m, textvariable=self.add_path, width=80).pack(side="left", fill="x", expand=True)
        self.add_kind = tk.StringVar(value="ItemInstanceData")
        m1 = ttk.Frame(f)
        m1.pack(anchor="w", pady=(2, 0))
        ttk.Radiobutton(m1, text=t("kind_material"), value="ItemInstanceData",
                        variable=self.add_kind).pack(side="left")
        ttk.Radiobutton(m1, text=t("kind_equipment"), value="EquipmentInstanceData",
                        variable=self.add_kind).pack(side="left", padx=(12, 0))
        m2 = ttk.Frame(f)
        m2.pack(anchor="w", pady=(4, 0))
        ttk.Label(m2, text=t("quantity")).pack(side="left")
        self.add_qty = tk.StringVar(value="1")
        ttk.Entry(m2, textvariable=self.add_qty, width=8).pack(side="left", padx=4)
        ttk.Button(m2, text=t("add"), command=self.add_item).pack(side="left", padx=(8, 0))
        ttk.Label(m2, style="Warn.TLabel", text=t("add_warn").split("\n")[0]).pack(side="left", padx=(12, 0))

    def _tab_teleport(self):
        f = self._frame(t("tab_tp"), "teleport")
        top = ttk.Frame(f)
        top.pack(fill="x", pady=(0, 6))
        ttk.Label(top, text=t("world")).pack(side="left")
        self.tp_world_cb = ttk.Combobox(top, state="readonly", width=34)
        self.tp_world_cb.pack(side="left", padx=4)
        self.tp_world_cb.bind("<<ComboboxSelected>>", lambda e: self._tp_pick_world())
        self.tp_unvisited = tk.BooleanVar(value=False)
        self.tp_links = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text=t("show_unvisited"), variable=self.tp_unvisited,
                        command=self.fill_teleport).pack(side="left", padx=(16, 0))
        ttk.Checkbutton(top, text=t("show_links"), variable=self.tp_links,
                        command=self.fill_teleport).pack(side="left", padx=(12, 0))
        card, self.tp_info = theme.card(f, text="", justify="left")
        card.pack(anchor="w", fill="x", pady=(0, 6))
        bm = ttk.Frame(f)
        bm.pack(fill="x", pady=(0, 2))
        self.bm_btn = ttk.Button(bm, text=t("bm_btn"), command=self.blood_moon)
        self.bm_btn.pack(side="left")
        self.bm_reset_btn = ttk.Button(bm, text=t("bm_reset_btn"), command=self.blood_moon_reset)
        self.bm_reset_btn.pack(side="left", padx=(6, 0))
        self.bm_lbl = ttk.Label(bm, text="", style="Muted.TLabel")
        self.bm_lbl.pack(side="left", padx=(10, 0))
        self.bm_warn = ttk.Label(f, text="", style="Warn.TLabel")
        self.bm_warn.pack(anchor="w", pady=(0, 6))
        self.tp_t = Table(f, [("zone", t("col_zone")), ("point", t("col_point")), ("type", t("col_type_s")),
                              ("open", t("col_open")), ("lvl", t("col_level")), ("id", t("col_id"))],
                          [210, 330, 120, 90, -60, 190])
        self.tp_t.pack(fill="both", expand=True)
        b = ttk.Frame(f)
        b.pack(anchor="w", pady=(6, 0))
        ttk.Button(b, text=t("tp_btn"), style="Accent.TButton", command=self.teleport).pack(side="left")
        ttk.Label(f, style="Muted.TLabel", text=t("tp_note")).pack(anchor="w", pady=(8, 0))
        ttk.Label(f, style="Warn.TLabel", text=t("tp_warn"), wraplength=1050).pack(anchor="w", pady=(4, 0))
        self.tp_t.tv.bind("<Double-1>", lambda e: self.teleport())

    def _tab_analysis(self):
        f = self._frame(t("tab_an"), "analysis")
        top = ttk.Frame(f)
        top.pack(fill="x", pady=(0, 6))
        ttk.Label(top, text=t("world")).pack(side="left")
        self.an_world_cb = ttk.Combobox(top, state="readonly", width=34)
        self.an_world_cb.pack(side="left", padx=4)
        self.an_world_cb.bind("<<ComboboxSelected>>", lambda e: self._an_pick_world())
        self.an_missing = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text=t("only_missing"), variable=self.an_missing,
                        command=self.fill_analysis).pack(side="left", padx=(16, 0))
        self.an_sum = ttk.Label(top, text="", style="Muted.TLabel")
        self.an_sum.pack(side="left", padx=14)
        self.an_t = Table(f, [("kind", t("col_kind")), ("where", t("col_where")), ("state", t("col_state")),
                              ("loot", t("col_loot"))], [150, 200, 100, -90], tree=(t("col_what"), 380))
        self.an_t.pack(fill="both", expand=True)
        b = ttk.Frame(f)
        b.pack(anchor="w", pady=(6, 0))
        ttk.Button(b, text=t("an_to_tp"), command=self.analysis_to_teleport).pack(side="left")
        ttk.Label(f, style="Muted.TLabel", text=t("an_note"), wraplength=1050).pack(anchor="w", pady=(8, 0))

    def _tab_raw(self):
        f = self._frame(t("tab_raw"), "raw")
        top = ttk.Frame(f)
        top.pack(fill="x", pady=(0, 6))
        ttk.Label(top, text=t("raw_source")).pack(side="left")
        self.raw_src_cb = ttk.Combobox(top, state="readonly", width=14)
        self.raw_src_cb.pack(side="left", padx=(4, 12))
        self.raw_src_cb.bind("<<ComboboxSelected>>", self._raw_pick_src)
        ttk.Label(top, text=t("path_filter")).pack(side="left")
        self.raw_q = tk.StringVar()
        e = ttk.Entry(top, textvariable=self.raw_q, width=44)
        e.pack(side="left", padx=4)
        e.bind("<Return>", lambda ev: self.fill_raw())
        ttk.Button(top, text=t("find"), command=self.fill_raw).pack(side="left")
        self.raw_count = ttk.Label(top, text="", style="Muted.TLabel")
        self.raw_count.pack(side="left", padx=12)
        self.raw_t = Table(f, [("path", t("col_path")), ("type", t("col_type_s")), ("value", t("col_value"))],
                           [640, 140, 240])
        self.raw_t.pack(fill="both", expand=True)
        b = ttk.Frame(f)
        b.pack(anchor="w", pady=(6, 0))
        ttk.Button(b, text=t("edit"), command=self.raw_edit).pack(side="left")
        ttk.Label(f, style="Muted.TLabel", text=t("raw_note")).pack(anchor="w", pady=(6, 0))
        self.raw_t.tv.bind("<Double-1>", lambda e: self.raw_edit())

    # ---------------------------------------------------------------- language
    def switch_lang(self, lang):
        if lang == i18n.get_lang():
            return
        state = {
            "tab": self.nb.index("current") if self.nb.tabs() else 0,
            "inv_q": self.inv_q.get(), "raw_q": self.raw_q.get(), "cat_q": self.cat_q.get(),
            "cat_hide": self.cat_hide.get(), "cat_type": self.cat_type.current(),
            "add_path": self.add_path.get(), "add_kind": self.add_kind.get(), "add_qty": self.add_qty.get(),
            "tp_unvisited": self.tp_unvisited.get(), "tp_links": self.tp_links.get(),
            "an_missing": self.an_missing.get(),
        }
        i18n.set_lang(lang)
        for w in self.winfo_children():
            if not isinstance(w, tk.Toplevel):
                w.destroy()
        self._build()
        self.raw_q.set(state["raw_q"])
        self.add_path.set(state["add_path"])
        self.add_kind.set(state["add_kind"])
        self.add_qty.set(state["add_qty"])
        self.tp_unvisited.set(state["tp_unvisited"])
        self.tp_links.set(state["tp_links"])
        self.an_missing.set(state["an_missing"])
        self.cat_hide.set(state["cat_hide"])
        if state["cat_type"] >= 0:
            self.cat_type.current(state["cat_type"])
        if self.main_doc is not None:
            self._apply_loaded()
        self.inv_q.set(state["inv_q"])
        self.cat_q.set(state["cat_q"])
        try:
            self.nb.select(state["tab"])
        except tk.TclError:
            pass
        if self.dirty:
            self.set_status("● " + t("unsaved"), dirty=True)

    # ----------------------------------------------------------------- loading
    def _default_profile(self):
        for d in default_save_dirs():
            p = os.path.join(d, "profile.sav")
            if os.path.exists(p):
                return p
        return None

    def open_dialog(self):
        if not self._confirm_discard():
            return
        dirs = default_save_dirs()
        p = filedialog.askopenfilename(title=t("open_title"), initialdir=dirs[0] if dirs else None,
                                       filetypes=[("Remnant 2 save", "*.sav"), (t("all_files"), "*.*")])
        if p:
            self.load(p)

    def reload(self):
        if self.main_doc is not None and self._confirm_discard():
            self.load(self.main_doc.path)

    def load(self, path, quiet=False):
        prev_slot = self.char.slot if (self.char is not None and self.pd is not None
                                       and path == self.pd.path) else None
        try:
            self.config(cursor="watch")
            self.update_idletasks()
            doc = Doc(path)
        except Exception as e:
            messagebox.showerror(TITLE, t("read_fail", path, e))
            return False
        finally:
            self.config(cursor="")
        self.log = []
        self.pd, self.wd = None, None
        if is_world_save(doc.sf):
            self.wd = doc
        else:
            self.pd = doc
        self._rewrap()
        if prev_slot is not None and self._chars:
            self.char = next((c for c in self._chars if c.slot == prev_slot), self.char)
        if self.char is not None and self.prof is not None:
            self._load_world_for(self.char)
        self._apply_loaded()
        if self.prof is None:
            self.nb.select(TAB_TP if self.wd is not None else TAB_RAW)
        if not quiet:
            self.set_status(t("loaded", os.path.basename(path), len(doc.sf.data.objects)))
        return True

    def _load_world_for(self, char):
        """Open save_<slot>.sav next to profile.sav (teleport, analysis)."""
        self.wd, self.ws = None, None
        p = os.path.join(os.path.dirname(self.pd.path), "save_%d.sav" % char.slot)
        if not os.path.exists(p):
            return
        try:
            self.wd = Doc(p)
            self.ws = WorldSave(self.wd.sf)
        except Exception as e:
            traceback.print_exc()
            self.wd, self.ws = None, None
            self.set_status(t("read_fail", p, e).replace("\n", " "))

    def _apply_loaded(self):
        """Push the loaded data into the (possibly freshly rebuilt) widgets."""
        chars = self._chars
        self.char_cb["values"] = [t("slot", c.slot, c.archetype, c.secondary, c.power_level) for c in chars]
        if self.char is not None:
            self.char_cb.current(chars.index(self.char))
        else:
            self.char_cb.set("")
        for i in PROFILE_TABS:
            self.nb.tab(i, state="normal" if self.prof else "disabled")
        for i in (TAB_TP, TAB_AN):
            self.nb.tab(i, state="normal" if self.ws is not None else "disabled")
        self.file_lbl.config(text=self.main_doc.path if self.main_doc else t("no_file"))
        srcs = []
        if self.pd is not None:
            srcs.append(("p", self.pd.name))
        if self.wd is not None:
            srcs.append(("w", self.wd.name))
        self._raw_srcs = srcs
        self.raw_src_cb["values"] = [n for _, n in srcs]
        if srcs:
            keys = [k for k, _ in srcs]
            if self._raw_src not in keys:
                self._raw_src = keys[0]
            self.raw_src_cb.current(keys.index(self._raw_src))
        self.refresh()

    def _on_char(self, _e=None):
        i = self.char_cb.current()
        if i < 0 or self._chars[i] is self.char:
            return
        if self.wd is not None and self.wd.dirty and not messagebox.askyesno(TITLE, t("world_dirty")):
            self.char_cb.current(self._chars.index(self.char))
            return
        old_wd = self.wd
        self.log = [(d, x) for d, x in self.log if d is not old_wd]
        self.char = self._chars[i]
        self._load_world_for(self.char)
        self._tp_world = None
        self._an_world = None
        self._apply_loaded()

    def _on_cat(self, _e=None):
        i = self.inv_cat.current()
        self._cat_value = self._cat_keys[i] if 0 <= i < len(self._cat_keys) else ALL
        self.fill_inventory()

    def _on_focus(self, event):
        """When the window gets focus back, check whether the game rewrote the files."""
        now = time.time()
        if now - self._last_focus_check < 1.5 or self.grab_current() is not None:
            return
        self._last_focus_check = now
        stale = [d for d in self.docs() if d.changed_on_disk()]
        if not stale:
            return
        names = ", ".join(d.name for d in stale)
        if not self.dirty:
            tab = self.nb.index("current")
            if self.load(self.main_doc.path, quiet=True):
                try:
                    self.nb.select(tab)
                except tk.TclError:
                    pass
                self.set_status(t("auto_reloaded", names))
        else:
            self.set_status(t("stale_status", names), dirty=True)

    def refresh(self):
        self._update_title()
        self.changes_btn.config(text=t("changes", len(self.log)))
        if self.char is not None:
            self.fill_overview()
            self.fill_currency()
            cats = sorted({it.category for it in self.char.items()})
            self._cat_keys = [ALL] + cats
            self.inv_cat["values"] = [t("all")] + cats
            if self._cat_value not in self._cat_keys:
                self._cat_value = ALL
            self.inv_cat.current(self._cat_keys.index(self._cat_value))
            self.fill_inventory()
            self.fill_traits()
            self.fill_catalog()
        self.fill_teleport()
        self.fill_analysis()
        self._raw_stale = True
        if self.nb.index("current") == TAB_RAW:
            self.fill_raw()

    def _on_tab(self, _e=None):
        if self.nb.index("current") == TAB_RAW and getattr(self, "_raw_stale", True):
            self.fill_raw()

    # -------------------------------------------------------------- fill tabs
    def fill_overview(self):
        c = self.char
        self.ov_lbl.config(text=t("overview", c.archetype, c.secondary, c.power_level, c.item_level,
                                  c.trait_rank, c.trait_points, c.experience))
        self.arch_t.clear()
        for i, a in enumerate(c.archetypes()):
            slot = {0: t("primary"), 1: t("secondary")}.get(a.slot, "")
            self.arch_t.add(i, (a.name, a.level, a.xp, slot))

    def fill_currency(self):
        self.cur_t.clear()
        for i, (n, p) in enumerate(CURRENCIES):
            it = self.char.find_item(p)
            self.cur_t.add(i, (self._currency_name(n, p), it.quantity if it else "—"))

    def _currency_name(self, n, p):
        name = db().name_for_path(p) or n
        if "CorruptedShard" in p and "10" not in name:
            name += " (max 10)"
        return name

    def fill_inventory(self):
        if self.char is None:
            return
        q = self.inv_q.get().lower().strip()
        cat = self._cat_value
        self.inv_t.clear()
        self._inv_items = {}
        n = 0
        for it in sorted(self.char.items(), key=lambda x: (x.category, x.name)):
            if cat != ALL and it.category != cat:
                continue
            if q and q not in ("%s %s" % (it.name, it.path)).lower():
                continue
            qty = it.quantity
            lvl = it.level
            self._inv_items[str(it.id)] = it
            self.inv_t.add(it.id, (it.name, it.category, it.instance_type or "",
                                   "" if qty is None else qty, "" if lvl is None else "+%d" % lvl, it.id))
            n += 1
        self.inv_count.config(text=t("count", n))

    def fill_traits(self):
        self.tr_t.clear()
        self._traits = self.char.traits()
        for i, tr in enumerate(self._traits):
            self.tr_t.add(i, (tr.name, t("kind_" + tr.kind), tr.level))

    def _owned_paths(self):
        return {i.path.lower() for i in self.char.items() if i.path} if self.char is not None else set()

    def fill_catalog(self):
        if self.char is None:
            return
        d = db()
        q = self.cat_q.get().lower().strip()
        ti = self.cat_type.current()
        typ = self._cat_types[ti] if 0 <= ti < len(self._cat_types) else ALL
        owned = self._owned_paths()
        hide = self.cat_hide.get()
        self.cat_t.clear()
        self._cat_rows = []
        for e in d.catalog():
            if typ != ALL and e["Type"] != typ:
                continue
            have = e["ProfileId"].lower() in owned
            if hide and have:
                continue
            name = d.item_name(e)
            if q and q not in (name + " " + d.english_name(e) + " " + e["Id"]).lower():
                continue
            self._cat_rows.append(e)
            self.cat_t.add(len(self._cat_rows) - 1, (name, t("itype_" + e["Type"]), world_label(e.get("World")),
                                                     "✓" if have else ""), tags=("muted",) if have else ())
        self.cat_count.config(text=t("count", len(self._cat_rows)))
        self.cat_note.config(text="")

    def _cat_sel(self, _e=None):
        sel = self.cat_t.selected()
        if sel is None:
            return
        e = self._cat_rows[int(sel)]
        note = e.get("Note") or ""
        self.cat_note.config(text=(t("where_get", note) + "   ·   " if note else "") + e["ProfileId"])

    def _tp_worlds(self):
        return self.ws.worlds() if self.ws is not None else []

    def _world_name(self, w):
        return t("campaign") if w.is_campaign else w.name

    def _tp_pick_world(self):
        i = self.tp_world_cb.current()
        ws = self._tp_worlds()
        if 0 <= i < len(ws):
            self._tp_world = ws[i].slot
        self.fill_teleport()

    def _current_tp_world(self):
        return next((x for x in self._tp_worlds() if x.slot == self._tp_world), None)

    def _zl(self, label):
        return localized(label, label)

    def _describe(self, w, zone_id, link_name):
        z, l = w.find(zone_id, link_name)
        if z is None:
            return w.describe(zone_id, link_name)
        if l is None:
            return "%s · %s" % (self._zl(z.label), link_name)
        return "%s · %s" % (self._zl(z.label), self._point_label(l, self._quest_names(w)))

    def _point_label(self, link, qnames):
        words = [t("hint_" + w) if ("hint_" + w) in i18n.S else w for w in point_hint(link.name_id)]
        qid = quest_id_of(link.name_id)
        qn = qnames.get(qid)
        parts = [t("type_" + link.type)]
        if qn and qn not in (link.zone.label, self._zl(link.zone.label)):
            parts.append(qn)
        if words:
            parts.append(" ".join(words))
        return " · ".join(parts)

    def _quest_names(self, w):
        d = db()
        out = {}
        for qid, (quest, state, zone_id) in w.quests().items():
            if quest.startswith(("Quest_Story_", "Quest_Global", "Quest_Event_")):
                continue
            ev = d.event(quest)
            if ev is not None:
                out[qid] = localized(quest, None) or self._zl(ev.get("Name") or ev.get("EventLocation"))
        return out

    def fill_teleport(self):
        self.tp_t.clear()
        self._tp_rows = []
        worlds = self._tp_worlds()
        self.bm_warn.config(text="")
        if not worlds:
            self.tp_world_cb["values"] = []
            self.tp_world_cb.set("")
            self.tp_info.config(text=t("no_world", self.char.slot) if self.char is not None else "")
            self.bm_lbl.config(text="")
            return
        self.tp_world_cb["values"] = [self._world_name(w) + (t("active_mark") if w.active else "") for w in worlds]
        if self._tp_world is None or self._tp_world not in [w.slot for w in worlds]:
            act = self.ws.active_world()
            self._tp_world = act.slot if act is not None else worlds[0].slot
        idx = [w.slot for w in worlds].index(self._tp_world)
        self.tp_world_cb.current(idx)
        w = worlds[idx]
        self.tp_info.config(text=t("tp_info", self._describe(w, *w.respawn), self._describe(w, *w.last_checkpoint)))
        bmo = w.blood_moon()
        if bmo is None:
            self.bm_lbl.config(text=t("bm_none"))
            self.bm_btn.state(["disabled"])
            self.bm_reset_btn.state(["disabled"])
        else:
            fmt = lambda d: d.strftime("%d.%m %H:%M") + " UTC" if d is not None else "—"
            ch = bmo.chance
            self.bm_lbl.config(text=t("bm_info", ("%g" % ch) if ch is not None else "?",
                                      fmt(bmo.last_check), fmt(bmo.last_triggered)))
            self.bm_btn.state(["!disabled"])
            self.bm_reset_btn.state(["!disabled"])
            if bmo.stuck:
                self.bm_warn.config(text=t("bm_stuck"))
        cur = w.respawn
        qnames = self._quest_names(w)
        focus_iid = None
        for z in w.zones():
            forced = self._tp_focus_zone == z.id
            if not z.visited and not self.tp_unvisited.get() and not forced:
                continue
            for l in z.links():
                if not l.can_respawn or l.disabled:
                    continue
                if not l.safe and not self.tp_links.get():
                    continue
                if not l.discovered and not self.tp_unvisited.get() and not forced:
                    continue
                name = self._point_label(l, qnames)
                is_cur = (z.id, l.name_id) == cur
                if is_cur:
                    name = "▶ " + name
                self._tp_rows.append(l)
                iid = len(self._tp_rows) - 1
                self.tp_t.add(iid, (self._zl(z.label), name, t("type_" + l.type), "✓" if l.discovered else "—",
                                    "" if z.level is None else z.level, l.name_id),
                              tags=("cur",) if is_cur else (() if l.discovered else ("muted",)))
                if forced and focus_iid is None and l.safe:
                    focus_iid = iid
        if focus_iid is not None:
            self.tp_t.select(focus_iid)
        self._tp_focus_zone = None

    def _an_pick_world(self):
        i = self.an_world_cb.current()
        ws = self._tp_worlds()
        if 0 <= i < len(ws):
            self._an_world = ws[i].slot
        self.fill_analysis()

    def fill_analysis(self):
        self.an_t.clear()
        self._an_rows = {}
        worlds = self._tp_worlds()
        if not worlds:
            self.an_world_cb["values"] = []
            self.an_world_cb.set("")
            self.an_sum.config(text="")
            return
        self.an_world_cb["values"] = [self._world_name(w) + (t("active_mark") if w.active else "") for w in worlds]
        if self._an_world is None or self._an_world not in [w.slot for w in worlds]:
            act = self.ws.active_world()
            self._an_world = act.slot if act is not None else worlds[0].slot
        idx = [w.slot for w in worlds].index(self._an_world)
        self.an_world_cb.current(idx)
        w = worlds[idx]
        try:
            entries = analyze(w, self._owned_paths())
        except Exception as e:
            traceback.print_exc()
            self.an_sum.config(text=str(e))
            return
        only_missing = self.an_missing.get()
        tv = self.an_t.tv
        n_missing = 0
        shown = 0
        for i, e in enumerate(entries):
            miss = e.missing
            n_missing += len(miss)
            if only_missing and not miss:
                continue
            loot = "%d/%d" % (len(e.loot) - len(miss), len(e.loot)) if e.loot else ""
            kind = t("an_" + e.kind.replace(" ", "_")) if ("an_" + e.kind.replace(" ", "_")) in i18n.S else e.kind
            tags = ("muted",) if (e.done and not miss) else (("miss",) if miss else ())
            iid = "e%d" % i
            tv.insert("", "end", iid=iid, text=e.name, values=(kind, e.where or "", t("state_done") if e.done else "",
                                                               loot), tags=tags, open=bool(miss) and only_missing)
            self._an_rows[iid] = e
            shown += 1
            for j, l in enumerate(e.loot):
                if only_missing and l.owned:
                    continue
                tv.insert(iid, "end", iid="%s_%d" % (iid, j), text=l.name,
                          values=(t("itype_" + l.type) if ("itype_" + l.type) in i18n.S else l.type, "", "",
                                  t("owned") if l.owned else t("missing")),
                          tags=("muted",) if l.owned else ("miss",))
                self._an_rows["%s_%d" % (iid, j)] = e
        self.an_sum.config(text=t("an_summary", shown, n_missing))

    def analysis_to_teleport(self):
        sel = self.an_t.selected()
        e = self._an_rows.get(sel) if sel else None
        if e is None:
            return
        zone_id = e.zone_id
        if zone_id is None and e.where_key:
            w = next((x for x in self._tp_worlds() if x.slot == self._an_world), None)
            z = next((z for z in w.zones() if z.label == e.where_key), None) if w else None
            zone_id = z.id if z else None
        if zone_id is None:
            return messagebox.showinfo(TITLE, t("an_no_zone"))
        # prefer the dungeon itself when the entry names one
        w = next((x for x in self._tp_worlds() if x.slot == self._an_world), None)
        if w is not None and e.where_key:
            z = next((z for z in w.zones() if z.label == e.where_key), None)
            if z is not None:
                zone_id = z.id
        self._tp_world = self._an_world
        self._tp_focus_zone = zone_id
        self.nb.select(TAB_TP)
        self.fill_teleport()

    def _raw_doc(self):
        return self.pd if self._raw_src == "p" else self.wd

    def _raw_pick_src(self, _e=None):
        i = self.raw_src_cb.current()
        if 0 <= i < len(self._raw_srcs):
            self._raw_src = self._raw_srcs[i][0]
        self.fill_raw()

    def fill_raw(self):
        doc = self._raw_doc()
        self.raw_t.clear()
        self._raw_rows = []
        if doc is None:
            self.raw_count.config(text="")
            return
        self._raw_stale = False
        q = self.raw_q.get().strip().lower()
        total = 0
        for path, p, bag, sd in walk(doc.sf):
            if q and q not in path.lower():
                continue
            total += 1
            if len(self._raw_rows) >= RAW_LIMIT:
                continue
            self._raw_rows.append((path, p))
            self.raw_t.add(len(self._raw_rows) - 1, (path, p.type.name, fmt_value(p.value)[:200]))
        self.raw_count.config(text=t("matches", total) + (t("matches_cut", RAW_LIMIT) if total > RAW_LIMIT else ""))

    # ------------------------------------------------------------------ edits
    def arch_set_xp(self, value=None):
        sel = self.arch_t.selected()
        if sel is None:
            return messagebox.showinfo(TITLE, t("pick_arch"))
        a = self.char.archetypes()[int(sel)]
        if value is None:
            value = _ask_int(self, t("arch_xp_title"), t("arch_xp_prompt", a.name, ARCHETYPE_MAX_XP),
                             a.xp, 0, ARCHETYPE_MAX_XP)
            if value is None:
                return
        old = a.xp
        self._edit(self.pd, "%s: XP %d → %d" % (a.name, old, value), lambda: a.set_xp(value))

    def cur_edit(self):
        sel = self.cur_t.selected()
        if sel is None:
            return
        name, path = CURRENCIES[int(sel)]
        name = self._currency_name(name, path)
        it = self.char.find_item(path)
        old = it.quantity if it else 0
        hi = 10 if "CorruptedShard" in path else 999999
        v = _ask_int(self, name, t("new_qty"), old or 1, 1, hi)
        if v is None:
            return
        ch = self.char
        self._edit(self.pd, "%s: %s → %d" % (name, old if it else t("none"), v), lambda: ch.set_currency(path, v))

    def _inv_sel(self, _e=None):
        it = self._cur_item()
        self.inv_path.config(text=it.path if it else "")

    def _cur_item(self):
        sel = self.inv_t.selected()
        return self._inv_items.get(sel) if sel else None

    def inv_dbl(self):
        it = self._cur_item()
        if it is None:
            return
        if it.levelable and not it.has_quantity_field:
            self.inv_level()
        else:
            self.inv_qty()

    def inv_qty(self):
        it = self._cur_item()
        if it is None:
            return
        if it.instance is None:
            return messagebox.showerror(TITLE, t("no_instance"))
        if not it.stackable and not messagebox.askyesno(TITLE, t("not_stackable", it.name, it.instance_type)):
            return
        old = it.quantity
        v = _ask_int(self, it.name, t("new_qty"), old or 1, 1, 999999)
        if v is None:
            return
        self._edit(self.pd, "%s: x%s → x%d" % (it.name, old, v), lambda: it.set_quantity(v))

    def inv_level(self):
        it = self._cur_item()
        if it is None:
            return
        if not it.levelable:
            return messagebox.showinfo(TITLE, t("not_levelable", it.name, it.instance_type))
        old = it.level or 0
        v = _ask_int(self, it.name, t("level_prompt"), old, 0, 20)
        if v is None:
            return
        self._edit(self.pd, "%s: +%d → +%d" % (it.name, old, v), lambda: it.set_level(v))

    def trait_level(self):
        sel = self.tr_t.selected()
        if sel is None:
            return
        tr = self._traits[int(sel)]
        v = _ask_int(self, tr.name, t("trait_prompt"), tr.level, 0, 10)
        if v is None:
            return
        old = tr.level
        self._edit(self.pd, "%s: %d → %d" % (tr.name, old, v), lambda: tr.set_level(v))

    def add_from_catalog(self):
        if self.char is None:
            return
        sel = self.cat_t.selected()
        if sel is None:
            return messagebox.showinfo(TITLE, t("pick_item"))
        e = self._cat_rows[int(sel)]
        name = db().item_name(e)
        if e["ProfileId"].lower() in self._owned_paths():
            return messagebox.showinfo(TITLE, t("already_have", name))
        inst, has_qty = ADD_RULES[e["Type"]]
        qty = None
        if has_qty:
            try:
                qty = int(self.cat_qty.get())
                if not 1 <= qty <= 999999:
                    raise ValueError
            except ValueError:
                return messagebox.showerror(TITLE, t("qty_int"))
        ch = self.char
        path = e["ProfileId"]
        self._edit(self.pd, t("added", name) + ("" if qty is None else " x%d" % qty),
                   lambda: ch.add_item(path, qty, inst))

    def add_item(self):
        if self.char is None:
            return
        path = self.add_path.get().strip()
        kind = self.add_kind.get()
        qty = None
        if kind == "ItemInstanceData":
            try:
                qty = int(self.add_qty.get())
                if qty < 1:
                    raise ValueError
            except ValueError:
                return messagebox.showerror(TITLE, t("qty_int"))
        ch = self.char
        self._edit(self.pd, lambda it: t("added", it.name), lambda: ch.add_item(path, qty, kind))

    def teleport(self):
        sel = self.tp_t.selected()
        if sel is None:
            return messagebox.showinfo(TITLE, t("tp_pick"))
        link = self._tp_rows[int(sel)]
        w = link.zone.world
        if not (link.safe and link.discovered and link.zone.visited):
            if not messagebox.askyesno(TITLE, t("tp_confirm_risky", self._zl(link.zone.label), link.name_id)):
                return
        if not w.active and not messagebox.askyesno(TITLE, t("tp_confirm_world", self._world_name(w))):
            return
        self._edit(self.wd, t("tp_done", self._zl(link.zone.label), link.name_id), lambda: w.teleport(link))

    def blood_moon(self):
        w = self._current_tp_world()
        bmo = w.blood_moon() if w is not None else None
        if bmo is None:
            return
        if not messagebox.askyesno(TITLE, t("bm_confirm")):
            return
        self._edit(self.wd, "%s: %s" % (self._world_name(w), t("bm_done")), bmo.force)

    def blood_moon_reset(self):
        w = self._current_tp_world()
        bmo = w.blood_moon() if w is not None else None
        if bmo is None:
            return
        self._edit(self.wd, "%s: %s" % (self._world_name(w), t("bm_reset_done")), bmo.reset)

    def raw_edit(self):
        sel = self.raw_t.selected()
        if sel is None:
            return
        doc = self._raw_doc()
        path, p = self._raw_rows[int(sel)]
        typ = p.type.name
        title = path.rsplit(".", 1)[-1]
        if typ in _INT_TYPES:
            lo, hi = _INT_TYPES[typ]
            v = _ask_int(self, title, path, p.value, lo, hi)
        elif typ in ("FloatProperty", "DoubleProperty"):
            v = simpledialog.askfloat(title, path, initialvalue=p.value, parent=self)
        elif typ in ("StrProperty",):
            v = simpledialog.askstring(title, path, initialvalue=p.value or "", parent=self)
        elif typ == "ByteProperty" and isinstance(p.value, ByteProp) and p.value.enum_name.name == "None":
            v = _ask_int(self, title, path, p.value.value, 0, 255)
            if v is None:
                return

            def setb():
                p.value.value = v
            return self._edit(doc, "%s = %d" % (path, v), setb)
        else:
            return messagebox.showinfo(TITLE, t("not_editable", typ))
        if v is None:
            return

        def setv():
            p.value = v
        self._edit(doc, "%s = %s" % (path, v), setv)

    # ------------------------------------------------------------------- save
    def save(self):
        docs = [d for d in self.docs() if d.dirty]
        if not docs:
            return messagebox.showinfo(TITLE, t("nothing_to_save"))
        stale = [d for d in docs if d.changed_on_disk()]
        if stale:
            if messagebox.askyesno(TITLE, t("stale_save", ", ".join(d.name for d in stale), len(self.log))):
                self.load(self.main_doc.path)
            else:
                self.set_status(t("stale_status", ", ".join(d.name for d in stale)), dirty=True)
            return
        if game_running():
            return messagebox.showerror(TITLE, t("game_running"))
        lines = ["• %s" % x for _, x in self.log[-15:]]
        if len(self.log) > 15:
            lines.insert(0, "…")
        if not messagebox.askyesno(TITLE, t("save_confirm", len(self.log), "\n".join(lines))):
            return
        baks = []
        try:
            for d in docs:
                baks.append(d.save(check_game=False))
        except StaleFileError as e:
            return messagebox.showerror(TITLE, t("stale_save", str(e), len(self.log)))
        except Exception as e:
            traceback.print_exc()
            return messagebox.showerror(TITLE, t("not_saved", e))
        bak = "\n".join(str(b) for b in baks)
        self.load(self.main_doc.path, quiet=True)
        self.set_status(t("saved_status", bak.replace("\n", "; ")))
        messagebox.showinfo(TITLE, t("saved_msg", bak))

    # --------------------------------------------------------------- windows
    def show_changes(self):
        win = DarkWindow(self, t("changes_title"), "760x420")
        tbl = Table(win.body, [("file", t("col_file")), ("change", t("col_change"))], [140, 560], height=12)
        tbl.pack(fill="both", expand=True)

        def fill():
            tbl.clear()
            for i, (d, x) in enumerate(self.log):
                tbl.add(i, (d.name, x))
            if not self.log:
                tbl.add("none", ("", t("no_changes_yet")), tags=("muted",))
        fill()
        b = ttk.Frame(win.body)
        b.pack(fill="x", pady=(10, 0))

        def undo_one():
            self.undo_last()
            fill()

        def undo_every():
            if self.log and messagebox.askyesno(TITLE, t("discard"), parent=win):
                self.undo_all()
                fill()
        ttk.Button(b, text=t("undo_last"), command=undo_one).pack(side="left")
        ttk.Button(b, text=t("undo_all"), command=undo_every).pack(side="left", padx=6)
        ttk.Button(b, text=t("close"), style="Accent.TButton", command=win.destroy).pack(side="right")

    def show_backups(self):
        doc = self.main_doc
        if doc is None:
            return
        sdir = save_dir_of(doc.path)
        win = DarkWindow(self, t("bk_title"), "900x520")
        tbl = Table(win.body, [("file", t("col_file")), ("src", t("col_source")), ("date", t("col_date")),
                               ("size", t("col_size"))], [160, 120, 220, -110], height=13)
        tbl.pack(fill="both", expand=True)
        details = ttk.Label(win.body, text="", style="Muted.TLabel", wraplength=860, justify="left")
        details.pack(anchor="w", pady=(6, 0))
        rows = []

        def fill():
            tbl.clear()
            rows[:] = list_backups(sdir)
            for i, b in enumerate(rows):
                tbl.add(i, (b["target"], t("src_" + b["source"]), _fmt_local(b["mtime"]),
                            "%.0f KB" % (b["size"] / 1024.0)))
            if not rows:
                tbl.add("none", (t("bk_none"), "", "", ""), tags=("muted",))

        def on_sel(_e=None):
            sel = tbl.selected()
            if sel is None or sel == "none":
                return
            b = rows[int(sel)]
            try:
                sf = SaveFile.load(b["path"])
                if sf.is_profile:
                    pr = Profile(sf)
                    ch = pr.active_character()
                    info = t("bk_details_profile", len(pr.characters()),
                             t("slot", ch.slot, ch.archetype, ch.secondary, ch.power_level) if ch else "—")
                else:
                    ws = WorldSave(sf)
                    w = ws.active_world()
                    played = sf.data.objects[0].props["TimePlayed"].value / 3600.0
                    info = t("bk_details_world", self._world_name(w) if w else "—",
                             self._describe(w, *w.respawn) if w else "—", played)
            except Exception as ex:
                info = str(ex)
            details.config(text="%s\n%s" % (b["path"], info))

        def do_restore():
            sel = tbl.selected()
            if sel is None or sel == "none":
                return
            b = rows[int(sel)]
            msg = t("bk_restore_confirm", b["target"], _fmt_local(b["mtime"]))
            if self.dirty:
                msg += t("bk_unsaved_note", len(self.log))
            if not messagebox.askyesno(TITLE, msg, parent=win):
                return
            if game_running():
                return messagebox.showerror(TITLE, t("game_running"), parent=win)
            try:
                target, safety = restore(b["path"], check_game=False)
            except Exception as ex:
                traceback.print_exc()
                return messagebox.showerror(TITLE, t("not_saved", ex), parent=win)
            main = self.main_doc.path
            self.load(main, quiet=True)
            fill()
            messagebox.showinfo(TITLE, t("bk_restored", target, b["path"], safety or "—"), parent=win)

        def open_dir():
            d = os.path.join(sdir, "_editor_backups")
            os.makedirs(d, exist_ok=True)
            if sys.platform == "win32":
                os.startfile(d)
            else:
                messagebox.showinfo(TITLE, d, parent=win)
        fill()
        tbl.tv.bind("<<TreeviewSelect>>", on_sel)
        tbl.tv.bind("<Double-1>", lambda e: do_restore())
        bar = ttk.Frame(win.body)
        bar.pack(fill="x", pady=(10, 0))
        ttk.Button(bar, text=t("restore_btn"), style="Accent.TButton", command=do_restore).pack(side="left")
        ttk.Button(bar, text=t("open_folder"), command=open_dir).pack(side="left", padx=6)
        ttk.Button(bar, text=t("close"), command=win.destroy).pack(side="right")
        ttk.Label(win.body, text=t("bk_note"), style="Muted.TLabel", wraplength=860).pack(anchor="w", pady=(8, 0))

    # ------------------------------------------------------------------ misc
    def set_status(self, s, dirty=False):
        if s and not s.startswith(("●", "⚠", "◆")):
            s = "◆  " + s
        self.status.config(text=s, style="Dirty.TLabel" if dirty else "Status.TLabel")

    def _update_title(self):
        doc = self.main_doc
        name = doc.name if doc else ""
        self.title("%s%s — %s" % ("* " if self.dirty else "", name, TITLE) if name else TITLE)

    def _confirm_discard(self):
        if not self.dirty:
            return True
        return messagebox.askyesno(TITLE, t("discard"))

    def on_close(self):
        if self._confirm_discard():
            self.destroy()


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    app = App(argv[0] if argv else None)
    theme.dark_titlebar(app)
    app.report_callback_exception = lambda *a: (traceback.print_exception(*a),
                                                messagebox.showerror(TITLE, "".join(traceback.format_exception(*a))[-1500:]))
    app.mainloop()


if __name__ == "__main__":
    main()
