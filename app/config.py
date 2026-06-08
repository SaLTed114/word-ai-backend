from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


def _get_base_dir() -> Path:
    """Get the base directory containing bundled resources."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[1]


def _get_data_dir() -> Path:
    """Get the writable data directory (DB, .env overrides, etc.)."""
    env_dir = os.environ.get("WORD_AI_DATA_DIR", "")
    if env_dir.strip():
        return Path(env_dir.strip())

    if getattr(sys, "frozen", False):
        # Check Windows registry (set by installer)
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                r"SOFTWARE\Word AI Assistant") as key:
                reg_dir, _ = winreg.QueryValueEx(key, "DataDir")
                if reg_dir and reg_dir.strip():
                    return Path(reg_dir.strip())
        except (OSError, ImportError):
            pass

        # Default: %APPDATA%\Word AI Assistant
        base = Path(os.environ["APPDATA"]) / "Word AI Assistant"
        base.mkdir(parents=True, exist_ok=True)
        return base
    return _get_base_dir()


PROJECT_ROOT = _get_base_dir()
DATA_DIR = _get_data_dir()

# .env is writable — use DATA_DIR, fall back to PROJECT_ROOT if not yet created
_ENV_PATH = DATA_DIR / ".env"
if not _ENV_PATH.exists() and (PROJECT_ROOT / ".env").exists():
    import shutil
    shutil.copy(PROJECT_ROOT / ".env", _ENV_PATH)
ENV_PATH = _ENV_PATH
AI_ENV_KEYS = (
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "OPENAI_BASE_URL",
    "OPENAI_API_ENDPOINT",
    "OPENAI_PROXY_URL",
    "OPENAI_TRUST_ENV",
    "OPENAI_USE_JSON_MODE",
)


def load_dotenv(path: Path | None = None, override: bool = False) -> None:
    """Load simple KEY=VALUE lines from .env without adding a dependency."""
    env_path = path or ENV_PATH
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if override or key not in os.environ:
            os.environ[key] = value


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _stringify_bool(value: bool) -> str:
    return "true" if value else "false"


def read_env_values(path: Path | None = None) -> dict[str, str]:
    env_path = path or ENV_PATH
    values: dict[str, str] = {}
    if not env_path.exists():
        return values

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def update_env_values(updates: Mapping[str, str], path: Path | None = None) -> None:
    env_path = path or ENV_PATH
    env_path.parent.mkdir(parents=True, exist_ok=True)
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    remaining = dict(updates)
    output: list[str] = []

    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or "=" not in raw_line:
            output.append(raw_line)
            continue

        key, _ = raw_line.split("=", 1)
        normalized_key = key.strip()
        if normalized_key in remaining:
            output.append(f"{normalized_key}={remaining.pop(normalized_key)}")
        else:
            output.append(raw_line)

    if output and output[-1].strip():
        output.append("")

    for key in AI_ENV_KEYS:
        if key in remaining:
            output.append(f"{key}={remaining.pop(key)}")

    for key, value in remaining.items():
        output.append(f"{key}={value}")

    env_path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")
    load_dotenv(env_path, override=True)


@dataclass
class AISettings:
    api_key: str
    model: str
    base_url: str
    api_endpoint: str | None = None
    proxy_url: str | None = None
    trust_env: bool = False
    use_json_mode: bool = True

    @classmethod
    def from_env(cls) -> "AISettings":
        load_dotenv(override=True)
        return cls(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            api_endpoint=os.getenv("OPENAI_API_ENDPOINT") or None,
            proxy_url=os.getenv("OPENAI_PROXY_URL") or None,
            trust_env=_parse_bool(os.getenv("OPENAI_TRUST_ENV"), False),
            use_json_mode=_parse_bool(os.getenv("OPENAI_USE_JSON_MODE"), True),
        )

    def is_ready(self) -> bool:
        return bool(self.api_key and self.model and (self.base_url or self.api_endpoint))

    def redacted(self) -> dict[str, str | bool | None]:
        suffix = f"...{self.api_key[-4:]}" if self.api_key else None
        return {
            "api_key": suffix,
            "model": self.model,
            "base_url": self.base_url,
            "api_endpoint": self.api_endpoint,
            "proxy_url": self.proxy_url,
            "trust_env": self.trust_env,
            "use_json_mode": self.use_json_mode,
        }

    def editable(self) -> dict[str, str | bool]:
        return {
            "api_key": self.api_key,
            "model": self.model,
            "base_url": self.base_url,
            "api_endpoint": self.api_endpoint or "",
            "proxy_url": self.proxy_url or "",
            "trust_env": self.trust_env,
            "use_json_mode": self.use_json_mode,
        }


def save_ai_settings(
    *,
    api_key: str,
    model: str,
    base_url: str,
    api_endpoint: str | None = None,
    proxy_url: str | None = None,
    trust_env: bool = False,
    use_json_mode: bool = True,
) -> AISettings:
    update_env_values(
        {
            "OPENAI_API_KEY": api_key.strip(),
            "OPENAI_MODEL": model.strip(),
            "OPENAI_BASE_URL": base_url.strip(),
            "OPENAI_API_ENDPOINT": (api_endpoint or "").strip(),
            "OPENAI_PROXY_URL": (proxy_url or "").strip(),
            "OPENAI_TRUST_ENV": _stringify_bool(trust_env),
            "OPENAI_USE_JSON_MODE": _stringify_bool(use_json_mode),
        }
    )
    return AISettings.from_env()
