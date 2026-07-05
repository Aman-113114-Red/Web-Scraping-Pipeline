# Scalable Web Scraping Pipeline

A production-ready, modular web scraping pipeline with a modern hybrid dashboard, REST API, and highly configurable architecture. Designed to support scraping multiple websites seamlessly by simply dropping in new parser modules.

## Architecture

The project follows clean architecture principles, separating concerns into distinct layers:

1. **Configuration**: Centralised settings loaded from `.env`.
2. **Scraper Engine**:
   - `Fetcher`: Handles HTTP requests, pagination, retries, and timeouts.
   - `Parsers`: Website-specific logic to extract data (dynamically loaded).
   - `Cleaner`: Generic normalisation of prices, ratings, and strings.
   - `Deduplicator`: Key-based duplicate removal.
3. **Storage Layer**: CSV, JSON, and optional PostgreSQL writers.
4. **REST API**: Flask backend providing endpoints for data, stats, logs, and triggers.
5. **Dashboard**: A premium, responsive HTML/CSS/JS frontend with live charts and real-time updates.

## Folder Structure

```
web-scraping-pipeline/
├── api/             # Flask application and REST routes
├── config/          # Centralised settings
├── scraper/         # Fetcher, cleaner, deduplicator, and parsers
├── static/          # CSS styles and JS dashboard logic
├── storage/         # CSV, JSON, and Database writers
├── templates/       # HTML dashboard layout
├── tests/           # Pytest suite
├── utils/           # Logger, retry decorators, and helpers
├── main.py          # CLI entry point
├── .env             # Environment variables
└── requirements.txt # Python dependencies
```

## Installation

1. Clone the repository and navigate to the folder.
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the environment template and adjust if necessary:
   ```bash
   cp .env.example .env
   ```

## How to Run

**1. Start the Dashboard & API Server**
```bash
python main.py serve
```
Open `http://localhost:5000` in your browser.

**2. Run the Scraper Standalone (CLI)**
```bash
python main.py scrape --parser books
```

## API Documentation

- `GET /api/data`: Returns scraped data (supports `?search=query`).
- `GET /api/stats`: Returns pipeline execution statistics.
- `GET /api/logs`: Returns recent log entries.
- `POST /api/scrape`: Triggers a scrape run. Body: `{"parser": "books"}`.
- `GET /api/config`: Reads current configuration.
- `PUT /api/config`: Updates configuration at runtime.
- `GET /api/export/csv`: Downloads the latest CSV.
- `GET /api/export/json`: Downloads the latest JSON.
- `GET /api/parsers`: Lists available parsers.

## Future Scalability

To add support for a new website (e.g., Amazon):
1. Create `scraper/amazon_parser.py`.
2. Implement the `Parser` class with methods `get_columns()`, `get_dedup_keys()`, `get_next_page()`, and `parse_listing()`.
3. Register it in `scraper/parser_loader.py` `PARSER_REGISTRY`.
4. The dashboard, API, cleaner, and storage layers will automatically adapt to the new data schema.

## License
MIT License
