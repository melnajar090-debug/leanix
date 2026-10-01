"""Main window: navigation, Refresh / Save, change detection, lock & conflict handling."""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from . import __version__, config
from .schema import ENTITIES, ENTITY_ORDER, LAYERS
from .store import (ConflictError, LockedError, Store, StoreError, find_conflicted_copies)
from .ui_common import LAYER_COLORS, style_tables
from .ui_forms import ConflictDialog, SetupDialog
from .ui_views import CapabilityMapView, DashboardView, InventoryView

POLL_MS = 15_000


class MainWindow(ctk.CTk):
    def __init__(self, store: Store, cfg: dict):
        super().__init__()
        self.store, self.cfg = store, cfg
        self.title(f"LeanIX Lite {__version__}")
        self.geometry("1320x820")
        self.minsize(1000, 640)
        style_tables()

        # ---- sidebar
        side = ctk.CTkFrame(self, width=230, corner_radius=0)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        ctk.CTkLabel(side, text="LeanIX Lite", font=ctk.CTkFont(size=22, weight="bold")).pack(
            anchor="w", padx=18, pady=(18, 0))
        ctk.CTkLabel(side, text="Enterprise architecture · BDAT", text_color="gray",
                     font=ctk.CTkFont(size=11)).pack(anchor="w", padx=18, pady=(0, 10))

        self.nav: dict[str, ctk.CTkButton] = {}
        self._nav_button(side, "dashboard", "Dashboard")
        self._nav_button(side, "capmap", "Capability Map")
        for layer in LAYERS:
            ctk.CTkLabel(side, text=layer.upper(), text_color=LAYER_COLORS[layer],
                         font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=18, pady=(12, 0))
            for ek in ENTITY_ORDER:
                if ENTITIES[ek].layer == layer:
                    self._nav_button(side, ek, ENTITIES[ek].plural)

        bottom = ctk.CTkFrame(side, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=12, pady=12)
        self.file_lbl = ctk.CTkLabel(bottom, text="", text_color="gray", font=ctk.CTkFont(size=10),
                                     wraplength=200, justify="left")
        self.file_lbl.pack(anchor="w", pady=(0, 6))
        ctk.CTkButton(bottom, text="Change OneDrive folder...", fg_color="transparent", border_width=1,
                      text_color=("gray20", "gray80"), command=self.change_file).pack(fill="x", pady=2)
        self.theme = ctk.CTkSwitch(bottom, text="Dark mode", command=self.toggle_theme)
        self.theme.pack(anchor="w", pady=(8, 0), padx=4)
        if ctk.get_appearance_mode() == "Dark":
            self.theme.select()

        # ---- main column
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(side="left", fill="both", expand=True)

        top = ctk.CTkFrame(main, height=54)
        top.pack(fill="x", padx=16, pady=(14, 0))
        self.refresh_btn = ctk.CTkButton(top, text="⟳  Refresh data", width=140, command=self.refresh_data)
        self.refresh_btn.pack(side="left", padx=10, pady=8)
        self.save_btn = ctk.CTkButton(top, text="💾  Save to Excel", width=150, fg_color="#2e8b57",
                                      hover_color="#256f46", command=self.save)
        self.save_btn.pack(side="left", pady=8)
        self.pending_lbl = ctk.CTkLabel(top, text="", font=ctk.CTkFont(weight="bold"))
        self.pending_lbl.pack(side="left", padx=14)
        self.status = ctk.CTkLabel(top, text="", text_color="gray")
        self.status.pack(side="right", padx=14)

        self.banner = ctk.CTkLabel(main, text="", fg_color="#7a5c00", text_color="white", corner_radius=6,
                                   anchor="w", justify="left", wraplength=1000)
        self.content = ctk.CTkFrame(main, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=16, pady=12)

        self.views = {"dashboard": DashboardView(self.content, self),
                      "capmap": CapabilityMapView(self.content, self)}
        for ek in ENTITY_ORDER:
            self.views[ek] = InventoryView(self.content, self, ek)
        self.current = ""
        self.show("dashboard")
        self.update_chrome()
        self.after(POLL_MS, self._poll)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self._startup_notices()

    # ------------------------------------------------------------ navigation
    def _nav_button(self, parent, key, text):
        b = ctk.CTkButton(parent, text=text, anchor="w", height=32, fg_color="transparent",
                          text_color=("gray10", "gray90"), hover_color=("gray75", "gray30"),
                          command=lambda: self.show(key))
        b.pack(fill="x", padx=10, pady=1)
        self.nav[key] = b

    def show(self, key: str):
        if self.current:
            self.views[self.current].pack_forget()
        self.current = key
        self.views[key].pack(fill="both", expand=True)
        self.views[key].refresh()
        for k, b in self.nav.items():
            b.configure(fg_color=("gray75", "gray30") if k == key else "transparent")

    def toggle_theme(self):
        ctk.set_appearance_mode("Dark" if self.theme.get() else "Light")
        self.cfg["appearance"] = "Dark" if self.theme.get() else "Light"
        config.save_config(self.cfg)
        self.after(50, self._restyle)

    def _restyle(self):
        style_tables()
        self.views[self.current].refresh()

    # ------------------------------------------------------------ state display
    def set_status(self, text: str):
        self.status.configure(text=text)

    def update_chrome(self):
        p = self.store.pending()
        if p:
            self.pending_lbl.configure(text=f"● {p.count} unsaved change(s)", text_color="#e0a030")
            self.save_btn.configure(state="normal")
        else:
            self.pending_lbl.configure(text="✔ All changes saved", text_color="#2e8b57")
            self.save_btn.configure(state="disabled")
        self.file_lbl.configure(text=f"{Path(self.store.path).name}\nrevision {self.store.revision}\n"
                                     f"{Path(self.store.path).parent}")

    def show_banner(self, text: str | None):
        if text:
            self.banner.configure(text="  " + text)
            self.banner.pack(fill="x", padx=16, pady=(8, 0), before=self.content)
        else:
            self.banner.pack_forget()

    def data_changed(self, _rid):
        """Called by forms / delete after the in-memory store was modified."""
        self.update_chrome()
        self.views[self.current].refresh()

    def _startup_notices(self):
        notes = list(self.store.load_warnings)
        dup = find_conflicted_copies(Path(self.store.path))
        if dup:
            notes.append("OneDrive may have created conflicted copies of the database next to it: "
                         + ", ".join(dup[:3]) + ". Check them, then delete the extras.")
        if notes:
            self.show_banner(" | ".join(notes))

    # ------------------------------------------------------------ refresh / save
    def refresh_data(self, quiet: bool = False) -> bool:
        if self.store.dirty:
            if not messagebox.askyesno(
                    "Unsaved changes",
                    "You have unsaved changes. Refreshing reloads the file and DISCARDS them.\n\n"
                    "Tip: press Save first - saving merges your changes with everyone else's.\n\n"
                    "Discard and refresh?", icon="warning", parent=self):
                return False
        try:
            self.store.load()
        except LockedError as e:
            if not quiet:
                messagebox.showwarning("File busy", f"{e}\n\nTry again in a moment.", parent=self)
            return False
        except Exception as e:  # corrupt / half-synced file
            if not quiet:
                messagebox.showerror("Cannot read file", f"{e}", parent=self)
            return False
        self.show_banner(None)
        self._startup_notices()
        self.update_chrome()
        self.views[self.current].refresh()
        self.set_status(f"Loaded {datetime.now():%H:%M:%S}")
        return True

    def save(self) -> bool:
        if not self.store.dirty:
            return True
        resolve = None
        while True:
            try:
                res = self.store.save(resolve)
                break
            except LockedError as e:
                if messagebox.askretrycancel(
                        "File is locked",
                        f"{e}\n\nYour changes are safe in the app and have NOT been lost.\n"
                        f"Close the file in Excel (or wait for OneDrive to finish syncing) and retry.",
                        parent=self):
                    continue
                return False
            except ConflictError as e:
                choice = ConflictDialog(self, e.conflicts).show()
                if choice is None:
                    return False
                resolve = choice
            except (StoreError, OSError) as e:
                messagebox.showerror("Save failed", f"{e}", parent=self)
                return False
            except Exception as e:  # e.g. corrupt zip while OneDrive is mid-sync
                messagebox.showerror("Save failed", f"Unexpected problem reading the current file:\n{e}\n\n"
                                                    f"Your changes are still in the app. Try Refresh later.",
                                     parent=self)
                return False
        self.show_banner(None)
        if res.warnings:
            messagebox.showinfo("Saved - please note", "\n\n".join(res.warnings), parent=self)
        self.update_chrome()
        self.views[self.current].refresh()
        self.set_status(f"Saved {datetime.now():%H:%M:%S} (revision {res.revision})")
        return True

    def _poll(self):
        try:
            if self.store.disk_changed():
                if not self.store.dirty:
                    if self.refresh_data(quiet=True):
                        self.set_status(f"Updated from OneDrive {datetime.now():%H:%M:%S}")
                else:
                    self.show_banner("The file changed on OneDrive since you opened it. "
                                     "Press Save to merge your changes with theirs (recommended).")
        finally:
            self.after(POLL_MS, self._poll)

    # ------------------------------------------------------------ misc
    def change_file(self):
        if self.store.dirty and not self.save():
            return
        result = SetupDialog(self).show()
        if not result:
            return
        try:
            new = open_or_create(*result)
        except Exception as e:
            messagebox.showerror("Cannot open file", str(e), parent=self)
            return
        self.store = new
        self.cfg["workbook_path"] = str(new.path)
        config.save_config(self.cfg)
        for v in self.views.values():
            v.store = new
        self.show_banner(None)
        self._startup_notices()
        self.update_chrome()
        self.views[self.current].refresh()

    def on_close(self):
        if self.store.dirty:
            ans = messagebox.askyesnocancel("Unsaved changes",
                                            "You have unsaved changes. Save them to Excel before closing?",
                                            parent=self)
            if ans is None:
                return
            if ans and not self.save():
                return
        self.destroy()


def open_or_create(mode: str, path: str) -> Store:
    """mode 'folder': use/create the database inside that folder; 'open': a specific .xlsx file."""
    if mode == "folder":
        target = Path(path) / config.DB_FILENAME
        if not target.exists():
            return Store.create_new(target, config.BACKUP_DIR)
        path = str(target)
    st = Store(path, config.BACKUP_DIR)
    st.load()
    return st


def run():
    cfg = config.load_config()
    ctk.set_appearance_mode(cfg.get("appearance", "Light"))
    ctk.set_default_color_theme("blue")

    store, message = None, ""
    path = cfg.get("workbook_path")
    if path and os.path.exists(path):
        try:
            store = open_or_create("open", path)
        except Exception as e:
            message = f"Could not open the saved database ({e})."
    elif path:
        message = f"The saved database file was not found:\n{path}"

    if store is None:
        root = ctk.CTk()
        root.withdraw()
        while store is None:
            dlg = SetupDialog(root, message)
            result = dlg.show()
            if not result:
                root.destroy()
                return
            try:
                store = open_or_create(*result)
            except Exception as e:
                message = f"That file could not be used: {e}"
        root.destroy()
        cfg["workbook_path"] = str(store.path)
        config.save_config(cfg)

    MainWindow(store, cfg).mainloop()
