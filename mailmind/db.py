from __future__ import annotations

import sqlite3
import hashlib
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .models import EmailRecord, ExtractionResult
from .privacy import redact_log_message


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_attachment_id(
    email_id: str,
    filename: str,
    mime_type: str | None,
    size: int | None,
    occurrence: int = 0,
) -> str:
    material = f"{email_id}\0{filename}\0{mime_type or ''}\0{size or ''}\0{occurrence}"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]
    return f"att_{digest}"


class Database:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS emails (
                    id TEXT PRIMARY KEY,
                    sender TEXT NOT NULL,
                    subject TEXT,
                    received_at TEXT,
                    body TEXT DEFAULT '',
                    rag_indexed INTEGER DEFAULT 0,
                    rag_body_hash TEXT,
                    rag_chunk_count INTEGER,
                    rag_indexed_at TEXT,
                    processed INTEGER DEFAULT 0,
                    task_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
        try:
            with self.connect() as conn:
                conn.execute("ALTER TABLE emails ADD COLUMN body TEXT DEFAULT ''")
        except sqlite3.OperationalError as exc:
            if "duplicate column name" not in str(exc).lower():
                raise
        with self.connect() as conn:
            conn.executescript(
                """

                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    email_id TEXT NOT NULL,
                    description TEXT NOT NULL,
                    due_at TEXT,
                    priority TEXT CHECK(priority IN ('high','medium','low')),
                    requires_reply INTEGER DEFAULT 0,
                    needs_review INTEGER DEFAULT 0,
                    completed INTEGER DEFAULT 0,
                    notified_24h INTEGER DEFAULT 0,
                    notified_now INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(email_id) REFERENCES emails(id)
                );

                CREATE TABLE IF NOT EXISTS attachments (
                    id TEXT PRIMARY KEY,
                    email_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    mime_type TEXT,
                    gmail_attachment_id TEXT,
                    size INTEGER,
                    local_path TEXT,
                    index_status TEXT DEFAULT 'pending',
                    index_error TEXT,
                    indexed INTEGER DEFAULT 0,
                    chunk_count INTEGER,
                    indexed_at TEXT,
                    FOREIGN KEY(email_id) REFERENCES emails(id)
                );

                CREATE TABLE IF NOT EXISTS processing_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_id TEXT,
                    status TEXT NOT NULL,
                    message TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
        self._ensure_column("attachments", "local_path", "TEXT")
        self._ensure_column("attachments", "gmail_attachment_id", "TEXT")
        self._ensure_column("attachments", "size", "INTEGER")
        self._ensure_column("attachments", "index_status", "TEXT DEFAULT 'pending'")
        self._ensure_column("attachments", "index_error", "TEXT")
        self._ensure_column("emails", "rag_indexed", "INTEGER DEFAULT 0")
        self._ensure_column("emails", "rag_body_hash", "TEXT")
        self._ensure_column("emails", "rag_chunk_count", "INTEGER")
        self._ensure_column("emails", "rag_indexed_at", "TEXT")
        self._backfill_attachment_remote_ids()
        self._dedupe_attachments()

    def _ensure_column(self, table: str, column: str, definition: str) -> None:
        try:
            with self.connect() as conn:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        except sqlite3.OperationalError as exc:
            if "duplicate column name" not in str(exc).lower():
                raise

    def email_exists(self, email_id: str) -> bool:
        with self.connect() as conn:
            row = conn.execute("SELECT 1 FROM emails WHERE id = ?", (email_id,)).fetchone()
            return row is not None

    def _backfill_attachment_remote_ids(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE attachments
                SET gmail_attachment_id = id
                WHERE gmail_attachment_id IS NULL OR gmail_attachment_id = ''
                """
            )

    def _dedupe_attachments(self) -> None:
        with self.connect() as conn:
            self._dedupe_attachments_for_conn(conn)

    def _dedupe_attachments_for_conn(self, conn: sqlite3.Connection) -> None:
        duplicate_groups = conn.execute(
            """
            SELECT email_id, filename, COALESCE(mime_type, '') AS mime_type, COUNT(*) AS count
            FROM attachments
            GROUP BY email_id, filename, COALESCE(mime_type, '')
            HAVING COUNT(*) > 1
            """
        ).fetchall()
        for group in duplicate_groups:
            rows = conn.execute(
                """
                SELECT *
                FROM attachments
                WHERE email_id = ?
                  AND filename = ?
                  AND COALESCE(mime_type, '') = ?
                ORDER BY indexed DESC,
                         COALESCE(chunk_count, 0) DESC,
                         indexed_at DESC,
                         id ASC
                """,
                (group["email_id"], group["filename"], group["mime_type"]),
            ).fetchall()
            keep = rows[0]
            for duplicate in rows[1:]:
                if not keep["local_path"] and duplicate["local_path"]:
                    conn.execute(
                        "UPDATE attachments SET local_path = ? WHERE id = ?",
                        (duplicate["local_path"], keep["id"]),
                    )
                conn.execute("DELETE FROM attachments WHERE id = ?", (duplicate["id"],))

    def save_email(self, email: EmailRecord) -> bool:
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO emails (id, sender, subject, received_at, processed)
                VALUES (?, ?, ?, ?, 0)
                """,
                (
                    email.id,
                    email.sender,
                    email.subject,
                    email.received_at.isoformat() if email.received_at else None,
                ),
            )
            existing = conn.execute("SELECT body FROM emails WHERE id = ?", (email.id,)).fetchone()
            existing_body = existing["body"] if existing else None
            if existing_body != email.body:
                conn.execute(
                    """
                    UPDATE emails
                    SET body = ?, rag_indexed = 0, rag_body_hash = NULL,
                        rag_chunk_count = NULL, rag_indexed_at = NULL
                    WHERE id = ?
                    """,
                    (email.body, email.id),
                )
            seen_attachment_keys: dict[tuple[str, str, int | None], int] = {}
            for attachment in email.attachments:
                key = (attachment.filename, attachment.mime_type or "", attachment.size)
                occurrence = seen_attachment_keys.get(key, 0)
                seen_attachment_keys[key] = occurrence + 1
                stable_id = stable_attachment_id(email.id, attachment.filename, attachment.mime_type, attachment.size, occurrence)
                existing_attachment = conn.execute(
                    """
                    SELECT id
                    FROM attachments
                    WHERE email_id = ?
                      AND filename = ?
                      AND COALESCE(mime_type, '') = COALESCE(?, '')
                      AND (size = ? OR size IS NULL OR ? IS NULL)
                    ORDER BY indexed DESC,
                             COALESCE(chunk_count, 0) DESC,
                             indexed_at DESC,
                             id ASC
                    LIMIT 1
                    """,
                    (email.id, attachment.filename, attachment.mime_type, attachment.size, attachment.size),
                ).fetchone()
                attachment_row_id = existing_attachment["id"] if existing_attachment else stable_id
                conn.execute(
                    """
                    INSERT OR IGNORE INTO attachments (
                        id, email_id, filename, mime_type, gmail_attachment_id, size
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (attachment_row_id, email.id, attachment.filename, attachment.mime_type, attachment.id, attachment.size),
                )
                conn.execute(
                    """
                    UPDATE attachments
                    SET gmail_attachment_id = ?,
                        filename = ?,
                        mime_type = ?,
                        size = ?
                    WHERE id = ?
                    """,
                    (attachment.id, attachment.filename, attachment.mime_type, attachment.size, attachment_row_id),
                )
            self._dedupe_attachments_for_conn(conn)
            return cur.rowcount > 0

    def save_extraction(self, email_id: str, result: ExtractionResult) -> list[str]:
        task_ids: list[str] = []
        with self.connect() as conn:
            for task in result.tasks if result.has_action else []:
                task_id = str(uuid.uuid4())[:8]
                task_ids.append(task_id)
                conn.execute(
                    """
                    INSERT INTO tasks (
                        id, email_id, description, due_at, priority, requires_reply, needs_review
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task_id,
                        email_id,
                        task.description,
                        task.due_at.isoformat() if task.due_at else None,
                        task.priority.value,
                        int(task.requires_reply),
                        int(task.needs_review),
                    ),
                )
            conn.execute(
                "UPDATE emails SET processed = 1, task_count = ? WHERE id = ?",
                (len(task_ids), email_id),
            )
            conn.execute(
                "INSERT INTO processing_logs (email_id, status, message) VALUES (?, ?, ?)",
                (email_id, "processed", result.reason),
            )
        return task_ids

    def replace_extraction(self, email_id: str, result: ExtractionResult) -> list[str]:
        with self.connect() as conn:
            conn.execute("DELETE FROM tasks WHERE email_id = ?", (email_id,))
            conn.execute(
                "UPDATE emails SET processed = 0, task_count = 0 WHERE id = ?",
                (email_id,),
            )
        return self.save_extraction(email_id, result)

    def mark_tasks_for_review(self, email_id: str) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                "UPDATE tasks SET needs_review = 1 WHERE email_id = ? AND completed = 0",
                (email_id,),
            )
            return cur.rowcount

    def log(self, email_id: str | None, status: str, message: str) -> None:
        safe_message = redact_log_message(message)
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO processing_logs (email_id, status, message) VALUES (?, ?, ?)",
                (email_id, status, safe_message),
            )

    def list_tasks(
        self,
        include_completed: bool = False,
        search: str | None = None,
        sort: str = "newest",
        requires_reply: bool = False,
        reply_thread: bool = False,
        has_attachments: bool = False,
        needs_review: bool = False,
        due_only: bool = False,
    ) -> list[dict]:
        where = []
        params: list[str] = []
        if not include_completed:
            where.append("t.completed = 0")
        if search:
            where.append("LOWER(t.description) LIKE ?")
            params.append(f"%{search.lower()}%")
        if requires_reply:
            where.append("t.requires_reply = 1")
        if reply_thread:
            where.append(
                """
                (
                  LOWER(e.subject) LIKE 're:%'
                  OR LOWER(e.subject) LIKE 'fw:%'
                  OR LOWER(e.subject) LIKE 'fwd:%'
                  OR e.subject LIKE '回复:%'
                  OR e.subject LIKE '答复:%'
                )
                """
            )
        if needs_review:
            where.append("t.needs_review = 1")
        if due_only:
            where.append("t.due_at IS NOT NULL")
        if has_attachments:
            where.append("EXISTS (SELECT 1 FROM attachments a WHERE a.email_id = t.email_id)")
        sql_where = f"WHERE {' AND '.join(where)}" if where else ""
        order_by = {
            "newest": "e.received_at DESC, t.created_at DESC",
            "priority": """
                CASE t.priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
                e.received_at DESC,
                t.created_at DESC
            """,
            "due": "t.due_at IS NULL ASC, t.due_at ASC, e.received_at DESC",
            "oldest": "e.received_at ASC, t.created_at ASC",
        }.get(sort, "e.received_at DESC, t.created_at DESC")
        with self.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT t.*, e.sender, e.subject, e.received_at
                FROM tasks t
                JOIN emails e ON e.id = t.email_id
                {sql_where}
                ORDER BY t.completed ASC, {order_by}
                """,
                params,
            ).fetchall()
            return [dict(row) for row in rows]

    def list_tasks_by_ids(self, task_ids: list[str]) -> list[dict]:
        if not task_ids:
            return []
        placeholders = ",".join("?" for _ in task_ids)
        with self.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT t.*, e.sender, e.subject
                FROM tasks t
                JOIN emails e ON e.id = t.email_id
                WHERE t.id IN ({placeholders})
                ORDER BY t.due_at IS NULL ASC, t.due_at ASC, t.created_at DESC
                """,
                task_ids,
            ).fetchall()
            by_id = {row["id"]: dict(row) for row in rows}
            return [by_id[task_id] for task_id in task_ids if task_id in by_id]

    def list_due_tasks(self, until_iso: str) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT t.*, e.sender, e.subject
                FROM tasks t
                JOIN emails e ON e.id = t.email_id
                WHERE t.completed = 0 AND t.due_at IS NOT NULL AND t.due_at <= ?
                ORDER BY t.due_at ASC
                """,
                (until_iso,),
            ).fetchall()
            return [dict(row) for row in rows]

    def list_unnotified_24h(self, until_iso: str) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT t.*, e.sender, e.subject
                FROM tasks t
                JOIN emails e ON e.id = t.email_id
                WHERE t.completed = 0
                  AND t.due_at IS NOT NULL
                  AND t.due_at <= ?
                  AND t.notified_24h = 0
                ORDER BY t.due_at ASC
                """,
                (until_iso,),
            ).fetchall()
            return [dict(row) for row in rows]

    def mark_notified_24h(self, task_ids: list[str]) -> None:
        if not task_ids:
            return
        with self.connect() as conn:
            conn.executemany("UPDATE tasks SET notified_24h = 1 WHERE id = ?", [(tid,) for tid in task_ids])

    def mark_task_done(self, task_id: str) -> bool:
        with self.connect() as conn:
            cur = conn.execute("UPDATE tasks SET completed = 1 WHERE id = ?", (task_id,))
            return cur.rowcount > 0

    def list_emails(self) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, sender, subject, received_at, processed, task_count, created_at,
                       CASE WHEN body IS NULL OR body = '' THEN 0 ELSE 1 END AS has_body
                FROM emails
                ORDER BY received_at DESC, created_at DESC
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def list_emails_for_rag(self, changed_only: bool = True) -> list[dict]:
        where = "body IS NOT NULL AND TRIM(body) != ''"
        if changed_only:
            where += " AND COALESCE(rag_indexed, 0) = 0"
        with self.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, sender, subject, received_at, body
                FROM emails
                WHERE {where}
                ORDER BY received_at DESC, created_at DESC
                """
            ).fetchall()
            emails = [dict(row) for row in rows]
            for email in emails:
                attachments = conn.execute(
                    "SELECT filename FROM attachments WHERE email_id = ? ORDER BY filename",
                    (email["id"],),
                ).fetchall()
                email["attachment_filenames"] = [attachment["filename"] for attachment in attachments]
            return emails

    def mark_email_rag_indexed(self, email_id: str, body_hash: str, chunk_count: int) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE emails
                SET rag_indexed = 1,
                    rag_body_hash = ?,
                    rag_chunk_count = ?,
                    rag_indexed_at = ?
                WHERE id = ?
                """,
                (body_hash, chunk_count, utcnow(), email_id),
            )

    def email_body_stats(self) -> dict:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS emails_total,
                    SUM(CASE WHEN body IS NOT NULL AND TRIM(body) != '' THEN 1 ELSE 0 END) AS email_bodies,
                    SUM(CASE WHEN rag_indexed = 1 THEN 1 ELSE 0 END) AS indexed_email_bodies,
                    COALESCE(SUM(rag_chunk_count), 0) AS email_chunks
                FROM emails
                """
            ).fetchone()
            return dict(row)

    def get_email(self, email_id: str) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM emails WHERE id = ?", (email_id,)).fetchone()
            if not row:
                return None
            email = dict(row)
            attachments = conn.execute(
                "SELECT * FROM attachments WHERE email_id = ? ORDER BY filename",
                (email_id,),
            ).fetchall()
            email["attachments"] = [dict(attachment) for attachment in attachments]
            tasks = conn.execute(
                "SELECT * FROM tasks WHERE email_id = ? ORDER BY created_at DESC",
                (email_id,),
            ).fetchall()
            email["tasks"] = [dict(task) for task in tasks]
            return email

    def update_email_body(self, email_id: str, body: str) -> None:
        with self.connect() as conn:
            conn.execute("UPDATE emails SET body = ? WHERE id = ?", (body, email_id))

    def list_attachments(self) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT a.*, e.sender, e.subject, e.received_at
                FROM attachments a
                JOIN emails e ON e.id = a.email_id
                ORDER BY e.received_at DESC, a.filename ASC
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def list_pdf_attachments(self) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT a.*, e.sender, e.subject, e.received_at
                FROM attachments a
                JOIN emails e ON e.id = a.email_id
                WHERE LOWER(a.filename) LIKE '%.pdf'
                   OR LOWER(COALESCE(a.mime_type, '')) = 'application/pdf'
                ORDER BY e.received_at DESC, a.filename ASC
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def get_attachment(self, attachment_id: str) -> dict | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT a.*, e.sender, e.subject, e.received_at
                FROM attachments a
                JOIN emails e ON e.id = a.email_id
                WHERE a.id = ? OR a.gmail_attachment_id = ?
                """,
                (attachment_id, attachment_id),
            ).fetchone()
            return dict(row) if row else None

    def update_attachment_index(
        self,
        attachment_id: str,
        *,
        local_path: str | None = None,
        index_status: str,
        indexed: bool,
        chunk_count: int | None = None,
        index_error: str | None = None,
    ) -> None:
        indexed_at = utcnow() if indexed else None
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE attachments
                SET local_path = COALESCE(?, local_path),
                    index_status = ?,
                    indexed = ?,
                    chunk_count = ?,
                    indexed_at = ?,
                    index_error = ?
                WHERE id = ?
                """,
                (
                    local_path,
                    index_status,
                    int(indexed),
                    chunk_count,
                    indexed_at,
                    index_error,
                    attachment_id,
                ),
            )

    def attachment_stats(self) -> dict:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN LOWER(filename) LIKE '%.pdf'
                              OR LOWER(COALESCE(mime_type, '')) = 'application/pdf'
                             THEN 1 ELSE 0 END) AS pdfs,
                    SUM(CASE WHEN indexed = 1 THEN 1 ELSE 0 END) AS indexed,
                    COALESCE(SUM(chunk_count), 0) AS chunks
                FROM attachments
                """
            ).fetchone()
            return dict(row)

    def list_logs(self, limit: int = 100) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM processing_logs ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]
