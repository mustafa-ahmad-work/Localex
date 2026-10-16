"""
PySide6 worker threads for asynchronous operations (Translation, Download, File Translation, Verification).
Guarantees responsive UI and safe cross-thread communication via Qt Signals.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QObject, QThread, Signal

from Localex.download_manager import DownloadProgress, ModelDownloader
from Localex.model_manager import ModelManager
from Localex.translator import TranslationEngine, TranslationResult

logger = logging.getLogger(__name__)


class TranslationWorker(QThread):
    """
    Executes model inference in a dedicated background thread.
    """
    translation_started = Signal()
    translation_finished = Signal(object)  # TranslationResult
    translation_failed = Signal(str)

    def __init__(
        self,
        engine: TranslationEngine,
        text: str,
        source_lang: str = "auto",
        target_lang: str = "ar",
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.engine = engine
        self.text = text
        self.source_lang = source_lang
        self.target_lang = target_lang

    def run(self) -> None:
        self.translation_started.emit()
        try:
            result = self.engine.translate(
                text=self.text,
                source_lang=self.source_lang,
                target_lang=self.target_lang,
            )
            self.translation_finished.emit(result)
        except Exception as e:
            logger.error(f"Worker translation failed: {e}")
            self.translation_failed.emit(str(e))


class DownloadWorker(QThread):
    """
    Executes chunked resumable downloads in a background thread.
    """
    progress_changed = Signal(object)  # DownloadProgress
    download_finished = Signal(bool)
    download_failed = Signal(str)

    def __init__(
        self,
        downloader: ModelDownloader,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.downloader = downloader
        # Wire callback to Qt signal emission
        self.downloader.progress_callback = self._on_progress

    def _on_progress(self, progress: DownloadProgress) -> None:
        self.progress_changed.emit(progress)

    def run(self) -> None:
        try:
            success = self.downloader.download()
            if success:
                self.download_finished.emit(True)
            else:
                if self.downloader.progress.error_message:
                    self.download_failed.emit(self.downloader.progress.error_message)
                else:
                    self.download_finished.emit(False)
        except Exception as e:
            logger.error(f"Download thread error: {e}")
            self.download_failed.emit(str(e))

    def pause(self) -> None:
        self.downloader.pause()

    def resume(self) -> None:
        self.downloader.resume()

    def cancel(self) -> None:
        self.downloader.cancel()


class FileTranslationWorker(QThread):
    """
    Translates TXT, Markdown, and CSV files chunk by chunk without modifying the original file.
    """
    progress_updated = Signal(int, int)  # current, total
    preview_ready = Signal(str)
    file_finished = Signal(str)  # output file path
    file_failed = Signal(str)

    def __init__(
        self,
        engine: TranslationEngine,
        input_file: Path,
        output_file: Path,
        source_lang: str = "auto",
        target_lang: str = "ar",
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.engine = engine
        self.input_file = Path(input_file)
        self.output_file = Path(output_file)
        self.source_lang = source_lang
        self.target_lang = target_lang
        self._is_cancelled = False

    def cancel(self) -> None:
        self._is_cancelled = True

    def run(self) -> None:
        try:
            ext = self.input_file.suffix.lower()
            if ext in (".txt", ".md", ".markdown", ".text"):
                self._translate_text_file()
            elif ext == ".csv":
                self._translate_csv_file()
            else:
                self.file_failed.emit(f"صيغة الملف غير مدعومة: {ext}")
        except Exception as e:
            logger.error(f"File translation error: {e}")
            self.file_failed.emit(str(e))

    def _read_with_fallback_encoding(self, file_path: Path) -> str:
        for enc in ("utf-8", "utf-8-sig", "cp1256", "cp1252", "latin1"):
            try:
                with open(file_path, "r", encoding=enc) as f:
                    return f.read()
            except (UnicodeDecodeError, OSError):
                continue
        raise ValueError(f"تعذر قراءة الملف {file_path.name}؛ تأكد من ترميز الملف.")

    def _translate_text_file(self) -> None:
        raw_text = self._read_with_fallback_encoding(self.input_file)
        if not raw_text.strip():
            self.file_failed.emit("الملف فارغ.")
            return

        paragraphs = raw_text.splitlines(keepends=True)
        total = len(paragraphs)
        translated_lines: List[str] = []

        for idx, line in enumerate(paragraphs):
            if self._is_cancelled:
                self.file_failed.emit("تم إلغاء عملية ترجمة الملف.")
                return

            if line.strip():
                res = self.engine.translate(
                    line.strip(),
                    source_lang=self.source_lang,
                    target_lang=self.target_lang,
                )
                end = "\r\n" if line.endswith("\r\n") else ("\n" if line.endswith("\n") else "")
                translated_lines.append(res.translated_text + end)
            else:
                translated_lines.append(line)

            self.progress_updated.emit(idx + 1, total)
            if idx == 0 or idx == 2:
                self.preview_ready.emit("".join(translated_lines[:3]))

        with open(self.output_file, "w", encoding="utf-8") as f:
            f.writelines(translated_lines)

        self.file_finished.emit(str(self.output_file))

    def _translate_csv_file(self) -> None:
        enc = "utf-8-sig"
        try:
            with open(self.input_file, "r", encoding=enc) as f:
                reader = list(csv.reader(f))
        except UnicodeDecodeError:
            with open(self.input_file, "r", encoding="cp1256") as f:
                reader = list(csv.reader(f))

        if not reader:
            self.file_failed.emit("ملف CSV فارغ.")
            return

        total = len(reader)
        translated_rows: List[List[str]] = []

        # Keep header as-is
        translated_rows.append(reader[0])
        self.progress_updated.emit(1, total)

        for idx, row in enumerate(reader[1:], start=1):
            if self._is_cancelled:
                self.file_failed.emit("تم إلغاء العملية.")
                return

            new_row = []
            for cell in row:
                if cell.strip():
                    res = self.engine.translate(
                        cell.strip(),
                        source_lang=self.source_lang,
                        target_lang=self.target_lang,
                    )
                    new_row.append(res.translated_text)
                else:
                    new_row.append(cell)

            translated_rows.append(new_row)
            self.progress_updated.emit(idx + 1, total)

        with open(self.output_file, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerows(translated_rows)

        self.file_finished.emit(str(self.output_file))
