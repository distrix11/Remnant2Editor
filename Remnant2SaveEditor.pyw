"""Double-click to start the Remnant 2 save editor GUI (needs Python 3.8+ for Windows)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from r2save.gui import main  # noqa: E402

main()
