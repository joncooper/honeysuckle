"""Configuration via pydantic-settings."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Find .env file - check backend dir first, then project root
_backend_dir = Path(__file__).parent.parent.parent.parent
_project_root = _backend_dir.parent
_env_file = _backend_dir / ".env" if (_backend_dir / ".env").exists() else _project_root / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(_env_file),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API Keys
    openai_api_key: str
    anthropic_api_key: str | None = None  # Optional - can use Claude Max OAuth instead

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # OpenAI Realtime settings
    openai_realtime_model: str = "gpt-4o-realtime-preview-2024-12-17"
    openai_realtime_voice: str = "alloy"

    # Claude Agent SDK settings
    claude_model: str = "claude-sonnet-4-20250514"

    # gday CLI path
    gday_path: str = "~/.local/bin/gday"

    # Observability
    phoenix_enabled: bool = True
    phoenix_port: int = 6006


settings = Settings()
