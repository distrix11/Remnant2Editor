# -*- mode: python ; coding: utf-8 -*-
# PyInstaller build of the GUI as a single windowed .exe.   Run:  build.bat
# (or:  python -m PyInstaller --clean --noconfirm Remnant2SaveEditor.spec)

import os
import re

# Version comes from r2save/__init__.py so the .exe "Details" tab always matches the app.
with open(os.path.join(SPECPATH, "r2save", "__init__.py"), encoding="utf-8") as _f:
    VERSION = re.search(r'__version__\s*=\s*"([^"]+)"', _f.read()).group(1)


def _version_file():
    """Write a Windows VERSIONINFO resource for the .exe (Properties -> Details).
    Plain text in PyInstaller's version-file format, so the spec needs no Windows-only imports."""
    n = tuple((list(map(int, re.findall(r"\d+", VERSION))) + [0, 0, 0, 0])[:4])
    strings = [
        ("CompanyName", "distrix11"),
        ("FileDescription", "Remnant 2 Save Editor"),
        ("FileVersion", VERSION),
        ("InternalName", "Remnant2SaveEditor"),
        ("LegalCopyright", "MIT License - github.com/distrix11/Remnant2Editor"),
        ("OriginalFilename", "Remnant2SaveEditor.exe"),
        ("ProductName", "Remnant 2 Save Editor"),
        ("ProductVersion", VERSION),
    ]
    text = (
        "VSVersionInfo(\n"
        "  ffi=FixedFileInfo(filevers=%r, prodvers=%r, mask=0x3f, flags=0x0, OS=0x40004,\n"
        "                    fileType=0x1, subtype=0x0, date=(0, 0)),\n"
        "  kids=[\n"
        "    StringFileInfo([StringTable('040904B0', [\n%s\n    ])]),\n"
        "    VarFileInfo([VarStruct('Translation', [1033, 1200])])\n"
        "  ]\n"
        ")\n" % (n, n, ",\n".join("      StringStruct(%r, %r)" % kv for kv in strings)))
    os.makedirs(workpath, exist_ok=True)
    path = os.path.join(workpath, "version_info.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


a = Analysis(
    ["Remnant2SaveEditor.pyw"],
    pathex=["."],
    datas=[
        ("r2save/data", "r2save/data"),        # db.json, names.json + licenses
        ("r2save/assets", "r2save/assets"),    # icons, emblem, Montserrat fonts + OFL
        ("LICENSE", "."),
        ("THIRD_PARTY_NOTICES.md", "."),
    ],
    hiddenimports=[],
    excludes=["PIL", "numpy", "pytest", "unittest", "pydoc_data"],
    noarchive=False,
)
pyz = PYZ(a.pure)

# R2_ONEDIR=1 builds a folder (exe + _internal) instead of a single self-extracting exe.
# The folder build unpacks nothing at start-up and usually triggers fewer antivirus heuristics.
ONEDIR = os.environ.get("R2_ONEDIR") == "1"

exe_options = dict(
    name="Remnant2SaveEditor",
    icon="r2save/assets/icon.ico",
    version=_version_file(),
    console=False,          # windowed app, no console window
    upx=False,              # UPX-packed exes trigger far more antivirus false positives
    debug=False,
    strip=False,
)

if ONEDIR:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, **exe_options)
    coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="Remnant2SaveEditor")
else:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], **exe_options)
