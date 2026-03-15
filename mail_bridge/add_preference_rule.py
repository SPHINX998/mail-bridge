from __future__ import annotations

import argparse
import json

from mail_bridge.config import get_settings
from mail_bridge.preferences import build_preference_note
from mail_bridge.rules import RulesStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Append a structured mail preference rule.")
    parser.add_argument(
        "--scope",
        required=True,
        choices=["sender", "domain", "keyword", "topic", "pattern"],
        help="Rule scope",
    )
    parser.add_argument("--value", required=True, help="Rule match value")
    parser.add_argument(
        "--action",
        required=True,
        choices=["always_notify", "never_notify", "brief", "summary", "full_excerpt"],
        help="Preferred handling action",
    )
    parser.add_argument("--reason", default="", help="Optional reason")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = get_settings()
    store = RulesStore(settings.memento_rules_file, settings.importance_policy_note)
    note = build_preference_note(
        scope=args.scope,
        value=args.value,
        action=args.action,
        reason=args.reason or None,
    )
    rules = store.add_note(note)
    print(
        json.dumps(
            {
                "note": note,
                "policy_note": rules.policy_note,
                "notes": rules.notes,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
