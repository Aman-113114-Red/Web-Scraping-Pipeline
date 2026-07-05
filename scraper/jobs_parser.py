"""
Jobs Parser — Template / Stub
==============================
Demonstrates the parser interface for a hypothetical jobs website.

This parser is **not connected to a live website**. It serves as:
  1. A structural template showing how to add a new parser.
  2. A demonstration that the pipeline handles multiple parser types.

To make this parser functional, update ``base_url`` and implement the
:meth:`parse_listing` and :meth:`get_next_page` methods against a real
jobs website.

Fields
------
  • Job Title
  • Company
  • Location
  • Salary
  • Job URL
  • Posted Date
"""

from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from utils.helpers import clean_whitespace, build_absolute_url
from utils.logger import get_logger

logger = get_logger(__name__)


class Parser:
    """
    Stub parser for a jobs listing website.

    Replace ``base_url`` and implement ``parse_listing`` / ``get_next_page``
    to connect to a real jobs site.
    """

    name: str = "Jobs Board"
    base_url: str = "https://example.com/jobs"

    # ------------------------------------------------------------------
    # Interface methods
    # ------------------------------------------------------------------
    def get_columns(self) -> List[str]:
        """Return the column names this parser produces."""
        return [
            "job_title",
            "company",
            "location",
            "salary",
            "job_url",
            "posted_date",
        ]

    def get_dedup_keys(self) -> List[str]:
        """Keys used to identify duplicate records."""
        return ["job_title", "company"]

    def get_next_page(self, soup: BeautifulSoup, current_url: str) -> Optional[str]:
        """
        Determine the URL of the next page.

        Override this method with real pagination logic when connecting
        to a live jobs website.

        Returns
        -------
        None
            Always returns ``None`` in the stub (single page).
        """
        # Example implementation (uncomment and adapt for a real site):
        # next_btn = soup.select_one("a.next-page")
        # if next_btn and next_btn.get("href"):
        #     return build_absolute_url(current_url, next_btn["href"])
        return None

    def parse_listing(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Parse a single page and return a list of job records.

        This stub implementation looks for a common job listing pattern.
        Adapt the CSS selectors for your target website.

        Parameters
        ----------
        soup : BeautifulSoup
            Parsed HTML of a jobs listing page.

        Returns
        -------
        list of dict
            One dict per job with keys matching :meth:`get_columns`.
        """
        records: List[Dict[str, Any]] = []

        # Common pattern: each job is in a card/row element
        # Adapt these selectors for the actual target site
        job_cards = soup.select("div.job-card, div.job-listing, tr.job-row")

        if not job_cards:
            logger.warning(
                "No job listings found on page. "
                "This is a stub parser — connect it to a real jobs site."
            )
            return records

        for card in job_cards:
            try:
                record = self._parse_job_card(card)
                if record:
                    records.append(record)
            except Exception as exc:
                logger.warning("Failed to parse a job card: %s", exc)

        logger.info("Parsed %d jobs from page", len(records))
        return records

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _parse_job_card(self, card) -> Optional[Dict[str, Any]]:
        """
        Parse a single job listing element.

        Adapt the CSS selectors below for the target website.
        """
        title_tag = card.select_one("h2.job-title, a.job-title, .title")
        company_tag = card.select_one("span.company, .company-name")
        location_tag = card.select_one("span.location, .job-location")
        salary_tag = card.select_one("span.salary, .job-salary")
        link_tag = card.select_one("a[href]")
        date_tag = card.select_one("span.date, time, .posted-date")

        title = clean_whitespace(title_tag.get_text()) if title_tag else "N/A"
        company = clean_whitespace(company_tag.get_text()) if company_tag else "N/A"
        location = clean_whitespace(location_tag.get_text()) if location_tag else "N/A"
        salary = clean_whitespace(salary_tag.get_text()) if salary_tag else "N/A"
        job_url = ""
        if link_tag and link_tag.get("href"):
            job_url = build_absolute_url(self.base_url, link_tag["href"])
        posted_date = clean_whitespace(date_tag.get_text()) if date_tag else "N/A"

        return {
            "job_title": title,
            "company": company,
            "location": location,
            "salary": salary,
            "job_url": job_url,
            "posted_date": posted_date,
        }
