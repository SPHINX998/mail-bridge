from __future__ import annotations

from mail_bridge.models import ClassificationResult, StoredMessageRecord, utc_now
from mail_bridge.store import StateStore


def test_store_deduplicates_by_dedupe_key(tmp_path) -> None:
    store = StateStore(tmp_path / "state.db")
    first = StoredMessageRecord(
        gmail_message_id="msg-1",
        dedupe_key="internet:<abc@test>",
        source_mailbox="ggyeluiyu+outlook@gmail.com",
        subject="合同今天截止",
        notified=True,
        created_at=utc_now(),
        classification=ClassificationResult(important=True, score=80, category="deadline"),
    )
    second = StoredMessageRecord(
        gmail_message_id="msg-2",
        dedupe_key="internet:<abc@test>",
        source_mailbox="ggyeluiyu+outlook@gmail.com",
        subject="合同今天截止",
        notified=True,
        created_at=utc_now(),
        classification=ClassificationResult(important=True, score=80, category="deadline"),
    )
    assert store.record_processed_message(first) is True
    assert store.record_processed_message(second) is False
