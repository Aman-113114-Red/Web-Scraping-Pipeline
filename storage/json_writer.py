"""
JSON Writer
===========
Generic JSON exporter that works with any ``list[dict]`` dataset.

Features
--------
  • Pretty-printed output
  • Metadata envelope (timestamp, count, source)
  • Handles Unicode safely
  • Returns the path to the generated file
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import Settings
from utils.helpers import timestamp_filename, timestamp_now, safe_filename
from utils.logger import get_logger

logger = get_logger(__name__)


def export_json(
    records: List[Dict[str, Any]],
    filename: Optional[str] = None,
    source: Optional[str] = None,
    output_dir: Optional[Path] = None,
) -> Path:
    """
    Export a dataset to a JSON file with metadata.

    Parameters
    ----------
    records : list of dict
        Data to export.
    filename : str, optional
        Output filename (without extension). Defaults to a timestamped name.
    source : str, optional
        Name of the data source (e.g. ``"books"``).
    output_dir : Path, optional
        Directory to write the file. Defaults to ``Settings.OUTPUT_FOLDER``.

    Returns
    -------
    Path
        Absolute path to the generated JSON file.

    Raises
    ------
    ValueError
        If *records* is empty.
    """
    if not records:
        raise ValueError("Cannot export an empty dataset to JSON")

    output_dir = output_dir or Settings.OUTPUT_FOLDER
    output_dir.mkdir(parents=True, exist_ok=True)

    if filename is None:
        filename = f"scraped_data_{timestamp_filename()}"
    filename = safe_filename(filename, ".json")

    filepath = output_dir / filename

    envelope: Dict[str, Any] = {
        "metadata": {
            "exported_at": timestamp_now(),
            "source": source or Settings.ACTIVE_PARSER,
            "record_count": len(records),
        },
        "data": records,
    }

    with open(filepath, "w", encoding="utf-8") as jsonfile:
        json.dump(envelope, jsonfile, indent=2, ensure_ascii=False)

    logger.info("JSON exported: %s (%d records)", filepath, len(records))
    return filepath
