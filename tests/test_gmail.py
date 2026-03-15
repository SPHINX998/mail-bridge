from __future__ import annotations

from pathlib import Path

from mail_bridge.config import Settings
from mail_bridge.gmail import load_granted_scopes, resolve_gmail_scopes, token_needs_reconsent


def build_settings(tmp_path: Path, scopes: list[str]) -> Settings:
    token_file = tmp_path / "token.json"
    return Settings(
        gmail_user_email="demo@gmail.com",
        gmail_watch_topic_name="projects/demo/topics/mail-bridge",
        gmail_oauth_scopes=scopes,
        gmail_oauth_client_file=tmp_path / "credentials.json",
        gmail_oauth_token_file=token_file,
        state_db_path=tmp_path / "state.db",
        memento_rules_file=tmp_path / "rules.json",
        notifier_mode="noop",
    )


def test_resolve_gmail_scopes_defaults_to_readonly(tmp_path: Path) -> None:
    settings = build_settings(tmp_path, [])
    assert resolve_gmail_scopes(settings) == ["https://www.googleapis.com/auth/gmail.readonly"]


def test_token_needs_reconsent_when_scope_missing(tmp_path: Path) -> None:
    settings = build_settings(tmp_path, ["https://www.googleapis.com/auth/gmail.modify"])
    settings.gmail_oauth_token_file.write_text(
        '{"scopes":["https://www.googleapis.com/auth/gmail.readonly"]}',
        encoding="utf-8",
    )
    assert load_granted_scopes(settings.gmail_oauth_token_file) == {
        "https://www.googleapis.com/auth/gmail.readonly"
    }
    assert token_needs_reconsent(settings) is True


def test_token_does_not_need_reconsent_when_scope_present(tmp_path: Path) -> None:
    settings = build_settings(tmp_path, ["https://www.googleapis.com/auth/gmail.modify"])
    settings.gmail_oauth_token_file.write_text(
        '{"scopes":["https://www.googleapis.com/auth/gmail.modify"]}',
        encoding="utf-8",
    )
    assert token_needs_reconsent(settings) is False
