# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Word AI Backend."""

from pathlib import Path

_base = Path(SPECPATH)  # directory containing this spec file

# Collect data directories to bundle
datas = []

# word-addin static files
_addin = _base / "word-addin"
if _addin.exists():
    datas.append((str(_addin), "word-addin"))

# prompts
_prompts = _base / "prompts"
if _prompts.exists():
    datas.append((str(_prompts), "prompts"))

# skills
_skills = _base / "skills"
if _skills.exists():
    datas.append((str(_skills), "skills"))

# SSL certs
_certs = _base / ".certs"
if _certs.exists():
    datas.append((str(_certs), ".certs"))

# App icon for shortcuts
_ico = _base / "assets" / "app.ico"
if _ico.exists():
    datas.append((str(_ico), "assets"))

# .env file (if it exists, include as default)
_env = _base / ".env"
if _env.exists():
    datas.append((str(_env), "."))

a = Analysis(
    ["server.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # FastAPI / Starlette / Uvicorn
        "fastapi",
        "starlette",
        "uvicorn",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.logging",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "uvicorn.config",
        "uvicorn.server",
        # App modules
        "app",
        "app.main",
        "app.models",
        "app.services",
        "app.config",
        "app.prompts",
        "app.storage",
        "app.context_builder",
        "app.ai_client",
        "app.api_cli",
        # Dependencies
        "openai",
        "httpx",
        "httpx._config",
        "pydantic",
        "pydantic.fields",
        "pydantic.main",
        # Standard library
        "http.server",
        "ssl",
        "asyncio",
        "json",
        "sqlite3",
        "uuid",
        "pathlib",
        "winreg",
        "shutil",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "pandas",
        "PIL",
        "cv2",
        "tensorflow",
        "torch",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="WordAI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Keep console so users can see logs
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="WordAI",
)
