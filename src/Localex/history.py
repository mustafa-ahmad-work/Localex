"""
History service layer connecting the translation workflow to the local SQLite database.
Handles retention policies, search, filtering, and export/import operations.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from Localex.database import DatabaseManager
from Localex.paths import default_paths

logger = logging.getLogger(__name__)


class HistoryService:
    """
    Coordinates translation recording and history management according to user preferences.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None) -> None:
        self.db = db_manager or DatabaseManager()

    def record_translation(
        self,
        source_text: str,
        translated_text: str,
        source_lang: str,
        target_lang: str,
        model_name: str = "",
        enabled: bool = True,
    ) -> Optional[int]:
        if not enabled or not source_text.strip() or not translated_text.strip():
            return None

        try:
            return self.db.add_translation(
                source_text=source_text,
                translated_text=translated_text,
                source_lang=source_lang,
                target_lang=target_lang,
                model_name=model_name,
            )
        except Exception as e:
            logger.error(f"Failed to record translation into history: {e}")
            return None

    def get_items(
        self,
        query: Optional[str] = None,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        return self.db.get_translations(
            search_query=query,
            source_lang=source_lang,
            target_lang=target_lang,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
        )

    def count(self, query: Optional[str] = None) -> int:
        return self.db.count_translations(query)

    def delete_item(self, item_id: int) -> bool:
        return self.db.delete_translation(item_id)

    def clear(self) -> None:
        self.db.clear_all()

    def enforce_retention(self, days: int) -> int:
        if days > 0:
            return self.db.prune_older_than(days)
        return 0

    def export_csv(self, file_path: Path | str) -> int:
        return self.db.export_to_csv(file_path)

    def export_txt(self, file_path: Path | str) -> int:
        return self.db.export_to_txt(file_path)

    def import_csv(self, file_path: Path | str) -> int:
        return self.db.import_from_csv(file_path)


default_history_service = HistoryService()
