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
PARSER_REGISTRY: Dict[str, str] = {
    "books": "scraper.books_parser",
    "quotes": "scraper.quotes_parser",
    "jobs": "scraper.jobs_parser",
}


def get_available_parsers() -> List[Dict[str, Any]]:
    """
    Return metadata for every registered parser.

    Returns
    -------
    list of dict
        Each dict contains ``name``, ``module``, and ``columns``.
    """
    result: List[Dict[str, Any]] = []
    for name, module_path in PARSER_REGISTRY.items():
        try:
            mod = importlib.import_module(module_path)
            parser_cls = getattr(mod, "Parser")
            parser = parser_cls()
            result.append({
                "name": name,
                "display_name": parser.name,
                "base_url": parser.base_url,
                "columns": parser.get_columns(),
            })
        except Exception as exc:
            logger.warning("Could not load parser '%s': %s", name, exc)
            result.append({
                "name": name,
                "display_name": name.title(),
                "base_url": "",
                "columns": [],
                "error": str(exc),
            })
    return result


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
