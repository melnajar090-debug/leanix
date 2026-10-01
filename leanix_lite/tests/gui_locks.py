"""Headless check of the UI's locked-file and conflict handling (run under xvfb)."""
import os, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tkinter import messagebox
from app import store as st
from app.store import Store
from app import ui_main

tmp = Path(tempfile.mkdtemp()); path = tmp / "ea.xlsx"
store = Store.create_new(path)
win = ui_main.MainWindow(store, {})
shown = []
messagebox.askretrycancel = lambda t, m, **k: (shown.append(("retry", t)), len(shown) < 2)[1]   # retry once, then cancel
messagebox.showinfo = lambda t, m, **k: shown.append(("info", m))
store.add("application", {"Name": "A", "Lifecycle Status": "Active"})
win.update_chrome()

# 1) Excel has the file open -> warn, keep changes, don't crash
(tmp / "~$ea.xlsx").write_text("x")
assert win.save() is False and store.dirty and len(shown) == 2, shown
# 2) Excel closed -> save works
(tmp / "~$ea.xlsx").unlink()
assert win.save() is True and not store.dirty

# 3) conflict: another user edits same field; user picks "theirs"
rid = "APP-0001"
other = Store(path); other.load()
other.update("application", rid, {"Name": "A", "Lifecycle Status": "Phase Out"}); other.save()
store.update("application", rid, {"Name": "A", "Lifecycle Status": "End of Life"})
class FakeDlg:
    def __init__(self, *a, **k): pass
    def show(self): return "theirs"
ui_main.ConflictDialog = FakeDlg
assert win.save() is True
assert store.get("application", rid)["Lifecycle Status"] == "Phase Out" and not store.dirty
print("GUI LOCK/CONFLICT OK")
win.destroy()
