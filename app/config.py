from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application settings
    APP_ENV: str = "development"
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000

    # Playwright browser settings
    BROWSER_HEADLESS: bool = False
    BROWSER_USER_DATA_DIR: str = "./data/browser-profile"

    # Discovery Configuration (Prompt 2)
    DISCOVERY_MAX_KEYWORDS: int = 10
    DISCOVERY_MAX_RESULTS_PER_KEYWORD: int = 50
    DISCOVERY_SCROLL_COUNT: int = 5
    DISCOVERY_DELAY_MIN: float = 1.5
    DISCOVERY_DELAY_MAX: float = 3.5

    # Future integration settings (Prompts 3-6)
    GEMINI_API_KEY: str | None = None
    SUPABASE_URL: str | None = None
    SUPABASE_KEY: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def resolved_browser_profile_dir(self) -> Path:
        """Returns the resolved absolute path to the browser user data directory."""
        path = Path(self.BROWSER_USER_DATA_DIR)
        if not path.is_absolute():
            # Resolve relative to project root (directory containing run.py / .env)
            project_root = Path(__file__).resolve().parent.parent
            path = (project_root / path).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache()
def get_settings() -> Settings:
    return Settings()
