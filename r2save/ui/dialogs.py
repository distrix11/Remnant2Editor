"""Secondary windows: change list, backups, about."""
from .common import *  # noqa: F401,F403
from .. import settings
from .. import __version__, APP_NAME, AUTHOR, REPO_URL
from ..storage import prune_backups
from .common import _ask_int, _fmt_local, _INT_TYPES, _ask_int as ask_int  # noqa: F401


class DialogsMixin:
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
        keep_vals = [10, 20, 50, 100, 0]
        keep_cb = ttk.Combobox(bar, state="readonly", width=12,
                               values=[str(v) if v else t("bk_keep_all") for v in keep_vals])
        try:
            cur = int(settings.get("backups_keep"))
        except (TypeError, ValueError):
            cur = 20
        keep_cb.current(keep_vals.index(cur) if cur in keep_vals else 1)

        def on_keep(_e=None):
            v = keep_vals[keep_cb.current()]
            settings.set("backups_keep", v)
            removed = []
            if v:
                for base in sorted({b["target"][:-4] for b in rows if b["source"] == "editor"}):
                    removed += prune_backups(os.path.join(sdir, "_editor_backups"), base, keep=v)
            fill()
            if removed:
                self.set_status(t("bk_pruned", len(removed)))
        keep_cb.bind("<<ComboboxSelected>>", on_keep)
        keep_cb.pack(side="right", padx=(4, 14))
        ttk.Label(bar, text=t("bk_keep")).pack(side="right")
        ttk.Label(win.body, text=t("bk_note"), style="Muted.TLabel", wraplength=860).pack(anchor="w", pady=(8, 0))

    def show_about(self):
        import platform
        import webbrowser
        win = DarkWindow(self, t("about_title"), "640x500")
        top = ttk.Frame(win.body)
        top.pack(fill="x")
        em = theme.image("emblem_64")
        if em is not None:
            ttk.Label(top, image=em).pack(side="left", padx=(0, 16))
        head = ttk.Frame(top)
        head.pack(side="left", fill="x")
        ttk.Label(head, text=APP_NAME, style="Brand.TLabel").pack(anchor="w")
        ttk.Label(head, text=t("about_version", __version__), style="Section.TLabel").pack(anchor="w")
        ttk.Label(head, text=t("about_tagline"), style="Muted.TLabel").pack(anchor="w", pady=(2, 0))

        def link(parent, text, url):
            lbl = tk.Label(parent, text=text, fg=theme.RED_GLOW, bg=theme.BG, cursor="hand2", font=theme.FONT)
            lbl.bind("<Button-1>", lambda e: webbrowser.open(url))
            return lbl

        theme.section(win.body, t("about_author")).pack(fill="x", pady=(16, 4))
        row = ttk.Frame(win.body)
        row.pack(anchor="w")
        ttk.Label(row, text="%s · MIT  —  " % AUTHOR).pack(side="left")
        link(row, REPO_URL.replace("https://", ""), REPO_URL).pack(side="left")

        theme.section(win.body, t("about_credits")).pack(fill="x", pady=(14, 4))
        for name, who, lic, url in (
                ("lib.remnant2.saves", "Andrew Savinykh", "MIT", "https://github.com/AndrewSav/lib.remnant2.saves"),
                ("lib.remnant2.analyzer", "Andrew Savinykh", "MIT", "https://github.com/AndrewSav/lib.remnant2.analyzer"),
                ("RemnantOverseer", "Angelore", "MIT", "https://github.com/Angelore/remnant-two-overseer"),
                ("Montserrat", "The Montserrat Project Authors", "SIL OFL 1.1", "https://github.com/JulietaUla/Montserrat")):
            r = ttk.Frame(win.body)
            r.pack(anchor="w", pady=1)
            link(r, name, url).pack(side="left")
            ttk.Label(r, text="  %s · %s" % (who, lic), style="Muted.TLabel").pack(side="left")

        theme.section(win.body, t("about_files")).pack(fill="x", pady=(14, 4))
        frozen = getattr(sys, "frozen", False)
        info = [t("about_settings", settings.PATH)]
        if frozen:
            info.append(t("about_log", os.path.join(settings.app_dir(), "editor.log")))
        info.append("Python %s · Tk %s · %s" % (platform.python_version(), self.tk.call("info", "patchlevel"),
                                                "exe" if frozen else "source"))
        ttk.Label(win.body, text="\n".join(info), style="Muted.TLabel", justify="left", wraplength=600).pack(anchor="w")
        ttk.Label(win.body, text=t("about_disclaimer"), style="Muted.TLabel", wraplength=600,
                  justify="left").pack(anchor="w", pady=(14, 0))
        bar = ttk.Frame(win.body)
        bar.pack(fill="x", side="bottom", pady=(10, 0))
        ttk.Button(bar, text="GitHub", command=lambda: webbrowser.open(REPO_URL)).pack(side="left")
        ttk.Button(bar, text=t("close"), style="Accent.TButton", command=win.destroy).pack(side="right")

    def show_quest_items(self):
        """Quest items of the selected world (they live in save_N.sav, not in the character inventory)."""
        from ..world import DUPLICABLE_QUEST_ITEMS
        if self.ws is None:
            return messagebox.showinfo(TITLE, t("qi_no_world"))
        win = DarkWindow(self, t("qi_title"), "760x440")
        ttk.Label(win.body, text=t("qi_note"), style="Muted.TLabel", wraplength=720,
                  justify="left").pack(anchor="w", pady=(0, 8))
        tbl = Table(win.body, [("world", t("world")), ("item", t("col_item")), ("id", "ID")], [220, 400, -60],
                    height=12)
        tbl.pack(fill="both", expand=True)
        rows = {}

        def fill():
            tbl.clear()
            rows.clear()
            n = 0
            for w in self.ws.worlds():
                for q in w.quest_items():
                    key = "%d:%d" % (w.slot, q.id)
                    rows[key] = (w.slot, q.id)
                    dup = any(k in q.path for k in DUPLICABLE_QUEST_ITEMS)
                    tbl.add(key, (self._world_name(w) + (t("active_mark") if w.active else ""), q.name, q.id),
                            tags=() if dup else ("muted",))
                    n += 1
            if not n:
                tbl.add("none", ("", t("qi_empty"), ""), tags=("muted",))

        def duplicate():
            sel = tbl.selected()
            if sel not in rows:
                return messagebox.showinfo(TITLE, t("qi_pick"), parent=win)
            slot, qid = rows[sel]
            w = next(x for x in self.ws.worlds() if x.slot == slot)
            q = next(x for x in w.quest_items() if x.id == qid)
            if not any(k in q.path for k in DUPLICABLE_QUEST_ITEMS):
                return messagebox.showinfo(TITLE, t("qi_not_dup", q.name), parent=win)
            n = _ask_int(win, q.name, t("qi_copies"), 2, 1, 20)
            if n is None:
                return
            name = q.name
            self._edit(self.wd, t("qi_done", name, n),
                       lambda: next(x for x in self.ws.worlds() if x.slot == slot).duplicate_quest_item(
                           next(x for x in next(y for y in self.ws.worlds() if y.slot == slot).quest_items()
                                if x.id == qid), n))
            fill()
        fill()
        b = ttk.Frame(win.body)
        b.pack(fill="x", pady=(10, 0))
        ttk.Button(b, text=t("qi_dup_btn"), command=duplicate).pack(side="left")
        ttk.Button(b, text=t("close"), style="Accent.TButton", command=win.destroy).pack(side="right")
