"""Compatibility entry point: the GUI lives in r2save.ui (app.py + one module per tab)."""
from .ui.common import *  # noqa: F401,F403
from .ui.common import _ask_int, _fmt_local, _INT_TYPES  # noqa: F401
from .ui.app import App, main  # noqa: F401

if __name__ == "__main__":
    main()
