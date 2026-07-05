"""
Tests for Storage Writers
"""

import json
from pathlib import Path
from storage.csv_writer import export_csv
from storage.json_writer import export_json


def test_export_csv(tmp_path):
    """Test CSV export."""
    records = [
        {"title": "Book 1", "price": "10.00"},
        {"title": "Book 2", "price": "20.00"},
    ]
    
    csv_path = export_csv(records, filename="test_export", output_dir=tmp_path)
    
    assert csv_path.exists()
    content = csv_path.read_text(encoding="utf-8")
    
    assert "title,price" in content
    assert "Book 1,10.00" in content
    assert "Book 2,20.00" in content


def test_export_json(tmp_path):
    """Test JSON export."""
    records = [
        {"title": "Book 1", "price": "10.00"},
    ]
    
    json_path = export_json(records, filename="test_export", source="test", output_dir=tmp_path)
    
    assert json_path.exists()
    content = json.loads(json_path.read_text(encoding="utf-8"))
    
    assert "metadata" in content
    assert content["metadata"]["source"] == "test"
    assert content["metadata"]["record_count"] == 1
    
    assert "data" in content
    assert content["data"][0]["title"] == "Book 1"
