"""
Main Entry Point
================
CLI for the Scalable Web Scraping Pipeline.

Usage
-----
    python main.py serve     # Start the Flask API and Dashboard (default)
    python main.py scrape    # Run the scraper once in the terminal
"""

import argparse
import sys

from api.app import create_app
from api.routes import _run_scraper
from config.settings import Settings
from utils.logger import get_logger

logger = get_logger("main")


def run_server() -> None:
    """Start the Flask API server and Dashboard."""
    app = create_app()
    logger.info("Starting dashboard server on http://%s:%d", Settings.API_HOST, Settings.API_PORT)
    app.run(
        host=Settings.API_HOST,
        port=Settings.API_PORT,
        debug=Settings.DEBUG,
        use_reloader=False,  # Prevent double-execution when debugging
    )


def run_cli_scrape(parser: str, base_url: str) -> None:
    """Run the scraper synchronously in the terminal."""
    logger.info("Starting standalone CLI scrape run")
    try:
        stats = _run_scraper(parser, base_url)
        logger.info("CLI scrape completed successfully")
        print("\n--- Scrape Statistics ---")
        for k, v in stats.items():
            print(f"{k.replace('_', ' ').title()}: {v}")
    except Exception as exc:
        logger.error("CLI scrape failed: %s", exc)
        sys.exit(1)


def main() -> None:
    """Parse arguments and start the appropriate mode."""
    parser = argparse.ArgumentParser(
        description="Scalable Web Scraping Pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: serve
    subparsers.add_parser("serve", help="Start the Flask API and Dashboard")

    # Command: scrape
    scrape_parser = subparsers.add_parser("scrape", help="Run the scraper standalone")
    scrape_parser.add_argument(
        "--parser",
        type=str,
        default=Settings.ACTIVE_PARSER,
        help="Parser module to use (e.g. books, quotes, jobs)",
    )
    scrape_parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="Override the base URL for the parser",
    )

    args = parser.parse_args()
    command = args.command or "serve"

    if command == "serve":
        run_server()
    elif command == "scrape":
        run_cli_scrape(args.parser, args.url)


if __name__ == "__main__":
    main()
