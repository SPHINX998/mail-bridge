from __future__ import annotations

import logging

from mail_bridge.config import Settings
from mail_bridge.models import ClassificationResult, MailItem
from mail_bridge.openclaw_cli import OpenClawCli

LOGGER = logging.getLogger(__name__)


class BaseNotifier:
    def notify(self, mail_item: MailItem, classification: ClassificationResult) -> None:
        raise NotImplementedError


class NoopNotifier(BaseNotifier):
    def notify(self, mail_item: MailItem, classification: ClassificationResult) -> None:
        LOGGER.info("noop notifier: %s", classification.qq_text)


class OpenClawQQBotNotifier(BaseNotifier):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = OpenClawCli(settings)

    def notify(self, mail_item: MailItem, classification: ClassificationResult) -> None:
        target = self.settings.qq_target_resolved
        if not target:
            raise RuntimeError("未配置 QQ_TARGET")
        if not target.lower().startswith("qqbot:"):
            raise RuntimeError("QQ_TARGET 必须是 OpenClaw QQ Bot 可识别的目标，例如 qqbot:c2c:OPENID")
        notification_text = classification.render_notification_text()
        if not notification_text:
            raise RuntimeError("分类结果未返回可发送的 qq_text")
        self.client.deliver_text(notification_text, target)


def build_notifier(settings: Settings) -> BaseNotifier:
    if settings.notifier_mode == "openclaw_qqbot":
        return OpenClawQQBotNotifier(settings)
    return NoopNotifier()
