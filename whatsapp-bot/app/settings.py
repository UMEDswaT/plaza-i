import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
    ai_provider: str = os.getenv("AI_PROVIDER", "openai").lower()
    freellmapi_base_url: str = os.getenv("FREELLMAPI_BASE_URL", "http://127.0.0.1:3001/v1")
    freellmapi_api_key: str = os.getenv("FREELLMAPI_API_KEY", "")
    freellmapi_model: str = os.getenv("FREELLMAPI_MODEL", "auto")
    meta_access_token: str = os.getenv("META_ACCESS_TOKEN", "")
    meta_app_secret: str = os.getenv("META_APP_SECRET", "")
    meta_verify_token: str = os.getenv("META_VERIFY_TOKEN", "")
    meta_phone_number_id: str = os.getenv("META_PHONE_NUMBER_ID", "")
    meta_graph_version: str = os.getenv("META_GRAPH_VERSION", "v25.0")
    admin_username: str = os.getenv("ADMIN_USERNAME", "plazai")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "")
    database_path: str = os.getenv("DATABASE_PATH", "./data/plazai.sqlite3")
    demo_mode: bool = os.getenv("DEMO_MODE", "0") == "1"
    ai_preview_mode: bool = os.getenv("AI_PREVIEW_MODE", "0") == "1"
    suggest_from_staff: bool = os.getenv("SUGGEST_FROM_STAFF", "1") == "1"

    def check(self) -> None:
        if not self.admin_password or len(self.admin_password) < 12:
            raise RuntimeError("ADMIN_PASSWORD must have at least 12 characters")
        if self.ai_provider not in ("openai", "freellmapi"):
            raise RuntimeError("AI_PROVIDER must be openai or freellmapi")
        if self.ai_provider == "freellmapi":
            # Experimental local-only, synthetic-data preview. Never send
            # live customer messages through a personal free-tier router.
            if not (self.demo_mode and self.ai_preview_mode):
                raise RuntimeError("FreeLLMAPI requires DEMO_MODE=1 and AI_PREVIEW_MODE=1")
            if not self.freellmapi_api_key or not self.freellmapi_base_url or not self.freellmapi_model:
                raise RuntimeError("FreeLLMAPI preview requires URL, API key and model")
            from app.freellmapi import FreeLLMAPIService
            # Validate endpoint before accepting an untrusted network URL.
            from urllib.parse import urlsplit
            parsed = urlsplit(self.freellmapi_base_url)
            if (not parsed.hostname or parsed.query or parsed.fragment or
                parsed.username or parsed.password or
                not self.freellmapi_base_url.rstrip("/").endswith("/v1") or
                (parsed.scheme != "https" and not
                 (parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1", "::1")))):
                raise RuntimeError("FreeLLMAPI endpoint requires HTTPS or loopback HTTP and /v1")
            return
        if self.demo_mode:
            if self.ai_preview_mode and not self.openai_api_key:
                raise RuntimeError("AI_PREVIEW_MODE requires OPENAI_API_KEY")
            return
        if self.ai_preview_mode:
            raise RuntimeError("AI_PREVIEW_MODE requires DEMO_MODE=1")
        required = {
            "OPENAI_API_KEY": self.openai_api_key,
            "META_ACCESS_TOKEN": self.meta_access_token,
            "META_APP_SECRET": self.meta_app_secret,
            "META_VERIFY_TOKEN": self.meta_verify_token,
            "META_PHONE_NUMBER_ID": self.meta_phone_number_id,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise RuntimeError("Missing required environment variables: " + ", ".join(missing))
