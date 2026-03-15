from __future__ import annotations

import pytest

from mail_bridge.preferences import build_preference_note


def test_build_preference_note_for_sender_always_notify() -> None:
    note = build_preference_note(
        scope="sender",
        value="王总",
        action="always_notify",
        reason="老板邮件通常需要立即处理",
    )
    assert note == "来自“王总”的邮件必须提醒。原因：老板邮件通常需要立即处理"


def test_build_preference_note_for_topic_summary() -> None:
    note = build_preference_note(
        scope="topic",
        value="付款审批",
        action="summary",
    )
    assert note == "主题涉及“付款审批”的邮件提醒时默认发摘要"


def test_build_preference_note_rejects_empty_value() -> None:
    with pytest.raises(ValueError, match="value 不能为空"):
        build_preference_note(scope="topic", value="   ", action="summary")
