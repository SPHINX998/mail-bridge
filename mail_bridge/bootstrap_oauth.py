from __future__ import annotations

import argparse

from mail_bridge.config import get_settings
from mail_bridge.gmail import GmailClient, resolve_gmail_scopes


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Gmail OAuth bootstrap")
    parser.add_argument("--no-browser", action="store_true", help="Do not auto-open the browser")
    parser.add_argument("--port", type=int, default=0, help="Local callback port, 0 means auto-select")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    settings = get_settings()
    gmail_client = GmailClient(settings)
    print(f"将申请 Gmail OAuth scopes: {', '.join(resolve_gmail_scopes(settings))}")
    token_file = gmail_client.run_interactive_oauth(open_browser=not args.no_browser, port=args.port)
    print(f"Gmail OAuth token 已写入: {token_file}")


if __name__ == "__main__":
    main()
