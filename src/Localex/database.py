"""
SQLite database manager for local translation history.
Provides privacy-first local storage, search, filtering, pruning, and export/import.
"""

from __future__ import annotations

import csv
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from Localex.paths import default_paths

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages SQLite database connections and operations for translation history.
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or default_paths.database_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS translations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_text TEXT NOT NULL,
                    translated_text TEXT NOT NULL,
                    source_lang TEXT NOT NULL,
                    target_lang TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    model_name TEXT,
                    char_count INTEGER,
                    is_favorite INTEGER DEFAULT 0
                )
            """)
            # Create indexes for search and filtering
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_translations_created ON translations(created_at DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_translations_langs ON translations(source_lang, target_lang)")
            conn.commit()

    def add_translation(
        self,
        source_text: str,
        translated_text: str,
        source_lang: str,
        target_lang: str,
        model_name: str = "",
        char_count: Optional[int] = None,
    ) -> int:
        if not source_text.strip():
            return -1
        if char_count is None:
            char_count = len(source_text)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO translations (source_text, translated_text, source_lang, target_lang, model_name, char_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_text,
                    translated_text,
                    source_lang,
                    target_lang,
                    model_name,
                    char_count,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            conn.commit()
            return cursor.lastrowid or -1

    def get_translations(
        self,
        search_query: Optional[str] = None,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        clauses = []
        params: List[Any] = []

        if search_query and search_query.strip():
            clauses.append("(source_text LIKE ? OR translated_text LIKE ?)")
            q = f"%{search_query.strip()}%"
            params.extend([q, q])

        if source_lang and source_lang != "all":
            clauses.append("source_lang = ?")
            params.append(source_lang)

        if target_lang and target_lang != "all":
            clauses.append("target_lang = ?")
            params.append(target_lang)

        if date_from:
            clauses.append("created_at >= ?")
            params.append(date_from)

        if date_to:
            clauses.append("created_at <= ?")
            params.append(date_to)

        where_stmt = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        query = f"""
            SELECT id, source_text, translated_text, source_lang, target_lang, created_at, model_name, char_count, is_favorite
            FROM translations
            {where_stmt}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def count_translations(self, search_query: Optional[str] = None) -> int:
        query = "SELECT COUNT(*) FROM translations"
        params: List[Any] = []
        if search_query and search_query.strip():
            query += " WHERE (source_text LIKE ? OR translated_text LIKE ?)"
            q = f"%{search_query.strip()}%"
            params.extend([q, q])

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            return row[0] if row else 0

    def delete_translation(self, item_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM translations WHERE id = ?", (item_id,))
            conn.commit()
            return cursor.rowcount > 0

    def clear_all(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM translations")
            conn.commit()

    def prune_older_than(self, days: int) -> int:
        if days <= 0:
            return 0
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM translations WHERE created_at < ?", (cutoff,))
            conn.commit()
            return cursor.rowcount

    def export_to_csv(self, file_path: Path | str) -> int:
        rows = self.get_translations(limit=100000)
        with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Source Lang", "Target Lang", "Source Text", "Translated Text", "Date", "Model"])
            for r in rows:
                writer.writerow([
                    r["id"],
                    r["source_lang"],
                    r["target_lang"],
                    r["source_text"],
                    r["translated_text"],
                    r["created_at"],
                    r.get("model_name", ""),
                ])
        return len(rows)

    def export_to_txt(self, file_path: Path | str) -> int:
        rows = self.get_translations(limit=100000)
        with open(file_path, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(f"[{r['created_at']}] ({r['source_lang']} -> {r['target_lang']})\n")
                f.write(f"Original:\n{r['source_text']}\n")
                f.write(f"Translation:\n{r['translated_text']}\n")
                f.write("-" * 50 + "\n\n")
        return len(rows)

    def import_from_csv(self, file_path: Path | str) -> int:
        count = 0
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                src_txt = row.get("Source Text") or row.get("source_text")
                tgt_txt = row.get("Translated Text") or row.get("translated_text")
                src_l = row.get("Source Lang") or row.get("source_lang", "auto")
                tgt_l = row.get("Target Lang") or row.get("target_lang", "ar")
                mdl = row.get("Model") or row.get("model_name", "imported")
                if src_txt and tgt_txt:
                    self.add_translation(src_txt, tgt_txt, src_l, tgt_l, mdl)
                    count += 1
        return count
