"""
HTTP Fetcher
============
Handles all HTTP communication:
  • Persistent ``requests.Session`` with configurable headers
  • Configurable timeout and User-Agent
  • Retry logic via the ``@retry`` decorator
  • Rate-limiting between requests
  • Pagination — fetches all pages in sequence
"""

import time
from typing import List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

from config.settings import Settings
from utils.logger import get_logger
from utils.retry import retry

logger = get_logger(__name__)


class Fetcher:
    """
    Responsible for making HTTP requests to target websites.

    Maintains a persistent session and applies retry / timeout policies
    defined in :class:`config.settings.Settings`.
    """

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": Settings.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        })
        self.timeout: int = Settings.TIMEOUT
        self.request_delay: float = Settings.REQUEST_DELAY

        # Metrics
        self.total_requests: int = 0
        self.successful_requests: int = 0
        self.failed_requests: int = 0

    # ------------------------------------------------------------------
    # Core fetch
    # ------------------------------------------------------------------
    @retry(exceptions=(requests.RequestException,))
    def fetch(self, url: str) -> Optional[BeautifulSoup]:
        """
        Fetch a single URL and return a parsed ``BeautifulSoup`` tree.

        Parameters
        ----------
        url : str
            Fully-qualified URL to fetch.

        Returns
        -------
        BeautifulSoup or None
            Parsed HTML, or ``None`` if the request fails after all retries.
        """
        self.total_requests += 1
        logger.info("Fetching: %s", url)

        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()

        self.successful_requests += 1
        logger.info("Fetched successfully: %s [%d]", url, response.status_code)
        return BeautifulSoup(response.text, "lxml")

    def fetch_safe(self, url: str) -> Optional[BeautifulSoup]:
        """
        Wrapper around :meth:`fetch` that catches all exceptions gracefully
        so the pipeline never crashes.
        """
        try:
            return self.fetch(url)
        except Exception as exc:
            self.failed_requests += 1
            logger.error("Failed to fetch %s after retries: %s", url, str(exc))
            return None

    # ------------------------------------------------------------------
    # Pagination helper
    # ------------------------------------------------------------------
    def fetch_all_pages(
        self,
        start_url: str,
        next_page_callback,
    ) -> List[Tuple[str, BeautifulSoup]]:
        """
        Fetch every page starting from *start_url*.

        Parameters
        ----------
        start_url : str
            URL of the first page.
        next_page_callback : callable
            A function ``(soup, current_url) -> Optional[str]`` that returns
            the URL of the next page, or ``None`` when there are no more pages.

        Returns
        -------
        list of tuple
            List of (url, BeautifulSoup) tuples for all successfully fetched pages.
        """
        pages: List[Tuple[str, BeautifulSoup]] = []
        current_url: Optional[str] = start_url

        while current_url:
            soup = self.fetch_safe(current_url)
            if soup is None:
                logger.warning("Stopping pagination — failed to fetch %s", current_url)
                break

            pages.append((current_url, soup))
            logger.info("Page %d fetched", len(pages))

            next_url = next_page_callback(soup, current_url)
            if next_url and next_url != current_url:
                current_url = next_url
                time.sleep(self.request_delay)  # rate-limiting
            else:
                current_url = None

        logger.info(
            "Pagination complete — %d pages fetched (%d OK, %d failed)",
            len(pages),
            self.successful_requests,
            self.failed_requests,
        )
        return pages

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------
    def get_metrics(self) -> dict:
        """Return request-level metrics for the dashboard."""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
        }

    def reset_metrics(self) -> None:
        """Reset all counters."""
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0

    def close(self) -> None:
        """Close the underlying session."""
        self.session.close()
