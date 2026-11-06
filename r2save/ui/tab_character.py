"""Character tab: overview and archetype XP."""
from .common import *  # noqa: F401,F403
from .common import _ask_int, _fmt_local, _INT_TYPES, _ask_int as ask_int  # noqa: F401


class CharacterTab:
    def _tab_overview(self):
        f = self._frame(t("tab_char"), "character")
        card, self.ov_lbl = theme.card(f, text="", justify="left")
        card.pack(anchor="w", fill="x")
        theme.section(f, t("archetypes_hdr")).pack(fill="x", pady=(14, 6))
        self.arch_t = Table(f, [("name", t("col_arch")), ("level", t("col_level")), ("xp", "XP"),
                                ("slot", t("col_equipped"))], [220, -80, -100, 120])
        self.arch_t.pack(fill="both", expand=True)
        b = ttk.Frame(f)
        b.pack(anchor="w", pady=(6, 0))
        ttk.Button(b, text=t("set_xp"), command=self.arch_set_xp).pack(side="left")
        ttk.Button(b, text=t("max_level"), command=lambda: self.arch_set_xp(ARCHETYPE_MAX_XP)).pack(
            side="left", padx=6)
        ttk.Label(f, style="Muted.TLabel", text=t("arch_note")).pack(anchor="w", pady=(8, 0))
        self.arch_t.tv.bind("<Double-1>", lambda e: self.arch_set_xp())

    def fill_overview(self):
        c = self.char
        self.ov_lbl.config(text=t("overview", c.archetype, c.secondary, c.power_level, c.item_level,
                                  c.trait_rank, c.trait_points, c.experience))
        self.arch_t.clear()
        for i, a in enumerate(c.archetypes()):
            slot = {0: t("primary"), 1: t("secondary")}.get(a.slot, "")
            self.arch_t.add(i, (a.name, a.level, a.xp, slot))

    def arch_set_xp(self, value=None):
        sel = self.arch_t.selected()
        if sel is None:
            return messagebox.showinfo(TITLE, t("pick_arch"))
        a = self.char.archetypes()[int(sel)]
        if value is None:
            value = _ask_int(self, t("arch_xp_title"), t("arch_xp_prompt", a.name, ARCHETYPE_MAX_XP),
                             a.xp, 0, ARCHETYPE_MAX_XP)
            if value is None:
                return
        old = a.xp
        self._edit(self.pd, "%s: XP %d → %d" % (a.name, old, value), lambda: a.set_xp(value))
