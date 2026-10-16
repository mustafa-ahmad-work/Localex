"""
Unit tests for SQLite database operations, filtering, and export/import.
"""

from pathlib import Path
import pytest
from Localex.database import DatabaseManager


def test_database_crud(tmp_path: Path):
    db_file = tmp_path / "test_history.db"
    db = DatabaseManager(db_path=db_file)

    # 1. Add translation
    row_id = db.add_translation(
        source_text="Hello world",
        translated_text="مرحبا بالعالم",
        source_lang="en",
        target_lang="ar",
        model_name="nllb-600m",
    )
    assert row_id > 0

    # 2. Query translations
    items = db.get_translations()
    assert len(items) == 1
    assert items[0]["source_text"] == "Hello world"
    assert items[0]["translated_text"] == "مرحبا بالعالم"
    assert items[0]["source_lang"] == "en"
    assert items[0]["target_lang"] == "ar"

    # 3. Search query
    res = db.get_translations(search_query="world")
    assert len(res) == 1
    res_ar = db.get_translations(search_query="بالعالم")
    assert len(res_ar) == 1
    res_none = db.get_translations(search_query="nonexistent")
    assert len(res_none) == 0

    # 4. Count
    assert db.count_translations() == 1

    # 5. Delete
    deleted = db.delete_translation(row_id)
    assert deleted is True
    assert db.count_translations() == 0


def test_database_export_import(tmp_path: Path):
    db_file = tmp_path / "test_history.db"
    db = DatabaseManager(db_path=db_file)

    db.add_translation("Apple", "تفاحة", "en", "ar")
    db.add_translation("Orange", "برتقال", "en", "ar")

    # Export to CSV
    csv_file = tmp_path / "export.csv"
    count = db.export_to_csv(csv_file)
    assert count == 2
    assert csv_file.exists()

    # Clear and Import
    db.clear_all()
    assert db.count_translations() == 0

    imported_count = db.import_from_csv(csv_file)
    assert imported_count == 2
    assert db.count_translations() == 2
