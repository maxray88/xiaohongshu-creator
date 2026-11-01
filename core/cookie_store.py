#!/usr/bin/env python3
"""XHS cookie session storage backed by a plaintext JSON file.

Cookies are kept under the user's data directory at the same trust level as
the design's SQLite store: anything with filesystem access can read them.
``expires_at`` values are naive local datetimes.
"""
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any

from io_utils import atomic_write_json
from xhs_config import COOKIE_EXPIRY_WARNING_HOURS, DATA_BASE


logger = logging.getLogger(__name__)


COOKIE_PATH = os.path.join(DATA_BASE, "xhs_cookies.json")


def _load() -> dict:
    try:
        with open(COOKIE_PATH, encoding="utf-8") as f:
            store = json.load(f)
    except FileNotFoundError:
        return {}
    except (OSError, ValueError, TypeError):
        logger.error("Failed to read cookie store", exc_info=True)
        return {}

    if not isinstance(store, dict):
        logger.error("Cookie store must be a JSON object")
        return {}
    return store


def _save(store: dict) -> None:
    os.makedirs(os.path.dirname(COOKIE_PATH), exist_ok=True)
    atomic_write_json(COOKIE_PATH, store)


def store_cookies(
    account_id: str,
    cookies: dict | list | str,
    expires_at: datetime,
) -> None:
    if isinstance(cookies, (dict, list)):
        cookies_json = json.dumps(cookies, ensure_ascii=False)
    else:
        cookies_json = cookies

    store = _load()
    now = datetime.now()
    store[account_id] = {
        "cookies_json": cookies_json,
        "expires_at": expires_at.isoformat(),
        "updated_at": now.isoformat(),
    }
    _save(store)


def get_cookies(account_id: str) -> dict[str, Any] | None:
    entry = _load().get(account_id)
    if not isinstance(entry, dict):
        return None

    raw = entry.get("cookies_json")
    try:
        cookies = json.loads(raw)
    except (TypeError, ValueError):
        cookies = raw
    return {
        "cookies": cookies,
        "expires_at": entry.get("expires_at"),
        "updated_at": entry.get("updated_at"),
    }


def is_expired(account_id: str) -> bool:
    entry = _load().get(account_id)
    if not isinstance(entry, dict):
        return True

    try:
        expires_at = datetime.fromisoformat(entry["expires_at"])
    except (KeyError, TypeError, ValueError):
        return True
    return datetime.now() >= expires_at


def needs_refresh(
    account_id: str,
    threshold_hours: int | None = None,
) -> bool:
    if threshold_hours is None:
        threshold_hours = COOKIE_EXPIRY_WARNING_HOURS

    entry = _load().get(account_id)
    if not isinstance(entry, dict):
        return True
    try:
        expires_at = datetime.fromisoformat(entry["expires_at"])
    except (KeyError, TypeError, ValueError):
        return True
    return datetime.now() >= expires_at - timedelta(hours=threshold_hours)


def get_all_expiring_soon(
    threshold_hours: int | None = None,
) -> list[dict[str, Any]]:
    if threshold_hours is None:
        threshold_hours = COOKIE_EXPIRY_WARNING_HOURS

    expiring: list[dict[str, Any]] = []
    for account_id, entry in _load().items():
        if not isinstance(entry, dict):
            continue
        try:
            expires_at = datetime.fromisoformat(entry["expires_at"])
        except (KeyError, TypeError, ValueError):
            continue
        if datetime.now() >= expires_at - timedelta(hours=threshold_hours):
            record = get_cookies(account_id)
            if record is not None:
                record["account_id"] = account_id
                expiring.append(record)
    return expiring
