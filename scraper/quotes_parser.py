"""
Quotes Parser — quotes.toscrape.com
====================================
Extracts quote data from the Quotes to Scrape website.

Fields extracted
----------------
  • Quote (text)
  • Author
  • Tags
  • Author URL
"""

from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from utils.helpers import clean_whitespace, build_absolute_url
from utils.logger import get_logger

logger = get_logger(__name__)


class Parser:
    """Parser for https://quotes.toscrape.com."""

    name: str = "Quotes to Scrape"
    base_url: str = "https://quotes.toscrape.com"

    # ------------------------------------------------------------------
    # Interface methods
    # ------------------------------------------------------------------
    def get_columns(self) -> List[str]:
        """Return the column names this parser produces."""
        return ["quote", "author", "tags", "author_url"]

    def get_dedup_keys(self) -> List[str]:
        """Keys used to identify duplicate records."""
        return ["quote", "author"]

    def get_next_page(self, soup: BeautifulSoup, current_url: str) -> Optional[str]:
        """
        Determine the URL of the next page.

        Returns
        -------
        str or None
            Absolute URL of the next page, or ``None`` if last page.
        """
        next_btn = soup.select_one("li.next > a")
        if next_btn and next_btn.get("href"):
            return build_absolute_url(self.base_url, next_btn["href"])
        return None

    def parse_listing(self, soup: BeautifulSoup, current_url: str) -> List[Dict[str, Any]]:
        """
        Parse a single page and return a list of quote records.

        Parameters
        ----------
        soup : BeautifulSoup
            Parsed HTML of a quotes page.
        current_url : str
            URL of the current page.

        Returns
        -------
        list of dict
            One dict per quote with keys matching :meth:`get_columns`.
        """
        records: List[Dict[str, Any]] = []
        quotes = soup.select("div.quote")

        if not quotes:
            logger.warning("No quotes found on page")
            return records

        for quote_div in quotes:
            try:
                record = self._parse_quote(quote_div, current_url)
                if record:
                    records.append(record)
            except Exception as exc:
                logger.warning("Failed to parse a quote: %s", exc)

        logger.info("Parsed %d quotes from page", len(records))
        return records

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _parse_quote(self, div: Tag, current_url: str) -> Optional[Dict[str, Any]]:
        """Parse a single ``<div class="quote">`` element."""
        # Quote text
        text_tag = div.select_one("span.text")
        if not text_tag:
            return None
        quote_text = clean_whitespace(text_tag.get_text())
        # Remove surrounding quotation marks
        quote_text = quote_text.strip("\u201c\u201d\"")

        # Author
        author_tag = div.select_one("small.author")
        author = clean_whitespace(author_tag.get_text()) if author_tag else "Unknown"

        # Author URL
        author_link = div.select_one("a[href*='author']")
        author_url = ""
        if author_link and author_link.get("href"):
            author_url = build_absolute_url(current_url, author_link["href"])

        # Tags
        tag_elements = div.select("div.tags a.tag")
        tags = ", ".join(
            clean_whitespace(tag.get_text()) for tag in tag_elements
        )

        return {
            "quote": quote_text,
            "author": author,
            "tags": tags,
            "author_url": author_url,
        }
