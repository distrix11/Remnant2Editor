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


__all__ = [n for n in dir() if not n.startswith("__")]
