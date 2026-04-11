"""
MOSDAC Web Scraper

Scraper for extracting weather data from mosdac.gov.in
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import json
import time
import logging

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from src.scraper.config import settings


logger = logging.getLogger(__name__)


class MOSDACScraper:
    """Web scraper for mosdac.gov.in weather data."""

    def __init__(self):
        """Initialize the scraper with configuration."""
        self.base_url = settings.BASE_URL
        self.output_dir = settings.OUTPUT_DIR
        self.timeout = settings.REQUEST_TIMEOUT
        self.max_retries = settings.MAX_RETRIES
        self.retry_delay = settings.RETRY_DELAY
        self.min_delay = settings.MIN_DELAY_SECONDS

        # Ensure output directory exists
        self.output_dir = Path(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Session for requests
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )

        # Last request time for rate limiting
        self._last_request_time = 0.0

        # Selenium driver (initialized on demand)
        self._driver: Optional[webdriver.Chrome] = None

    def _rate_limit(self):
        """Apply rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        self._last_request_time = time.time()

    def _get(self, url: str, use_selenium: bool = False) -> Optional[str]:
        """
        Fetch a URL with retries and rate limiting.

        Args:
            url: URL to fetch
            use_selenium: Use Selenium for JavaScript-rendered content

        Returns:
            HTML content or None on failure
        """
        self._rate_limit()

        for attempt in range(self.max_retries):
            try:
                if use_selenium:
                    html = self._selenium_get(url)
                else:
                    response = self.session.get(url, timeout=self.timeout)
                    response.raise_for_status()
                    return response.text
                return html
            except requests.RequestException as e:
                logger.warning(
                    f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
        return None

    def _selenium_get(self, url: str) -> Optional[str]:
        """
        Fetch a URL using Selenium for JavaScript-rendered content.

        Args:
            url: URL to fetch

        Returns:
            HTML content or None on failure
        """
        if self._driver is None:
            options = webdriver.ChromeOptions()
            if settings.HEADLESS:
                options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            self._driver = webdriver.Chrome(options=options)

        try:
            self._driver.get(url)
            wait = WebDriverWait(self._driver, settings.SELENIUM_WAIT_TIMEOUT)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            return self._driver.page_source
        except WebDriverException as e:
            logger.error(f"Selenium error: {e}")
            return None

    def close(self):
        """Close Selenium driver if open."""
        if self._driver:
            self._driver.quit()
            self._driver = None

    def scrape_satellites(self) -> List[Dict[str, Any]]:
        """
        Scrape satellite information from MOSDAC website.

        Returns:
            List of satellite dictionaries with name, launch_date, agency, description
        """
        satellites = []

        # Try common MOSDAC satellite page paths - first with Selenium for dynamic content
        urls_to_try = [
            f"{self.base_url}/satellite",
            f"{self.base_url}/satellites",
            f"{self.base_url}/data/satellite",
            f"{self.base_url}/satellitedata",
        ]

        for url in urls_to_try:
            # Try with Selenium first for dynamic content
            html = self._get(url, use_selenium=True)
            if html:
                soup = BeautifulSoup(html, "html.parser")

                # Look for satellite information
                for link in soup.find_all("a", href=True):
                    href = link.get("href", "")
                    if href and (
                        "satellite" in href.lower() or "insat" in href.lower()
                    ):
                        text = link.get_text(strip=True)
                        if text:
                            satellites.append(
                                {
                                    "name": text,
                                    "url": self.base_url + href
                                    if href.startswith("/")
                                    else href,
                                    "source": "MOSDAC",
                                    "scraped_at": datetime.utcnow().isoformat(),
                                }
                            )

                if satellites:
                    break

        # Return empty list if no data found - no hardcoded fallbacks
        return satellites

    def scrape_sensors(self) -> List[Dict[str, Any]]:
        """
        Scrape sensor information from MOSDAC website.

        Returns:
            List of sensor dictionaries
        """
        sensors = []

        # Scrape sensors from the website - use Selenium for dynamic content
        urls_to_try = [
            f"{self.base_url}/sensors",
            f"{self.base_url}/instrument",
            f"{self.base_url}/data/sensors",
        ]

        for url in urls_to_try:
            html = self._get(url, use_selenium=True)
            if html:
                soup = BeautifulSoup(html, "html.parser")

                for link in soup.find_all("a", href=True):
                    href = link.get("href", "")
                    if href and ("sensor" in href.lower() or "ims" in href.lower()):
                        text = link.get_text(strip=True)
                        if text:
                            sensors.append(
                                {
                                    "name": text,
                                    "type": "Weather Sensor",
                                    "url": self.base_url + href
                                    if href.startswith("/")
                                    else href,
                                    "scraped_at": datetime.utcnow().isoformat(),
                                }
                            )

                if sensors:
                    break

        # Return empty list if no data found - no hardcoded fallbacks
        return sensors

    def scrape_products(self) -> List[Dict[str, Any]]:
        """
        Scrape data product information from MOSDAC website.

        Returns:
            List of product dictionaries
        """
        products = []

        # Common product page paths - use Selenium for dynamic content
        urls_to_try = [
            f"{self.base_url}/products",
            f"{self.base_url}/dataproducts",
            f"{self.base_url}/data/products",
            f"{self.base_url}/product",
        ]

        for url in urls_to_try:
            html = self._get(url, use_selenium=True)
            if html:
                soup = BeautifulSoup(html, "html.parser")

                # Look for product information
                for link in soup.find_all("a", href=True):
                    href = link.get("href", "")
                    if href and any(
                        keyword in href.lower()
                        for keyword in ["product", "data", "imagery"]
                    ):
                        text = link.get_text(strip=True)
                        if text and len(text) > 2:
                            products.append(
                                {
                                    "name": text,
                                    "category": "Weather Data",
                                    "url": self.base_url + href
                                    if href.startswith("/")
                                    else href,
                                    "scraped_at": datetime.utcnow().isoformat(),
                                }
                            )

                if products:
                    break

        # Return empty list if no data found - no hardcoded fallbacks
        return products

    def scrape_faqs(self) -> List[Dict[str, Any]]:
        """
        Scrape FAQ information from MOSDAC website.

        Returns:
            List of FAQ dictionaries with question and answer
        """
        faqs = []

        urls_to_try = [
            f"{self.base_url}/faq",
            f"{self.base_url}/faqs",
            f"{self.base_url}/faq",
            f"{self.base_url}/help",
        ]

        for url in urls_to_try:
            # Use Selenium for dynamic FAQ content (expandable sections)
            html = self._get(url, use_selenium=True)
            if html:
                soup = BeautifulSoup(html, "html.parser")

                # Try common FAQ patterns
                for details in soup.find_all("details"):
                    summary = details.find("summary")
                    if summary:
                        question = summary.get_text(strip=True)
                        # Find the answer in paragraphs after summary
                        answer_parts = []
                        for sibling in details.find_next_siblings():
                            if sibling.name and sibling.get_text(strip=True):
                                answer_parts.append(sibling.get_text(strip=True))
                        if question:
                            faqs.append(
                                {
                                    "question": question,
                                    "answer": " ".join(answer_parts)
                                    if answer_parts
                                    else "",
                                    "scraped_at": datetime.utcnow().isoformat(),
                                }
                            )

                # Try definition list pattern
                if not faqs:
                    for dt in soup.find_all("dt"):
                        dd = dt.find_next_sibling("dd")
                        if dt.get_text(strip=True):
                            faqs.append(
                                {
                                    "question": dt.get_text(strip=True),
                                    "answer": dd.get_text(strip=True) if dd else "",
                                    "scraped_at": datetime.utcnow().isoformat(),
                                }
                            )

                if faqs:
                    break

        # Return empty list if no data found - no hardcoded fallbacks
        return faqs

    def scrape_documents(self) -> List[Dict[str, Any]]:
        """
        Scrape document metadata from MOSDAC website.

        Returns:
            List of document dictionaries
        """
        documents = []

        urls_to_try = [
            f"{self.base_url}/documents",
            f"{self.base_url}/docs",
            f"{self.base_url}/publications",
            f"{self.base_url}/manuals",
        ]

        for url in urls_to_try:
            # Use Selenium for dynamic document listings
            html = self._get(url, use_selenium=True)
            if html:
                soup = BeautifulSoup(html, "html.parser")

                for link in soup.find_all("a", href=True):
                    href = link.get("href", "")
                    if href and any(
                        ext in href.lower() for ext in [".pdf", ".doc", ".docx"]
                    ):
                        text = link.get_text(strip=True)
                        if text:
                            documents.append(
                                {
                                    "title": text,
                                    "url": self.base_url + href
                                    if href.startswith("/")
                                    else href,
                                    "type": "PDF" if ".pdf" in href else "Document",
                                    "scraped_at": datetime.utcnow().isoformat(),
                                }
                            )

                if documents:
                    break

        # Return empty list if no data found - no hardcoded fallbacks
        return documents

    def _save_json(self, data: Any, filename: str) -> Path:
        """
        Save data as JSON file.

        Args:
            data: Data to save (expected: List[Dict])
            filename: Output filename

        Returns:
            Path to saved file
        """
        output_path = self.output_dir / filename

        # Ensure we're outputting single-nested array [{...}] not [[{...}]]
        # If data is a list containing lists, flatten it
        if isinstance(data, list) and data and isinstance(data[0], list):
            # Flatten the nested structure
            flat_data = []
            for item in data:
                if isinstance(item, list):
                    flat_data.extend(item)
                else:
                    flat_data.append(item)
            data = flat_data

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(
            f"Saved {len(data) if isinstance(data, list) else 1} items to {output_path}"
        )
        return output_path

    def scrape_all(self) -> Dict[str, Path]:
        """
        Run all scrapers and save results to JSON.

        Returns:
            Dictionary mapping data type to output file paths
        """
        outputs = {}

        # Scrape all data types
        satellites = self.scrape_satellites()
        sensors = self.scrape_sensors()
        products = self.scrape_products()
        faqs = self.scrape_faqs()
        documents = self.scrape_documents()

        # Save all to JSON
        outputs["satellites"] = self._save_json(satellites, "satellites.json")
        outputs["sensors"] = self._save_json(sensors, "sensors.json")
        outputs["products"] = self._save_json(products, "products.json")
        outputs["faqs"] = self._save_json(faqs, "faqs.json")
        outputs["documents"] = self._save_json(documents, "documents.json")

        return outputs

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
