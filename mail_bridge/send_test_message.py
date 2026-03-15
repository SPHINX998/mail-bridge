from __future__ import annotations

import argparse
import base64
import json
from email.message import EmailMessage

from mail_bridge.config import get_settings
from mail_bridge.gmail import build_authorized_session


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send a Gmail API test message to the configured mailbox.")
    parser.add_argument("--subject", required=True, help="Subject line")
    parser.add_argument("--body", required=True, help="Plain text body")
    parser.add_argument("--from-name", default="Boss", help="Display name for From header")
    parser.add_argument("--attachment-name", default=None, help="Optional attachment filename")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    settings = get_settings()
    session = build_authorized_session(settings)

    message = EmailMessage()
    message["To"] = settings.gmail_user_email
    message["From"] = f"{args.from_name} <{settings.gmail_user_email}>"
    message["Subject"] = args.subject
    message.set_content(args.body)
    if args.attachment_name:
        message.add_attachment(
            b"%PDF-1.4\n% mail-bridge test attachment\n",
            maintype="application",
            subtype="pdf",
            filename=args.attachment_name,
        )

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    response = session.post(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        json={"raw": raw},
        timeout=30,
    )
    response.raise_for_status()
    print(json.loads(response.content.decode("utf-8"))["id"])


if __name__ == "__main__":
    main()
