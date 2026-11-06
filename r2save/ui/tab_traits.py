"""Traits tab: levels with a trait-point budget check."""
from .common import *  # noqa: F401,F403
from .common import _ask_int  # noqa: F401


class TraitsTab:
    def _tab_traits(self):
        f = self._frame(t("tab_traits"), "traits")
        card, self.tr_budget = theme.card(f, text="", justify="left")
        card.pack(anchor="w", fill="x", pady=(0, 8))
        self.tr_t = Table(f, [("name", t("col_trait")), ("kind", t("col_kind")), ("lvl", t("col_level"))],
                          [300, 160, -80])
        self.tr_t.pack(fill="both", expand=True)
        b = ttk.Frame(f)
        b.pack(anchor="w", pady=(6, 0))
        ttk.Button(b, text=t("trait_level_btn"), command=self.trait_level).pack(side="left")
        ttk.Label(f, style="Muted.TLabel", text=t("traits_note"), wraplength=1000).pack(anchor="w", pady=(8, 0))
        self.tr_t.tv.bind("<Double-1>", lambda e: self.trait_level())

    def fill_traits(self):
        self.tr_t.clear()
        self._traits = self.char.traits()
        for i, tr in enumerate(self._traits):
            free = tr.kind not in self.char.SPENDABLE_KINDS
            self.tr_t.add(i, (tr.name, t("kind_" + tr.kind), tr.level), tags=("muted",) if free else ())
        spent, avail = self.char.trait_budget()
        if avail is None:
            self.tr_budget.config(text=t("tr_budget_unknown", spent), style="Info.TLabel")
        elif spent > avail:
            self.tr_budget.config(text=t("tr_budget_over", spent, avail, spent - avail), style="InfoWarn.TLabel")
        else:
            self.tr_budget.config(text=t("tr_budget", spent, avail, avail - spent), style="Info.TLabel")

    def traits_overspent(self):
        """(spent, available) when the active character spends more than it has, else None."""
        if self.char is None:
            return None
        spent, avail = self.char.trait_budget()
        return (spent, avail) if avail is not None and spent > avail else None

    def trait_level(self):
        sel = self.tr_t.selected()
        if sel is None:
            return
        tr = self._traits[int(sel)]
        v = _ask_int(self, tr.name, t("trait_prompt"), tr.level, 0, 10)
        if v is None:
            return
        old = tr.level
        if tr.kind in self.char.SPENDABLE_KINDS and v > old:
            spent, avail = self.char.trait_budget()
            new_spent = spent - old + v
            if avail is not None and new_spent > avail and \
                    not messagebox.askyesno(TITLE, t("tr_over_confirm", tr.name, new_spent, avail)):
                return
        self._edit(self.pd, "%s: %d → %d" % (tr.name, old, v), lambda: tr.set_level(v))
