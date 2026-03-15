from __future__ import annotations

import logging
from concurrent.futures import TimeoutError

import google.auth
from google.cloud import pubsub_v1
from google.oauth2 import service_account

from mail_bridge.config import Settings
from mail_bridge.service import MailBridgeService, parse_pubsub_message

LOGGER = logging.getLogger(__name__)

PUBSUB_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


class PubSubStreamingSubscriber:
    def __init__(self, settings: Settings, service: MailBridgeService) -> None:
        self.settings = settings
        self.service = service
        self.subscriber_client: pubsub_v1.SubscriberClient | None = None
        self.streaming_pull_future = None

    def start(self) -> None:
        if self.settings.pubsub_mode != "streaming_pull":
            LOGGER.info("pubsub mode is %s; skip local streaming subscriber", self.settings.pubsub_mode)
            return
        if not self.settings.pubsub_subscription_name:
            LOGGER.warning("PUBSUB_SUBSCRIPTION_NAME 未配置，跳过本地订阅器")
            return
        credentials = self._load_credentials()
        self.subscriber_client = pubsub_v1.SubscriberClient(credentials=credentials)
        self.streaming_pull_future = self.subscriber_client.subscribe(
            self.settings.pubsub_subscription_name,
            callback=self._callback,
        )
        LOGGER.info("pubsub streaming pull started: %s", self.settings.pubsub_subscription_name)

    def stop(self) -> None:
        if self.streaming_pull_future is not None:
            self.streaming_pull_future.cancel()
            try:
                self.streaming_pull_future.result(timeout=5)
            except TimeoutError:
                LOGGER.warning("timed out waiting for streaming pull shutdown")
            except Exception:
                pass
            self.streaming_pull_future = None
        if self.subscriber_client is not None:
            self.subscriber_client.close()
            self.subscriber_client = None

    def _callback(self, message: pubsub_v1.subscriber.message.Message) -> None:
        try:
            event = parse_pubsub_message(
                pubsub_message_id=message.message_id,
                data=message.data,
                published_at=message.publish_time.isoformat() if message.publish_time else None,
            )
            self.service.handle_history_event(event)
            message.ack()
        except ValueError as error:
            LOGGER.error("invalid pubsub message, ack and drop: %s", error)
            message.ack()
        except Exception as error:
            LOGGER.exception("pubsub streaming pull processing failed: %s", error)
            message.nack()

    def _load_credentials(self):
        service_account_file = self.settings.gcp_service_account_file
        if service_account_file and service_account_file.exists():
            LOGGER.info("using service account credentials for pubsub subscriber: %s", service_account_file)
            return service_account.Credentials.from_service_account_file(
                str(service_account_file),
                scopes=PUBSUB_SCOPES,
            )
        credentials, _ = google.auth.default(scopes=PUBSUB_SCOPES)
        LOGGER.info("using application default credentials for pubsub subscriber")
        return credentials
