# mail-bridge agent notes

This file is for AI/code agents working inside this repository.

Treat this repository as the publishable self-hosted copy.

## Read order

When starting work, read files in this order:

1. `README.md`
2. `docs/ARCHITECTURE.md`
3. `docs/CONFIGURATION.md`
4. `docs/runbooks/OPERATIONS.md`

## Project purpose

This project is a local Gmail real-time bridge.

This repository is the publishable self-hosted copy.

Assume secrets, tokens, `.env`, and local runtime state are intentionally excluded.

Primary job:

- receive Gmail events from Pub/Sub
- fetch minimal mail content
- classify importance
- notify only when important

Do not redesign it into a general mail client unless explicitly asked.

## Current deployment assumptions

- Runtime mode: `Pub/Sub StreamingPull`
- No public domain required
- Windows service name: `mail-bridge`
- OpenClaw classifier mode: `cli`
- Notification mode: `openclaw_qqbot`
- Local state DB: `data/mail-bridge.db`
- Service logs:
  - `data/mail-bridge-service.log`
  - `data/mail-bridge-service.err.log`

## Safety

- Never print or commit secrets from `.env` or `.secrets`
- Treat Gmail app passwords, OAuth tokens, and ADC JSON as sensitive
- Do not rotate or revoke credentials unless explicitly requested
- Keep examples and tests generic; do not reintroduce personal email addresses or QQ targets

## Change guidelines

- Prefer minimal targeted changes
- Keep event flow observable
- Preserve structured logging in `mail_bridge/service.py`
- Update docs when changing config keys, runtime flow, or operations
