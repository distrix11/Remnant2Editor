"""World analysis tab."""
from .common import *  # noqa: F401,F403
from .common import _ask_int, _fmt_local, _INT_TYPES, _ask_int as ask_int  # noqa: F401


class AnalysisTab:
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
