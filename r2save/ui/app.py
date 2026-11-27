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
from . import anim


def _geometry_on_screen(geo):
    """True if a saved 'WxH+X+Y' still has its title bar on a connected monitor (it may have been unplugged)."""
    import re
    m = re.match(r"^(\d+)x(\d+)\+(-?\d+)\+(-?\d+)$", geo or "")
    if not m:
        return False
    w, h, x, y = map(int, m.groups())
    if w < 400 or h < 300:
        return False
    left, top, width, height = 0, 0, 1 << 16, 1 << 16
    if sys.platform == "win32":
        try:
            import ctypes
            gsm = ctypes.windll.user32.GetSystemMetrics
            left, top, width, height = gsm(76), gsm(77), gsm(78), gsm(79)   # the virtual screen (all monitors)
        except Exception:
            pass
    return left <= x + 60 and x + w - 60 <= left + width and top <= y and y + 40 <= top + height


class App(CharacterTab, ResourcesTab, InventoryTab, TraitsTab, AddItemTab, TeleportTab, AnalysisTab, RawTab, DialogsMixin, tk.Tk):
    def __init__(self, path=None, splash=False):
        theme.register_fonts()
        # no settings.json yet = a fresh install (no "What's new" then); read before anything writes the file
        self._fresh_install = not os.path.exists(settings.PATH)
        super().__init__()
        i18n.load_lang()
        self.title(TITLE)
        self._prefetched = {}    # path -> Doc parsed while the splash was up
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
        sp = None
        if splash and anim.enabled():
            from .. import __version__
            self.withdraw()
            sp = anim.Splash(self, __version__)
            sp.step(0.15, t("sp_ui"))
        self._build()
        self._place_window()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.bind("<FocusIn>", self._on_focus, add="+")
        # main window only (not dialogs); keycode makes Ctrl+Z / Ctrl+S work with a Cyrillic keyboard layout too
        self.bind("<Control-KeyPress>", self._on_ctrl_key)
        if path is None:
            path = self._default_profile()
        self._game_state = False
        self._game_thread = None
        if sp is None:
            self._start(path)
            return
        sp.step(0.45, t("sp_db"))
        db().catalog()
        if path:
            sp.step(0.65, t("sp_save"))
            self._prefetch(path, sp)
        sp.finish(lambda: self._reveal(path))

    def _start(self, path):
        """Everything that runs once the main window is visible."""
        if path:
            self.after(50, lambda: self.load(path))
        self.after(80, self._restore_tab)
        self.after(700, self._maybe_whats_new)
        self.after(500, self._game_tick)
        from .. import updates
        if updates.due():
            self.after(4000, self.start_update_check)

    def _reveal(self, path):
        """Splash done: show the main window with a short fade-in."""
        self.deiconify()
        theme.dark_titlebar(self)
        anim.fade_in(self)
        self.after(30, self.tab_motion.snap)
        self._start(path)

    def _prefetch(self, path, sp):
        """Parse the save files while the splash is up, so load() later only wraps them. Errors are left for load()
        to report with its usual messages."""
        try:
            doc = Doc(path)
            self._prefetched[path] = doc
            if doc.sf.is_profile:
                pr = Profile(doc.sf)
                ch = pr.active_character()
                if ch is not None:
                    sp.step(0.85, t("sp_world"))
                    wp = os.path.join(os.path.dirname(path), "save_%d.sav" % ch.slot)
                    if os.path.exists(wp):
                        self._prefetched[wp] = Doc(wp)
        except Exception:
            traceback.print_exc()

    def _open_doc(self, path):
        """A Doc for path: the one parsed during the splash if it is still current, else a fresh read."""
        doc = self._prefetched.pop(path, None)
        if doc is not None and not doc.changed_on_disk():
            return doc
        return Doc(path)

    # --- window size, tab and worlds remembered in settings.json ---------------------------------------------------

    def _place_window(self):
        """Last window size/position if it still fits a screen, else a default scaled for the display (125 % / 150 %
        scaling makes the text bigger, so the 100 % size would cut off tabs and notes)."""
        self.update_idletasks()
        scale = max(1.0, self.winfo_fpixels("1i") / 96.0)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        req_w, req_h = self.winfo_reqwidth(), self.winfo_reqheight()
        self.minsize(min(int(860 * scale), sw), min(int(560 * scale), sh))
        w = min(max(int(1180 * scale), req_w), sw - 40)
        h = min(max(int(760 * scale), req_h), sh - 80)
        geo = "%dx%d" % (w, h)
        saved = settings.get("window")
        if isinstance(saved, str) and _geometry_on_screen(saved):
            geo = saved
        self.geometry(geo)
        if settings.get("window_zoomed"):
            try:
                self.state("zoomed")
            except tk.TclError:
                pass

    def _save_ui_state(self):
        try:
            zoomed = self.state() == "zoomed"
            settings.set("window_zoomed", zoomed)
            if self.state() == "normal":
                settings.set("window", self.geometry())
            settings.set("tab", self.nb.index("current"))
        except tk.TclError:
            pass

    def _restore_tab(self):
        tab = settings.get("tab")
        if not isinstance(tab, int) or not 0 <= tab < len(self.nb.tabs()):
            return
        if self.prof is None and tab in PROFILE_TABS:
            return      # load() picked the right tab for a world-only file
        try:
            if str(self.nb.tab(tab, "state")) == "normal":
                self.nb.select(tab)
        except tk.TclError:
            pass

    def _remembered_world(self, kind):
        """World slot the user last picked on the Teleport ('tp') or Analysis ('an') tab for this world file."""
        if self.wd is None:
            return None
        v = (settings.get("worlds") or {}).get(self.wd.name, {}).get(kind)
        return v if isinstance(v, int) else None

    def _remember_world(self, kind, slot):
        if self.wd is None:
            return
        allw = settings.get("worlds")
        allw = allw if isinstance(allw, dict) else {}
        entry = allw.get(self.wd.name) if isinstance(allw.get(self.wd.name), dict) else {}
        entry[kind] = slot
        allw[self.wd.name] = entry
        settings.set("worlds", allw)

    def _maybe_whats_new(self):
        """Once after an update: what changed in this version. A fresh install just records the version."""
        from .. import __version__
        seen = settings.get("last_seen_version")
        if seen == __version__:
            return
        settings.set("last_seen_version", __version__)
        if not self._fresh_install:
            self.show_whats_new()

    def _on_ctrl_key(self, e):
        k = (e.keysym or "").lower()
        if sys.platform == "win32":     # Windows virtual-key codes do not depend on the layout
            k = {90: "z", 83: "s"}.get(e.keycode, k)
        if k == "z":
            self.undo_last()
            return "break"
        if k == "s":
            self.save()
            return "break"
        return None

    def _game_tick(self):
        """Every few seconds: show a banner while Remnant 2 runs. `tasklist` runs in a thread so the UI never waits."""
        import threading

        def work():
            try:
                self._game_state = bool(game_running())
            except Exception:  # noqa: BLE001
                self._game_state = False
        if self._game_thread is None or not self._game_thread.is_alive():
            self._game_thread = threading.Thread(target=work, daemon=True)
            self._game_thread.start()
        shown = self.game_banner.winfo_manager() != ""
        self.game_banner.config(wraplength=max(360, self.winfo_width() - 90))
        if self._game_state and not shown:
            self.game_banner.pack(fill="x", padx=14, pady=(6, 0), before=self._top_bar)
        elif not self._game_state and shown:
            self.game_banner.pack_forget()
        self.after(4000, self._game_tick)

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
        if doc is not None and doc.read_only:
            messagebox.showinfo(TITLE, t("ro_edit", doc.name))
            return None
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
        self.show_tech = tk.BooleanVar(value=bool(settings.get("show_tech")))
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
        # one button with the current language; a click opens the list of languages
        self.lang_btn = ttk.Button(langs, text=i18n.get_lang().upper() + "  ▾", width=6,
                                   command=self._lang_menu)
        self.lang_btn.pack(side="right")
        self.file_lbl = ttk.Label(head, text="", style="Muted.TLabel", anchor="e")
        self.file_lbl.pack(side="right", fill="x", expand=True, pady=(6, 0), padx=(18, 14))
        self._set_file_label()
        tk.Frame(self, bg=theme.RED, height=2).pack(fill="x", padx=14)
        self.game_banner = ttk.Label(self, text=t("game_banner"), style="InfoWarn.TLabel", wraplength=1080,
                                     justify="left")
        bar = ttk.Frame(self, padding=(14, 10, 14, 6))
        bar.pack(fill="x")
        self._top_bar = bar
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
        self._apply_tech()
        self.tab_motion = anim.TabMotion(self.nb)
        self.after(60, self.tab_motion.snap)

    def _frame(self, title, icon=None):
        f = ttk.Frame(self.nb, padding=(4, 12, 4, 4))
        img = theme.tab_image(icon) if icon else None
        if img is not None:
            self.nb.add(f, text=" " + title, image=img, compound="left")
        else:
            self.nb.add(f, text=title)
        return f

    def _lang_menu(self):
        m = tk.Menu(self, tearoff=0, bg=theme.PANEL, fg=theme.TEXT, activebackground=theme.RED_DK,
                    activeforeground="#fff4ec", bd=0, font=theme.FONT_M)
        cur = i18n.get_lang()
        for code in i18n.LANGS:
            m.add_command(label="%s  %s  %s" % ("●" if code == cur else "  ", code.upper(), i18n.LANG_NAMES[code]),
                          command=lambda c=code: self.switch_lang(c))
        b = self.lang_btn
        try:
            m.tk_popup(b.winfo_rootx(), b.winfo_rooty() + b.winfo_height())
        finally:
            m.grab_release()

    def _set_file_label(self):
        """Path of the open file, shortened from the left so it fits next to the title (Backups… shows it in full)."""
        doc = self.main_doc
        if doc is None:
            self.file_lbl.config(text=t("no_file"))
            return
        p = os.path.normpath(doc.path)
        parts = p.split(os.sep)
        text = p if len(p) <= 60 else "…" + os.sep + os.sep.join(parts[-3:])
        if len(text) > 60:
            text = "…" + text[-59:]
        self.file_lbl.config(text=text)

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
            doc = self._open_doc(path)
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror(TITLE, self._read_error(path, e))
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
        self._warn_read_only()
        return True

    def _read_error(self, path, e):
        """A message a player can act on, for a file the editor could not open."""
        name = os.path.basename(path)
        if "corrupted" in str(e):
            return t("err_corrupt", name)
        version, build = peek_header(path)
        return t("err_format", name, version if version is not None else "?", build if build is not None else "?",
                 ", ".join(map(str, KNOWN_FILE_VERSIONS)), LOG_HINT, "%s: %s" % (type(e).__name__, e))

    def _warn_read_only(self):
        """Tell once per load when a file is open read-only (format not fully understood)."""
        for d in (self.pd, self.wd):
            if d is not None and d.read_only:
                version, build = peek_header(d.path)
                self.set_status(t("ro_status", d.name), dirty=True)
                messagebox.showinfo(TITLE, t("ro_format", d.name, version, build, LOG_HINT))

    def _load_world_for(self, char):
        """Open save_<slot>.sav next to profile.sav (teleport, analysis)."""
        self.wd, self.ws = None, None
        p = os.path.join(os.path.dirname(self.pd.path), "save_%d.sav" % char.slot)
        if not os.path.exists(p):
            return
        try:
            self.wd = self._open_doc(p)
            self.ws = WorldSave(self.wd.sf)
        except Exception as e:
            traceback.print_exc()
            self.wd, self.ws = None, None
            self.set_status(t("world_read_fail", os.path.basename(p), LOG_HINT), dirty=True)

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
        self._set_file_label()
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
            cats = sorted({it.category for it in self.char.items()}, key=lambda c: cat_label(c).lower())
            self._cat_keys = [ALL] + cats
            self.inv_cat["values"] = [t("all")] + [cat_label(c) for c in cats]
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
        tm = getattr(self, "tab_motion", None)
        if tm is not None and self.winfo_viewable():
            try:
                tm.changed(self.nametowidget(self.nb.select()))
            except (KeyError, tk.TclError):
                tm.snap()

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
        saved = []
        try:
            for d in docs:
                baks.append(d.save(check_game=False))
                saved.append(d)
        except Exception as e:
            if not isinstance(e, (StaleFileError, UnknownFormatError)):
                traceback.print_exc()
            if isinstance(e, StaleFileError):
                msg = t("stale_save", str(e), len(self.log))
            elif isinstance(e, UnknownFormatError):
                msg = t("err_ro_save", str(e))
            elif "verification failed" in str(e) or "unknown save format" in str(e):
                msg = t("err_verify", LOG_HINT, e)
            else:
                msg = t("not_saved", e)
            if saved:
                # some files are already written: their edits are no longer pending (and can't be undone)
                self.log = [(d, x) for d, x in self.log if d not in saved]
                self.refresh()
                names = ", ".join(d.name for d in saved)
                self.set_status(t("partial_status", names), dirty=True)
                msg = t("partial_saved", names, "\n".join(str(b) for b in baks)) + "\n\n" + msg
            return messagebox.showerror(TITLE, msg)
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
            self._save_ui_state()
            self.destroy()


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    app = App(argv[0] if argv else None, splash=True)
    theme.dark_titlebar(app)
    app.report_callback_exception = lambda *a: (traceback.print_exception(*a),
                                                messagebox.showerror(TITLE, "".join(traceback.format_exception(*a))[-1500:]))
    app.mainloop()
