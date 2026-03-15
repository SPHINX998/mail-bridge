from __future__ import annotations

import json

from mail_bridge.service import parse_pubsub_message


def test_parse_pubsub_message() -> None:
    event = parse_pubsub_message(
        pubsub_message_id="123",
        data=json.dumps({"emailAddress": "demo@gmail.com", "historyId": "456"}).encode("utf-8"),
        published_at="2026-03-15T10:00:00Z",
    )
    assert event.pubsub_message_id == "123"
    assert event.gmail_email == "demo@gmail.com"
    assert event.history_id == "456"
