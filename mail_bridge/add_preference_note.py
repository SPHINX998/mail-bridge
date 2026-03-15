from __future__ import annotations

import argparse
import json

from mail_bridge.config import get_settings
from mail_bridge.rules import RulesStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Append a long-term mail preference note.")
    parser.add_argument("--note", required=True, help="Preference note text")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = get_settings()
    store = RulesStore(settings.memento_rules_file, settings.importance_policy_note)
    rules = store.add_note(args.note)
    print(
        json.dumps(
            {
                "policy_note": rules.policy_note,
                "notes": rules.notes,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
