from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_dotenv(path: Path | None = None) -> None:
    """Load simple KEY=VALUE lines from .env without adding a dependency."""
    env_path = path or PROJECT_ROOT / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


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
        load_dotenv()
        use_json_mode = os.getenv("OPENAI_USE_JSON_MODE", "true").lower()
        trust_env = os.getenv("OPENAI_TRUST_ENV", "false").lower()
        return cls(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            api_endpoint=os.getenv("OPENAI_API_ENDPOINT") or None,
            proxy_url=os.getenv("OPENAI_PROXY_URL") or None,
            trust_env=trust_env in {"1", "true", "yes"},
            use_json_mode=use_json_mode not in {"0", "false", "no"},
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
