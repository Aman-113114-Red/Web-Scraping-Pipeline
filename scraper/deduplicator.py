"""
Deduplicator
=============
Removes duplicate records from a dataset using configurable key fields.
"""

from typing import Any, Dict, List, Optional, Set

from utils.helpers import record_hash
from utils.logger import get_logger

logger = get_logger(__name__)


class Deduplicator:
    """
    Removes duplicate records based on a hash of selected key fields.

    If no dedup keys are specified, the full record is hashed.
    """

    def __init__(self) -> None:
        self.duplicates_removed: int = 0

    def deduplicate(
        self,
        records: List[Dict[str, Any]],
        keys: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Remove duplicate records from *records*.

        Parameters
        ----------
        records : list of dict
            Dataset to deduplicate.
        keys : list of str, optional
            Fields to use for duplicate detection.
            If ``None``, all fields are used.

        Returns
        -------
        list of dict
            Deduplicated dataset (order preserved).
        """
        if not records:
            logger.warning("Deduplicator received an empty dataset")
            return []

        seen: Set[str] = set()
        unique: List[Dict[str, Any]] = []

        for record in records:
            h = record_hash(record, keys)
            if h not in seen:
                seen.add(h)
                unique.append(record)

        self.duplicates_removed = len(records) - len(unique)

        if self.duplicates_removed > 0:
            logger.info(
                "Removed %d duplicate(s) — %d unique records remain",
                self.duplicates_removed,
                len(unique),
            )
        else:
            logger.info("No duplicates found in %d records", len(records))

        return unique

    def get_stats(self) -> Dict[str, int]:
        """Return deduplication statistics."""
        return {"duplicates_removed": self.duplicates_removed}
