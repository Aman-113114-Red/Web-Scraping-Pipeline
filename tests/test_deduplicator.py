"""
Tests for Deduplicator
"""

from scraper.deduplicator import Deduplicator


def test_deduplicator():
    """Test removing duplicates based on keys."""
    records = [
        {"title": "Book 1", "url": "url1", "price": "10"},
        {"title": "Book 2", "url": "url2", "price": "20"},
        {"title": "Book 1", "url": "url1", "price": "15"}, # Duplicate keys
    ]
    
    dedup = Deduplicator()
    # Deduplicate based on title and url
    unique = dedup.deduplicate(records, keys=["title", "url"])
    
    assert len(unique) == 2
    assert unique[0]["title"] == "Book 1"
    assert unique[1]["title"] == "Book 2"
    assert dedup.duplicates_removed == 1


def test_deduplicator_no_keys():
    """Test deduplicating on full record hash."""
    records = [
        {"a": 1, "b": 2},
        {"a": 1, "b": 2},
        {"a": 2, "b": 2},
    ]
    
    dedup = Deduplicator()
    unique = dedup.deduplicate(records)
    
    assert len(unique) == 2
    assert dedup.duplicates_removed == 1


def test_deduplicator_empty():
    """Test deduplicating empty list."""
    dedup = Deduplicator()
    assert dedup.deduplicate([]) == []
    assert dedup.duplicates_removed == 0
