from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mail_bridge.config import Settings

JSON_FENCE_PATTERN = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)
JSON_TASK_LOCK = threading.Lock()


class OpenClawCliError(RuntimeError):
    pass


@dataclass(slots=True)
class OpenClawCommandResult:
    stdout: str
    stderr: str


class OpenClawCli:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.command = self._resolve_command(settings.openclaw_command)
        self.node_command = self._resolve_node_command()
        self.json_task_script = Path(__file__).with_name("openclaw_json_task.mjs")
        self.qqbot_send_script = Path(__file__).with_name("openclaw_qqbot_send_task.mjs")
        self.openclaw_home_dir = self._resolve_openclaw_home_dir()
        self.openclaw_config_file = self._resolve_openclaw_config_file()

    def run_agent_json(
        self,
        prompt: str,
        input_payload: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "prompt": prompt,
            "input": input_payload or {},
            "agentId": self.settings.openclaw_agent_id,
            "provider": self.settings.openclaw_json_provider,
            "model": self.settings.openclaw_json_model,
            "thinking": self.settings.openclaw_json_thinking_level,
            "timeoutMs": self.settings.openclaw_timeout_seconds * 1000,
            "sessionId": session_id,
        }
        if self.openclaw_config_file is not None:
            payload["configFile"] = str(self.openclaw_config_file)
        if self.openclaw_home_dir is not None:
            payload["openclawHome"] = str(self.openclaw_home_dir)
        if session_id:
            payload["sessionFile"] = str(self._build_json_session_file(session_id))
        result = self._run_json_task(payload, timeout_seconds=self.settings.openclaw_timeout_seconds + 30)
        return extract_json_object(result.stdout)

    def deliver_text(self, text: str, target: str, session_id: str | None = None) -> OpenClawCommandResult:
        payload: dict[str, Any] = {
            "target": target,
            "text": text,
            "timeoutMs": self.settings.openclaw_timeout_seconds * 1000,
        }
        if self.openclaw_config_file is not None:
            payload["configFile"] = str(self.openclaw_config_file)
        if self.openclaw_home_dir is not None:
            payload["openclawHome"] = str(self.openclaw_home_dir)
        if session_id:
            payload["sessionId"] = session_id
        return self._run_node_task(
            script_path=self.qqbot_send_script,
            payload=payload,
            timeout_seconds=self.settings.openclaw_timeout_seconds + 30,
        )

    def _run(self, args: list[str], timeout_seconds: int) -> OpenClawCommandResult:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            env=self._build_env(),
            check=False,
        )
        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            stdout = (completed.stdout or "").strip()
            detail = stderr or stdout or f"exit code {completed.returncode}"
            raise OpenClawCliError(detail)
        return OpenClawCommandResult(stdout=completed.stdout, stderr=completed.stderr)

    def _run_json_task(self, payload: dict[str, Any], timeout_seconds: int) -> OpenClawCommandResult:
        return self._run_node_task(
            script_path=self.json_task_script,
            payload=payload,
            timeout_seconds=timeout_seconds,
        )

    def _run_node_task(self, script_path: Path, payload: dict[str, Any], timeout_seconds: int) -> OpenClawCommandResult:
        with JSON_TASK_LOCK:
            completed = subprocess.run(
                [self.node_command, str(script_path)],
                input=json.dumps(payload, ensure_ascii=False),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
                env=self._build_env(),
                check=False,
            )
        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            stdout = (completed.stdout or "").strip()
            detail = stderr or stdout or f"exit code {completed.returncode}"
            raise OpenClawCliError(detail)
        return OpenClawCommandResult(stdout=completed.stdout, stderr=completed.stderr)

    @staticmethod
    def _resolve_command(configured_command: str) -> str:
        raw_command = configured_command.strip()
        if raw_command:
            configured_path = Path(raw_command)
            if configured_path.exists():
                return str(configured_path)
            discovered = shutil.which(raw_command)
            if discovered:
                return discovered
        if os.name == "nt":
            default_windows_path = Path.home() / "AppData" / "Roaming" / "npm" / "openclaw.cmd"
            if default_windows_path.exists():
                return str(default_windows_path)
        discovered_default = shutil.which("openclaw")
        if discovered_default:
            return discovered_default
        raise OpenClawCliError("找不到 OpenClaw 命令，请检查 OPENCLAW_COMMAND 配置")

    def _build_agent_args(self, session_id: str | None = None) -> list[str]:
        args = [self.command, "agent"]
        selected_session_id = session_id or self.settings.openclaw_session_id
        if selected_session_id:
            args.extend(["--session-id", selected_session_id])
            return args
        args.extend(["--agent", self.settings.openclaw_agent_id])
        return args

    @staticmethod
    def _resolve_node_command() -> str:
        discovered = shutil.which("node")
        if discovered:
            return discovered
        if os.name == "nt":
            default_windows_path = Path("C:/Program Files/nodejs/node.exe")
            if default_windows_path.exists():
                return str(default_windows_path)
        raise OpenClawCliError("找不到 Node.js 命令，无法运行 OpenClaw JSON task")

    def _build_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["OPENCLAW_NO_COLOR"] = "1"
        env["NO_COLOR"] = "1"
        if self.openclaw_home_dir is not None:
            home_dir = str(self.openclaw_home_dir)
            env["HOME"] = home_dir
            env["USERPROFILE"] = home_dir
            if self.openclaw_home_dir.drive:
                env["HOMEDRIVE"] = self.openclaw_home_dir.drive
                env["HOMEPATH"] = str(self.openclaw_home_dir).removeprefix(self.openclaw_home_dir.drive)
            env["APPDATA"] = str(self.openclaw_home_dir / "AppData" / "Roaming")
            env.setdefault("LOCALAPPDATA", str(self.openclaw_home_dir / "AppData" / "Local"))
            env["OPENCLAW_STATE_DIR"] = str(self.openclaw_home_dir / ".openclaw")
        if self.openclaw_config_file is not None:
            env["OPENCLAW_CONFIG_PATH"] = str(self.openclaw_config_file)
        return env

    def _resolve_openclaw_home_dir(self) -> Path | None:
        current_home = Path.home()
        current_config = current_home / ".openclaw" / "openclaw.json"
        if _config_supports_json_task(current_config, self.settings.openclaw_agent_id):
            return current_home
        inferred_home = _infer_windows_user_home_from_command(self.command)
        if (
            inferred_home is not None
            and inferred_home != current_home
            and _config_supports_json_task(inferred_home / ".openclaw" / "openclaw.json", self.settings.openclaw_agent_id)
        ):
            return inferred_home
        if current_config.exists():
            return current_home
        return inferred_home

    def _resolve_openclaw_config_file(self) -> Path | None:
        if self.openclaw_home_dir is None:
            return None
        config_file = self.openclaw_home_dir / ".openclaw" / "openclaw.json"
        return config_file if config_file.exists() else None

    def _build_json_session_file(self, session_id: str) -> Path:
        if self.openclaw_home_dir is None:
            raise OpenClawCliError("无法解析 OpenClaw home，不能持久化 JSON task session")
        normalized_session_id = "".join(
            character if character.isalnum() or character in ("-", "_") else "-"
            for character in session_id
        ).strip("-")
        safe_session_id = normalized_session_id or "mail-bridge-inbox"
        return self.openclaw_home_dir / ".openclaw" / "mail-bridge" / "sessions" / f"{safe_session_id}.jsonl"


def extract_json_object(text: str) -> dict[str, Any]:
    raw_text = text.strip()
    if not raw_text:
        raise OpenClawCliError("OpenClaw 返回为空")

    fenced_match = JSON_FENCE_PATTERN.search(raw_text)
    if fenced_match:
        return json.loads(fenced_match.group(1))

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(raw_text[start : end + 1])
        raise OpenClawCliError(f"无法从 OpenClaw 输出中解析 JSON: {raw_text[:200]}")


def _infer_windows_user_home_from_command(command: str) -> Path | None:
    normalized = command.replace("\\", "/")
    match = re.search(r"^([A-Za-z]:/Users/[^/]+)/AppData/Roaming/npm/(?:openclaw(?:\.cmd|\.exe)?|node_modules/.+)$", normalized)
    if not match:
        return None
    return Path(match.group(1))


def _config_supports_json_task(config_file: Path, agent_id: str) -> bool:
    if not config_file.exists():
        return False
    try:
        raw = json.loads(config_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return _extract_model_ref(raw, agent_id) is not None


def _extract_model_ref(config: Mapping[str, Any], agent_id: str) -> tuple[str, str] | None:
    agents = config.get("agents")
    if not isinstance(agents, Mapping):
        return None
    agent_entries = agents.get("list")
    if isinstance(agent_entries, list):
        for entry in agent_entries:
            if not isinstance(entry, Mapping) or entry.get("id") != agent_id:
                continue
            model = entry.get("model")
            if isinstance(model, Mapping):
                fallbacks = model.get("fallbacks")
                if isinstance(fallbacks, list):
                    for candidate in fallbacks:
                        parsed = _parse_model_ref(candidate)
                        if parsed is not None:
                            return parsed
                parsed = _parse_model_ref(model.get("primary"))
                if parsed is not None:
                    return parsed
    defaults_model = agents.get("defaults", {}).get("model") if isinstance(agents.get("defaults"), Mapping) else None
    if isinstance(defaults_model, Mapping):
        return _parse_model_ref(defaults_model.get("primary"))
    return _parse_model_ref(defaults_model)


def _parse_model_ref(value: object) -> tuple[str, str] | None:
    if not isinstance(value, str) or "/" not in value:
        return None
    provider, model = value.split("/", maxsplit=1)
    provider = provider.strip()
    model = model.strip()
    if not provider or not model:
        return None
    return provider, model
