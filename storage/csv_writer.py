"""
CSV Writer
==========
Generic CSV exporter that works with any ``list[dict]`` dataset.

Features
--------
  • Auto-detects column headers from the data
  • Supports custom column ordering
  • Handles Unicode safely
  • Returns the path to the generated file
"""

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import Settings
from utils.helpers import timestamp_filename, safe_filename
from utils.logger import get_logger

logger = get_logger(__name__)


def export_csv(
    records: List[Dict[str, Any]],
    filename: Optional[str] = None,
    columns: Optional[List[str]] = None,
    output_dir: Optional[Path] = None,
) -> Path:
    """
    Export a dataset to a CSV file.

    Parameters
    ----------
    records : list of dict
        Data to export.
    filename : str, optional
        Output filename (without extension). Defaults to a timestamped name.
    columns : list of str, optional
        Column order. If ``None``, columns are inferred from the first record.
    output_dir : Path, optional
        Directory to write the file. Defaults to ``Settings.OUTPUT_FOLDER``.

    Returns
    -------
    Path
        Absolute path to the generated CSV file.

    Raises
    ------
    ValueError
        If *records* is empty.
    """
    if not records:
        raise ValueError("Cannot export an empty dataset to CSV")

    output_dir = output_dir or Settings.OUTPUT_FOLDER
    output_dir.mkdir(parents=True, exist_ok=True)

    if filename is None:
        filename = f"scraped_data_{timestamp_filename()}"
    filename = safe_filename(filename, ".csv")

    filepath = output_dir / filename

    # Determine column headers
    if columns is None:
        columns = list(records[0].keys())

    with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)

    logger.info("CSV exported: %s (%d records)", filepath, len(records))
    return filepath
