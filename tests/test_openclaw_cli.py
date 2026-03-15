from __future__ import annotations

import json
from pathlib import Path

from mail_bridge.config import Settings
from mail_bridge.openclaw_cli import OpenClawCli, _config_supports_json_task, _infer_windows_user_home_from_command


def test_infer_windows_user_home_from_command() -> None:
    command = "C:/Users/sphin/AppData/Roaming/npm/openclaw.cmd"
    assert _infer_windows_user_home_from_command(command) == Path("C:/Users/sphin")


def test_config_supports_json_task_when_agent_has_model_fallback(tmp_path: Path) -> None:
    config_file = tmp_path / "openclaw.json"
    config_file.write_text(
        json.dumps(
            {
                "agents": {
                    "defaults": {"model": {"primary": "codeflow/gpt-5.4"}},
                    "list": [
                        {
                            "id": "main",
                            "model": {
                                "primary": "codeflow/gpt-5.4",
                                "fallbacks": ["codeflow/claude-sonnet-4-6"],
                            },
                        }
                    ],
                }
            }
        ),
        encoding="utf-8",
    )
    assert _config_supports_json_task(config_file, "main") is True


def test_config_supports_json_task_rejects_incomplete_config(tmp_path: Path) -> None:
    config_file = tmp_path / "openclaw.json"
    config_file.write_text(json.dumps({"gateway": {"port": 18789}}), encoding="utf-8")
    assert _config_supports_json_task(config_file, "main") is False


def test_json_session_file_uses_stable_openclaw_path(tmp_path: Path) -> None:
    home_dir = tmp_path / "user-home"
    config_dir = home_dir / ".openclaw"
    config_dir.mkdir(parents=True)
    (config_dir / "openclaw.json").write_text(
        json.dumps({"agents": {"defaults": {"model": {"primary": "codeflow/gpt-5.4"}}}}),
        encoding="utf-8",
    )
    settings = Settings(
        gmail_user_email="demo@gmail.com",
        gmail_watch_topic_name="projects/demo/topics/mail-bridge",
        gmail_oauth_client_file=tmp_path / "credentials.json",
        gmail_oauth_token_file=tmp_path / "token.json",
        state_db_path=tmp_path / "state.db",
        memento_rules_file=tmp_path / "rules.json",
        notifier_mode="noop",
        openclaw_command="python",
    )
    client = OpenClawCli(settings)
    client.openclaw_home_dir = home_dir
    session_file = client._build_json_session_file("mail-bridge-inbox-clean")
    assert session_file == home_dir / ".openclaw" / "mail-bridge" / "sessions" / "mail-bridge-inbox-clean.jsonl"
