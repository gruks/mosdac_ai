"""
MOSDAC Scraper Configuration

Configuration settings for the MOSDAC web scraper.
Using environment variables with os.getenv for Python 3.13 compatibility.
"""

import os
from pathlib import Path


class ScraperSettings:
    """Configuration settings for MOSDAC web scraper."""

    # MOSDAC Website
    BASE_URL: str = os.getenv("MOSDAC_BASE_URL", "https://www.mosdac.gov.in")

    # Output settings
    OUTPUT_DIR: Path = Path(os.getenv("MOSDAC_OUTPUT_DIR", "data/raw"))

    # Request settings
    REQUEST_TIMEOUT: int = int(os.getenv("MOSDAC_REQUEST_TIMEOUT", "30"))
    MAX_RETRIES: int = int(os.getenv("MOSDAC_MAX_RETRIES", "3"))
    RETRY_DELAY: float = float(os.getenv("MOSDAC_RETRY_DELAY", "1.0"))

    # Rate limiting
    REQUESTS_PER_SECOND: float = float(os.getenv("MOSDAC_RPS", "1.0"))
    MIN_DELAY_SECONDS: float = float(os.getenv("MOSDAC_MIN_DELAY", "1.0"))

    # Selenium settings (for JavaScript-rendered content)
    SELENIUM_WAIT_TIMEOUT: int = int(os.getenv("MOSDAC_SELENIUM_WAIT", "10"))
    HEADLESS: bool = os.getenv("MOSDAC_HEADLESS", "true").lower() == "true"


# Global settings instance
settings = ScraperSettings()
