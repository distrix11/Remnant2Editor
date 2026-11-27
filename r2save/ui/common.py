"""Shared pieces of the GUI: constants, dialogs aliases, Table, DarkWindow."""
import datetime
import os
import sys
import time
import traceback
import tkinter as tk
from tkinter import ttk, filedialog

from .. import theme
from .. import i18n
from .. import settings
from ..i18n import t

from ..core import SaveFile, ByteProp, SaveFormatError, KNOWN_FILE_VERSIONS, peek_header
from ..nav import walk, fmt_value
from ..profile import Profile, CURRENCIES, ARCHETYPE_MAX_XP
from ..storage import default_save_dirs, game_running, list_backups, restore, save_dir_of
from ..world import WorldSave, is_world_save, point_hint, quest_id_of
from ..doc import Doc, StaleFileError, UnknownFormatError
from ..itemdb import db, ADD_RULES, world_label, localized
from ..analyzer import analyze

messagebox = theme
simpledialog = theme

TITLE = "Remnant 2 Save Editor"
LOG_HINT = r"%APPDATA%\Remnant2SaveEditor\editor.log"
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


def cat_label(cat):
    """Inventory category (a folder name from the item path, e.g. 'Amulets') in the UI language."""
    key = "cat_" + cat
    return t(key) if key in i18n.S else cat.replace("_", " ")


def _fmt_local(ts):
    return datetime.datetime.fromtimestamp(ts).strftime("%d.%m.%Y %H:%M:%S")


class Table(ttk.Frame):
    """Treeview + scrollbar with sortable columns. tree=True shows a first tree column.

    The tabs refill their tables after every edit. clear() remembers the selection, scroll position, sort order and
    expanded rows, and puts them back once the refill is done, so an edit does not throw the user back to the top.

    `height` is the number of rows the table asks for; the tables expand anyway, so a small value keeps the notes
    and buttons below them visible in a small window."""

    def __init__(self, master, columns, widths, height=4, tree=None):
        super().__init__(master)
        self._pending = None
        self._sort = None        # (column, reverse) of the last header click, re-applied after a refill
        cols = [c for c, _ in columns]
        self._cols = cols
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
        tv = self.tv
        if self._pending is None:
            sel = tv.selection()
            key = None
            if sel:
                it = tv.item(sel[0])
                key = (sel[0], it.get("text"), tuple(it.get("values") or ())[:1])
            opened = [i for i in tv.get_children() if tv.item(i, "open")]
            self._pending = (key, tv.yview()[0], len(tv.get_children()), opened)
            self.after_idle(self._restore)
        tv.delete(*tv.get_children())

    def _restore(self):
        """After a refill: sort order, expanded rows, selection and scroll position as they were before clear()."""
        if self._pending is None or not self.winfo_exists():
            return
        key, top, count, opened = self._pending
        self._pending = None
        tv = self.tv
        if self._sort is not None:
            self._apply_sort(*self._sort)
        for i in opened:
            if tv.exists(i):
                tv.item(i, open=True)
        if tv.selection():          # the tab selected a row itself (e.g. "Teleport to this zone")
            return
        if key is not None and tv.exists(key[0]):
            it = tv.item(key[0])
            # the same iid may be another row after a new search: keep it only if it shows the same thing
            if (it.get("text"), tuple(it.get("values") or ())[:1]) == key[1:]:
                tv.selection_set(key[0])
        if len(tv.get_children()) == count:
            tv.yview_moveto(top)
        elif tv.selection():
            tv.see(tv.selection()[0])

    def show_columns(self, hidden=()):
        """Hide some columns (e.g. technical ones) without changing the data."""
        self.tv.configure(displaycolumns=[c for c in self._cols if c not in hidden])

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
        self._apply_sort(col, rev)
        self._rev[col] = not rev
        self._sort = (col, rev)

    def _apply_sort(self, col, rev):
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


__all__ = [n for n in dir() if not n.startswith("__")]
