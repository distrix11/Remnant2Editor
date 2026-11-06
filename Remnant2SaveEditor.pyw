"""Starts the Remnant 2 save editor GUI. Double-click (needs Python 3.8+) or build an .exe with build.bat."""
import os
import sys

if getattr(sys, "frozen", False) or sys.stderr is None:
    # A windowed .exe has no console: sys.stdout / sys.stderr are None and any traceback print
    # would crash. Send them to a log file instead.
    _log_dir = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "Remnant2SaveEditor")
    try:
        os.makedirs(_log_dir, exist_ok=True)
        _log = open(os.path.join(_log_dir, "editor.log"), "a", encoding="utf-8", buffering=1)
    except OSError:
        _log = open(os.devnull, "w")
    sys.stdout = sys.stderr = _log
if not getattr(sys, "frozen", False):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from r2save.gui import main  # noqa: E402

main()
