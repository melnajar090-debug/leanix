"""Per-user settings (not shared): path of the shared workbook, appearance."""
from __future__ import annotations

import json
import os
from pathlib import Path


def config_dir() -> Path:
    base = os.environ.get("APPDATA")                    # Windows: C:\Users\<you>\AppData\Roaming
    root = Path(base) if base else Path.home()
    return root / ("LeanIXLite" if base else ".leanix_lite")


CONFIG_PATH = config_dir() / "config.json"
BACKUP_DIR = config_dir() / "backups"                   # local on purpose: not synced by OneDrive


def load_config(path: Path = CONFIG_PATH) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_config(cfg: dict, path: Path = CONFIG_PATH) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except OSError:
        pass   # settings are a convenience; never crash over them
