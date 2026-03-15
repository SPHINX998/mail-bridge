from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

MAX_NOTES = 100


@dataclass(slots=True)
class ImportanceRules:
    version: str = "v2"
    policy_note: str = ""
    notes: list[str] = field(default_factory=list)


class RulesStore:
    def __init__(self, path: Path, policy_note: str) -> None:
        self.path = path
        self.policy_note = policy_note

    def ensure_exists(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            return
        default_rules = ImportanceRules(policy_note=self.policy_note)
        self.path.write_text(
            json.dumps(asdict(default_rules), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load(self) -> ImportanceRules:
        self.ensure_exists()
        raw_data = json.loads(self.path.read_text(encoding="utf-8"))
        return ImportanceRules(
            version=raw_data.get("version", "v2"),
            policy_note=raw_data.get("policy_note", self.policy_note),
            notes=self._normalize_notes(raw_data.get("notes", [])),
        )

    def save(self, rules: ImportanceRules) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(asdict(rules), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def add_note(self, note: str) -> ImportanceRules:
        normalized_note = " ".join(note.split()).strip()
        if not normalized_note:
            raise ValueError("偏好备注不能为空")
        rules = self.load()
        deduped_notes = [item for item in rules.notes if item != normalized_note]
        deduped_notes.append(normalized_note)
        rules.notes = deduped_notes[-MAX_NOTES:]
        self.save(rules)
        return rules

    @staticmethod
    def _normalize_notes(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        normalized: list[str] = []
        for item in value:
            if isinstance(item, dict):
                text = " ".join(str(item.get("text", "")).split()).strip()
            else:
                text = " ".join(str(item).split()).strip()
            if text:
                normalized.append(text)
        return normalized[-MAX_NOTES:]
