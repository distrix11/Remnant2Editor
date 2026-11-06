"""Resources tab: currencies and materials."""
from .common import *  # noqa: F401,F403
from .common import _ask_int, _fmt_local, _INT_TYPES, _ask_int as ask_int  # noqa: F401


class ResourcesTab:
    def _tab_currency(self):
        f = self._frame(t("tab_res"), "resources")
        self.cur_t = Table(f, [("name", t("col_res")), ("qty", t("col_qty"))], [320, -140])
        self.cur_t.pack(fill="both", expand=True)
        b = ttk.Frame(f)
        b.pack(anchor="w", pady=(6, 0))
        ttk.Button(b, text=t("edit"), command=self.cur_edit).pack(side="left")
        ttk.Label(f, style="Muted.TLabel", text=t("res_note")).pack(anchor="w", pady=(8, 0))
        self.cur_t.tv.bind("<Double-1>", lambda e: self.cur_edit())

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
