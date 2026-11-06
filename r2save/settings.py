"""Small persisted settings (settings.json): language, backups to keep.

Location: next to the editor when run from source; %APPDATA%\\Remnant2SaveEditor when packaged as .exe
(a PyInstaller one-file build unpacks itself into a temporary folder that is deleted on exit).
"""
import json
import os
import sys

DEFAULTS = {
    "language": "en",
    "backups_keep": 20,      # editor backups kept per save file; 0 = keep everything
}


def app_dir():
    if getattr(sys, "frozen", False):
        base = os.path.join(os.environ.get("APPDATA") or os.path.dirname(sys.executable), "Remnant2SaveEditor")
        try:
            os.makedirs(base, exist_ok=True)
        except OSError:
            base = os.path.dirname(sys.executable)
        return base
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


PATH = os.path.join(app_dir(), "settings.json")


def _read():
    try:
        with open(PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get(key):
    return _read().get(key, DEFAULTS.get(key))


def set(key, value):  # noqa: A001 - mirrors get()
    data = _read()
    data[key] = value
    try:
        with open(PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError:
        pass
