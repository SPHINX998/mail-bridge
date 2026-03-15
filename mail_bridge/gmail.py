from __future__ import annotations

import base64
import json
import logging
import re
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any

from google.auth.transport.requests import AuthorizedSession, Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from mail_bridge.config import Settings
from mail_bridge.models import MailItem, utc_now

LOGGER = logging.getLogger(__name__)


class HistorySyncRequiredError(RuntimeError):
    pass


def save_credentials(token_file: Path, credentials: Credentials) -> None:
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(credentials.to_json(), encoding="utf-8")


def resolve_gmail_scopes(settings: Settings) -> list[str]:
    scopes = [scope.strip() for scope in settings.gmail_oauth_scopes if scope.strip()]
    if scopes:
        return scopes
    return ["https://www.googleapis.com/auth/gmail.readonly"]


def load_granted_scopes(token_file: Path) -> set[str]:
    if not token_file.exists():
        return set()
    try:
        raw = json.loads(token_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    scopes = raw.get("scopes")
    if isinstance(scopes, list):
        return {str(scope).strip() for scope in scopes if str(scope).strip()}
    if isinstance(scopes, str) and scopes.strip():
        return {scope.strip() for scope in scopes.split(" ") if scope.strip()}
    return set()


def token_needs_reconsent(settings: Settings) -> bool:
    requested_scopes = set(resolve_gmail_scopes(settings))
    granted_scopes = load_granted_scopes(settings.gmail_oauth_token_file)
    return bool(requested_scopes) and not requested_scopes.issubset(granted_scopes)


def load_credentials(settings: Settings, interactive: bool = False) -> Credentials:
    scopes = resolve_gmail_scopes(settings)
    credentials: Credentials | None = None
    if settings.gmail_oauth_token_file.exists() and not token_needs_reconsent(settings):
        credentials = Credentials.from_authorized_user_file(str(settings.gmail_oauth_token_file), scopes)
    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        save_credentials(settings.gmail_oauth_token_file, credentials)
    if credentials and credentials.valid:
        return credentials
    if settings.gmail_oauth_token_file.exists() and token_needs_reconsent(settings) and not interactive:
        requested = ", ".join(scopes)
        raise RuntimeError(
            "当前 Gmail OAuth token 的 scope 不满足要求。"
            f"需要重新授权后再继续，目标 scope: {requested}。"
            "运行 `python -m mail_bridge.bootstrap_oauth` 覆盖旧 token。"
        )
    if not interactive:
        raise RuntimeError(
            "缺少可用的 Gmail OAuth token。先准备 credentials.json，再运行 "
            "`python -m mail_bridge.bootstrap_oauth`。"
        )
    if not settings.gmail_oauth_client_file.exists():
        raise FileNotFoundError(f"找不到 OAuth client 文件: {settings.gmail_oauth_client_file}")
    credentials = run_interactive_oauth_flow(settings, scopes=scopes)
    save_credentials(settings.gmail_oauth_token_file, credentials)
    return credentials


def run_interactive_oauth_flow(
    settings: Settings,
    scopes: list[str] | None = None,
    *,
    open_browser: bool = True,
    port: int = 0,
) -> Credentials:
    if not settings.gmail_oauth_client_file.exists():
        raise FileNotFoundError(f"找不到 OAuth client 文件: {settings.gmail_oauth_client_file}")
    flow = InstalledAppFlow.from_client_secrets_file(
        str(settings.gmail_oauth_client_file),
        scopes or resolve_gmail_scopes(settings),
    )
    return flow.run_local_server(
        port=port,
        access_type="offline",
        prompt="consent",
        open_browser=open_browser,
    )


def build_authorized_session(settings: Settings) -> AuthorizedSession:
    credentials = load_credentials(settings, interactive=False)
    return AuthorizedSession(credentials)


class GmailClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def run_interactive_oauth(self, *, open_browser: bool = True, port: int = 0) -> Path:
        scopes = resolve_gmail_scopes(self.settings)
        credentials = run_interactive_oauth_flow(
            self.settings,
            scopes=scopes,
            open_browser=open_browser,
            port=port,
        )
        save_credentials(self.settings.gmail_oauth_token_file, credentials)
        return self.settings.gmail_oauth_token_file

    def _session(self) -> AuthorizedSession:
        return build_authorized_session(self.settings)

    def renew_watch(self) -> dict[str, Any]:
        request_body = {
            "topicName": self.settings.gmail_watch_topic_name,
            "labelIds": self.settings.gmail_watch_label_ids,
            "labelFilterBehavior": self.settings.gmail_watch_label_filter_behavior,
        }
        LOGGER.info("renewing gmail watch for %s", self.settings.gmail_user_email)
        response = self._session().post(
            "https://gmail.googleapis.com/gmail/v1/users/me/watch",
            json=request_body,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def list_history(self, start_history_id: str) -> tuple[list[dict[str, Any]], str | None]:
        items: list[dict[str, Any]] = []
        next_page_token: str | None = None
        latest_history_id: str | None = None
        try:
            while True:
                response = self._session().get(
                    "https://gmail.googleapis.com/gmail/v1/users/me/history",
                    params={
                        "startHistoryId": start_history_id,
                        "historyTypes": "messageAdded",
                        "maxResults": 100,
                        "pageToken": next_page_token,
                    },
                    timeout=30,
                )
                response.raise_for_status()
                data = response.json()
                items.extend(data.get("history", []))
                latest_history_id = data.get("historyId", latest_history_id)
                next_page_token = data.get("nextPageToken")
                if not next_page_token:
                    break
        except Exception as error:
            if getattr(getattr(error, "response", None), "status_code", None) == 404 or "404" in str(error):
                raise HistorySyncRequiredError(str(error)) from error
            raise
        return items, latest_history_id

    def get_message(self, message_id: str) -> MailItem:
        response = self._session().get(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
            params={"format": "full"},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        payload = data.get("payload", {})
        headers = {header["name"].lower(): header["value"] for header in payload.get("headers", [])}
        source_mailbox = (
            headers.get("delivered-to")
            or headers.get("x-original-to")
            or headers.get("x-forwarded-to")
            or headers.get("to")
            or self.settings.gmail_user_email
        )
        return MailItem(
            gmail_message_id=data["id"],
            gmail_thread_id=data["threadId"],
            internet_message_id=headers.get("message-id"),
            source_mailbox=source_mailbox,
            from_header=headers.get("from", ""),
            to_header=headers.get("to", ""),
            subject=headers.get("subject", ""),
            snippet=data.get("snippet", ""),
            body_preview=extract_body_preview(payload, self.settings.body_preview_bytes),
            attachment_names=extract_attachment_names(payload, self.settings.max_attachment_names),
            label_ids=list(data.get("labelIds", [])),
            internal_timestamp=timestamp_from_internal_date(data.get("internalDate")),
            history_id=data.get("historyId", ""),
        )


def timestamp_from_internal_date(value: str | None) -> datetime:
    if not value:
        return utc_now()
    return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)


def decode_base64_data(value: str) -> str:
    padded = value + "=" * (-len(value) % 4)
    raw_bytes = base64.urlsafe_b64decode(padded.encode("utf-8"))
    return raw_bytes.decode("utf-8", errors="ignore")


def flatten_parts(payload: dict[str, Any]) -> list[dict[str, Any]]:
    parts = [payload]
    for part in payload.get("parts", []) or []:
        parts.extend(flatten_parts(part))
    return parts


def extract_attachment_names(payload: dict[str, Any], limit: int) -> list[str]:
    names: list[str] = []
    for part in flatten_parts(payload):
        filename = (part.get("filename") or "").strip()
        body = part.get("body", {})
        if filename and body.get("attachmentId"):
            names.append(filename)
        if len(names) >= limit:
            return names[:limit]
    return names[:limit]


def extract_body_preview(payload: dict[str, Any], max_bytes: int) -> str:
    text_candidates: list[str] = []
    html_candidates: list[str] = []
    for part in flatten_parts(payload):
        mime_type = (part.get("mimeType") or "").lower()
        body_data = (part.get("body") or {}).get("data")
        if not body_data:
            continue
        decoded = decode_base64_data(body_data)
        if mime_type == "text/plain":
            text_candidates.append(decoded)
        elif mime_type == "text/html":
            html_candidates.append(decoded)
    content = "\n".join(text_candidates).strip()
    if not content and html_candidates:
        content = re.sub(r"<[^>]+>", " ", "\n".join(html_candidates))
        content = unescape(content)
    content = re.sub(r"\s+", " ", content).strip()
    return content.encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore")
