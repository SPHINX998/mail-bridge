from __future__ import annotations

from email.utils import parseaddr

from mail_bridge.config import Settings
from mail_bridge.models import ClassificationResult, MailItem
from mail_bridge.openclaw_cli import OpenClawCli
from mail_bridge.rules import RulesStore


class BaseClassifier:
    def classify(self, mail_item: MailItem) -> ClassificationResult:
        raise NotImplementedError


class OpenClawCliClassifier(BaseClassifier):
    def __init__(self, settings: Settings, rules_store: RulesStore) -> None:
        self.settings = settings
        self.rules_store = rules_store
        self.client = OpenClawCli(settings)

    def classify(self, mail_item: MailItem) -> ClassificationResult:
        rules = self.rules_store.load()
        notes = rules.notes[:8]
        session_id = _resolve_classifier_session_id(self.settings.openclaw_session_id)
        payload = self._mail_payload(mail_item)
        prompt = (
            "你是用户的邮件助理。"
            "请根据 INPUT_JSON 中的邮件内容、用户偏好和补充备注，判断这封邮件是否值得立刻通过 QQ 提醒用户。"
            "通常以下情形应判为 important=true：来自老板或核心联系人；要求今天/尽快回复；合同、付款、发票、面试、offer、审批等明确业务事项；用户需要马上采取动作。"
            "通常以下情形应判为 important=false：营销推广、订阅简报、自动通知、无动作要求的普通抄送。"
            "如果 important=true，请额外生成简洁摘要 summary，并根据内容选择 send_mode："
            "只需短提醒用 brief；短提醒+摘要用 summary；短提醒+摘要+正文片段用 full_excerpt。"
            "body_excerpt 只保留最关键的正文片段，不要超过 180 个中文字符。"
            "memory_hints 只返回最多 2 条、可帮助后续理解用户偏好的短句；没有则返回空数组。"
            "不要追问，不要解释，不要输出 JSON 以外的任何文字。"
            "严格只返回一个 JSON 对象，字段必须完整："
            "{\"important\":true,\"score\":88,\"category\":\"deadline\",\"reason\":[\"老板邮件\",\"今天截止\"],\"qq_text\":\"🚨 重要邮件：王总 / 今天内确认合同终稿\",\"summary\":\"王总发来合同终稿，需要你今天确认。\",\"body_excerpt\":\"请在今天18:00前确认合同终稿并回复审批意见。\",\"send_mode\":\"summary\",\"needs_action\":true,\"deadline_hint\":\"今天18:00\",\"memory_hints\":[\"老板发来的合同/付款邮件通常重要\"]}。"
            "reason 和 memory_hints 必须是字符串数组；qq_text 必须是一句可直接发送到 QQ 的短提醒；没有 deadline_hint 时请返回 null。"
            "如果 important=false，请返回空字符串 summary/body_excerpt/qq_text，send_mode 返回 brief。"
        )
        input_payload = {
            "mail": payload,
            "user_policy_note": rules.policy_note or self.settings.importance_policy_note,
            "notes": notes,
        }
        data = self.client.run_agent_json(prompt, input_payload=input_payload, session_id=session_id)
        return self._build_result(mail_item, data)

    @staticmethod
    def _mail_payload(mail_item: MailItem) -> dict[str, object]:
        return {
            "source_mailbox": mail_item.source_mailbox,
            "from": mail_item.from_header,
            "to": mail_item.to_header,
            "subject": mail_item.subject,
            "snippet": mail_item.snippet,
            "body_preview": mail_item.body_preview,
            "attachment_names": mail_item.attachment_names,
            "label_ids": mail_item.label_ids,
            "received_at": mail_item.internal_timestamp.isoformat(),
            "internet_message_id": mail_item.internet_message_id,
        }

    def _build_result(self, mail_item: MailItem, data: dict[str, object]) -> ClassificationResult:
        important = bool(data.get("important", False))
        score = _normalize_score(data.get("score"))
        category = str(data.get("category") or ("important" if important else "routine"))
        reason = _normalize_reason(data.get("reason")) or ["OpenClaw 未返回理由"]
        qq_text = _normalize_text(data.get("qq_text"), max_length=120)
        summary = _normalize_text(data.get("summary"), max_length=180)
        body_excerpt = _normalize_text(data.get("body_excerpt"), max_length=220)
        send_mode = _normalize_send_mode(data.get("send_mode"), important=important, summary=summary, body_excerpt=body_excerpt)
        if important and not qq_text:
            qq_text = _build_default_qq_text(mail_item, reason)
        return ClassificationResult(
            important=important,
            score=score,
            category=category,
            reason=reason,
            qq_text=qq_text,
            summary=summary,
            body_excerpt=body_excerpt,
            send_mode=send_mode,
            needs_action=bool(data.get("needs_action", important)),
            deadline_hint=None if data.get("deadline_hint") in (None, "") else str(data.get("deadline_hint")),
            memory_hints=_normalize_reason(data.get("memory_hints"))[:2],
        )


def _normalize_score(value: object) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, score))


def _normalize_reason(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None:
        return []
    text = str(value).strip()
    return [text] if text else []


def _normalize_text(value: object, max_length: int) -> str:
    text = " ".join(str(value or "").split()).strip()
    if not text:
        return ""
    return text[:max_length].rstrip()


def _normalize_send_mode(
    value: object,
    *,
    important: bool,
    summary: str,
    body_excerpt: str,
) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"brief", "summary", "full_excerpt"}:
        return normalized
    if not important:
        return "brief"
    if body_excerpt:
        return "full_excerpt"
    if summary:
        return "summary"
    return "brief"


def _build_default_qq_text(mail_item: MailItem, reasons: list[str]) -> str:
    from_name, from_address = parseaddr(mail_item.from_header)
    sender = from_name or from_address or "未知发件人"
    subject_text = mail_item.subject.strip() or "无主题"
    reason_text = " / ".join(reasons[:2]) if reasons else "需要关注"
    return f"重要邮件：{sender} / {subject_text[:48]} / {reason_text[:64]}"


def _resolve_classifier_session_id(base_session_id: str | None) -> str | None:
    base = (base_session_id or "").strip()
    return base or None


def build_classifier(settings: Settings, rules_store: RulesStore) -> BaseClassifier:
    return OpenClawCliClassifier(settings, rules_store)
