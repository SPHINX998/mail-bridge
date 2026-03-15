from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PreferenceScope = Literal["sender", "domain", "keyword", "topic", "pattern"]
PreferenceAction = Literal["always_notify", "never_notify", "brief", "summary", "full_excerpt"]

MAX_SCOPE_VALUE_LENGTH = 80
MAX_REASON_LENGTH = 120


@dataclass(slots=True)
class PreferenceRule:
    scope: PreferenceScope
    value: str
    action: PreferenceAction
    reason: str | None = None

    def to_note(self) -> str:
        return build_preference_note(
            scope=self.scope,
            value=self.value,
            action=self.action,
            reason=self.reason,
        )


def build_preference_note(
    *,
    scope: PreferenceScope,
    value: str,
    action: PreferenceAction,
    reason: str | None = None,
) -> str:
    normalized_value = _normalize_text(value, MAX_SCOPE_VALUE_LENGTH)
    if not normalized_value:
        raise ValueError("偏好规则的 value 不能为空")
    normalized_reason = _normalize_text(reason, MAX_REASON_LENGTH)
    subject = _build_scope_subject(scope, normalized_value)
    predicate = _build_action_predicate(action)
    note = f"{subject}{predicate}"
    if normalized_reason:
        note = f"{note}。原因：{normalized_reason}"
    return note


def _build_scope_subject(scope: PreferenceScope, value: str) -> str:
    mapping = {
        "sender": f"来自“{value}”的邮件",
        "domain": f"来自域名“{value}”的邮件",
        "keyword": f"包含关键词“{value}”的邮件",
        "topic": f"主题涉及“{value}”的邮件",
        "pattern": f"符合“{value}”特征的邮件",
    }
    try:
        return mapping[scope]
    except KeyError as error:
        raise ValueError(f"不支持的偏好 scope: {scope}") from error


def _build_action_predicate(action: PreferenceAction) -> str:
    mapping = {
        "always_notify": "必须提醒",
        "never_notify": "默认不提醒",
        "brief": "提醒时默认只发短提醒",
        "summary": "提醒时默认发摘要",
        "full_excerpt": "提醒时默认发摘要和正文片段",
    }
    try:
        return mapping[action]
    except KeyError as error:
        raise ValueError(f"不支持的偏好 action: {action}") from error


def _normalize_text(value: str | None, max_length: int) -> str:
    text = " ".join(str(value or "").split()).strip()
    if not text:
        return ""
    return text[:max_length].rstrip()
