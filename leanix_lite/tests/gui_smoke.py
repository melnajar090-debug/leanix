"""Headless GUI smoke test (run under xvfb): drives real windows, saves, takes screenshots."""
import os, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import customtkinter as ctk
from app import schema
from app.store import Store
from app.ui_forms import RecordForm
from app.ui_main import MainWindow

shots = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp())
tmp = Path(tempfile.mkdtemp())
path = tmp / "ea.xlsx"
store = Store.create_new(path, tmp / "bk")
win = None

def snap(name):
    win.update_idletasks(); win.update()
    subprocess.run(["import", "-window", "root", str(shots / f"{name}.png")], check=False)

def fill(form, **vals):
    for k, v in vals.items():
        f, w = form._widgets[k]
        if f.kind == "long":
            w.delete("1.0", "end"); w.insert("1.0", v)
        elif f.kind in ("choice",):
            w.set(v)
        elif f.kind == "ref":
            w.set(v)
        else:
            w.delete(0, "end"); w.insert(0, v)

def new(ek, **vals):
    form = RecordForm(win, store, ek, None, win.data_changed)
    fill(form, **vals)
    for rule, direction, picker in form._pickers:
        pass
    form._submit()
    assert not form.winfo_exists() or form.error.cget("text") == "", form.error.cget("text")
    win.update()

ctk.set_appearance_mode("Light")
win = MainWindow(store, {})
win.geometry("1320x820+0+0")
win.update()

new("capability", Name="Sales", **{"Business Owner": "Maria"})
new("capability", Name="Lead Management", **{"Parent Capability": "BC-0001 · Sales"})
new("process", Name="Order to Cash", **{"Process Owner": "Omar"})
new("dataobject", Name="Customer", **{"Data Classification": "Confidential", "Contains Personal Data": "Yes"})
new("itcomponent", Name="PostgreSQL 15", Provider="PostgreSQL", **{"Technical Stack": "Database", "Lifecycle Status": "Active"})
new("itcomponent", Name="Windows Server 2012", Provider="Microsoft", **{"Technical Stack": "Operating System", "Lifecycle Status": "End of Life"})

# application with relationships through the form pickers
form = RecordForm(win, store, "application", None, win.data_changed)
fill(form, Name="CRM Suite", Description="Customer relationship mgmt", **{"Lifecycle Status": "Active",
     "Business Criticality": "High", "Business Owner": "Maria"})
for rule, direction, picker in form._pickers:
    key = (rule.source, rule.target, direction)
    if key == ("application", "capability", "out"):
        picker._vars["BC-0002"].set(True)
    if key == ("application", "itcomponent", "out"):
        picker._vars["ITC-0001"].set(True)
    if key == ("application", "dataobject", "out"):
        picker._vars["DO-0001"].set(True)
snap("form_application")
form._submit(); win.update()
new("application", Name="Legacy Billing", **{"Lifecycle Status": "Phase Out", "Business Criticality": "Mission Critical"})
assert store.pending().count > 8
snap("dashboard_unsaved")

assert win.save()
assert not store.dirty, "save should clear pending"
for key in ["application", "capmap", "dashboard", "itcomponent"]:
    win.show(key); snap(f"view_{key}")

# validation error is shown inline, not raised
form = RecordForm(win, store, "application", None, win.data_changed)
form._submit(); win.update()
assert "required" in form.error.cget("text"), form.error.cget("text")
snap("form_error"); form.destroy()

# dark mode
ctk.set_appearance_mode("Dark"); win.theme.select(); win._restyle()
win.show("dashboard"); snap("dashboard_dark")
win.show("application"); snap("view_application_dark")

# reload from disk gives same data
s2 = Store(path); s2.load()
assert len(s2.all("application")) == 2 and len(s2.links) == 3, (len(s2.all("application")), len(s2.links))
win.destroy()
print("GUI SMOKE OK")
