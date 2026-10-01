"""Modal dialogs: record form (with relationship pickers), conflict resolution, first-run setup."""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog

import customtkinter as ctk

from . import schema
from .schema import ENTITIES
from .store import Store, ValidationError


def _modal(win: ctk.CTkToplevel, parent) -> None:
    try:
        if parent.winfo_viewable():       # a transient child of a hidden window would be hidden too
            win.transient(parent)
    except Exception:
        pass
    win.after(150, lambda: (win.winfo_exists() and (win.grab_set(), win.focus_force())))


class _Picker(ctk.CTkFrame):
    """Searchable multi-select checklist used for relationships."""

    def __init__(self, master, options: list[tuple[str, str]], selected: set[str]):
        super().__init__(master, fg_color="transparent")
        self._vars: dict[str, tk.BooleanVar] = {}
        self._labels: dict[str, str] = dict(options)
        self.search = ctk.CTkEntry(self, placeholder_text="Filter...", height=26)
        self.search.pack(fill="x")
        self.search.bind("<KeyRelease>", lambda _e: self._apply_filter())
        self.box = ctk.CTkScrollableFrame(self, height=110)
        self.box.pack(fill="x", pady=(4, 0))
        self._boxes: dict[str, ctk.CTkCheckBox] = {}
        if not options:
            ctk.CTkLabel(self.box, text="(nothing to link yet)", text_color="gray").pack(anchor="w")
        for rid, label in options:
            var = tk.BooleanVar(value=rid in selected)
            self._vars[rid] = var
            cb = ctk.CTkCheckBox(self.box, text=label, variable=var, height=22, checkbox_height=18,
                                 checkbox_width=18)
            cb.pack(anchor="w", pady=1)
            self._boxes[rid] = cb

    def _apply_filter(self):
        q = self.search.get().strip().lower()
        for rid, cb in self._boxes.items():
            cb.pack_forget()
            if not q or q in self._labels[rid].lower():
                cb.pack(anchor="w", pady=1)

    def selected(self) -> set[str]:
        return {rid for rid, v in self._vars.items() if v.get()}


class RecordForm(ctk.CTkToplevel):
    def __init__(self, parent, store: Store, ek: str, rid: str | None, on_done):
        super().__init__(parent)
        self.store, self.ek, self.rid, self.on_done = store, ek, rid, on_done
        ent = ENTITIES[ek]
        self.title(f"{'Edit' if rid else 'New'} {ent.label}" + (f" - {rid}" if rid else ""))
        self.geometry("640x760")
        self.minsize(560, 480)
        self._widgets: dict[str, tuple[schema.Field, object]] = {}
        self._ref_maps: dict[str, dict[str, str]] = {}
        self._pickers: list[tuple[schema.RelationRule, str, _Picker]] = []

        body = ctk.CTkScrollableFrame(self)
        body.pack(fill="both", expand=True, padx=12, pady=(12, 4))
        existing = store.get(ek, rid) if rid else {}

        ctk.CTkLabel(body, text=f"{ent.layer} layer  ·  {ent.label}", text_color="gray").pack(anchor="w")
        for f in ent.fields:
            ctk.CTkLabel(body, text=f.name + (" *" if f.required else ""),
                         font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10, 2))
            val = existing.get(f.name, "") if existing else ""
            if f.kind == "long":
                w = ctk.CTkTextbox(body, height=90, wrap="word")
                w.insert("1.0", val)
            elif f.kind == "choice":
                w = ctk.CTkOptionMenu(body, values=[""] + list(f.choices), dynamic_resizing=False)
                w.set(val)
            elif f.kind == "ref":
                opts = {"": ""}
                for orid, rec in store.records[f.ref].items():
                    if orid != rid:
                        opts[store.label_of(f.ref, orid)] = orid
                self._ref_maps[f.name] = opts
                w = ctk.CTkOptionMenu(body, values=list(opts), dynamic_resizing=False)
                w.set(store.label_of(f.ref, val) if val in store.records[f.ref] else "")
            else:
                w = ctk.CTkEntry(body)
                w.insert(0, val)
            w.pack(fill="x")
            self._widgets[f.name] = (f, w)

        rules = schema.rules_for(ek)
        if rules:
            ctk.CTkLabel(body, text="Relationships", font=ctk.CTkFont(size=15, weight="bold")
                         ).pack(anchor="w", pady=(22, 0))
        for rule, direction in rules:
            other = rule.target if direction == "out" else rule.source
            wording = rule.source_view if direction == "out" else rule.target_view
            ctk.CTkLabel(body, text=wording, font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10, 0))
            current = set(store.links_of(ek, rid, rule, direction)) if rid else set()
            options = [(orid, store.label_of(other, orid)) for orid in store.records[other]
                       if not (other == ek and orid == rid)]
            picker = _Picker(body, options, current)
            picker.pack(fill="x")
            self._pickers.append((rule, direction, picker))

        self.error = ctk.CTkLabel(self, text="", text_color="#e5534b", wraplength=580, justify="left")
        self.error.pack(fill="x", padx=14)
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=12, pady=10)
        ctk.CTkButton(bar, text="Cancel", width=90, fg_color="gray40", hover_color="gray30",
                      command=self.destroy).pack(side="right", padx=(8, 0))
        ctk.CTkButton(bar, text="Apply", width=120, command=self._submit
                      ).pack(side="right")
        ctk.CTkLabel(bar, text="Changes go to the file when you press Save in the main window.",
                     text_color="gray", font=ctk.CTkFont(size=11)).pack(side="left")
        _modal(self, parent)

    def _collect(self) -> dict[str, str]:
        out = {}
        for name, (f, w) in self._widgets.items():
            if f.kind == "long":
                out[name] = w.get("1.0", "end").strip()
            elif f.kind == "ref":
                out[name] = self._ref_maps[name].get(w.get(), "")
            else:
                out[name] = w.get().strip()
        return out

    def _submit(self):
        values = self._collect()
        try:
            rid = self.rid
            if rid:
                self.store.update(self.ek, rid, values)
            else:
                rid = self.store.add(self.ek, values)
            for rule, direction, picker in self._pickers:
                self.store.set_links(self.ek, rid, rule, direction, picker.selected())
        except ValidationError as e:
            self.error.configure(text="\n".join("• " + m for m in e.errors))
            return
        self.on_done(rid)
        self.destroy()


class ConflictDialog(ctk.CTkToplevel):
    """Shows conflicting changes and returns 'mine', 'theirs' or None."""

    def __init__(self, parent, conflicts):
        super().__init__(parent)
        self.choice: str | None = None
        self.title("Conflicting changes")
        self.geometry("720x460")
        ctk.CTkLabel(self, text="Someone else changed the same data since you last refreshed.",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=14, pady=(14, 2))
        ctk.CTkLabel(self, text="Nothing has been written yet. Choose whose version to keep for the items below "
                                "(all your other changes are merged either way).",
                     wraplength=680, justify="left", text_color="gray").pack(anchor="w", padx=14)
        box = ctk.CTkTextbox(self, wrap="word")
        box.pack(fill="both", expand=True, padx=14, pady=10)
        box.insert("1.0", "\n\n".join("• " + c.describe() for c in conflicts))
        box.configure(state="disabled")
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=14, pady=(0, 12))
        ctk.CTkButton(bar, text="Cancel (decide later)", fg_color="gray40", hover_color="gray30",
                      command=self.destroy).pack(side="right", padx=(8, 0))
        ctk.CTkButton(bar, text="Keep THEIR version", command=lambda: self._pick("theirs")
                      ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(bar, text="Keep MY version", command=lambda: self._pick("mine")).pack(side="right")
        _modal(self, parent)

    def _pick(self, choice):
        self.choice = choice
        self.destroy()

    def show(self) -> str | None:
        self.wait_window()
        return self.choice


class SetupDialog(ctk.CTkToplevel):
    """First-run (or broken-path) chooser. ``.result`` is ('folder'|'open', path) or None."""

    def __init__(self, parent, message: str = ""):
        super().__init__(parent)
        from . import config
        self.result: tuple[str, str] | None = None
        self.title("LeanIX Lite - connect your OneDrive folder")
        self.geometry("600x420")
        self.resizable(False, False)
        ctk.CTkLabel(self, text="Connect the shared OneDrive folder",
                     font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=20, pady=(20, 4))
        ctk.CTkLabel(self, wraplength=560, justify="left", text_color="gray",
                     text=(message + "\n\n" if message else "") +
                          f"Choose a folder inside your OneDrive. The app creates its own Excel database "
                          f"('{config.DB_FILENAME}') there, or opens it if it already exists. "
                          f"Share that folder with your manager so you both use the same data. "
                          f"The choice is remembered on this computer.").pack(anchor="w", padx=20)

        detected = config.detect_onedrive_folders()
        self._start = str(detected[0]) if detected else ""
        if detected:
            ctk.CTkLabel(self, text="OneDrive found on this PC:  " + "   |   ".join(str(d) for d in detected),
                         wraplength=560, justify="left", font=ctk.CTkFont(size=11)).pack(
                anchor="w", padx=20, pady=(10, 0))
        else:
            ctk.CTkLabel(self, text="No OneDrive folder was detected automatically - you can still browse "
                                    "to it (usually C:\\Users\\<you>\\OneDrive...).",
                         wraplength=560, justify="left", text_color="#e0a030",
                         font=ctk.CTkFont(size=11)).pack(anchor="w", padx=20, pady=(10, 0))

        ctk.CTkButton(self, text="Select the OneDrive folder...", height=42, command=self._folder).pack(
            fill="x", padx=20, pady=(18, 8))
        ctk.CTkButton(self, text="Advanced: open a specific existing .xlsx file...", height=30,
                      fg_color="transparent", border_width=1, text_color=("gray20", "gray80"),
                      command=self._open).pack(fill="x", padx=20)
        ctk.CTkButton(self, text="Quit", fg_color="gray40", hover_color="gray30", width=80,
                      command=self.destroy).pack(anchor="e", padx=20, pady=18)
        _modal(self, parent)

    def _folder(self):
        from tkinter import messagebox
        p = filedialog.askdirectory(parent=self, title="Select the OneDrive folder for LeanIX Lite",
                                    initialdir=self._start or None, mustexist=True)
        if not p:
            return
        if "onedrive" not in p.lower() and not messagebox.askyesno(
                "Not a OneDrive folder?",
                f"'{p}' does not look like a OneDrive folder, so your manager may not see the data.\n\n"
                f"Use it anyway?", parent=self):
            return
        self.result = ("folder", p)
        self.destroy()

    def _open(self):
        p = filedialog.askopenfilename(parent=self, title="Select the shared Excel file",
                                       filetypes=[("Excel workbook", "*.xlsx")])
        if p:
            self.result = ("open", p)
            self.destroy()

    def show(self):
        self.wait_window()
        return self.result
