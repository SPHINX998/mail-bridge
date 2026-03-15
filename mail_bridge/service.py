from __future__ import annotations

import base64
import binascii
import json
import logging
from email.utils import parseaddr

from google.auth.transport.requests import Request
from google.oauth2 import id_token

from mail_bridge.classifier import BaseClassifier
from mail_bridge.config import Settings
from mail_bridge.gmail import GmailClient, HistorySyncRequiredError
from mail_bridge.logging_utils import log_structured_event
from mail_bridge.models import ProcessOutcome, PubSubHistoryEvent, StoredMessageRecord, WatchState, utc_now
from mail_bridge.notifier import BaseNotifier
from mail_bridge.store import StateStore

LOGGER = logging.getLogger(__name__)


class MailBridgeService:
    def __init__(
        self,
        settings: Settings,
        store: StateStore,
        gmail_client: GmailClient,
        classifier: BaseClassifier,
        notifier: BaseNotifier,
    ) -> None:
        self.settings = settings
        self.store = store
        self.gmail_client = gmail_client
        self.classifier = classifier
        self.notifier = notifier

    def renew_watch_if_needed(self, force: bool = False) -> WatchState:
        state = self.store.get_watch_state(self.settings.gmail_user_email)
        if not force and state and not state.needs_renewal(self.settings.gmail_watch_renew_margin_hours):
            return state
        response = self.gmail_client.renew_watch()
        updated_state = WatchState(
            email=self.settings.gmail_user_email,
            cursor_history_id=response.get("historyId") if state is None or not state.cursor_history_id else state.cursor_history_id,
            watch_history_id=response.get("historyId"),
            expiration_epoch_ms=int(response["expiration"]) if response.get("expiration") else None,
            updated_at=utc_now(),
            last_renewed_at=utc_now(),
            last_error=None,
        )
        self.store.save_watch_state(updated_state)
        return updated_state

    def get_watch_status(self) -> dict[str, object]:
        state = self.store.get_watch_state(self.settings.gmail_user_email)
        if state is None:
            return {"configured": False}
        return {
            "configured": True,
            "email": state.email,
            "cursor_history_id": state.cursor_history_id,
            "watch_history_id": state.watch_history_id,
            "expiration_epoch_ms": state.expiration_epoch_ms,
            "expiration_at": None if state.expiration_at() is None else state.expiration_at().isoformat(),
            "last_renewed_at": None if state.last_renewed_at is None else state.last_renewed_at.isoformat(),
            "last_error": state.last_error,
        }

    def handle_pubsub_push(self, envelope: dict[str, object], authorization_header: str | None = None) -> ProcessOutcome:
        self._verify_pubsub_request(authorization_header)
        event = parse_pubsub_event(envelope)
        return self.handle_history_event(event)

    def handle_history_event(self, event: PubSubHistoryEvent) -> ProcessOutcome:
        log_structured_event(
            LOGGER,
            "pubsub_history_event_received",
            pubsub_message_id=event.pubsub_message_id,
            gmail_email=event.gmail_email,
            history_id=event.history_id,
            published_at=event.published_at,
        )
        if event.gmail_email != self.settings.gmail_user_email:
            log_structured_event(
                LOGGER,
                "pubsub_history_event_ignored",
                pubsub_message_id=event.pubsub_message_id,
                gmail_email=event.gmail_email,
                expected_gmail_email=self.settings.gmail_user_email,
                reason="mailbox_mismatch",
            )
            return ProcessOutcome(processed_count=0, notified_count=0, latest_history_id=None)
        is_new_pubsub_event = self.store.record_pubsub_event(event.pubsub_message_id, event.history_id)
        log_structured_event(
            LOGGER,
            "pubsub_history_event_recorded",
            pubsub_message_id=event.pubsub_message_id,
            history_id=event.history_id,
            is_new=is_new_pubsub_event,
        )

        state = self.store.get_watch_state(self.settings.gmail_user_email)
        if state is None or not state.cursor_history_id:
            bootstrap_state = WatchState(
                email=self.settings.gmail_user_email,
                cursor_history_id=event.history_id,
                watch_history_id=event.history_id,
                expiration_epoch_ms=None if state is None else state.expiration_epoch_ms,
                updated_at=utc_now(),
                last_renewed_at=None if state is None else state.last_renewed_at,
                last_error=None,
            )
            self.store.save_watch_state(bootstrap_state)
            log_structured_event(
                LOGGER,
                "watch_cursor_bootstrapped",
                email=self.settings.gmail_user_email,
                cursor_history_id=event.history_id,
            )
            return ProcessOutcome(processed_count=0, notified_count=0, latest_history_id=event.history_id)

        try:
            history_items, latest_history_id = self.gmail_client.list_history(state.cursor_history_id)
        except HistorySyncRequiredError as error:
            self.store.mark_watch_error(self.settings.gmail_user_email, str(error))
            reset_state = WatchState(
                email=self.settings.gmail_user_email,
                cursor_history_id=event.history_id,
                watch_history_id=None if state is None else state.watch_history_id,
                expiration_epoch_ms=None if state is None else state.expiration_epoch_ms,
                updated_at=utc_now(),
                last_renewed_at=None if state is None else state.last_renewed_at,
                last_error="history cursor expired; reset to latest push historyId",
            )
            self.store.save_watch_state(reset_state)
            log_structured_event(
                LOGGER,
                "watch_cursor_reset",
                email=self.settings.gmail_user_email,
                previous_cursor_history_id=state.cursor_history_id,
                replacement_history_id=event.history_id,
                reason="history_cursor_expired",
                error=str(error),
            )
            return ProcessOutcome(processed_count=0, notified_count=0, latest_history_id=event.history_id)

        log_structured_event(
            LOGGER,
            "history_batch_loaded",
            email=self.settings.gmail_user_email,
            start_history_id=state.cursor_history_id,
            latest_history_id=latest_history_id,
            history_item_count=len(history_items),
        )
        processed_count = 0
        notified_count = 0
        for history_item in sorted(history_items, key=lambda item: int(item.get("id", 0))):
            for message_added in history_item.get("messagesAdded", []):
                message_ref = message_added.get("message", {})
                if "INBOX" not in message_ref.get("labelIds", []):
                    continue
                mail_item = self.gmail_client.get_message(message_ref["id"])
                classification = self.classifier.classify(mail_item)
                should_notify = classification.important
                dedupe_key = build_dedupe_key(mail_item)
                if self.store.is_message_processed(mail_item.gmail_message_id, dedupe_key):
                    log_structured_event(
                        LOGGER,
                        "message_deduplicated",
                        gmail_message_id=mail_item.gmail_message_id,
                        dedupe_key=dedupe_key,
                        source_mailbox=mail_item.source_mailbox,
                        subject=mail_item.subject,
                    )
                    continue
                log_structured_event(
                    LOGGER,
                    "message_classified",
                    gmail_message_id=mail_item.gmail_message_id,
                    gmail_thread_id=mail_item.gmail_thread_id,
                    internet_message_id=mail_item.internet_message_id,
                    source_mailbox=mail_item.source_mailbox,
                    from_header=mail_item.from_header,
                    to_header=mail_item.to_header,
                    subject=mail_item.subject,
                    attachment_names=mail_item.attachment_names,
                    label_ids=mail_item.label_ids,
                    internal_timestamp=mail_item.internal_timestamp,
                    history_id=mail_item.history_id,
                    important=classification.important,
                    score=classification.score,
                    category=classification.category,
                    reason=classification.reason,
                    send_mode=classification.send_mode,
                    needs_action=classification.needs_action,
                    deadline_hint=classification.deadline_hint,
                )
                record = StoredMessageRecord(
                    gmail_message_id=mail_item.gmail_message_id,
                    dedupe_key=dedupe_key,
                    source_mailbox=mail_item.source_mailbox,
                    subject=mail_item.subject,
                    notified=False,
                    created_at=utc_now(),
                    classification=classification,
                )
                if should_notify:
                    try:
                        self.notifier.notify(mail_item, classification)
                    except Exception as error:
                        log_structured_event(
                            LOGGER,
                            "notification_failed",
                            gmail_message_id=mail_item.gmail_message_id,
                            subject=mail_item.subject,
                            notifier_mode=self.settings.notifier_mode,
                            notification_target=self._notification_target(),
                            error=str(error),
                        )
                        raise
                    log_structured_event(
                        LOGGER,
                        "notification_sent",
                        gmail_message_id=mail_item.gmail_message_id,
                        subject=mail_item.subject,
                        notifier_mode=self.settings.notifier_mode,
                        notification_target=self._notification_target(),
                        qq_text=classification.render_notification_text(),
                        send_mode=classification.send_mode,
                    )
                if not self.store.record_processed_message(record):
                    log_structured_event(
                        LOGGER,
                        "message_record_race_skipped",
                        gmail_message_id=mail_item.gmail_message_id,
                        dedupe_key=dedupe_key,
                    )
                    continue
                processed_count += 1
                if should_notify:
                    self.store.mark_message_notified(mail_item.gmail_message_id)
                    notified_count += 1
                log_structured_event(
                    LOGGER,
                    "message_recorded",
                    gmail_message_id=mail_item.gmail_message_id,
                    subject=mail_item.subject,
                    notified=should_notify,
                    processed_count=processed_count,
                    notified_count=notified_count,
                )

        next_history_id = latest_history_id or event.history_id
        self.store.update_cursor_history_id(self.settings.gmail_user_email, next_history_id)
        log_structured_event(
            LOGGER,
            "history_batch_completed",
            email=self.settings.gmail_user_email,
            latest_history_id=next_history_id,
            processed_count=processed_count,
            notified_count=notified_count,
        )
        return ProcessOutcome(
            processed_count=processed_count,
            notified_count=notified_count,
            latest_history_id=next_history_id,
        )

    def _verify_pubsub_request(self, authorization_header: str | None) -> None:
        if not self.settings.pubsub_expected_service_account_email:
            return
        if not authorization_header or not authorization_header.startswith("Bearer "):
            raise PermissionError("缺少 Pub/Sub Bearer token")
        token = authorization_header.split(" ", maxsplit=1)[1].strip()
        claims = id_token.verify_oauth2_token(token, Request(), audience=self.settings.pubsub_audience_resolved)
        if claims.get("email") != self.settings.pubsub_expected_service_account_email:
            raise PermissionError("Pub/Sub service account 不匹配")
        if not claims.get("email_verified"):
            raise PermissionError("Pub/Sub service account 邮箱未验证")

    def _notification_target(self) -> str | None:
        if self.settings.notifier_mode == "openclaw_qqbot":
            return self.settings.qq_target_resolved
        return None


def parse_pubsub_event(envelope: dict[str, object]) -> PubSubHistoryEvent:
    message = envelope.get("message")
    if not isinstance(message, dict):
        raise ValueError("无效的 Pub/Sub envelope.message")
    data = message.get("data")
    if not isinstance(data, str):
        raise ValueError("Pub/Sub message.data 缺失")
    try:
        payload = json.loads(decode_pubsub_data(data))
    except binascii.Error as error:
        raise ValueError("Pub/Sub data 不是合法 base64") from error
    return PubSubHistoryEvent(
        pubsub_message_id=str(message.get("messageId")),
        gmail_email=str(payload["emailAddress"]),
        history_id=str(payload["historyId"]),
        published_at=None if message.get("publishTime") is None else str(message.get("publishTime")),
    )


def parse_pubsub_message(
    pubsub_message_id: str,
    data: bytes,
    published_at: str | None = None,
) -> PubSubHistoryEvent:
    try:
        payload = json.loads(data.decode("utf-8"))
    except UnicodeDecodeError as error:
        raise ValueError("Pub/Sub message data 不是合法 UTF-8 JSON") from error
    return PubSubHistoryEvent(
        pubsub_message_id=pubsub_message_id,
        gmail_email=str(payload["emailAddress"]),
        history_id=str(payload["historyId"]),
        published_at=published_at,
    )


def decode_pubsub_data(value: str) -> str:
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8")


def build_dedupe_key(mail_item) -> str:
    if mail_item.internet_message_id:
        return f"internet:{mail_item.internet_message_id.strip().lower()}"
    _, from_address = parseaddr(mail_item.from_header)
    normalized_subject = " ".join(mail_item.subject.lower().split())
    minute_bucket = mail_item.internal_timestamp.strftime("%Y%m%d%H%M")
    return f"fallback:{from_address.lower()}:{normalized_subject}:{minute_bucket}"
