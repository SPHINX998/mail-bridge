from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from mail_bridge.logging_utils import log_structured_event


def test_log_structured_event_outputs_json(caplog) -> None:
    logger = logging.getLogger("mail_bridge.tests.logging")
    with caplog.at_level(logging.INFO, logger=logger.name):
        log_structured_event(
            logger,
            "message_classified",
            gmail_message_id="abc123",
            important=True,
            internal_timestamp=datetime(2026, 3, 15, 2, 45, tzinfo=timezone.utc),
            reason=["deadline", "vip_sender"],
        )
    payload = json.loads(caplog.records[0].message)
    assert payload["event"] == "message_classified"
    assert payload["gmail_message_id"] == "abc123"
    assert payload["important"] is True
    assert payload["internal_timestamp"] == "2026-03-15T02:45:00+00:00"
    assert payload["reason"] == ["deadline", "vip_sender"]
