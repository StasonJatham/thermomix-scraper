"""Configuration and settings."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import ClassVar


class RunMode(str, Enum):
    """Scraper run modes."""
    
    SKIP_EXISTING = "skip"      # Skip already downloaded recipes (default)
    UPDATE = "update"           # Re-download and update existing recipes
    REDOWNLOAD_ALL = "redownload"  # Force re-download everything
    CONTINUE = "continue"       # Continue from last saved state


@dataclass
class Config:
    """Application configuration."""
    
    # Paths
    output_dir: Path = field(default_factory=lambda: Path("/data"))
    state_file: Path | None = None
    chromedriver_path: Path = field(default_factory=lambda: Path("/usr/bin/chromedriver"))
    
    # Cookidoo settings
    locale: str = "de"
    username: str | None = None
    password: str | None = None
    
    # Run settings
    mode: RunMode = RunMode.SKIP_EXISTING
    headless: bool = True
    recipe_ids: list[str] = field(default_factory=list)
    
    # Timeouts
    page_load_timeout: float = 3.0
    scroll_timeout: float = 1.0
    request_timeout: float = 30.0
    
    # Rate limiting
    download_delay: float = 0.2
    algolia_delay: float = 0.1
    retry_delay: float = 2.0
    max_retries: int = 2
    
    # State persistence
    save_interval: int = 10  # Save state every N downloads
    
    # Logging
    log_level: str = "INFO"
    debug: bool = False
    
    # Class-level defaults
    ENV_PREFIX: ClassVar[str] = "THERMOMIX_"
    LEGACY_PREFIX: ClassVar[str] = "COOKIDOO_"
    
    def __post_init__(self) -> None:
        """Ensure paths are Path objects and set derived values."""
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)
        if isinstance(self.chromedriver_path, str):
            self.chromedriver_path = Path(self.chromedriver_path)
        
        # Default state file location
        if self.state_file is None:
            self.state_file = self.output_dir / ".scraper_state.json"
        elif isinstance(self.state_file, str):
            self.state_file = Path(self.state_file)
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def base_url(self) -> str:
        """Cookidoo base URL for configured locale."""
        return f"https://cookidoo.{self.locale}/"
    
    @property
    def url_locale(self) -> str:
        """URL locale format (e.g., 'de-DE')."""
        lang = self.locale.split("-")[0]
        return f"{lang}-{lang.upper()}" if len(lang) == 2 else self.locale
    
    @classmethod
    def from_env(cls) -> Config:
        """Load configuration from environment variables."""
        def get_env(*names: str, default: str | None = None) -> str | None:
            for name in names:
                val = os.getenv(name)
                if val and val.strip():
                    return val.strip()
            return default
        
        def get_bool(*names: str, default: bool = False) -> bool:
            val = get_env(*names)
            if val is None:
                return default
            return val.lower() in ("1", "true", "yes", "on")
        
        # Parse mode from env
        mode_str = get_env("THERMOMIX_MODE", "RUN_MODE", default="skip")
        try:
            mode = RunMode(mode_str.lower()) if mode_str else RunMode.SKIP_EXISTING
        except ValueError:
            mode = RunMode.SKIP_EXISTING
        
        # Parse recipe IDs (comma-separated)
        recipe_ids_str = get_env("THERMOMIX_RECIPE_IDS", "RECIPE_IDS", default="")
        recipe_ids = [r.strip() for r in recipe_ids_str.split(",") if r.strip()] if recipe_ids_str else []
        
        return cls(
            output_dir=Path(get_env("THERMOMIX_OUTPUT", "OUTPUT_DIR", default="/data")),
            chromedriver_path=Path(get_env("CHROMEDRIVER_PATH", default="/usr/bin/chromedriver")),
            locale=get_env("THERMOMIX_LOCALE", "COOKIDOO_LOCALE", "LOCALE", default="de"),
            username=get_env("THERMOMIX_USERNAME", "COOKIDOO_EMAIL", "COOKIDOO_USERNAME", "USERNAME"),
            password=get_env("THERMOMIX_PASSWORD", "COOKIDOO_PASSWORD", "PASSWORD"),
            mode=mode,
            headless=get_bool("THERMOMIX_HEADLESS", "HEADLESS", default=True),
            recipe_ids=recipe_ids,
            debug=get_bool("THERMOMIX_DEBUG", "DEBUG", default=False),
            log_level=get_env("THERMOMIX_LOG_LEVEL", "LOG_LEVEL", default="INFO"),
        )


def setup_logging(config: Config) -> logging.Logger:
    """Configure application logging."""
    level = logging.DEBUG if config.debug else getattr(logging, config.log_level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    logger = logging.getLogger("thermomix")
    logger.setLevel(level)
    
    return logger
