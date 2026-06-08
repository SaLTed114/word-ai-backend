# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the GUI installer. Single-file exe with embedded WordAI dist."""

from pathlib import Path

_base = Path(SPECPATH)

datas = []

# Embed the WordAI dist directory
dist_dir = _base / "dist" / "WordAI"
if dist_dir.exists():
    # Collect each file individually for one-file mode
    for f in dist_dir.rglob("*"):
        if f.is_file():
            rel = f.relative_to(dist_dir.parent)
            datas.append((str(f), str(rel.parent)))

excluded_modules = [
    "fastapi",
    "starlette",
    "uvicorn",
    "openai",
    "httpx",
    "pydantic",
    "IPython",
    "jedi",
    "parso",
    "pygments",
    "sphinx",
    "docutils",
    "babel",
    "pytest",
    "py",
    "pluggy",
    "astroid",
    "mypy",
    "black",
    "blib2to3",
    "yapf",
    "yapf_third_party",
    "nbformat",
    "jsonschema",
    "jsonschema_specifications",
    "referencing",
    "rpds",
    "zmq",
    "psutil",
    "platformdirs",
    "matplotlib",
    "numpy",
    "pandas",
    "PIL",
    "cv2",
    "tensorflow",
    "torch",
    "PyQt5",
    "PyQt6",
    "PySide2",
    "PySide6",
    "qtpy",
    "cryptography",
    "bcrypt",
    "zstandard",
    "brotli",
    "brotlicffi",
]

a = Analysis(
    ["scripts\\installer_gui.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "tkinter",
        "tkinter.filedialog",
        "tkinter.messagebox",
        "tkinter.ttk",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_modules,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    a.zipfiles,
    name="WordAI-Setup",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
