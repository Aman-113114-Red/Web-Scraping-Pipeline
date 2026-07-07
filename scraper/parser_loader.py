"""
Dynamic Parser Loader
=====================
Loads the active parser module at runtime based on ``Settings.ACTIVE_PARSER``.

Every parser module must expose the following interface:

    class Parser:
        name: str                       — human-readable name
        base_url: str                   — default base URL for this source

        def get_columns(self) -> list[str]
        def get_dedup_keys(self) -> list[str]
        def get_next_page(self, soup, current_url) -> str | None
        def parse_listing(self, soup) -> list[dict]
"""

import importlib
from typing import Any, Dict, List

from utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Registry of known parsers  (name → module path)
# ---------------------------------------------------------------------------
WEBSITE_REGISTRY: List[Dict[str, Any]] = [
    {
        "parser": "books",
        "module": "scraper.books_parser",
        "name": "Books",
        "type": "Books Website",
        "domain": "books.toscrape.com",
        "icon": "📚",
        "theme_color": "blue",
        "supported": True,
        "protection": "None",
        "title": "📚 Books Dashboard",
        "expected_columns": ["Title", "Price", "Rating", "Availability"],
        "overview_cards": ["Books", "Ratings", "Prices", "Stock"],
        "description": "Extracts Title, Price, Rating, Availability",
        "charts": [
            {"id": "chartDistribution", "columns": ["price", "rating"], "title": "Price Distribution", "type": "bar", "numeric": True},
            {"id": "chartRatings", "columns": ["rating", "availability"], "title": "Ratings Distribution", "type": "doughnut"}
        ]
    },
    {
        "parser": "quotes",
        "module": "scraper.quotes_parser",
        "name": "Quotes",
        "type": "Quotes Website",
        "domain": "quotes.toscrape.com",
        "icon": "💬",
        "theme_color": "purple",
        "supported": True,
        "protection": "None",
        "title": "💬 Quotes Dashboard",
        "expected_columns": ["Quote", "Author", "Tags"],
        "overview_cards": ["Quotes", "Authors", "Tags", "Categories"],
        "description": "Extracts Quote, Author, Tags",
        "charts": [
            {"id": "chartDistribution", "columns": ["author", "tags"], "title": "Quotes by Author", "type": "bar"},
            {"id": "chartRatings", "columns": ["tags", "author"], "title": "Tag Distribution", "type": "doughnut"}
        ]
    },
    {
        "parser": "jobs",
        "module": "scraper.jobs_parser",
        "name": "Jobs",
        "type": "Jobs Website",
        "domain": "python.org",
        "icon": "💼",
        "theme_color": "cyan",
        "supported": True,
        "protection": "None",
        "title": "💼 Jobs Dashboard",
        "expected_columns": ["Job", "Company", "Location", "Apply"],
        "overview_cards": ["Jobs", "Companies", "Locations", "Dates"],
        "description": "Extracts Title, Company, Location, Date",
        "charts": [
            {"id": "chartDistribution", "columns": ["location", "company"], "title": "Jobs by Location", "type": "bar"},
            {"id": "chartRatings", "columns": ["company", "location"], "title": "Jobs by Company", "type": "doughnut"}
        ]
    }
]

PARSER_REGISTRY: Dict[str, str] = {entry["parser"]: entry["module"] for entry in WEBSITE_REGISTRY}


def get_available_parsers() -> List[Dict[str, Any]]:
    """
    Return metadata for every registered website in the registry.

    Returns
    -------
    list of dict
        List of all supported website metadata configurations.
    """
    return WEBSITE_REGISTRY


def load_parser(parser_name: str) -> Any:
    """
    Dynamically load and instantiate a parser by name.

    Parameters
    ----------
    parser_name : str
        Key in ``PARSER_REGISTRY`` (e.g. ``"books"``).

    Returns
    -------
    Parser
        An instance of the requested parser.

    Raises
    ------
    ValueError
        If the parser name is not found in the registry.
    ImportError
        If the parser module cannot be imported.
    """
    parser_name = parser_name.strip().lower()

    if parser_name not in PARSER_REGISTRY:
        available = ", ".join(PARSER_REGISTRY.keys())
        raise ValueError(
            f"Unknown parser '{parser_name}'. Available parsers: {available}"
        )

    module_path = PARSER_REGISTRY[parser_name]
    logger.info("Loading parser module: %s", module_path)

    module = importlib.import_module(module_path)
    parser_cls = getattr(module, "Parser")
    parser = parser_cls()

    logger.info(
        "Parser loaded: %s (%s) — columns: %s",
        parser.name,
        parser.base_url,
        parser.get_columns(),
    )
    return parser


def register_parser(name: str, module_path: str) -> None:
    """
    Register a new parser at runtime.

    Parameters
    ----------
    name : str
        Short name for the parser (e.g. ``"amazon"``).
    module_path : str
        Dotted module path (e.g. ``"scraper.amazon_parser"``).
    """
    PARSER_REGISTRY[name] = module_path
    logger.info("Registered parser: %s -> %s", name, module_path)
