from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib.parse import urlparse
from datetime import datetime, timezone

from utils.normalize import compute_text_hash


class SQLiteStore:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS guests (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE,
                created_at TEXT
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY,
                guest_id INTEGER,
                source_type TEXT,
                url TEXT,
                title TEXT,
                domain TEXT,
                video_id TEXT,
                comment_id TEXT,
                author TEXT,
                like_count INTEGER,
                reply_count INTEGER,
                published_at TEXT,
                text TEXT,
                text_hash TEXT,
                extra_json TEXT,
                UNIQUE(guest_id, source_type, url, comment_id, video_id, text_hash)
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY,
                guest_id INTEGER,
                link_type TEXT,
                url TEXT,
                title TEXT,
                UNIQUE(guest_id, link_type, url)
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS about_guest (
                guest_id INTEGER PRIMARY KEY,
                summary TEXT
            );
            """
        )
        self.conn.commit()

    def ensure_guest(self, name: str) -> int:
        cur = self.conn.cursor()
        cur.execute("INSERT OR IGNORE INTO guests(name, created_at) VALUES (?, ?)", (name, datetime.now(timezone.utc).isoformat()))
        self.conn.commit()
        cur.execute("SELECT id FROM guests WHERE name=?", (name,))
        row = cur.fetchone()
        return int(row[0])

    def upsert_records(self, guest_id: int, records: Iterable[Dict]) -> int:
        cur = self.conn.cursor()
        inserted = 0
        for r in records:
            source_type = r.get("source_type")
            url = r.get("url")
            title = r.get("title")
            video_id = r.get("video_id")
            comment_id = r.get("comment_id")
            author = r.get("author")
            like_count = r.get("like_count")
            reply_count = r.get("reply_count")
            published_at = r.get("published_at")
            text = r.get("text")
            text_hash = compute_text_hash(text) if text else None
            domain = urlparse(url).netloc if url else None
            extra = {k: v for k, v in r.items() if k not in {"source_type", "url", "title", "video_id", "comment_id", "author", "like_count", "reply_count", "published_at", "text"}}
            extra_json = json.dumps(extra, ensure_ascii=False) if extra else None
            try:
                cur.execute(
                    """
                    INSERT OR IGNORE INTO records
                    (guest_id, source_type, url, title, domain, video_id, comment_id, author, like_count, reply_count, published_at, text, text_hash, extra_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (guest_id, source_type, url, title, domain, video_id, comment_id, author, like_count, reply_count, published_at, text, text_hash, extra_json),
                )
                inserted += cur.rowcount
            except Exception:
                continue
        self.conn.commit()
        return inserted

    def upsert_links(self, guest_id: int, link_type: str, urls: List[str]) -> int:
        cur = self.conn.cursor()
        count = 0
        for u in urls:
            try:
                cur.execute("INSERT OR IGNORE INTO links(guest_id, link_type, url, title) VALUES (?, ?, ?, ?)", (guest_id, link_type, u, None))
                count += cur.rowcount
            except Exception:
                continue
        self.conn.commit()
        return count

    def upsert_about(self, guest_id: int, summary: Optional[str]) -> None:
        if not summary:
            return
        cur = self.conn.cursor()
        cur.execute("INSERT INTO about_guest(guest_id, summary) VALUES (?, ?) ON CONFLICT(guest_id) DO UPDATE SET summary=excluded.summary", (guest_id, summary))
        self.conn.commit()


