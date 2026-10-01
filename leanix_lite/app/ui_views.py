"""Main-area views: Dashboard, Inventory grid (one per entity type) and Capability Map."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

from . import schema
from .schema import ENTITIES, LAYERS
from .ui_common import (LAYER_COLORS, LIFECYCLE_COLORS, SCALE, BarChart, palette)
from .ui_forms import RecordForm


class BaseView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.store = app.store

    def refresh(self):          # pragma: no cover - overridden
        pass


# ------------------------------------------------------------------------ dashboard
class DashboardView(BaseView):
    def __init__(self, master, app):
        super().__init__(master, app)
        ctk.CTkLabel(self, text="Dashboard", font=ctk.CTkFont(size=24, weight="bold")).pack(
            anchor="w", pady=(0, 8))
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True)

    def refresh(self):
        for w in self.scroll.winfo_children():
            w.destroy()
        s = self.store

        # --- BDAT tiles
        tiles = ctk.CTkFrame(self.scroll, fg_color="transparent")
        tiles.pack(fill="x")
        for i in range(4):
            tiles.columnconfigure(i, weight=1, uniform="t")
        for i, layer in enumerate(LAYERS):
            keys = [k for k, e in ENTITIES.items() if e.layer == layer]
            card = ctk.CTkFrame(tiles, corner_radius=10)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0))
            ctk.CTkLabel(card, text=layer.upper(), text_color=LAYER_COLORS[layer],
                         font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=14, pady=(12, 0))
            total = sum(len(s.records[k]) for k in keys)
            ctk.CTkLabel(card, text=str(total), font=ctk.CTkFont(size=34, weight="bold")).pack(
                anchor="w", padx=14)
            ctk.CTkLabel(card, text="  ·  ".join(f"{len(s.records[k])} {ENTITIES[k].plural}"
                                                  for k in keys), text_color="gray",
                         font=ctk.CTkFont(size=11), wraplength=200, justify="left").pack(
                anchor="w", padx=14, pady=(0, 12))

        # --- charts
        charts = ctk.CTkFrame(self.scroll, fg_color="transparent")
        charts.pack(fill="x", pady=10)
        for i in range(2):
            charts.columnconfigure(i, weight=1, uniform="c")

        def count(ek, field, order):
            seen = {}
            for r in s.all(ek):
                seen[r[field] or "(not set)"] = seen.get(r[field] or "(not set)", 0) + 1
            keys = [o for o in order if o in seen] + [k for k in seen if k not in order]
            return keys, seen

        def chart(row, col, title, ek, field, order, colors=None):
            bc = BarChart(charts, title, corner_radius=10)
            bc.grid(row=row, column=col, sticky="nsew", padx=(0 if col == 0 else 8, 0),
                    pady=(0 if row == 0 else 8, 0))
            keys, seen = count(ek, field, order)
            bc.set_data([(k, seen[k], (colors or {}).get(k, SCALE[i % len(SCALE)]))
                         for i, k in enumerate(keys)])

        chart(0, 0, "Applications by lifecycle status", "application", "Lifecycle Status",
              schema.LIFECYCLE, LIFECYCLE_COLORS)
        chart(0, 1, "Applications by business criticality", "application", "Business Criticality",
              schema.CRITICALITY)
        chart(1, 0, "Data objects by classification", "dataobject", "Data Classification",
              schema.DATA_CLASSIFICATION)
        chart(1, 1, "IT components by technical stack", "itcomponent", "Technical Stack",
              schema.TECH_CATEGORY)

        # --- insights
        ctk.CTkLabel(self.scroll, text="Things to look at", font=ctk.CTkFont(size=16, weight="bold")
                     ).pack(anchor="w", pady=(14, 4))
        rule = {(r.source, r.target): r for r in schema.RELATION_RULES}

        def unlinked(ek, other, direction="out"):
            r = rule[(ek, other)] if direction == "out" else rule[(other, ek)]
            return [x for x in s.all(ek) if not s.links_of(ek, x[ENTITIES[ek].id_field], r, direction)]

        idf = lambda ek: ENTITIES[ek].id_field
        insights = [
            ("Applications not mapped to any business capability",
             [(ek_r[idf("application")], ek_r["Name"]) for ek_r in unlinked("application", "capability")]),
            ("Applications without a business owner",
             [(r[idf("application")], r["Name"]) for r in s.all("application") if not r["Business Owner"]]),
            ("Applications phasing out or end of life",
             [(r[idf("application")], f"{r['Name']} ({r['Lifecycle Status']})") for r in s.all("application")
              if r["Lifecycle Status"] in ("Phase Out", "End of Life")]),
            ("Applications not running on any IT component",
             [(r[idf("application")], r["Name"]) for r in unlinked("application", "itcomponent")]),
            ("IT components at end of life",
             [(r[idf("itcomponent")], r["Name"]) for r in s.all("itcomponent")
              if r["Lifecycle Status"] == "End of Life"]),
            ("Business capabilities with no supporting application",
             [(r[idf("capability")], r["Name"]) for r in unlinked("capability", "application", "in")]),
            ("Data objects with personal data not used by any application",
             [(r[idf("dataobject")], r["Name"]) for r in unlinked("dataobject", "application", "in")
              if r["Contains Personal Data"] == "Yes"]),
        ]
        for title, items in insights:
            row = ctk.CTkFrame(self.scroll, corner_radius=8)
            row.pack(fill="x", pady=3)
            ok = not items
            ctk.CTkLabel(row, text="✔" if ok else str(len(items)), width=36,
                         text_color="#2e8b57" if ok else "#e0a030",
                         font=ctk.CTkFont(size=15, weight="bold")).pack(side="left", padx=(8, 0), pady=8)
            txt = ctk.CTkFrame(row, fg_color="transparent")
            txt.pack(side="left", fill="x", expand=True, pady=6)
            ctk.CTkLabel(txt, text=title, anchor="w").pack(anchor="w")
            if items:
                shown = ", ".join(n for _, n in items[:6]) + (f" … +{len(items) - 6} more" if len(items) > 6 else "")
                ctk.CTkLabel(txt, text=shown, anchor="w", text_color="gray", font=ctk.CTkFont(size=11),
                             wraplength=900, justify="left").pack(anchor="w")


# ------------------------------------------------------------------------ inventory
class InventoryView(BaseView):
    def __init__(self, master, app, ek: str):
        super().__init__(master, app)
        self.ek = ek
        ent = ENTITIES[ek]
        self.ent = ent
        self._sort = (ent.id_field, False)
        self.cols = [ent.id_field] + [f.name for f in ent.fields if f.kind != "long"] + ["Modified At"]

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x")
        ctk.CTkLabel(head, text=ent.plural, font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        ctk.CTkLabel(head, text=f"  {ent.layer} layer", text_color=LAYER_COLORS[ent.layer]).pack(
            side="left", pady=(8, 0))
        ctk.CTkButton(head, text=f"+ New {ent.label}", width=140, command=self.add).pack(side="right")

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", pady=8)
        self.search = ctk.CTkEntry(bar, placeholder_text="Search any column...", width=260)
        self.search.pack(side="left")
        self.search.bind("<KeyRelease>", lambda _e: self.refresh())
        self.filters: dict[str, ctk.CTkOptionMenu] = {}
        for f in ent.fields:
            if f.kind == "choice":
                ctk.CTkLabel(bar, text=f.name + ":", text_color="gray").pack(side="left", padx=(14, 4))
                m = ctk.CTkOptionMenu(bar, values=["All"] + list(f.choices), width=130,
                                      command=lambda _v: self.refresh())
                m.pack(side="left")
                self.filters[f.name] = m
        self.count_lbl = ctk.CTkLabel(bar, text="", text_color="gray")
        self.count_lbl.pack(side="right")

        wrap = ctk.CTkFrame(self, corner_radius=8)
        wrap.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(wrap, columns=self.cols, show="headings", selectmode="browse")
        for c in self.cols:
            self.tree.heading(c, text=c, command=lambda c=c: self._sort_by(c))
            fixed = c.endswith("ID") or c == "Modified At"
            self.tree.column(c, width=125 if c.endswith("ID") else 150 if c == "Modified At" else 135,
                             minwidth=90, stretch=not fixed)
        vs = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        hs = ttk.Scrollbar(wrap, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        vs.pack(side="right", fill="y", padx=(0, 2), pady=2)
        hs.pack(side="bottom", fill="x", padx=2)
        self.tree.pack(fill="both", expand=True, padx=2, pady=2)
        self.tree.bind("<Double-1>", lambda _e: self.edit())
        self.tree.bind("<Return>", lambda _e: self.edit())
        self.tree.bind("<Delete>", lambda _e: self.delete())

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", pady=(8, 0))
        ctk.CTkButton(actions, text="Edit", width=90, command=self.edit).pack(side="left")
        ctk.CTkButton(actions, text="Delete", width=90, fg_color="#b8433b", hover_color="#8f332d",
                      command=self.delete).pack(side="left", padx=8)
        ctk.CTkLabel(actions, text="Double-click a row to edit. Click a column header to sort.",
                     text_color="gray").pack(side="left", padx=10)
        self.recolor()

    def recolor(self):
        self.tree.tag_configure("end", foreground="#e5534b")
        self.tree.tag_configure("out", foreground="#e0a030")

    def _display(self, rec) -> list[str]:
        vals = []
        for c in self.cols:
            v = rec.get(c, "")
            if c in {f.name for f in self.ent.fields if f.kind == "ref"}:
                v = self.store.label_of(self.ent.field(c).ref, v)
            vals.append(v)
        return vals

    def _sort_by(self, col):
        prev, rev = self._sort
        self._sort = (col, (not rev) if prev == col else False)
        self.refresh()

    def refresh(self):
        sel = self.tree.selection()
        for i in self.tree.get_children():
            self.tree.delete(i)
        q = self.search.get().strip().lower()
        active = {n: m.get() for n, m in self.filters.items() if m.get() != "All"}
        rows = []
        for rec in self.store.all(self.ek):
            if any(rec.get(n, "") != v for n, v in active.items()):
                continue
            disp = self._display(rec)
            if q and not any(q in str(x).lower() for x in disp) and q not in rec.get("Description", "").lower():
                continue
            rows.append((rec, disp))
        col, rev = self._sort
        ci = self.cols.index(col)
        rows.sort(key=lambda r: (r[1][ci] or "").lower(), reverse=rev)
        for rec, disp in rows:
            status = rec.get("Lifecycle Status", "")
            tag = ("end",) if status == "End of Life" else ("out",) if status == "Phase Out" else ()
            self.tree.insert("", "end", iid=rec[self.ent.id_field], values=disp, tags=tag)
        total = len(self.store.records[self.ek])
        self.count_lbl.configure(text=f"{len(rows)} of {total}")
        if sel and self.tree.exists(sel[0]):
            self.tree.selection_set(sel[0])

    def _selected(self) -> str | None:
        sel = self.tree.selection()
        return sel[0] if sel else None

    def add(self):
        RecordForm(self.app, self.store, self.ek, None, self.app.data_changed)

    def edit(self):
        rid = self._selected()
        if not rid:
            messagebox.showinfo("Edit", f"Select a {self.ent.label.lower()} first.", parent=self.app)
            return
        RecordForm(self.app, self.store, self.ek, rid, self.app.data_changed)

    def delete(self):
        rid = self._selected()
        if not rid:
            messagebox.showinfo("Delete", f"Select a {self.ent.label.lower()} first.", parent=self.app)
            return
        n_links = len(self.store.related(self.ek, rid))
        name = self.store.name_of(self.ek, rid)
        msg = f"Delete {self.ent.label.lower()} '{name}' ({rid})?"
        if n_links:
            msg += f"\n\nIts {n_links} relationship(s) will be removed too."
        msg += "\n\nThis takes effect in the file when you press Save."
        if messagebox.askyesno("Confirm delete", msg, icon="warning", parent=self.app):
            notes = self.store.delete(self.ek, rid)
            self.app.data_changed(None)
            if notes:
                self.app.set_status("; ".join(notes[:3]))


# ------------------------------------------------------------------------ capability map
class CapabilityMapView(BaseView):
    def __init__(self, master, app):
        super().__init__(master, app)
        ctk.CTkLabel(self, text="Capability Map", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(self, text="Business capabilities as a hierarchy, with the processes that realize them "
                                "and the applications that support them.", text_color="gray").pack(
            anchor="w", pady=(0, 8))
        wrap = ctk.CTkFrame(self, corner_radius=8)
        wrap.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(wrap, columns=("type", "id", "info"), selectmode="browse")
        self.tree.heading("#0", text="Name")
        self.tree.heading("type", text="Type")
        self.tree.heading("id", text="ID")
        self.tree.heading("info", text="Lifecycle / Owner")
        self.tree.column("#0", width=380)
        self.tree.column("type", width=110)
        self.tree.column("id", width=100)
        self.tree.column("info", width=220)
        vs = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vs.set)
        vs.pack(side="right", fill="y", padx=(0, 2), pady=2)
        self.tree.pack(fill="both", expand=True, padx=2, pady=2)
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", pady=(8, 0))
        ctk.CTkButton(btns, text="Expand all", width=100, command=lambda: self._toggle(True)).pack(side="left")
        ctk.CTkButton(btns, text="Collapse all", width=100, command=lambda: self._toggle(False)).pack(
            side="left", padx=8)

    def _toggle(self, open_: bool):
        def walk(item):
            self.tree.item(item, open=open_)
            for c in self.tree.get_children(item):
                walk(c)
        for i in self.tree.get_children():
            walk(i)

    def refresh(self):
        s = self.store
        for i in self.tree.get_children():
            self.tree.delete(i)
        caps = s.records["capability"]
        rule_app = next(r for r in schema.RELATION_RULES if (r.source, r.target) == ("application", "capability"))
        rule_proc = next(r for r in schema.RELATION_RULES if (r.source, r.target) == ("process", "capability"))
        children: dict[str, list[str]] = {}
        for cid, rec in caps.items():
            parent = rec["Parent Capability"] if rec["Parent Capability"] in caps else ""
            children.setdefault(parent, []).append(cid)

        def add(parent_iid, cid, depth=0):
            rec = caps[cid]
            iid = f"cap:{cid}"
            self.tree.insert(parent_iid, "end", iid=iid, text=rec["Name"], open=True,
                             values=("Capability", cid, rec["Business Owner"]))
            for pid in s.links_of("capability", cid, rule_proc, "in"):
                p = s.get("process", pid)
                if p:
                    self.tree.insert(iid, "end", text="⚙ " + p["Name"], values=("Process", pid, p["Process Owner"]))
            for aid in s.links_of("capability", cid, rule_app, "in"):
                a = s.get("application", aid)
                if a:
                    self.tree.insert(iid, "end", text="▣ " + a["Name"],
                                     values=("Application", aid, a["Lifecycle Status"]))
            for kid in sorted(children.get(cid, []), key=lambda k: caps[k]["Name"].lower()):
                add(iid, kid, depth + 1)

        for root in sorted(children.get("", []), key=lambda k: caps[k]["Name"].lower()):
            add("", root)
