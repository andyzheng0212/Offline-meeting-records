"""Policy database management using SQLite FTS5."""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from pdfminer.high_level import extract_text
from docx import Document  # type: ignore

SECTION_PATTERN = re.compile(r"(第[一二三四五六七八九十百千0-9]+条|Chapter\s+\d+|条款\s*\d+)")


@dataclass
class PolicyConfig:
    policy_source_dir: Path
    policy_db_path: Path
    snippet_length: int
    top_k: int


class PolicyDatabase:
    """Manage policy import and search operations."""

    def __init__(self, config: PolicyConfig) -> None:
        self.config = config
        self.config.policy_source_dir.mkdir(parents=True, exist_ok=True)
        self.config.policy_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.config.policy_db_path)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.fts_available = True
        self._last_errors: List[str] = []
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS policies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                section TEXT,
                source TEXT,
                content TEXT
            )
            """
        )
        try:
            cur.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS policies_fts USING fts5(
                    title, section, content, content='policies', content_rowid='id'
                )
                """
            )
        except sqlite3.OperationalError:
            # FTS5 may be unavailable in some SQLite builds (e.g. custom/minimal builds)
            self.fts_available = False
        cur.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS policies_fts USING fts5(
                title, section, content, content='policies', content_rowid='id'
            )
            """
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def import_sources(self) -> int:
        files = list(self.config.policy_source_dir.glob("**/*"))
        entries: List[Tuple[str, str, str, str]] = []
        self._last_errors = []
        for file in files:
            if not file.is_file():
                continue
            try:
                if file.suffix.lower() == ".pdf":
                    text = extract_text(str(file))
                elif file.suffix.lower() == ".docx":
                    text = self._extract_docx(file)
                else:
                    continue
                entries.extend(self._split_sections(file.stem, file.name, text))
            except Exception as exc:  # pylint: disable=broad-except
                message = f"{file.name}: {exc}"
                print(f"[PolicyDB] 导入失败 {message}")
                self._last_errors.append(message)
        with self.conn:
            self.conn.execute("DELETE FROM policies")
            if self.fts_available:
                try:
                    self.conn.execute("DELETE FROM policies_fts")
                except sqlite3.OperationalError:
                    self.fts_available = False
            self.conn.executemany(
                "INSERT INTO policies(title, section, source, content) VALUES (?, ?, ?, ?)", entries
            )
            if self.fts_available:
                try:
                    self.conn.execute("INSERT INTO policies_fts(policies_fts) VALUES('rebuild')")
                except sqlite3.OperationalError:
                    self.fts_available = False
        return len(entries)

    def pop_last_errors(self) -> List[str]:
        errors = list(self._last_errors)
        self._last_errors.clear()
        return errors

        for file in files:
            if file.suffix.lower() == ".pdf":
                text = extract_text(str(file))
            elif file.suffix.lower() == ".docx":
                text = self._extract_docx(file)
            else:
                continue
            entries.extend(self._split_sections(file.stem, file.name, text))
        with self.conn:
            self.conn.execute("DELETE FROM policies")
            self.conn.execute("DELETE FROM policies_fts")
            self.conn.executemany(
                "INSERT INTO policies(title, section, source, content) VALUES (?, ?, ?, ?)", entries
            )
            self.conn.execute("INSERT INTO policies_fts(policies_fts) VALUES('rebuild')")
        return len(entries)

    def _extract_docx(self, path: Path) -> str:
        doc = Document(str(path))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)

    def _split_sections(self, title: str, source: str, text: str) -> List[Tuple[str, str, str, str]]:
        sections: List[Tuple[str, str, str, str]] = []
        chunks = self._chunk_text(text)
        for idx, chunk in enumerate(chunks, start=1):
            section_title = chunk[0]
            content = chunk[1]
            sections.append((title, section_title, source, content))
        return sections

    def _chunk_text(self, text: str) -> List[Tuple[str, str]]:
        matches = list(SECTION_PATTERN.finditer(text))
        chunks: List[Tuple[str, str]] = []
        if not matches:
            length = self.config.snippet_length
            for idx in range(0, len(text), length):
                snippet = text[idx : idx + length]
                if snippet.strip():
                    chunks.append((f"段落{idx // length + 1}", snippet))
            return chunks

        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            title = match.group(0)
            snippet = text[start:end].strip()
            if snippet:
                chunks.append((title, snippet))
        return chunks

    def search(self, query: str) -> List[dict]:
        if not query.strip():
            return []
        snippet_length = self.config.snippet_length
        try:
            if self.fts_available:
                sql = (
                    "SELECT p.title, p.section, p.source, "
                    "snippet(policies_fts, 2, '[', ']', '...', ?) as snippet "
                    "FROM policies_fts JOIN policies p ON p.id = policies_fts.rowid "
                    "WHERE policies_fts MATCH ? LIMIT ?"
                )
                cursor = self.conn.execute(sql, (snippet_length, query, self.config.top_k))
            else:
                raise sqlite3.OperationalError
        except sqlite3.OperationalError:
            like_query = f"%{query.strip()}%"
            cursor = self.conn.execute(
                "SELECT title, section, source, substr(content, 1, ?) as snippet "
                "FROM policies WHERE content LIKE ? OR title LIKE ? OR section LIKE ? LIMIT ?",
                (snippet_length, like_query, like_query, like_query, self.config.top_k),
            )
        sql = (
            "SELECT p.title, p.section, p.source, "
            "snippet(policies_fts, 2, '[', ']', '...', ?) as snippet "
            "FROM policies_fts JOIN policies p ON p.id = policies_fts.rowid "
            "WHERE policies_fts MATCH ? LIMIT ?"
        )
        cursor = self.conn.execute(sql, (snippet_length, query, self.config.top_k))
        results = []
        for row in cursor.fetchall():
            results.append(
                {
                    "title": row[0],
                    "section": row[1],
                    "source": row[2],
                    "snippet": row[3],
                }
            )
        return results


def build_policy_db(config: dict, base_path: Path) -> PolicyDatabase:
    paths = config["paths"]
    policy_cfg = config["policy"]
    db_path = base_path / paths["policy_db_dir"] / policy_cfg["database_name"]
    source_dir = base_path / paths["policy_source_dir"]
    policy_config = PolicyConfig(
        policy_source_dir=source_dir,
        policy_db_path=db_path,
        snippet_length=policy_cfg["snippet_length"],
        top_k=policy_cfg["top_k"],
    )
    return PolicyDatabase(policy_config)
