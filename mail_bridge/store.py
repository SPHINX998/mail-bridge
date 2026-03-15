from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from threading import Lock

from mail_bridge.models import StoredMessageRecord, WatchState, utc_now


class StateStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS watch_state (
                    email TEXT PRIMARY KEY,
                    cursor_history_id TEXT,
                    watch_history_id TEXT,
                    expiration_epoch_ms INTEGER,
                    updated_at TEXT NOT NULL,
                    last_renewed_at TEXT,
                    last_error TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_messages (
                    gmail_message_id TEXT PRIMARY KEY,
                    dedupe_key TEXT NOT NULL UNIQUE,
                    source_mailbox TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    notified INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    classification_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS pubsub_events (
                    pubsub_message_id TEXT PRIMARY KEY,
                    history_id TEXT NOT NULL,
                    received_at TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def get_watch_state(self, email: str) -> WatchState | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                """
                SELECT email, cursor_history_id, watch_history_id, expiration_epoch_ms,
                       updated_at, last_renewed_at, last_error
                FROM watch_state
                WHERE email = ?
                """,
                (email,),
            ).fetchone()
        if row is None:
            return None
        return WatchState(
            email=row["email"],
            cursor_history_id=row["cursor_history_id"],
            watch_history_id=row["watch_history_id"],
            expiration_epoch_ms=row["expiration_epoch_ms"],
            updated_at=datetime.fromisoformat(row["updated_at"]),
            last_renewed_at=None
            if not row["last_renewed_at"]
            else datetime.fromisoformat(row["last_renewed_at"]),
            last_error=row["last_error"],
        )

    def save_watch_state(self, state: WatchState) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO watch_state (
                    email, cursor_history_id, watch_history_id, expiration_epoch_ms,
                    updated_at, last_renewed_at, last_error
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(email) DO UPDATE SET
                    cursor_history_id = excluded.cursor_history_id,
                    watch_history_id = excluded.watch_history_id,
                    expiration_epoch_ms = excluded.expiration_epoch_ms,
                    updated_at = excluded.updated_at,
                    last_renewed_at = excluded.last_renewed_at,
                    last_error = excluded.last_error
                """,
                (
                    state.email,
                    state.cursor_history_id,
                    state.watch_history_id,
                    state.expiration_epoch_ms,
                    state.updated_at.isoformat(),
                    None if state.last_renewed_at is None else state.last_renewed_at.isoformat(),
                    state.last_error,
                ),
            )
            connection.commit()

    def update_cursor_history_id(self, email: str, cursor_history_id: str) -> None:
        state = self.get_watch_state(email)
        updated_state = WatchState(
            email=email,
            cursor_history_id=cursor_history_id,
            watch_history_id=None if state is None else state.watch_history_id,
            expiration_epoch_ms=None if state is None else state.expiration_epoch_ms,
            updated_at=utc_now(),
            last_renewed_at=None if state is None else state.last_renewed_at,
            last_error=None if state is None else state.last_error,
        )
        self.save_watch_state(updated_state)

    def mark_watch_error(self, email: str, error_text: str) -> None:
        state = self.get_watch_state(email)
        updated_state = WatchState(
            email=email,
            cursor_history_id=None if state is None else state.cursor_history_id,
            watch_history_id=None if state is None else state.watch_history_id,
            expiration_epoch_ms=None if state is None else state.expiration_epoch_ms,
            updated_at=utc_now(),
            last_renewed_at=None if state is None else state.last_renewed_at,
            last_error=error_text,
        )
        self.save_watch_state(updated_state)

    def record_pubsub_event(self, pubsub_message_id: str, history_id: str) -> bool:
        with self._lock, self._connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO pubsub_events (pubsub_message_id, history_id, received_at)
                    VALUES (?, ?, ?)
                    """,
                    (pubsub_message_id, history_id, utc_now().isoformat()),
                )
                connection.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def record_processed_message(self, record: StoredMessageRecord) -> bool:
        with self._lock, self._connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO processed_messages (
                        gmail_message_id, dedupe_key, source_mailbox, subject,
                        notified, created_at, classification_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.gmail_message_id,
                        record.dedupe_key,
                        record.source_mailbox,
                        record.subject,
                        1 if record.notified else 0,
                        record.created_at.isoformat(),
                        json.dumps(record.classification.to_json(), ensure_ascii=False),
                    ),
                )
                connection.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def is_message_processed(self, gmail_message_id: str, dedupe_key: str) -> bool:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM processed_messages
                WHERE gmail_message_id = ? OR dedupe_key = ?
                LIMIT 1
                """,
                (gmail_message_id, dedupe_key),
            ).fetchone()
        return row is not None

    def mark_message_notified(self, gmail_message_id: str) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                UPDATE processed_messages
                SET notified = 1
                WHERE gmail_message_id = ?
                """,
                (gmail_message_id,),
            )
            connection.commit()
