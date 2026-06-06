@echo off
setlocal enabledelayedexpansion

title Word AI - Build

echo ============================================
echo  Word AI Assistant - Build Script
echo ============================================
echo.

REM Check prerequisites
where pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller not found. Run: pip install pyinstaller
    exit /b 1
)

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found.
    exit /b 1
)

set "PROJECT_ROOT=%~dp0.."
cd /d "%PROJECT_ROOT%"

echo [1/4] Installing dependencies...
pip install -r requirements.txt pyinstaller --quiet 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    exit /b 1
)

echo [2/4] Checking SSL certificates...
if not exist ".certs\localhost.pem" (
    echo [*] Generating SSL certificates...
    python scripts\generate_cert.py
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to generate certificates.
        exit /b 1
    )
) else (
    echo [*] SSL certificates OK.
)

echo.
echo [3/4] Building Word AI application...
pyinstaller build.spec --clean --noconfirm
if %errorlevel% neq 0 (
    echo [ERROR] Application build failed.
    exit /b 1
)
echo [*] Application built: dist\WordAI\

echo.
echo [4/4] Building GUI installer...
pyinstaller installer.spec --clean --noconfirm
if %errorlevel% neq 0 (
    echo [ERROR] Installer build failed.
    exit /b 1
)

echo.
echo ============================================
echo  Build complete.
echo ============================================
echo.
echo   Application:  dist\WordAI\WordAI.exe
echo   Installer:    dist\WordAI-Setup.exe
echo.
echo To distribute, give users: dist\WordAI-Setup.exe
echo.
endlocal
