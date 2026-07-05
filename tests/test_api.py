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
    """Test the /api/stats endpoint."""
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.get_json()
    assert "records_scraped" in data
    assert "status" in data


def test_api_config_get(client):
    """Test getting configuration."""
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.get_json()
    assert "active_parser" in data
    assert "timeout" in data


def test_api_parsers(client):
    """Test listing parsers."""
    response = client.get("/api/parsers")
    assert response.status_code == 200
    data = response.get_json()
    assert "parsers" in data
    assert "active" in data
    assert len(data["parsers"]) > 0
    assert any(p["name"] == "books" for p in data["parsers"])
