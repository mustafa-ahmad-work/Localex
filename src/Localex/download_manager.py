"""
Resumable chunked download manager with speed, ETA, pause/cancel, and SHA256 verification.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional

import requests

from Localex.model_manager import (
    CATALOG,
    ModelCatalogItem,
    ModelFileInfo,
    compute_file_sha256,
)

logger = logging.getLogger(__name__)


class DownloadState:
    IDLE = "idle"
    CONNECTING = "connecting"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"


class DownloadProgress:
    def __init__(self) -> None:
        self.state: str = DownloadState.IDLE
        self.current_file: str = ""
        self.current_file_index: int = 0
        self.total_files: int = 0
        self.file_downloaded_bytes: int = 0
        self.file_total_bytes: int = 0
        self.total_downloaded_bytes: int = 0
        self.grand_total_bytes: int = 0
        self.speed_bps: float = 0.0
        self.eta_seconds: float = 0.0
        self.error_message: str = ""
        self.overall_percent: float = 0.0


class ModelDownloader:
    """
    Downloads model files sequentially with resume capability and SHA256 integrity verification.
    """

    def __init__(
        self,
        catalog_item: ModelCatalogItem,
        destination_dir: Path,
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
        chunk_size: int = 128 * 1024,  # 128 KB
    ) -> None:
        self.catalog_item = catalog_item
        self.destination_dir = destination_dir
        self.progress_callback = progress_callback
        self.chunk_size = chunk_size

        self._is_paused = False
        self._is_cancelled = False
        self.progress = DownloadProgress()

        # Calculate grand total expected bytes
        self.progress.grand_total_bytes = sum(f.size_bytes for f in self.catalog_item.files)
        self.progress.total_files = len(self.catalog_item.files)

    def pause(self) -> None:
        self._is_paused = True
        self.progress.state = DownloadState.PAUSED
        self._notify()

    def resume(self) -> None:
        self._is_paused = False
        self.progress.state = DownloadState.DOWNLOADING
        self._notify()

    def cancel(self) -> None:
        self._is_cancelled = True
        self.progress.state = DownloadState.CANCELLED
        self._notify()

    def _notify(self) -> None:
        if self.progress_callback:
            try:
                self.progress_callback(self.progress)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")

    def download(self) -> bool:
        """
        Executes the download process. Blocks the calling thread (should be run in QThread / Worker).
        Returns True if successful and verified, False otherwise.
        """
        self.destination_dir.mkdir(parents=True, exist_ok=True)
        self._is_cancelled = False
        self._is_paused = False

        # Compute already downloaded bytes across completed files
        completed_bytes = 0
        for f in self.catalog_item.files:
            target_path = self.destination_dir / f.filename
            if target_path.exists() and target_path.stat().st_size == f.size_bytes:
                completed_bytes += f.size_bytes

        self.progress.total_downloaded_bytes = completed_bytes

        session = requests.Session()
        session.headers.update({
            "User-Agent": "OfflineWindowsTranslator/1.0",
        })

        for idx, file_info in enumerate(self.catalog_item.files):
            if self._is_cancelled:
                self.progress.state = DownloadState.CANCELLED
                self._notify()
                return False

            self.progress.current_file_index = idx + 1
            self.progress.current_file = file_info.filename
            self.progress.file_total_bytes = file_info.size_bytes

            final_file = self.destination_dir / file_info.filename
            part_file = self.destination_dir / f"{file_info.filename}.part"

            # Check if file is already completely downloaded and matches size
            if final_file.exists() and final_file.stat().st_size == file_info.size_bytes:
                logger.info(f"File {file_info.filename} is already present and matches expected size.")
                continue

            success = self._download_single_file(session, file_info, final_file, part_file)
            if not success:
                return False

        # Post-download verification of checksums
        self.progress.state = DownloadState.VERIFYING
        self._notify()

        for file_info in self.catalog_item.files:
            if not file_info.sha256:
                continue
            final_file = self.destination_dir / file_info.filename
            if not final_file.exists():
                self.progress.state = DownloadState.FAILED
                self.progress.error_message = f"الملف المكتمل مفقود: {file_info.filename}"
                self._notify()
                return False

            logger.info(f"Verifying checksum for {file_info.filename}...")
            actual_hash = compute_file_sha256(final_file)
            if actual_hash.lower() != file_info.sha256.lower():
                self.progress.state = DownloadState.CORRUPTED if hasattr(DownloadState, "CORRUPTED") else DownloadState.FAILED
                self.progress.error_message = (
                    f"فشل التحقق من سلامة الملف {file_info.filename}. شفرة SHA256 غير متطابقة."
                )
                self._notify()
                return False

        self.progress.state = DownloadState.COMPLETED
        self.progress.overall_percent = 100.0
        self.progress.speed_bps = 0
        self.progress.eta_seconds = 0
        self._notify()
        return True

    def _download_single_file(
        self,
        session: requests.Session,
        file_info: ModelFileInfo,
        final_file: Path,
        part_file: Path,
    ) -> bool:
        """Downloads a single file with resume support."""
        existing_size = part_file.stat().st_size if part_file.exists() else 0
        headers = {}
        write_mode = "wb"

        if existing_size > 0:
            if existing_size == file_info.size_bytes:
                # Already fully downloaded in .part
                part_file.replace(final_file)
                return True
            if existing_size < file_info.size_bytes:
                headers["Range"] = f"bytes={existing_size}-"
                write_mode = "ab"
            else:
                # Corrupted part file larger than expected
                existing_size = 0
                part_file.unlink(missing_ok=True)

        self.progress.state = DownloadState.CONNECTING
        self._notify()

        try:
            response = session.get(file_info.url, headers=headers, stream=True, timeout=15)
        except Exception as e:
            self.progress.state = DownloadState.FAILED
            self.progress.error_message = f"فشل الاتصال بالخادم لتحميل {file_info.filename}: {e}"
            self._notify()
            return False

        # If server does not support 206 Partial Content, reset to beginning
        if response.status_code == 200 and existing_size > 0:
            existing_size = 0
            write_mode = "wb"
        elif response.status_code not in (200, 206):
            self.progress.state = DownloadState.FAILED
            self.progress.error_message = f"استجابة غير صالحة من الخادم ({response.status_code}) لـ {file_info.filename}"
            self._notify()
            return False

        self.progress.state = DownloadState.DOWNLOADING
        downloaded_in_file = existing_size

        speed_samples: List[float] = []
        last_time = time.time()
        bytes_since_last_sample = 0

        try:
            with open(part_file, write_mode) as f:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    while self._is_paused and not self._is_cancelled:
                        time.sleep(0.3)

                    if self._is_cancelled:
                        self.progress.state = DownloadState.CANCELLED
                        self._notify()
                        return False

                    if not chunk:
                        continue

                    f.write(chunk)
                    chunk_len = len(chunk)
                    downloaded_in_file += chunk_len
                    bytes_since_last_sample += chunk_len
                    self.progress.file_downloaded_bytes = downloaded_in_file

                    # Calculate total progress
                    now = time.time()
                    elapsed = now - last_time
                    if elapsed >= 0.5:
                        speed = bytes_since_last_sample / elapsed
                        speed_samples.append(speed)
                        if len(speed_samples) > 5:
                            speed_samples.pop(0)
                        avg_speed = sum(speed_samples) / len(speed_samples)
                        self.progress.speed_bps = avg_speed

                        # Overall calculation
                        # Prior completed files + current file downloaded
                        current_total_done = (
                            self.progress.total_downloaded_bytes
                            - (existing_size if write_mode == "ab" else 0)
                            + downloaded_in_file
                        )
                        remaining_bytes = max(0, self.progress.grand_total_bytes - current_total_done)
                        self.progress.eta_seconds = remaining_bytes / avg_speed if avg_speed > 0 else 0
                        self.progress.overall_percent = min(
                            99.9,
                            (current_total_done / self.progress.grand_total_bytes * 100.0)
                            if self.progress.grand_total_bytes > 0
                            else 0.0,
                        )

                        last_time = now
                        bytes_since_last_sample = 0
                        self._notify()

        except Exception as e:
            self.progress.state = DownloadState.FAILED
            self.progress.error_message = f"انقطع التنزيل أثناء تحميل {file_info.filename}: {e}"
            self._notify()
            return False

        # Finished downloading this file: atomically move .part to final
        if part_file.exists():
            part_file.replace(final_file)
        self.progress.total_downloaded_bytes += (downloaded_in_file - existing_size)
        return True
