from __future__ import annotations

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any


def _normalize(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_normalize(item) for item in value]
    return value


def log_structured_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    payload = {"event": event}
    for key, value in fields.items():
        if value is None:
            continue
        payload[key] = _normalize(value)
    logger.info(json.dumps(payload, ensure_ascii=False, sort_keys=True))
