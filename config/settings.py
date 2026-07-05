"""
Centralized Configuration Module
=================================
Loads all settings from environment variables via .env file.
Every module in the pipeline reads configuration from this single source.
No hardcoded values anywhere in the codebase.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Resolve project root and load .env
# ---------------------------------------------------------------------------
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class Settings:
    """Application-wide settings sourced from environment variables."""

    # --- Scraper ----------------------------------------------------------
    BASE_URL: str = os.getenv("BASE_URL", "https://books.toscrape.com")
    ACTIVE_PARSER: str = os.getenv("ACTIVE_PARSER", "books")
    TIMEOUT: int = int(os.getenv("TIMEOUT", "30"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY: int = int(os.getenv("RETRY_DELAY", "2"))
    USER_AGENT: str = os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    )
    REQUEST_DELAY: float = float(os.getenv("REQUEST_DELAY", "1"))

    # --- Output -----------------------------------------------------------
    OUTPUT_FOLDER: Path = PROJECT_ROOT / os.getenv("OUTPUT_FOLDER", "output")
    LOG_FOLDER: Path = PROJECT_ROOT / os.getenv("LOG_FOLDER", "logs")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

    # --- API --------------------------------------------------------------
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "5000"))
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

    # --- Database (optional) ----------------------------------------------
    DB_URL: Optional[str] = os.getenv("DB_URL") or None

    # --- Derived Paths ----------------------------------------------------
    TEMPLATES_FOLDER: Path = PROJECT_ROOT / "templates"
    STATIC_FOLDER: Path = PROJECT_ROOT / "static"

    @classmethod
    def ensure_directories(cls) -> None:
        """Create output and log directories if they don't exist."""
        try:
            cls.OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
            cls.LOG_FOLDER.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass

    @classmethod
    def get_parser_config(cls) -> dict:
        """Return a dictionary of parser-relevant configuration."""
        return {
            "base_url": cls.BASE_URL,
            "active_parser": cls.ACTIVE_PARSER,
            "timeout": cls.TIMEOUT,
            "max_retries": cls.MAX_RETRIES,
            "retry_delay": cls.RETRY_DELAY,
            "user_agent": cls.USER_AGENT,
            "request_delay": cls.REQUEST_DELAY,
        }

    @classmethod
    def update_runtime(cls, **kwargs: str) -> None:
        """
        Update settings at runtime (e.g., from the Settings panel).

        Accepts keyword arguments matching setting names.
        Also persists changes to the .env file.
        """
        env_path = PROJECT_ROOT / ".env"
        env_lines: list[str] = []
        if env_path.exists():
            env_lines = env_path.read_text(encoding="utf-8").splitlines()

        mapping = {
            "base_url": ("BASE_URL", str),
            "active_parser": ("ACTIVE_PARSER", str),
            "timeout": ("TIMEOUT", int),
            "max_retries": ("MAX_RETRIES", int),
            "retry_delay": ("RETRY_DELAY", int),
            "user_agent": ("USER_AGENT", str),
            "request_delay": ("REQUEST_DELAY", float),
            "output_folder": ("OUTPUT_FOLDER", str),
            "log_level": ("LOG_LEVEL", str),
            "debug": ("DEBUG", str),
            "db_url": ("DB_URL", str),
        }

        for key, value in kwargs.items():
            lower_key = key.lower()
            if lower_key not in mapping:
                continue

            env_key, cast_type = mapping[lower_key]
            os.environ[env_key] = str(value)

            # Update class attribute
            if hasattr(cls, env_key):
                if cast_type == int:
                    setattr(cls, env_key, int(value))
                elif cast_type == float:
                    setattr(cls, env_key, float(value))
                elif env_key in ("OUTPUT_FOLDER", "LOG_FOLDER"):
                    setattr(cls, env_key, PROJECT_ROOT / str(value))
                elif env_key == "DEBUG":
                    setattr(cls, env_key, str(value).lower() in ("true", "1", "yes"))
                else:
                    setattr(cls, env_key, str(value))

            # Update .env file
            found = False
            for i, line in enumerate(env_lines):
                if line.strip().startswith(f"{env_key}=") or line.strip().startswith(f"{env_key} ="):
                    env_lines[i] = f"{env_key}={value}"
                    found = True
                    break
            if not found:
                env_lines.append(f"{env_key}={value}")

        try:
            env_path.write_text("\n".join(env_lines) + "\n", encoding="utf-8")
        except OSError:
            pass

    @classmethod
    def to_dict(cls) -> dict:
        """Serialize current settings to a dictionary for API responses."""
        return {
            "base_url": cls.BASE_URL,
            "active_parser": cls.ACTIVE_PARSER,
            "timeout": cls.TIMEOUT,
            "max_retries": cls.MAX_RETRIES,
            "retry_delay": cls.RETRY_DELAY,
            "user_agent": cls.USER_AGENT,
            "request_delay": cls.REQUEST_DELAY,
            "output_folder": str(cls.OUTPUT_FOLDER),
            "log_folder": str(cls.LOG_FOLDER),
            "log_level": cls.LOG_LEVEL,
            "api_host": cls.API_HOST,
            "api_port": cls.API_PORT,
            "debug": cls.DEBUG,
            "db_url": cls.DB_URL or "",
        }


# Ensure directories exist on import
Settings.ensure_directories()
