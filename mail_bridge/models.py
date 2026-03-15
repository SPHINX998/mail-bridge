from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Literal


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class MailItem:
    gmail_message_id: str
    gmail_thread_id: str
    internet_message_id: str | None
    source_mailbox: str
    from_header: str
    to_header: str
    subject: str
    snippet: str
    body_preview: str
    attachment_names: list[str]
    label_ids: list[str]
    internal_timestamp: datetime
    history_id: str


@dataclass(slots=True)
class ClassificationResult:
    schema_version: str = "v2"
    important: bool = False
    score: int = 0
    category: str = "routine"
    reason: list[str] = field(default_factory=list)
    qq_text: str = ""
    summary: str = ""
    body_excerpt: str = ""
    send_mode: Literal["brief", "summary", "full_excerpt"] = "brief"
    needs_action: bool = False
    deadline_hint: str | None = None
    memory_hints: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    def render_notification_text(self) -> str:
        lines: list[str] = []
        lead_text = self.qq_text.strip()
        summary_text = self.summary.strip()
        excerpt_text = self.body_excerpt.strip()
        if lead_text:
            lines.append(lead_text)
        if self.send_mode in {"summary", "full_excerpt"} and summary_text:
            lines.append(f"摘要：{summary_text}")
        if self.send_mode == "full_excerpt" and excerpt_text:
            lines.append(f"片段：{excerpt_text}")
        return "\n".join(lines).strip()


@dataclass(slots=True)
class WatchState:
    email: str
    cursor_history_id: str | None
    watch_history_id: str | None
    expiration_epoch_ms: int | None
    updated_at: datetime
    last_renewed_at: datetime | None = None
    last_error: str | None = None

    def expiration_at(self) -> datetime | None:
        if self.expiration_epoch_ms is None:
            return None
        return datetime.fromtimestamp(self.expiration_epoch_ms / 1000, tz=timezone.utc)

    def needs_renewal(self, margin_hours: int) -> bool:
        expiration_at = self.expiration_at()
        if expiration_at is None:
            return True
        return expiration_at <= utc_now() + timedelta(hours=margin_hours)


@dataclass(slots=True)
class PubSubHistoryEvent:
    pubsub_message_id: str
    gmail_email: str
    history_id: str
    published_at: str | None = None


@dataclass(slots=True)
class ProcessOutcome:
    processed_count: int
    notified_count: int
    latest_history_id: str | None


@dataclass(slots=True)
class StoredMessageRecord:
    gmail_message_id: str
    dedupe_key: str
    source_mailbox: str
    subject: str
    notified: bool
    created_at: datetime
    classification: ClassificationResult
