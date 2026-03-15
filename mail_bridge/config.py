from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        enable_decoding=False,
    )

    app_host: str = "0.0.0.0"
    app_port: int = 8787
    public_base_url: str = "https://your-public-domain.example.com"

    gmail_user_email: str
    gmail_watch_topic_name: str
    gmail_oauth_scopes: list[str] = Field(
        default_factory=lambda: ["https://www.googleapis.com/auth/gmail.readonly"]
    )
    gmail_watch_label_ids: list[str] = Field(default_factory=lambda: ["INBOX"])
    gmail_watch_label_filter_behavior: Literal["INCLUDE", "EXCLUDE"] = "INCLUDE"
    gmail_oauth_client_file: Path = Path("credentials.json")
    gmail_oauth_token_file: Path = Path(".secrets/gmail-token.json")
    gmail_watch_check_interval_minutes: int = 60
    gmail_watch_renew_margin_hours: int = 24

    pubsub_mode: Literal["push", "streaming_pull"] = "streaming_pull"
    pubsub_subscription_name: str | None = None
    pubsub_expected_audience: str | None = None
    pubsub_expected_service_account_email: str | None = None
    gcp_service_account_file: Path | None = Path(".secrets/gcp-service-account.json")

    state_db_path: Path = Path("data/mail-bridge.db")
    body_preview_bytes: int = 4096
    max_attachment_names: int = 10

    openclaw_command: str = "openclaw"
    openclaw_agent_id: str = "main"
    openclaw_session_id: str | None = None
    openclaw_json_provider: str | None = None
    openclaw_json_model: str | None = None
    openclaw_json_thinking_level: Literal["off", "minimal", "low", "medium", "high", "xhigh"] = "off"
    openclaw_timeout_seconds: int = 180

    importance_policy_note: str = "你看着办，或者小龙虾在对话中学习"
    memento_rules_file: Path = Path("../memento/data/mail-bridge-importance.json")

    notifier_mode: Literal["openclaw_qqbot", "noop"] = "openclaw_qqbot"
    qq_target: str = ""

    @field_validator("gmail_oauth_scopes", "gmail_watch_label_ids", mode="before")
    @classmethod
    def parse_list_setting(cls, value: object) -> object:
        if isinstance(value, str):
            raw_value = value.strip()
            if not raw_value:
                return []
            if raw_value.startswith("["):
                return json.loads(raw_value)
            return [item.strip() for item in raw_value.split(",") if item.strip()]
        return value

    @field_validator(
        "gmail_oauth_client_file",
        "gmail_oauth_token_file",
        "gcp_service_account_file",
        "state_db_path",
        "memento_rules_file",
        mode="before",
    )
    @classmethod
    def normalize_path(cls, value: object) -> object:
        if isinstance(value, str):
            return Path(value)
        return value

    @property
    def qq_target_resolved(self) -> str | None:
        target = self.qq_target.strip()
        if not target:
            return None
        if target.lower().startswith("qqbot:"):
            return target
        if re.fullmatch(r"[0-9a-fA-F]{32}", target):
            return f"qqbot:c2c:{target}"
        if re.fullmatch(
            r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
            target,
        ):
            return f"qqbot:c2c:{target}"
        return target

    @property
    def pubsub_audience_resolved(self) -> str:
        if self.pubsub_expected_audience:
            return self.pubsub_expected_audience
        return f"{self.public_base_url.rstrip('/')}/pubsub/push"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
