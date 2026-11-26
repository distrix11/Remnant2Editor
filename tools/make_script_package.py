"""Builds the script-only package (no .exe/.dll/.bat) for sites that do not accept executables, e.g. Nexus Mods.

    python tools/make_script_package.py [output_dir]

The archive holds the Python sources, data and assets, the double-click starter Remnant2SaveEditor.pyw, the licenses
and a short READ ME FIRST.txt. The user needs Python 3.8+ from python.org (it includes Tkinter).
"""
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from r2save import __version__  # noqa: E402

FORBIDDEN = (".exe", ".dll", ".bat", ".cmd", ".com", ".scr", ".msi", ".ps1", ".vbs", ".pyd", ".so")
TOP = "Remnant2SaveEditor"

README = """Remnant 2 Save Editor {v}, script package (no .exe inside)
=================================================================

ENGLISH
1. Install Python 3.8 or newer from https://www.python.org/downloads/ (once). Keep the default options:
   they include Tkinter (the window toolkit) and the Python launcher that opens .pyw files.
2. Extract this whole archive anywhere, for example into Documents.
3. Close Remnant 2 completely.
4. Double-click Remnant2SaveEditor.pyw.
   If it opens in a text editor instead: right-click it > Open with > Python (pythonw / Python launcher).

Do not want to install Python? Download the ready-to-run build (with Remnant2SaveEditor.exe) from
https://github.com/distrix11/Remnant2Editor/releases/latest

The editor backs up every file before saving. Settings are kept in settings.json next to this file,
the log in %APPDATA%\\Remnant2SaveEditor\\editor.log (attach it to bug reports).

РУССКИЙ
1. Один раз установи Python 3.8 или новее с https://www.python.org/downloads/ (настройки по умолчанию:
   в них есть Tkinter и запускалка для .pyw).
2. Распакуй архив целиком в любую папку.
3. Полностью закрой Remnant 2.
4. Дважды щёлкни Remnant2SaveEditor.pyw.
   Если он открылся в блокноте: правый клик > Открыть с помощью > Python.

Не хочешь ставить Python? Готовая сборка с .exe: https://github.com/distrix11/Remnant2Editor/releases/latest
"""


def files():
    yield "Remnant2SaveEditor.pyw"
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        if os.path.exists(os.path.join(ROOT, name)):
            yield name
    for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, "r2save")):
        dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
        for f in sorted(filenames):
            if f.endswith((".pyc", ".pyo")):
                continue
            yield os.path.relpath(os.path.join(dirpath, f), ROOT).replace(os.sep, "/")


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "dist")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "Remnant2SaveEditor-v%s-scripts.zip" % __version__)
    names = list(files())
    bad = [n for n in names if n.lower().endswith(FORBIDDEN)]
    if bad:
        raise SystemExit("refusing to package executables: %s" % bad)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for n in names:
            z.write(os.path.join(ROOT, n), TOP + "/" + n)
        z.writestr(TOP + "/READ ME FIRST.txt", README.format(v=__version__).replace("\n", "\r\n"))
    print(out, len(names) + 1, "files", os.path.getsize(out), "bytes")


if __name__ == "__main__":
    main()
