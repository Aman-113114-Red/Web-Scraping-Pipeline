"""
Tests for Fetcher module
"""

from unittest.mock import patch, MagicMock
import pytest
import requests
from bs4 import BeautifulSoup
from scraper.fetcher import Fetcher


@pytest.fixture
def fetcher():
    """Returns a Fetcher instance."""
    return Fetcher()


@patch("scraper.fetcher.requests.Session.get")
def test_fetch_success(mock_get, fetcher):
    """Test successful fetch."""
    mock_response = MagicMock()
    mock_response.text = "<html><body><h1>Test</h1></body></html>"
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    soup = fetcher.fetch("http://test.com")
    
    assert soup is not None
    assert isinstance(soup, BeautifulSoup)
    assert soup.find("h1").text == "Test"
    assert fetcher.successful_requests == 1
    assert fetcher.total_requests == 1


@patch("scraper.fetcher.requests.Session.get")
def test_fetch_retry_and_fail(mock_get, fetcher):
    """Test fetch fails after retries."""
    # We patch settings to ensure fast retries for the test
    with patch("config.settings.Settings.MAX_RETRIES", 1), \
         patch("config.settings.Settings.RETRY_DELAY", 0):
         
        mock_get.side_effect = requests.RequestException("Network Error")

        # fetch_safe should catch the exception and return None
        soup = fetcher.fetch_safe("http://test.com")
        
        assert soup is None
        assert fetcher.failed_requests == 1


def test_fetch_all_pages(fetcher):
    """Test fetch_all_pages logic."""
    # Mock fetch_safe to return a valid soup 3 times, then None
    call_count = [0]
    
    def mock_fetch_safe(url):
        if call_count[0] < 3:
            call_count[0] += 1
            return BeautifulSoup(f"<html>Page {call_count[0]}</html>", "html.parser")
        return None
    
    fetcher.fetch_safe = mock_fetch_safe
    
    # Mock callback to increment URL
    def mock_next_page(soup, current_url):
        if call_count[0] < 3:
            return f"http://test.com/page{call_count[0]+1}"
        return None

    # Patch REQUEST_DELAY to 0 for fast testing
    fetcher.request_delay = 0

    pages = fetcher.fetch_all_pages("http://test.com/page1", mock_next_page)
    
    assert len(pages) == 3
    assert pages[0][0] == "http://test.com/page1"
    assert pages[1][0] == "http://test.com/page2"
    assert pages[2][0] == "http://test.com/page3"
    assert "Page 1" in pages[0][1].text
