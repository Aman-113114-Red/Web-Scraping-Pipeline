"""
Tests for API routes
"""

import pytest
from flask import Flask
from api.app import create_app


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_dashboard_route(client):
    """Test the dashboard HTML is served."""
    # The dashboard template might try to render, but without the actual templates folder it might fail.
    # However, since we defined templates_folder to the absolute path in Settings, it should work.
    response = client.get("/")
    assert response.status_code == 200
    assert b"Dashboard" in response.data or b"html" in response.data


def test_api_stats(client):
    """Test the /api/stats endpoint returns consistent envelope."""
    response = client.get("/api/stats")
    assert response.status_code == 200
    envelope = response.get_json()
    assert envelope["success"] is True
    data = envelope["data"]
    assert "records_scraped" in data
    assert "status" in data


def test_api_config_get(client):
    """Test getting configuration returns consistent envelope."""
    response = client.get("/api/config")
    assert response.status_code == 200
    envelope = response.get_json()
    assert envelope["success"] is True
    data = envelope["data"]
    assert "active_parser" in data
    assert "timeout" in data


def test_api_parsers(client):
    """Test listing parsers returns consistent envelope."""
    response = client.get("/api/parsers")
    assert response.status_code == 200
    envelope = response.get_json()
    assert envelope["success"] is True
    data = envelope["data"]
    assert "parsers" in data
    assert "active" in data
    assert len(data["parsers"]) > 0
    assert any(p["name"] == "books" for p in data["parsers"])


def test_api_data(client):
    """Test the /api/data endpoint returns consistent envelope."""
    response = client.get("/api/data")
    assert response.status_code == 200
    envelope = response.get_json()
    assert envelope["success"] is True
    data = envelope["data"]
    assert "records" in data
    assert "columns" in data
    assert "total" in data
    assert "parser" in data


def test_api_logs(client):
    """Test the /api/logs endpoint returns consistent envelope."""
    response = client.get("/api/logs")
    assert response.status_code == 200
    envelope = response.get_json()
    assert envelope["success"] is True
    data = envelope["data"]
    assert "logs" in data
    assert "total" in data


def test_api_scrape_status(client):
    """Test the /api/scrape/status endpoint returns consistent envelope."""
    response = client.get("/api/scrape/status")
    assert response.status_code == 200
    envelope = response.get_json()
    assert envelope["success"] is True
    data = envelope["data"]
    assert "status" in data
    assert "is_running" in data
    assert data["status"] in ("idle", "running", "completed", "failed")


def test_api_error_format(client):
    """Test that error responses use consistent envelope."""
    response = client.get("/api/export/csv")
    # May be 404 if no file exists — verify error envelope format
    if response.status_code == 404:
        envelope = response.get_json()
        assert envelope["success"] is False
        assert "error" in envelope
