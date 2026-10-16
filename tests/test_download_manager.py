"""
Unit tests for download manager logic, progress reporting, and range resume.
"""

from pathlib import Path
import pytest
from Localex.download_manager import (
    DownloadProgress,
    DownloadState,
    ModelDownloader,
)
from Localex.model_manager import (
    ModelCatalogItem,
    ModelFileInfo,
)


def test_download_progress_init():
    p = DownloadProgress()
    assert p.state == DownloadState.IDLE
    assert p.overall_percent == 0.0
    assert p.speed_bps == 0.0


def test_model_downloader_setup(tmp_path: Path):
    cat_item = ModelCatalogItem(
        model_id="test-model",
        name="Test Model",
        description="A test model",
        architecture="NLLB",
        quantization="INT8",
        required_disk_mb=10,
        required_ram_mb=50,
        repo_id="test/repo",
        files=[
            ModelFileInfo("file1.bin", "http://example.com/file1.bin", 1000),
            ModelFileInfo("file2.bin", "http://example.com/file2.bin", 2000),
        ],
    )
    downloader = ModelDownloader(cat_item, tmp_path)
    assert downloader.progress.grand_total_bytes == 3000
    assert downloader.progress.total_files == 2

    # Test pause and cancel flags
    downloader.pause()
    assert downloader._is_paused is True
    assert downloader.progress.state == DownloadState.PAUSED

    downloader.resume()
    assert downloader._is_paused is False
    assert downloader.progress.state == DownloadState.DOWNLOADING

    downloader.cancel()
    assert downloader._is_cancelled is True
    assert downloader.progress.state == DownloadState.CANCELLED
