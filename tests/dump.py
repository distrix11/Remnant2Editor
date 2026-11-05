"""Dump every property path of a save (for exploration). usage: dump.py file.sav [filter]"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from r2save.core import SaveFile  # noqa: E402
from r2save.nav import walk, fmt_value  # noqa: E402

sf = SaveFile.load(sys.argv[1])
flt = sys.argv[2] if len(sys.argv) > 2 else None
for path, p, bag, sd in walk(sf):
    if flt and flt not in path:
        continue
    print("%s [%s] %s" % (path, p.type.name, fmt_value(p.value)))
