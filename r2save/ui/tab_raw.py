"""All fields tab: raw editor for any scalar property."""
from .common import *  # noqa: F401,F403
from .common import _ask_int, _fmt_local, _INT_TYPES, _ask_int as ask_int  # noqa: F401


class RawTab:
    def _tab_raw(self):
        f = self._frame(t("tab_raw"), "raw")
        top = ttk.Frame(f)
        top.pack(fill="x", pady=(0, 6))
        ttk.Label(top, text=t("raw_source")).pack(side="left")
        self.raw_src_cb = ttk.Combobox(top, state="readonly", width=14)
        self.raw_src_cb.pack(side="left", padx=(4, 12))
        self.raw_src_cb.bind("<<ComboboxSelected>>", self._raw_pick_src)
        ttk.Label(top, text=t("path_filter")).pack(side="left")
        self.raw_q = tk.StringVar()
        e = ttk.Entry(top, textvariable=self.raw_q, width=44)
        e.pack(side="left", padx=4)
        e.bind("<Return>", lambda ev: self.fill_raw())
        ttk.Button(top, text=t("find"), command=self.fill_raw).pack(side="left")
        self.raw_count = ttk.Label(top, text="", style="Muted.TLabel")
        self.raw_count.pack(side="left", padx=12)
        self.raw_t = Table(f, [("path", t("col_path")), ("type", t("col_type_s")), ("value", t("col_value"))],
                           [640, 140, 240])
        self.raw_t.pack(fill="both", expand=True)
        b = ttk.Frame(f)
        b.pack(anchor="w", pady=(6, 0))
        ttk.Button(b, text=t("edit"), command=self.raw_edit).pack(side="left")
        ttk.Label(f, style="Muted.TLabel", text=t("raw_note")).pack(anchor="w", pady=(6, 0))
        self.raw_t.tv.bind("<Double-1>", lambda e: self.raw_edit())

    def _raw_doc(self):
        return self.pd if self._raw_src == "p" else self.wd

    def _raw_pick_src(self, _e=None):
        i = self.raw_src_cb.current()
        if 0 <= i < len(self._raw_srcs):
            self._raw_src = self._raw_srcs[i][0]
        self.fill_raw()

    def fill_raw(self):
        doc = self._raw_doc()
        self.raw_t.clear()
        self._raw_rows = []
        if doc is None:
            self.raw_count.config(text="")
            return
        self._raw_stale = False
        q = self.raw_q.get().strip().lower()
        total = 0
        for path, p, bag, sd in walk(doc.sf):
            if q and q not in path.lower():
                continue
            total += 1
            if len(self._raw_rows) >= RAW_LIMIT:
                continue
            self._raw_rows.append((path, p))
            self.raw_t.add(len(self._raw_rows) - 1, (path, p.type.name, fmt_value(p.value)[:200]))
        self.raw_count.config(text=t("matches", total) + (t("matches_cut", RAW_LIMIT) if total > RAW_LIMIT else ""))

    def raw_edit(self):
        sel = self.raw_t.selected()
        if sel is None:
            return
        doc = self._raw_doc()
        path, p = self._raw_rows[int(sel)]
        typ = p.type.name
        title = path.rsplit(".", 1)[-1]
        if typ in _INT_TYPES:
            lo, hi = _INT_TYPES[typ]
            v = _ask_int(self, title, path, p.value, lo, hi)
        elif typ in ("FloatProperty", "DoubleProperty"):
            v = simpledialog.askfloat(title, path, initialvalue=p.value, parent=self)
        elif typ in ("StrProperty",):
            v = simpledialog.askstring(title, path, initialvalue=p.value or "", parent=self)
        elif typ == "ByteProperty" and isinstance(p.value, ByteProp) and p.value.enum_name.name == "None":
            v = _ask_int(self, title, path, p.value.value, 0, 255)
            if v is None:
                return

            def setb():
                p.value.value = v
            return self._edit(doc, "%s = %d" % (path, v), setb)
        else:
            return messagebox.showinfo(TITLE, t("not_editable", typ))
        if v is None:
            return

        def setv():
            p.value = v
        self._edit(doc, "%s = %s" % (path, v), setv)
