"""Teleport tab: spawn points and Blood Moon."""
from .common import *  # noqa: F401,F403
from .common import _ask_int, _fmt_local, _INT_TYPES, _ask_int as ask_int  # noqa: F401


class TeleportTab:
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
        ttk.Button(b, text=t("stone_open_btn"), command=self.open_stone).pack(side="left", padx=(18, 0))
        ttk.Button(b, text=t("stone_open_all_btn"), command=self.open_all_stones).pack(side="left", padx=(6, 0))
        ttk.Label(f, style="Muted.TLabel", text=t("tp_note")).pack(anchor="w", pady=(8, 0))
        ttk.Label(f, style="Warn.TLabel", text=t("tp_warn"), wraplength=1050).pack(anchor="w", pady=(4, 0))
        self.tp_t.tv.bind("<Double-1>", lambda e: self.teleport())

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
        parts = [t("type_" + link.type)]
        stone = link.stone_name
        if stone:
            # world stones: the save stores the travel-menu name ('Mournful Promenade')
            parts.append(self._zl(stone))
            return " · ".join(parts)
        words = [t("hint_" + w) if ("hint_" + w) in i18n.S else w for w in point_hint(link.name_id)]
        qn = qnames.get(quest_id_of(link.name_id))
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
                self.tp_t.add(iid, (self._zl(z.label), name, t("type_" + l.type), "✓" if l.discovered else ("⚠" if l.undiscovered_stone else "—"),
                                    "" if z.level is None else z.level, l.name_id),
                              tags=("cur",) if is_cur else (() if l.discovered else ("muted",)))
                if forced and focus_iid is None and l.safe:
                    focus_iid = iid
        if focus_iid is not None:
            self.tp_t.select(focus_iid)
        self._tp_focus_zone = None

    def teleport(self):
        sel = self.tp_t.selected()
        if sel is None:
            return messagebox.showinfo(TITLE, t("tp_pick"))
        link = self._tp_rows[int(sel)]
        w = link.zone.world
        point = self._point_label(link, self._quest_names(w))
        if link.undiscovered_stone:
            if not messagebox.askyesno(TITLE, t("tp_confirm_stone", self._zl(link.zone.label), point)):
                return
        elif not (link.safe and link.discovered and link.zone.visited):
            if not messagebox.askyesno(TITLE, t("tp_confirm_risky", self._zl(link.zone.label), point)):
                return
        if not w.active and not messagebox.askyesno(TITLE, t("tp_confirm_world", self._world_name(w))):
            return
        self._edit(self.wd, t("tp_done", self._zl(link.zone.label), point), lambda: w.teleport(link))

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

    def open_stone(self):
        sel = self.tp_t.selected()
        if sel is None:
            return messagebox.showinfo(TITLE, t("tp_pick"))
        link = self._tp_rows[int(sel)]
        if link.type != "Waypoint":
            return messagebox.showinfo(TITLE, t("stone_not_stone"))
        if link.discovered:
            return messagebox.showinfo(TITLE, t("stone_already", self._zl(link.stone_name or link.zone.label)))
        name = self._zl(link.stone_name or link.zone.label)
        self._edit(self.wd, t("stone_opened", name), link.discover)

    def open_all_stones(self):
        w = self._current_tp_world()
        if w is None:
            return
        todo = [l for l in w.stones() if not l.discovered]
        if not todo:
            return messagebox.showinfo(TITLE, t("stone_all_open", self._world_name(w)))
        names = ", ".join(self._zl(l.stone_name or l.zone.label) for l in todo)
        if not messagebox.askyesno(TITLE, t("stone_open_all_confirm", len(todo), self._world_name(w), names)):
            return
        self._edit(self.wd, t("stone_opened_all", len(todo), self._world_name(w)), w.discover_all_stones)
