"""Add item tab: catalog and manual path."""
from .common import *  # noqa: F401,F403
from .common import _ask_int, _fmt_local, _INT_TYPES, _ask_int as ask_int  # noqa: F401


class AddItemTab:
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
