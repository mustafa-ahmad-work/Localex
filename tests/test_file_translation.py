"""
Unit tests for document and file translation logic.
"""

from pathlib import Path
import csv
import pytest
from Localex.workers import FileTranslationWorker
from Localex.translator import TranslationEngine


def test_file_translation_text_file(tmp_path: Path):
    in_file = tmp_path / "sample.txt"
    in_file.write_text("Hello world.\n\nThis is paragraph two.\nThird line.", encoding="utf-8")

    out_file = tmp_path / "sample_translated.txt"

    engine = TranslationEngine()
    # Mock translator cache so translation succeeds without real model
    engine._cache[("Hello world.", "en", "ar")] = "مرحبا بالعالم."
    engine._cache[("This is paragraph two.", "en", "ar")] = "هذه هي الفقرة الثانية."
    engine._cache[("Third line.", "en", "ar")] = "السطر الثالث."

    worker = FileTranslationWorker(
        engine=engine,
        input_file=in_file,
        output_file=out_file,
        source_lang="en",
        target_lang="ar",
    )
    worker._translate_text_file()

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "مرحبا بالعالم." in content
    assert "هذه هي الفقرة الثانية." in content


def test_file_translation_csv_file(tmp_path: Path):
    in_csv = tmp_path / "data.csv"
    with open(in_csv, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["ID", "Name"])
        w.writerow(["1", "Apple"])
        w.writerow(["2", "Orange"])

    out_csv = tmp_path / "data_translated.csv"

    engine = TranslationEngine()
    engine._cache[("Apple", "en", "ar")] = "تفاحة"
    engine._cache[("Orange", "en", "ar")] = "برتقال"

    worker = FileTranslationWorker(
        engine=engine,
        input_file=in_csv,
        output_file=out_csv,
        source_lang="en",
        target_lang="ar",
    )
    worker._translate_csv_file()

    assert out_csv.exists()
    with open(out_csv, "r", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["ID", "Name"]
    assert rows[1] == ["1", "تفاحة"]
    assert rows[2] == ["2", "برتقال"]
