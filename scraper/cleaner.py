"""
Data Cleaner
=============
Generic data-cleaning pipeline that works on any ``list[dict]``.

Responsibilities
----------------
  • Normalize prices (strip currency symbols, convert to float)
  • Normalize ratings (ensure numeric)
  • Strip excess whitespace from all string fields
  • Fill missing / ``None`` fields with sensible defaults
  • Validate records against expected columns
"""

import re
from typing import Any, Dict, List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)


class Cleaner:
    """
    Stateless data cleaner.

    Applies a sequence of transformations to every record in a dataset.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def clean(
        self,
        records: List[Dict[str, Any]],
        columns: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Clean an entire dataset.

        Parameters
        ----------
        records : list of dict
            Raw records straight from the parser.
        columns : list of str, optional
            Expected column names. Records missing any of these keys will
            have them filled with defaults.

        Returns
        -------
        list of dict
            Cleaned records.
        """
        if not records:
            logger.warning("Cleaner received an empty dataset")
            return []

        cleaned: List[Dict[str, Any]] = []
        for i, record in enumerate(records):
            try:
                record = self._fill_missing(record, columns)
                record = self._clean_strings(record)
                record = self._normalize_price(record)
                record = self._normalize_rating(record)
                cleaned.append(record)
            except Exception as exc:
                logger.warning("Skipping record %d due to cleaning error: %s", i, exc)

        logger.info(
            "Cleaned %d / %d records", len(cleaned), len(records)
        )
        return cleaned

    # ------------------------------------------------------------------
    # Cleaning steps
    # ------------------------------------------------------------------
    @staticmethod
    def _fill_missing(
        record: Dict[str, Any],
        columns: Optional[List[str]],
    ) -> Dict[str, Any]:
        """Ensure every expected column exists with a non-None value."""
        if columns:
            for col in columns:
                if col not in record or record[col] is None:
                    record[col] = "N/A"
        else:
            for key in list(record.keys()):
                if record[key] is None:
                    record[key] = "N/A"
        return record

    @staticmethod
    def _clean_strings(record: Dict[str, Any]) -> Dict[str, Any]:
        """Strip and collapse whitespace in every string field."""
        for key, value in record.items():
            if isinstance(value, str):
                record[key] = re.sub(r"\s+", " ", value).strip()
        return record

    @staticmethod
    def _normalize_price(record: Dict[str, Any]) -> Dict[str, Any]:
        """
        If the record has a ``price`` field, ensure it is a clean float string.

        Handles currency symbols like ``£``, ``$``, ``€``, and the
        ``Â`` encoding artefact from books.toscrape.com.
        """
        if "price" not in record:
            return record

        price = record["price"]
        if isinstance(price, (int, float)):
            record["price"] = f"{float(price):.2f}"
            return record

        if isinstance(price, str):
            # Remove known currency symbols and artefacts
            price = price.replace("Â", "").replace("£", "").replace("$", "").replace("€", "").strip()
            match = re.search(r"[\d]+\.?\d*", price)
            record["price"] = f"{float(match.group()):.2f}" if match else "0.00"

        return record

    @staticmethod
    def _normalize_rating(record: Dict[str, Any]) -> Dict[str, Any]:
        """
        If the record has a ``rating`` field, ensure it is an integer (1-5).
        """
        if "rating" not in record:
            return record

        rating = record["rating"]
        if isinstance(rating, int):
            return record

        # Map word ratings
        word_map = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
        if isinstance(rating, str):
            lower = rating.strip().lower()
            if lower in word_map:
                record["rating"] = word_map[lower]
            else:
                try:
                    record["rating"] = int(float(lower))
                except (ValueError, TypeError):
                    record["rating"] = 0

        return record
