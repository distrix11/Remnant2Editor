# -*- mode: python ; coding: utf-8 -*-
# PyInstaller build of the GUI as a single windowed .exe.   Run:  build.bat
# (or:  python -m PyInstaller --clean --noconfirm Remnant2SaveEditor.spec)

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

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Remnant2SaveEditor",
    icon="r2save/assets/icon.ico",
    console=False,          # windowed app, no console window
    upx=False,              # UPX-packed exes trigger far more antivirus false positives
    debug=False,
    strip=False,
)
