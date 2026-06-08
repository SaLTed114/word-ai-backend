@echo off
setlocal enabledelayedexpansion

title Word AI - Build

echo ============================================
echo  Word AI Assistant - Build Script
echo ============================================
echo.

REM Check prerequisites
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found.
    exit /b 1
)

where openssl >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] OpenSSL not found. It is required to generate the local HTTPS certificate.
    exit /b 1
)

set "PROJECT_ROOT=%~dp0.."
cd /d "%PROJECT_ROOT%"

echo [1/4] Installing dependencies...
python -m pip install -r requirements.txt pyinstaller --quiet 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    exit /b 1
)

python -m PyInstaller --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller is not available after dependency installation.
    exit /b 1
)

echo [2/4] Preparing HTTPS certificate for installer...
if not exist ".certs\localhost.pem" (
    echo [*] Generating local HTTPS certificate...
    python scripts\generate_cert.py
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to generate certificates.
        exit /b 1
    )
) else (
    echo [*] HTTPS certificate OK.
)

echo.
echo [3/4] Building Word AI application...
python -m PyInstaller build.spec --clean --noconfirm
if %errorlevel% neq 0 (
    echo [ERROR] Application build failed.
    exit /b 1
)
echo [*] Application built: dist\WordAI\

echo.
echo [4/4] Building GUI installer...
python -m PyInstaller installer.spec --clean --noconfirm
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
echo   Certificate:  setup trusts the bundled localhost HTTPS certificate
echo.
echo To distribute, give users: dist\WordAI-Setup.exe
echo.
endlocal
