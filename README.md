# Intelligent Web Scraping Platform

![Status](https://img.shields.io/badge/Status-Production_Ready-success)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Flask](https://img.shields.io/badge/Backend-Flask-lightgrey)
![Architecture](https://img.shields.io/badge/Architecture-Modular-orange)

An intelligent, adaptive, and scalable web scraping pipeline featuring a professional SaaS-grade dashboard. This platform dynamically detects target websites, routes them to specialized scraping modules, cleans the extracted data, and presents rich analytics in a highly responsive user interface.

---

## 🌟 Key Features

* **Intelligent Website Detection:** Instantly evaluates any URL, determines support status, detects anti-bot protections, and routes to the appropriate parser.
* **Modular Scraping Architecture:** Easily extensible `WEBSITE_REGISTRY` pattern allows adding new target sites without modifying core pipeline logic.
* **Schema-Aware Analytics:** The dashboard automatically generates contextual charts (e.g., *Price Distribution* for Books, *Salary Trends* for Jobs) based on the specific schema of the scraped data.
* **Robust Data Pipeline:** Built-in deduplication, configurable request retries, exponential backoff, and robust error handling.
* **Professional UI/UX:** Responsive design, smooth micro-animations, comprehensive empty states, interactive live logs, and a dark/light mode toggle.
* **Instant Export:** Export structured datasets directly to CSV or JSON formats.

---

## 🏗️ Architecture

The platform follows a clean separation of concerns:

1. **Frontend (Vanilla JS + CSS + HTML):** A high-performance, lightweight SPA (Single Page Application) powered by modern CSS Grid/Flexbox and Chart.js.
2. **Backend API (Flask):** Exposes RESTful endpoints for triggering scrapes, fetching system metrics, streaming logs, and downloading data.
3. **Scraping Engine (Requests + BeautifulSoup):** Executes parallel HTTP requests with anti-bot evasion heuristics.
4. **Data Processor:** Cleans schemas and deduplicates records in memory.
5. **Storage Layer:** Persists state and historical runs on the filesystem.

---

## 🚀 Supported Targets

The platform currently includes robust parsers for the following domain templates:

| Domain | Extracted Entities | Analytics Focus |
|--------|---------------------|-----------------|
| **Books (E-commerce)** | Title, Price, Rating, Availability | Value Distribution, Category Trends |
| **Quotes (Content)** | Quote Text, Author, Tags | Tag Density, Author Frequency |
| **Python Jobs (Listings)**| Job Title, Company, Location | Geographic Spread, Hiring Trends |

*Note: Unsupported or protected websites will gracefully degrade, showing a clear explanation in the UI without crashing the application.*

---

## ⚙️ Installation & Setup

### Prerequisites
- Python 3.9+
- pip (Python package installer)

### Local Development

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/web-scraping-pipeline.git
   cd web-scraping-pipeline
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Flask application:**
   ```bash
   python main.py
   ```
   *The application will be available at `http://localhost:5000`.*

---

## 🛠️ Usage

1. **Target a Website:** Enter a target URL in the top navigation bar. The system will immediately validate the URL and verify if a parser exists.
2. **Configure Settings:** Navigate to the **Workspace** tab to adjust timeouts, retry limits, and user-agent strings.
3. **Start Scraping:** Click "Start Scraping". Monitor the pipeline execution in real-time through the progressive UI indicator.
4. **Analyze Data:** View schema-aware charts in the **Analytics** tab and browse raw data in the **Data Explorer**.
5. **Export:** Click the CSV or JSON buttons to download the sanitized dataset.

---

## 📈 Future Scalability

The pipeline is designed with horizontal scalability in mind. Future upgrades could trivially introduce:
- Distributed task queues (e.g., Celery + Redis).
- Headless browser integration (e.g., Playwright) for JS-heavy targets.
- Database persistence (PostgreSQL / MongoDB) replacing local file storage.

---

*This project was engineered to demonstrate production-grade software development, architectural design patterns, and full-stack proficiency.*
