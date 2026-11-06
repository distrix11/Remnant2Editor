"""Inventory tab: search, quantity, upgrade level, delete."""
from .common import *  # noqa: F401,F403
from .common import _ask_int, _fmt_local, _INT_TYPES, _ask_int as ask_int  # noqa: F401


class InventoryTab:
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
        ttk.Button(b, text=t("del_btn"), command=self.inv_delete).pack(side="left", padx=(18, 0))
        self.inv_path = ttk.Label(f, text="", style="Muted.TLabel")
        self.inv_path.pack(anchor="w", pady=(6, 0))
        self.inv_t.tv.bind("<<TreeviewSelect>>", self._inv_sel)
        self.inv_t.tv.bind("<Double-1>", lambda e: self.inv_dbl())
        self.inv_t.tv.bind("<Delete>", lambda e: self.inv_delete())

    def _on_cat(self, _e=None):
        i = self.inv_cat.current()
        self._cat_value = self._cat_keys[i] if 0 <= i < len(self._cat_keys) else ALL
        self.fill_inventory()

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

    def _owned_paths(self):
        return {i.path.lower() for i in self.char.items() if i.path} if self.char is not None else set()

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

    def inv_delete(self):
        it = self._cur_item()
        if it is None:
            return
        why = self.char.delete_blockers(it)
        if why:
            lines = [t("del_why_" + code, detail) if code in ("type", "equipped", "attached") else t("del_why_" + code)
                     for code, detail in why]
            return messagebox.showerror(TITLE, t("del_blocked", it.name) + "\n\n" +
                                        "\n".join("• " + x for x in lines))
        qty = it.quantity
        label = "%s ×%d" % (it.name, qty) if it.has_quantity_field and qty else it.name
        if not messagebox.askyesno(TITLE, t("del_confirm", label)):
            return
        self._edit(self.pd, t("del_change", label), lambda: self.char.remove_item(it))
