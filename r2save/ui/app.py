"""Main window: open files, undo history, layout, saving. Tabs live in tab_*.py mixins."""
from .common import *  # noqa: F401,F403
from .common import _ask_int, _fmt_local, _INT_TYPES, _ask_int as ask_int  # noqa: F401
from .tab_character import CharacterTab
from .tab_resources import ResourcesTab
from .tab_inventory import InventoryTab
from .tab_traits import TraitsTab
from .tab_add import AddItemTab
from .tab_teleport import TeleportTab
from .tab_analysis import AnalysisTab
from .tab_raw import RawTab
from .dialogs import DialogsMixin


class App(CharacterTab, ResourcesTab, InventoryTab, TraitsTab, AddItemTab, TeleportTab, AnalysisTab, RawTab, DialogsMixin, tk.Tk):
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
        ttk.Button(langs, text="?", width=3, command=self.show_about).pack(side="right", padx=(10, 0))
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
        over = self.traits_overspent() if self.pd is not None and self.pd.dirty else None
        if over is not None and not messagebox.askyesno(TITLE, t("tr_over_save", over[0], over[1])):
            return
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
