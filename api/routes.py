"""
API Routes
==========
REST API endpoints for the web scraping pipeline.

Endpoints
---------
  GET  /api/data           — Return scraped data (supports ``?search=`` query)
  GET  /api/stats          — Return pipeline statistics
  GET  /api/logs           — Return recent log entries
  POST /api/scrape         — Trigger a scrape run
  GET  /api/scrape/status  — Return current scraping status
  GET  /api/config         — Read current configuration
  PUT  /api/config         — Update configuration
  GET  /api/export/csv     — Download CSV file
  GET  /api/export/json    — Download JSON file
  GET  /api/parsers        — List available parsers with columns

Response Format
---------------
All JSON endpoints return a consistent envelope:

  Success — ``{"success": true,  "data": ...}``
  Failure — ``{"success": false, "error": "...", "details": ...}``
"""

import time
import threading
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request, send_file

from config.settings import Settings
from scraper.fetcher import Fetcher
from scraper.parser_loader import load_parser, get_available_parsers
from scraper.cleaner import Cleaner
from scraper.deduplicator import Deduplicator
from storage.csv_writer import export_csv
from storage.json_writer import export_json
from storage.db_writer import DatabaseWriter
from utils.logger import get_logger, get_log_buffer
from utils.helpers import timestamp_now

logger = get_logger(__name__)

api_bp = Blueprint("api", __name__, url_prefix="/api")

# ---------------------------------------------------------------------------
# In-memory state (shared across requests within one process)
# ---------------------------------------------------------------------------
_state: Dict[str, Any] = {
    "data": [],
    "columns": [],
    "stats": {
        "records_scraped": 0,
        "pages_crawled": 0,
        "execution_time": 0.0,
        "duplicates_removed": 0,
        "successful_requests": 0,
        "failed_requests": 0,
        "status": "idle",
        "last_run": None,
    },
    "csv_path": None,
    "json_path": None,
    "is_running": False,
    "scrape_error": None,
}
_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Response Helpers — every endpoint uses these for a consistent envelope
# ---------------------------------------------------------------------------
def _success(payload: Any, status_code: int = 200):
    """Return ``{"success": true, "data": <payload>}`` with the given HTTP status."""
    return jsonify({"success": True, "data": payload}), status_code


def _error(message: str, details: Any = None, status_code: int = 500):
    """Return ``{"success": false, "error": "...", "details": ...}``."""
    body: Dict[str, Any] = {"success": False, "error": message}
    if details is not None:
        body["details"] = details
    return jsonify(body), status_code


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------
def _get_latest_file(extension: str) -> Optional[Path]:
    """Find the most recently modified file with the given extension in the output folder."""
    if not Settings.OUTPUT_FOLDER.exists():
        return None
    files = list(Settings.OUTPUT_FOLDER.glob(f"*{extension}"))
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def _load_state_from_files() -> None:
    """
    Pre-populate _state from existing output files on startup.

    This ensures Data Explorer, Analytics, and Stats display data
    immediately after a server restart or Vercel cold start, without
    requiring a fresh scrape run.

    Guards
    ------
    - Skips loading if a scrape is currently in progress (prevents
      overwriting partially-updated in-memory data).
    - Skips loading if _state already holds fresh data from a
      completed scrape (prevents stale file data from overwriting
      a successful in-memory result on the same instance).
    """
    # Don't interfere while a scrape is in progress
    if _state["is_running"]:
        return

    # Don't overwrite fresh in-memory data from a completed scrape
    if _state["data"] and _state["stats"]["status"] == "completed":
        return

    latest_json = _get_latest_file(".json")
    if not latest_json:
        return

    try:
        with open(latest_json, "r", encoding="utf-8") as f:
            content = json.load(f)

        data = content.get("data", [])
        meta = content.get("metadata", {})

        if not data:
            return

        columns = list(data[0].keys())
        latest_csv = _get_latest_file(".csv")

        with _lock:
            _state["data"] = data
            _state["columns"] = columns
            _state["json_path"] = str(latest_json)
            _state["csv_path"] = str(latest_csv) if latest_csv else None
            _state["stats"]["records_scraped"] = meta.get("record_count", len(data))
            _state["stats"]["last_run"] = meta.get("exported_at", None)
            _state["stats"]["status"] = "completed"

        logger.info(
            "Loaded %d records from %s on startup",
            len(data),
            latest_json.name,
        )
    except Exception as exc:
        logger.warning("Could not load state from files: %s", exc)


# Hydrate state from existing output files on module load
_load_state_from_files()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _run_scraper(parser_name: Optional[str] = None, base_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute the full scraping pipeline.

    Parameters
    ----------
    parser_name : str, optional
        Parser to use. Defaults to ``Settings.ACTIVE_PARSER``.
    base_url : str, optional
        Override the base URL.

    Returns
    -------
    dict
        Summary of the scrape run.
    """
    parser_name = parser_name or Settings.ACTIVE_PARSER
    start_time = time.time()

    with _lock:
        _state["is_running"] = True
        _state["stats"]["status"] = "running"
        _state["scrape_error"] = None

    try:
        # 1. Load parser
        parser = load_parser(parser_name)
        url = base_url or parser.base_url
        columns = parser.get_columns()

        logger.info("Starting scrape: parser=%s, url=%s", parser_name, url)

        # 2. Fetch all pages
        fetcher = Fetcher()
        pages = fetcher.fetch_all_pages(url, parser.get_next_page)

        # 3. Parse all pages
        all_records: List[Dict[str, Any]] = []
        for page_url, page_soup in pages:
            records = parser.parse_listing(page_soup, page_url)
            all_records.extend(records)

        logger.info("Parsed %d raw records from %d pages", len(all_records), len(pages))

        # 4. Clean
        cleaner = Cleaner()
        cleaned = cleaner.clean(all_records, columns)

        # 5. Deduplicate
        dedup = Deduplicator()
        final_data = dedup.deduplicate(cleaned, parser.get_dedup_keys())

        # 6. Export CSV & JSON
        csv_path = export_csv(final_data, f"{parser_name}_data", columns)
        json_path = export_json(final_data, f"{parser_name}_data", parser.name)

        # 7. Optional database storage
        try:
            db_writer = DatabaseWriter()
            if db_writer.enabled:
                db_writer.save(final_data, f"scraped_{parser_name}", columns)
                db_writer.close()
        except Exception as db_exc:
            logger.warning("Database storage skipped: %s", db_exc)

        # 8. Update metrics
        elapsed = round(time.time() - start_time, 2)
        fetcher_metrics = fetcher.get_metrics()

        with _lock:
            _state["data"] = final_data
            _state["columns"] = columns
            _state["csv_path"] = str(csv_path)
            _state["json_path"] = str(json_path)
            _state["scrape_error"] = None
            _state["stats"] = {
                "records_scraped": len(final_data),
                "pages_crawled": len(pages),
                "execution_time": elapsed,
                "duplicates_removed": dedup.duplicates_removed,
                "successful_requests": fetcher_metrics["successful_requests"],
                "failed_requests": fetcher_metrics["failed_requests"],
                "status": "completed",
                "last_run": timestamp_now(),
            }
            _state["is_running"] = False

        fetcher.close()

        logger.success(  # type: ignore[attr-defined]
            "Scrape complete: %d records in %.2fs", len(final_data), elapsed
        )
        return _state["stats"]

    except Exception as exc:
        elapsed = round(time.time() - start_time, 2)
        with _lock:
            _state["stats"]["status"] = "failed"
            _state["stats"]["execution_time"] = elapsed
            _state["stats"]["last_run"] = timestamp_now()
            _state["is_running"] = False
            _state["scrape_error"] = str(exc)
        logger.error("Scrape failed: %s", exc)
        raise


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@api_bp.route("/data", methods=["GET"])
def get_data():
    """Return scraped data, optionally filtered by a search query."""
    # Re-hydrate from files if state is empty (cold start / restart)
    if not _state["data"]:
        _load_state_from_files()

    search = request.args.get("search", "").strip().lower()
    data = _state["data"]
    columns = _state["columns"]

    if search and data:
        data = [
            record for record in data
            if any(
                search in str(v).lower()
                for v in record.values()
            )
        ]

    return _success({
        "records": data,
        "columns": columns,
        "total": len(data),
        "parser": Settings.ACTIVE_PARSER,
    })


@api_bp.route("/stats", methods=["GET"])
def get_stats():
    """Return pipeline statistics."""
    # Re-hydrate from files if state is empty (cold start / restart)
    if _state["stats"]["records_scraped"] == 0:
        _load_state_from_files()

    return _success(_state["stats"])


@api_bp.route("/logs", methods=["GET"])
def get_logs():
    """Return recent log entries from the in-memory buffer or log file."""
    limit = request.args.get("limit", 100, type=int)
    logs = get_log_buffer()

    # Fallback: supplement from log file if buffer has fewer entries than requested
    if len(logs) < limit:
        log_file = Settings.LOG_FOLDER / "pipeline.log"
        if log_file.exists():
            try:
                lines = log_file.read_text(encoding="utf-8").strip().splitlines()
                file_logs = []
                for line in lines[-limit:]:
                    parts = line.split(" | ", 3)
                    if len(parts) >= 3:
                        file_logs.append({
                            "timestamp": parts[0].strip(),
                            "level": parts[1].strip(),
                            "message": parts[3].strip() if len(parts) > 3 else parts[2].strip(),
                            "module": parts[2].strip() if len(parts) > 3 else "",
                        })
                # Merge: file logs first, then buffer logs (avoid duplicates by timestamp)
                buffer_timestamps = {l.get("timestamp") for l in logs}
                merged = [l for l in file_logs if l.get("timestamp") not in buffer_timestamps]
                merged.extend(logs)
                logs = merged
            except Exception:
                pass

    return _success({
        "logs": logs[-limit:],
        "total": len(logs),
    })


@api_bp.route("/scrape", methods=["POST"])
def trigger_scrape():
    """
    Trigger a scrape run.

    Accepts optional JSON body:
    ``{"parser": "books", "base_url": "https://..."}``
    """
    if _state["is_running"]:
        return _error("A scrape is already running", status_code=409)

    body = request.get_json(silent=True) or {}
    parser_name = body.get("parser", Settings.ACTIVE_PARSER)
    base_url = body.get("base_url")

    try:
        stats = _run_scraper(parser_name, base_url)
        return _success({
            "message": "Scrape completed successfully",
            "stats": stats,
            "status": "completed",
        })
    except Exception as exc:
        return _error(str(exc))


@api_bp.route("/scrape/status", methods=["GET"])
def get_scrape_status():
    """Return the current scraping status (lightweight status check)."""
    return _success({
        "status": _state["stats"]["status"],
        "is_running": _state["is_running"],
        "error": _state.get("scrape_error"),
    })


@api_bp.route("/config", methods=["GET"])
def get_config():
    """Return current configuration."""
    return _success(Settings.to_dict())


@api_bp.route("/config", methods=["PUT"])
def update_config():
    """
    Update configuration at runtime.

    Accepts a JSON body with any subset of configuration keys.
    """
    body = request.get_json(silent=True)
    if not body:
        return _error("No configuration provided", status_code=400)

    try:
        Settings.update_runtime(**body)
        logger.info("Configuration updated: %s", list(body.keys()))
        return _success({
            "message": "Configuration updated",
            "config": Settings.to_dict(),
        })
    except Exception as exc:
        return _error(str(exc))


@api_bp.route("/export/csv", methods=["GET"])
def export_csv_endpoint():
    """Download the most recent CSV export."""
    csv_path = _state.get("csv_path")
    if not csv_path or not Path(csv_path).exists():
        latest_csv = _get_latest_file(".csv")
        if latest_csv:
            csv_path = str(latest_csv)
            
    if not csv_path or not Path(csv_path).exists():
        return _error("No CSV file available. Run a scrape first.", status_code=404)
    return send_file(csv_path, as_attachment=True, mimetype="text/csv")


@api_bp.route("/export/json", methods=["GET"])
def export_json_endpoint():
    """Download the most recent JSON export."""
    json_path = _state.get("json_path")
    if not json_path or not Path(json_path).exists():
        latest_json = _get_latest_file(".json")
        if latest_json:
            json_path = str(latest_json)

    if not json_path or not Path(json_path).exists():
        return _error("No JSON file available. Run a scrape first.", status_code=404)
    return send_file(json_path, as_attachment=True, mimetype="application/json")


@api_bp.route("/parsers", methods=["GET"])
def list_parsers():
    """List all available parsers with their metadata and columns."""
    parsers = get_available_parsers()
    return _success({
        "parsers": parsers,
        "active": Settings.ACTIVE_PARSER,
    })
