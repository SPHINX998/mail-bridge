from __future__ import annotations

import json

from mail_bridge.rules import MAX_NOTES, RulesStore


def test_rules_store_add_note_deduplicates_and_appends_latest(tmp_path) -> None:
    store = RulesStore(tmp_path / "rules.json", "你看着办")
    store.ensure_exists()
    store.add_note("老板发来的付款审批邮件必须提醒")
    rules = store.add_note("老板发来的付款审批邮件必须提醒")
    assert rules.notes == ["老板发来的付款审批邮件必须提醒"]


def test_rules_store_load_normalizes_legacy_dict_notes(tmp_path) -> None:
    rules_path = tmp_path / "rules.json"
    rules_path.write_text(
        json.dumps(
            {
                "version": "v2",
                "policy_note": "你看着办",
                "notes": [
                    {"text": "老板邮件默认更重要"},
                    "  带明确截止时间的审批要提醒  ",
                    {"text": "   "},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    store = RulesStore(rules_path, "你看着办")
    rules = store.load()
    assert rules.notes == ["老板邮件默认更重要", "带明确截止时间的审批要提醒"]


def test_rules_store_add_note_caps_length(tmp_path) -> None:
    store = RulesStore(tmp_path / "rules.json", "你看着办")
    store.ensure_exists()
    for index in range(MAX_NOTES + 5):
        store.add_note(f"note-{index}")
    rules = store.load()
    assert len(rules.notes) == MAX_NOTES
    assert rules.notes[0] == "note-5"
    assert rules.notes[-1] == f"note-{MAX_NOTES + 4}"
