# LeanIX Lite

A small desktop app for managing an enterprise-architecture repository (BDAT: **B**usiness,
**D**ata, **A**pplication, **T**echnology), inspired by SAP LeanIX. All data lives in **one Excel
file** in a shared OneDrive folder, so you and your manager work on the same data.

## What it manages

| Layer | Fact sheets |
|---|---|
| Business | Business Capabilities (hierarchical), Business Processes |
| Data | Data Objects (classification, personal-data flag) |
| Application | Applications (lifecycle, criticality, owners) |
| Technology | IT Components (provider, technical stack, lifecycle) |

Links between them (Application *supports* Capability, *runs on* IT Component, *uses* Data Object, ...)
are edited inside each record's form and stored in the `Relationships` sheet. Allowed link types are
listed in `app/schema.py` (`RELATION_RULES`).

Screens: Dashboard (BDAT counts, charts, "things to look at"), Capability Map (tree), and a searchable,
sortable, filterable grid per fact sheet with Add / Edit / Delete.

## Run it

Needs Python 3.10+ on Windows (Tkinter is included in the python.org installer).

```
cd leanix_lite
pip install -r requirements.txt
python main.py
```

On first launch click **Select the OneDrive folder...** and pick a folder inside your synced OneDrive.
The app creates `EA-Repository.xlsx` there itself (or opens it if it exists). The choice is remembered per user in
`%APPDATA%\LeanIXLite\config.json`. Your manager does the same and picks the *same* file.

## Build the standalone .exe (for your manager)

See `HOW-TO-GET-THE-EXE.txt` for a plain-language walkthrough. On a Windows machine with Python, double-click `build_exe.bat`. It creates a venv,
installs dependencies, runs the tests and runs PyInstaller. Result: `dist\LeanIXLite.exe`
- copy it to your manager; no Python needed. (PyInstaller cannot cross-compile, so it must be built on Windows.)
If your company's antivirus or policy blocks unsigned executables, run from source instead (`run_app.bat`).

## How shared editing works (important)

OneDrive syncs whole files, so the app protects against overwriting each other's work:

* **Save merges, it does not overwrite.** On Save the app re-reads the file as it is now and applies
  *only your changes* (new, edited, deleted records and links) on top. Edits to different fields or
  different records merge automatically.
* **Real conflicts are shown, never silent.** If you both changed the same field (or one edited what
  the other deleted), a dialog lets you keep *their* or *your* version before anything is written.
* **New records can't collide.** If you both create `APP-0007`, yours is renumbered on save and its
  links follow it.
* **Locked file = no crash.** If the file is open in Excel (detected through Excel's `~$` owner file
  and `PermissionError`) or OneDrive is mid-sync, you get a Retry/Cancel box; your changes stay in the app.
* **Refresh data** reloads the file. The app also checks every 15 s: if nothing is unsaved it refreshes
  by itself, otherwise it shows a banner.
* **Backups:** before every save the previous file is copied to `%APPDATA%\LeanIXLite\backups`
  (last 15 kept, local, not synced).

Team rules that keep this smooth: edit through the app, not by hand in Excel; save soon after editing;
click **Refresh** before a long editing session.

### Known limits

* Two saves within the OneDrive sync delay (seconds) from two computers can still make OneDrive create a
  "conflicted copy". The app warns if it finds files named like `<name>-<something>.xlsx` next to the
  database (this naming is a heuristic; check OneDrive's behaviour in your tenant).
* The app owns the workbook layout: it rewrites the file on save, so charts/macros/colours added by hand in
  Excel are not preserved. Extra *columns* you add to a sheet are kept.
* Rows typed directly into Excel without an ID get one when loaded; press Save to persist it.
* There is no per-user permission model: anyone with access to the file can edit everything.

## Project layout

```
main.py              entry point
app/schema.py        BDAT entities, fields, dropdown values, allowed relationships
app/store.py         Excel read/write, validation, merge-on-save, locking, backups
app/config.py        per-user settings (%APPDATA%\LeanIXLite\config.json)
app/ui_main.py       main window, Refresh/Save, lock + conflict handling
app/ui_views.py      Dashboard, inventory grid, capability map
app/ui_forms.py      record form, conflict dialog, first-run setup
tests/               pytest suite for the store + headless GUI smoke scripts
```

Run the tests: `python -m pytest -q tests`.
