"""
Books Parser — books.toscrape.com
=================================
Extracts book data from the Books to Scrape catalogue.

Fields extracted
----------------
  • Title
  • Price
  • Rating
  • Availability
  • Category
  • Product URL
  • Image URL
"""

from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from utils.helpers import clean_whitespace, build_absolute_url
from utils.logger import get_logger

logger = get_logger(__name__)

# Mapping from word ratings to numbers
RATING_MAP = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
}


class Parser:
    """Parser for https://books.toscrape.com."""

    name: str = "Books to Scrape"
    base_url: str = "https://books.toscrape.com"

    # ------------------------------------------------------------------
    # Interface methods
    # ------------------------------------------------------------------
    def get_columns(self) -> List[str]:
        """Return the column names this parser produces."""
        return [
            "title",
            "price",
            "rating",
            "availability",
            "category",
            "product_url",
            "image_url",
        ]

    def get_dedup_keys(self) -> List[str]:
        """Keys used to identify duplicate records."""
        return ["title", "product_url"]

    def get_next_page(self, soup: BeautifulSoup, current_url: str) -> Optional[str]:
        """
        Determine the URL of the next page.

        Parameters
        ----------
        soup : BeautifulSoup
            Parsed HTML of the current page.
        current_url : str
            URL of the current page.

        Returns
        -------
        str or None
            Absolute URL of the next page, or ``None`` if this is the last page.
        """
        next_btn = soup.select_one("li.next > a")
        if next_btn and next_btn.get("href"):
            return build_absolute_url(current_url, next_btn["href"])
        return None

    def parse_listing(self, soup: BeautifulSoup, current_url: str) -> List[Dict[str, Any]]:
        """
        Parse a single listing page and return a list of book records.

        Parameters
        ----------
        soup : BeautifulSoup
            Parsed HTML of a catalogue page.
        current_url : str
            URL of the current page.

        Returns
        -------
        list of dict
            One dict per book with keys matching :meth:`get_columns`.
        """
        records: List[Dict[str, Any]] = []
        articles: List[Tag] = soup.select("article.product_pod")

        if not articles:
            logger.warning("No book articles found on page")
            return records

        # Detect category from breadcrumb (if on a category page)
        category = self._extract_category(soup)

        for article in articles:
            try:
                record = self._parse_article(article, category, current_url)
                if record:
                    records.append(record)
            except Exception as exc:
                logger.warning("Failed to parse a book article: %s", exc)

        logger.info("Parsed %d books from page", len(records))
        return records

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _parse_article(
        self,
        article: Tag,
        default_category: str,
        current_url: str,
    ) -> Optional[Dict[str, Any]]:
        """Parse a single ``<article class="product_pod">`` element."""
        # Title & URL
        title_tag = article.select_one("h3 > a")
        if not title_tag:
            return None

        title = clean_whitespace(title_tag.get("title", title_tag.get_text()))
        relative_url = title_tag.get("href", "")
        product_url = build_absolute_url(current_url, relative_url)
        
        # Validation for accidental duplicates from malformed relatives
        if "catalogue/catalogue" in product_url:
            product_url = product_url.replace("catalogue/catalogue", "catalogue")

        # Price
        price_tag = article.select_one("p.price_color")
        price_text = clean_whitespace(price_tag.get_text()) if price_tag else "0.00"
        # Remove currency symbol, keep number
        price = price_text.replace("Â", "").replace("£", "").replace("$", "").strip()

        # Rating
        rating_tag = article.select_one("p.star-rating")
        rating = 0
        if rating_tag:
            classes = rating_tag.get("class", [])
            for cls in classes:
                if cls.lower() in RATING_MAP:
                    rating = RATING_MAP[cls.lower()]
                    break

        # Availability
        avail_tag = article.select_one("p.instock.availability")
        availability = clean_whitespace(avail_tag.get_text()) if avail_tag else "Unknown"

        # Image
        img_tag = article.select_one("div.image_container img")
        image_url = ""
        if img_tag and img_tag.get("src"):
            image_url = build_absolute_url(current_url, img_tag["src"])
            if "catalogue/catalogue" in image_url:
                image_url = image_url.replace("catalogue/catalogue", "catalogue")

        return {
            "title": title,
            "price": price,
            "rating": rating,
            "availability": availability,
            "category": default_category,
            "product_url": product_url,
            "image_url": image_url,
        }

    @staticmethod
    def _extract_category(soup: BeautifulSoup) -> str:
        """Extract the category name from the breadcrumb trail."""
        breadcrumbs = soup.select("ul.breadcrumb li")
        if len(breadcrumbs) >= 3:
            # Pattern: Home > Books > Category
            cat_tag = breadcrumbs[-1]
            active = cat_tag.select_one("a")
            if active:
                return clean_whitespace(active.get_text())
            return clean_whitespace(cat_tag.get_text())
        return "General"
