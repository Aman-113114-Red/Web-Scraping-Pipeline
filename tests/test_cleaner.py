"""
Tests for Cleaner module
"""

import pytest
from scraper.cleaner import Cleaner


@pytest.fixture
def cleaner():
    return Cleaner()


def test_cleaner_normalize_price(cleaner):
    """Test price cleaning."""
    records = [
        {"price": "£51.77"},
        {"price": "$10.50"},
        {"price": "Â£22.99"}, # test the artefact from books.toscrape
        {"price": "Free"},    # non-numeric
        {"price": 45.0},
    ]
    cleaned = cleaner.clean(records)
    assert cleaned[0]["price"] == "51.77"
    assert cleaned[1]["price"] == "10.50"
    assert cleaned[2]["price"] == "22.99"
    assert cleaned[3]["price"] == "0.00"
    assert cleaned[4]["price"] == "45.00"


def test_cleaner_normalize_rating(cleaner):
    """Test rating conversion."""
    records = [
        {"rating": "One"},
        {"rating": "FIVE"},
        {"rating": "Three"},
        {"rating": "Unknown"},
        {"rating": 4},
        {"rating": "4.5"},
    ]
    cleaned = cleaner.clean(records)
    assert cleaned[0]["rating"] == 1
    assert cleaned[1]["rating"] == 5
    assert cleaned[2]["rating"] == 3
    assert cleaned[3]["rating"] == 0
    assert cleaned[4]["rating"] == 4
    assert cleaned[5]["rating"] == 4


def test_cleaner_whitespace(cleaner):
    """Test whitespace stripping."""
    records = [
        {"title": "   A   Book   With    Spaces   \n"}
    ]
    cleaned = cleaner.clean(records)
    assert cleaned[0]["title"] == "A Book With Spaces"


def test_cleaner_fill_missing(cleaner):
    """Test filling missing columns."""
    records = [
        {"title": "Book 1"}
    ]
    columns = ["title", "price", "rating"]
    cleaned = cleaner.clean(records, columns=columns)
    
    assert cleaned[0]["title"] == "Book 1"
    assert cleaned[0]["price"] == "0.00"
    assert cleaned[0]["rating"] == 0
