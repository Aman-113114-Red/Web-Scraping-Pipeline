"""
Helper Utilities
================
General-purpose utility functions used across the pipeline.
"""

import re
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin


def timestamp_now() -> str:
    """Return the current UTC timestamp as an ISO-8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def timestamp_filename() -> str:
    """Return a filename-safe timestamp string."""
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def safe_filename(name: str, extension: str = "") -> str:
    """
    Convert an arbitrary string into a safe filename.

    Parameters
    ----------
    name : str
        Raw name to sanitise.
    extension : str
        File extension to append (including the dot, e.g. ``".csv"``).

    Returns
    -------
    str
        Sanitised filename.
    """
    safe = re.sub(r"[^\w\-.]", "_", name.strip().lower())
    safe = re.sub(r"_+", "_", safe).strip("_")
    return f"{safe}{extension}" if extension else safe


def build_absolute_url(base: str, relative: str) -> str:
    """
    Build an absolute URL from a base URL and a relative path.

    Parameters
    ----------
    base : str
        The base URL (e.g. ``"https://books.toscrape.com/catalogue/"``).
    relative : str
        The relative path (e.g. ``"../media/book.jpg"``).

    Returns
    -------
    str
        Fully-qualified URL.
    """
    return urljoin(base, relative)


def record_hash(record: Dict[str, Any], keys: Optional[List[str]] = None) -> str:
    """
    Generate a deterministic hash for a record based on selected keys.

    Parameters
    ----------
    record : dict
        Data record.
    keys : list of str, optional
        Keys to include in the hash. If ``None``, all keys are used.

    Returns
    -------
    str
        SHA-256 hex digest.
    """
    selected = {k: record.get(k, "") for k in (keys or record.keys())}
    raw = "|".join(str(v) for v in selected.values())
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def parse_number(text: str) -> Optional[float]:
    """
    Extract the first numeric value from a string.

    Examples
    --------
    >>> parse_number("£51.77")
    51.77
    >>> parse_number("In stock (22 available)")
    22.0
    """
    match = re.search(r"[\d]+\.?[\d]*", text)
    return float(match.group()) if match else None


def clean_whitespace(text: str) -> str:
    """Collapse multiple whitespace characters into a single space and strip."""
    return re.sub(r"\s+", " ", text).strip()


def validate_record(record: Dict[str, Any], required_keys: List[str]) -> bool:
    """
    Check that a record contains all required keys with non-empty values.

    Parameters
    ----------
    record : dict
        Data record to validate.
    required_keys : list of str
        Keys that must be present and non-empty.

    Returns
    -------
    bool
        ``True`` if valid; ``False`` otherwise.
    """
    for key in required_keys:
        val = record.get(key)
        if val is None or (isinstance(val, str) and not val.strip()):
            return False
    return True


def truncate(text: str, max_length: int = 100) -> str:
    """Truncate a string to *max_length* characters, appending '…' if cut."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 1] + "…"
