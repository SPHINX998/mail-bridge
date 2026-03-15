from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from mail_bridge.classifier import OpenClawCliClassifier
from mail_bridge.config import Settings
from mail_bridge.models import MailItem
from mail_bridge.openclaw_cli import extract_json_object
from mail_bridge.rules import RulesStore


def build_settings(tmp_path: Path) -> Settings:
    return Settings(
        gmail_user_email="demo@gmail.com",
        gmail_watch_topic_name="projects/demo/topics/mail-bridge",
        gmail_oauth_client_file=tmp_path / "credentials.json",
        gmail_oauth_token_file=tmp_path / "token.json",
        state_db_path=tmp_path / "state.db",
        memento_rules_file=tmp_path / "rules.json",
        notifier_mode="noop",
        openclaw_command="python",
    )


def build_mail_item() -> MailItem:
    return MailItem(
        gmail_message_id="1",
        gmail_thread_id="t1",
        internet_message_id="<abc@test>",
        source_mailbox="demo+outlook@gmail.com",
        from_header="Boss <boss@example.com>",
        to_header="demo@gmail.com",
        subject="合同今天截止",
        snippet="请今天确认合同",
        body_preview="需要今天下班前确认并回复。",
        attachment_names=["合同终稿.pdf"],
        label_ids=["INBOX"],
        internal_timestamp=datetime.now(timezone.utc),
        history_id="100",
    )


def test_openclaw_classifier_builds_structured_result(tmp_path: Path) -> None:
    settings = build_settings(tmp_path)
    rules_store = RulesStore(settings.memento_rules_file, "你看着办")
    classifier = OpenClawCliClassifier(settings, rules_store)
    result = classifier._build_result(
        build_mail_item(),
        {
            "important": True,
            "score": 91,
            "category": "deadline",
            "reason": ["老板邮件", "今天截止"],
            "qq_text": "重要邮件：王总 / 今天内确认合同终稿",
            "summary": "王总发来合同终稿，需要今天内确认。",
            "body_excerpt": "请今天下班前确认并回复。",
            "send_mode": "summary",
            "needs_action": True,
            "deadline_hint": "今天",
            "memory_hints": ["老板合同邮件通常重要"],
        },
    )
    assert result.important is True
    assert result.score == 91
    assert result.category == "deadline"
    assert result.summary == "王总发来合同终稿，需要今天内确认。"
    assert result.body_excerpt == "请今天下班前确认并回复。"
    assert result.send_mode == "summary"
    assert result.needs_action is True
    assert result.deadline_hint == "今天"
    assert result.memory_hints == ["老板合同邮件通常重要"]


def test_openclaw_classifier_builds_default_qq_text_when_missing(tmp_path: Path) -> None:
    settings = build_settings(tmp_path)
    rules_store = RulesStore(settings.memento_rules_file, "你看着办")
    classifier = OpenClawCliClassifier(settings, rules_store)
    result = classifier._build_result(
        build_mail_item(),
        {
            "important": True,
            "score": 77,
            "category": "important",
            "reason": ["需要今天确认"],
            "qq_text": "",
            "summary": "",
            "body_excerpt": "",
            "send_mode": "brief",
            "needs_action": True,
            "deadline_hint": "今天",
            "memory_hints": [],
        },
    )
    assert result.qq_text.startswith("重要邮件：")


def test_openclaw_classifier_sends_structured_input(tmp_path: Path) -> None:
    settings = build_settings(tmp_path)
    rules_store = RulesStore(settings.memento_rules_file, "你看着办")
    classifier = OpenClawCliClassifier(settings, rules_store)

    class StubClient:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        def run_agent_json(
            self,
            prompt: str,
            input_payload: dict[str, object] | None = None,
            session_id: str | None = None,
        ) -> dict[str, object]:
            self.calls.append(
                {
                    "prompt": prompt,
                    "input_payload": input_payload,
                    "session_id": session_id,
                }
            )
            return {
                "important": True,
                "score": 90,
                "category": "deadline",
                "reason": ["老板邮件", "今天截止"],
                "qq_text": "重要邮件：王总 / 今天内确认合同终稿",
                "summary": "王总发来合同终稿，需要今天内确认。",
                "body_excerpt": "请今天下班前确认并回复。",
                "send_mode": "summary",
                "needs_action": True,
                "deadline_hint": "今天",
                "memory_hints": ["老板合同邮件通常重要"],
            }

    stub = StubClient()
    classifier.client = stub

    result = classifier.classify(build_mail_item())

    assert result.important is True
    assert len(stub.calls) == 1
    call = stub.calls[0]
    input_payload = call["input_payload"]
    assert isinstance(input_payload, dict)
    assert input_payload["mail"]["subject"] == "合同今天截止"
    assert input_payload["mail"]["from"] == "Boss <boss@example.com>"
    assert input_payload["user_policy_note"] == "你看着办"
    assert input_payload["notes"] == []
    assert call["session_id"] == settings.openclaw_session_id
    assert "严格只返回一个 JSON 对象" in str(call["prompt"])
    assert "send_mode" in str(call["prompt"])


def test_notification_rendering_uses_summary_mode() -> None:
    from mail_bridge.models import ClassificationResult

    result = ClassificationResult(
        important=True,
        qq_text="🚨 重要邮件：王总 / 合同终稿 / 今天18:00前确认",
        summary="王总要你在今天18:00前确认合同终稿。",
        body_excerpt="请在今天18:00前确认合同终稿并回复审批意见。",
        send_mode="summary",
    )
    assert result.render_notification_text() == (
        "🚨 重要邮件：王总 / 合同终稿 / 今天18:00前确认\n"
        "摘要：王总要你在今天18:00前确认合同终稿。"
    )


def test_extract_json_object_supports_fenced_json() -> None:
    payload = """
```json
{"important": true, "score": 88, "qq_text": "重要邮件"}
```
    """.strip()
    data = extract_json_object(payload)
    assert data["important"] is True
    assert data["score"] == 88
