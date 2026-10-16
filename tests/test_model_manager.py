"""
Unit tests for model manager and integrity verification.
"""

from pathlib import Path
import pytest
from Localex.model_manager import (
    ModelManager,
    ModelStatus,
    compute_file_sha256,
)


def test_validate_empty_dir(tmp_path: Path):
    mm = ModelManager(models_root=tmp_path)
    is_valid, reason = mm.validate_model_directory(tmp_path / "non_existent")
    assert is_valid is False
    assert "ليس مجلداً" in reason


def test_validate_incomplete_dir(tmp_path: Path):
    mm = ModelManager(models_root=tmp_path)
    model_dir = tmp_path / "test_model"
    model_dir.mkdir()

    # Only model.bin
    (model_dir / "model.bin").write_bytes(b"dummy model weights" * 200)
    is_valid, reason = mm.validate_model_directory(model_dir)
    assert is_valid is False
    assert "SentencePiece" in reason


def test_validate_valid_mock_dir(tmp_path: Path):
    mm = ModelManager(models_root=tmp_path)
    model_dir = tmp_path / "test_model"
    model_dir.mkdir()

    (model_dir / "model.bin").write_bytes(b"dummy model weights" * 200)
    (model_dir / "sentencepiece.bpe.model").write_bytes(b"dummy spm" * 200)
    (model_dir / "shared_vocabulary.txt").write_bytes(b"dummy vocab" * 20)

    is_valid, reason = mm.validate_model_directory(model_dir)
    assert is_valid is True
    assert "صحيح" in reason


def test_compute_sha256(tmp_path: Path):
    test_file = tmp_path / "test.bin"
    test_file.write_bytes(b"hello world ctranslate2")
    # Expected SHA256 of b"hello world ctranslate2"
    import hashlib
    expected = hashlib.sha256(b"hello world ctranslate2").hexdigest()
    assert compute_file_sha256(test_file) == expected
