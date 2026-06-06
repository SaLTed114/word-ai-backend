"""
GUI installer for Word AI Assistant.

Packaged as a standalone exe with PyInstaller.
Embeds the dist/WordAI directory and installs it.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


APP_NAME = "Word AI Assistant"
APP_EXE = "WordAI.exe"


def _is_admin() -> bool:
    """Check if the process has administrator privileges."""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def _elevate() -> None:
    """Re-launch the current script with administrator privileges."""
    import ctypes
    exe = sys.executable
    params = " ".join(sys.argv[1:])
    ret = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", exe, params, None, 1  # 1 = SW_SHOWNORMAL
    )
    if ret <= 32:
        raise RuntimeError(f"Failed to elevate (code {ret}). Installation requires admin rights.")


def get_bundled_source() -> Path | None:
    """Find the bundled WordAI dist directory or the source project."""
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
        # One-file mode: data is extracted to _MEIPASS
        wordai = base / "WordAI"
        if (wordai / APP_EXE).exists():
            return wordai
        # Maybe data was bundled differently
        for candidate in [base, base / "dist" / "WordAI", base.parent]:
            if (candidate / APP_EXE).exists():
                return candidate
        return None
    else:
        # Running from source: look for dist directory
        project = Path(__file__).resolve().parents[1]
        wordai = project / "dist" / "WordAI"
        if (wordai / APP_EXE).exists():
            return wordai
        return project  # fallback to project root


class InstallerApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} Setup")
        self.root.geometry("520x420")
        self.root.resizable(False, False)
        self.root.configure(bg="#f5f6f8")

        # Try to set icon
        try:
            self.root.iconbitmap(default="")
        except Exception:
            pass

        # State
        self.install_dir = tk.StringVar(value=str(Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "WordAIAssistant"))
        self.create_desktop = tk.BooleanVar(value=True)
        self.source_dir = get_bundled_source()

        # Build UI
        self._build_header()
        self._build_body()
        self._build_footer()

        # Center on screen
        self.root.update_idletasks()
        w, h = self.root.winfo_width(), self.root.winfo_height()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    def _build_header(self):
        header = tk.Frame(self.root, bg="#2563eb", height=80)
        header.pack(fill="x")
        header.pack_propagate(False)

        title = tk.Label(
            header, text=APP_NAME, font=("Segoe UI", 18, "bold"),
            bg="#2563eb", fg="white"
        )
        title.pack(pady=(18, 0))

        subtitle = tk.Label(
            header, text="AI-powered writing assistant for Microsoft Word",
            font=("Segoe UI", 10), bg="#2563eb", fg="#bfdbfe"
        )
        subtitle.pack()

    def _build_body(self):
        body = tk.Frame(self.root, bg="#f5f6f8")
        body.pack(fill="both", expand=True, padx=32, pady=20)

        # Install directory
        tk.Label(body, text="Install location", font=("Segoe UI", 11, "bold"),
                 bg="#f5f6f8", anchor="w").pack(fill="x")

        dir_frame = tk.Frame(body, bg="#f5f6f8")
        dir_frame.pack(fill="x", pady=(4, 16))
        entry = tk.Entry(dir_frame, textvariable=self.install_dir, font=("Segoe UI", 10),
                         relief="solid", borderwidth=1)
        entry.pack(side="left", fill="x", expand=True, ipady=4)
        tk.Button(dir_frame, text="Browse...", command=self._browse_install,
                  font=("Segoe UI", 10), bg="#e5e7eb", borderwidth=0,
                  cursor="hand2", padx=12).pack(side="left", padx=(8, 0))

        # Desktop shortcut
        tk.Checkbutton(body, text="Create desktop shortcut", variable=self.create_desktop,
                       font=("Segoe UI", 10), bg="#f5f6f8", activebackground="#f5f6f8",
                       cursor="hand2").pack(anchor="w", pady=(0, 16))

        # Separator
        ttk.Separator(body, orient="horizontal").pack(fill="x", pady=(0, 12))

        tk.Label(
            body,
            text="After installation, open Word to see the Word AI tab in the ribbon.\n"
                 "Configure your AI model in the Settings panel before use.",
            font=("Segoe UI", 9), bg="#f5f6f8", fg="#6b7280", justify="left"
        ).pack(anchor="w")

    def _build_footer(self):
        footer = tk.Frame(self.root, bg="#f5f6f8")
        footer.pack(fill="x", padx=32, pady=(0, 20))

        tk.Button(footer, text="Cancel", command=self.root.destroy,
                  font=("Segoe UI", 10), bg="#e5e7eb", borderwidth=0,
                  cursor="hand2", padx=24, pady=6).pack(side="right", padx=(8, 0))

        self.install_btn = tk.Button(
            footer, text="Install", command=self._do_install,
            font=("Segoe UI", 10, "bold"), bg="#2563eb", fg="white",
            borderwidth=0, cursor="hand2", padx=24, pady=6
        )
        self.install_btn.pack(side="right")

    def _browse_install(self):
        path = filedialog.askdirectory(title="Choose install location")
        if path:
            self.install_dir.set(path)

    def _do_install(self):
        install_path = Path(self.install_dir.get())
        data_path = install_path / "data"

        if not install_path.parent.exists():
            messagebox.showerror("Error", f"Invalid install path:\n{install_path}")
            return

        if not self.source_dir or not self.source_dir.exists():
            messagebox.showerror("Error", "Source files not found. The installer may be corrupted.")
            return

        self.install_btn.config(text="Installing...", state="disabled")

        try:
            self._run_install(install_path, data_path)
        except Exception as e:
            messagebox.showerror("Installation Failed", str(e))
            self.install_btn.config(text="Install", state="normal")
            return

        self.install_btn.config(text="Installed!")

        # Ask to launch
        if messagebox.askyesno("Installation Complete",
                               f"{APP_NAME} has been installed.\n\nLaunch now?"):
            exe = install_path / APP_EXE
            if exe.exists():
                subprocess.Popen([str(exe)], cwd=str(install_path))

        self.root.destroy()

    def _run_install(self, install_path: Path, data_path: Path):
        # Remove existing installation
        if install_path.exists():
            shutil.rmtree(install_path, ignore_errors=True)

        # Copy files
        shutil.copytree(self.source_dir, install_path)
        os.makedirs(data_path, exist_ok=True)

        # Copy default .env from template if none exists
        env_file = data_path / ".env"
        if not env_file.exists():
            default_env = install_path / "_internal" / ".env.example"
            if default_env.exists():
                shutil.copy(default_env, env_file)

        # Create shortcuts
        self._create_shortcut(install_path, "desktop")
        self._create_shortcut(install_path, "start_menu")

        # Registry: install info
        self._set_registry("HKLM", f"SOFTWARE\\{APP_NAME}", "InstallDir", str(install_path))
        self._set_registry("HKLM", f"SOFTWARE\\{APP_NAME}", "DataDir", str(data_path))

        # Registry: trust manifest for Word sideloading
        guid = "6b4a47f8-6f03-4dc2-b41b-3e414abbb8f9"
        wef_key = f"HKCU\\SOFTWARE\\Microsoft\\Office\\16.0\\WEF\\TrustedCatalogs\\{{{guid}}}"
        self._set_registry("HKCU", wef_key.replace("HKCU\\", ""), "Id", guid)
        self._set_registry("HKCU", wef_key.replace("HKCU\\", ""), "Url", "https://localhost:3443")
        self._set_registry("HKCU", wef_key.replace("HKCU\\", ""), "Flags", "1", "REG_DWORD")
        # Also copy manifest locally for fallback
        addin_dir = install_path / "addin"
        addin_dir.mkdir(parents=True, exist_ok=True)
        for src in [
            install_path / "_internal" / "word-addin" / "manifest.xml",
            self.source_dir / "word-addin" / "manifest.xml",
        ]:
            if src.exists():
                shutil.copy(src, addin_dir / "manifest.xml")
                break

        # Trust SSL certificate
        cert_file = install_path / "_internal" / ".certs" / "localhost.pem"
        if cert_file.exists():
            subprocess.run(
                ["certutil", "-addstore", "-f", "Root", str(cert_file)],
                capture_output=True
            )

        # Create uninstaller shortcut
        uninstaller = install_path / "uninstall.bat"
        self._write_uninstaller(uninstaller, install_path, data_path)

    def _create_shortcut(self, install_path: Path, kind: str):
        """Create a Windows shortcut using PowerShell."""
        if kind == "desktop" and not self.create_desktop.get():
            return

        appdata = os.environ.get("APPDATA", "")
        if kind == "start_menu":
            link_dir = os.path.join(os.environ.get("ProgramData", "C:\\ProgramData"),
                                    "Microsoft", "Windows", "Start Menu", "Programs", APP_NAME)
            os.makedirs(link_dir, exist_ok=True)
        else:
            link_dir = os.path.join(os.environ.get("PUBLIC", "C:\\Users\\Public"), "Desktop")

        link_path = os.path.join(link_dir, f"{APP_NAME}.lnk")
        target = str(install_path / APP_EXE)

        icon = str(install_path / "_internal" / "assets" / "app.ico")
        ps = f"""
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut('{link_path}')
$s.TargetPath = '{target}'
$s.WorkingDirectory = '{install_path}'
$s.IconLocation = '{icon}'
$s.Save()
"""
        try:
            subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                           capture_output=True, check=True)
        except subprocess.CalledProcessError:
            pass

    def _set_registry(self, hive: str, key: str, name: str, value: str, reg_type: str = "REG_SZ"):
        """Set a registry value via reg.exe."""
        try:
            full_key = f"{hive}\\{key}"
            subprocess.run(
                ["reg", "add", full_key, "/v", name, "/t", reg_type, "/d", value, "/f"],
                capture_output=True, check=True
            )
        except subprocess.CalledProcessError:
            pass

    def _write_uninstaller(self, path: Path, install_path: Path, data_path: Path):
        """Write the uninstall batch script."""
        content = f"""@echo off
title Uninstall {APP_NAME}
echo ============================================
echo   Uninstall {APP_NAME}
echo ============================================
echo.
net session >nul 2>&1 || (echo Run as administrator. & pause & exit /b 1)
echo.
echo [*] Stopping running instances...
taskkill /f /im {APP_EXE} >nul 2>&1
echo [*] Removing shortcuts...
rmdir /s /q "%ProgramData%\\Microsoft\\Windows\\Start Menu\\Programs\\{APP_NAME}" 2>nul
del /q "%PUBLIC%\\Desktop\\{APP_NAME}.lnk" 2>nul
echo [*] Removing registry entries...
reg delete "HKLM\\SOFTWARE\\{APP_NAME}" /f >nul 2>&1
reg delete "HKCU\\SOFTWARE\\Microsoft\\Office\\16.0\\WEF\\TrustedCatalogs\\{{6b4a47f8-6f03-4dc2-b41b-3e414abbb8f9}}" /f >nul 2>&1
echo [*] Removing SSL certificate...
certutil -delstore "Root" "localhost" >nul 2>&1
echo.
set /p "KEEP=Keep data at {data_path}? [Y/n]: "
if /i not "%KEEP%"=="n" (
    echo [*] Data kept at: {data_path}
) else (
    echo [*] Removing data...
    rmdir /s /q "{data_path}" 2>nul
)
echo [*] Removing application files...
cd /d "%TEMP%"
rmdir /s /q "{install_path}" 2>nul
echo.
echo ============================================
echo   {APP_NAME} has been uninstalled.
echo ============================================
pause
"""
        path.write_text(content, encoding="ascii", errors="replace")

    def run(self):
        self.root.mainloop()


def main():
    if not _is_admin():
        try:
            _elevate()
        except RuntimeError:
            pass  # User declined elevation
        sys.exit(0)
    app = InstallerApp()
    app.run()


if __name__ == "__main__":
    main()
