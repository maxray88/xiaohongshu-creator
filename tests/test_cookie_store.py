#!/usr/bin/env python3
"""cookie_store 的 JSON 持久化与过期窗口测试。"""

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core"))
import cookie_store as S  # noqa: E402


def _patch_path(tmp_path, monkeypatch):
    path = tmp_path / "xhs_cookies.json"
    monkeypatch.setattr(S, "COOKIE_PATH", str(path))
    return path


def test_store_and_get_dict_cookies(tmp_path, monkeypatch):
    _patch_path(tmp_path, monkeypatch)
    cookies = {"token": "abc", "secure": True}
    expires_at = datetime.now() + timedelta(hours=10)

    S.store_cookies("dict-account", cookies, expires_at)

    assert S.get_cookies("dict-account") == {
        "cookies": cookies,
        "expires_at": expires_at.isoformat(),
        "updated_at": S.get_cookies("dict-account")["updated_at"],
    }
    assert S.is_expired("dict-account") is False


def test_store_and_get_list_and_string_cookies(tmp_path, monkeypatch):
    _patch_path(tmp_path, monkeypatch)
    list_cookies = [{"name": "web_session", "value": "abc"}]
    string_cookies = "web_session=abc"
    expires_at = datetime.now() + timedelta(hours=10)

    S.store_cookies("list-account", list_cookies, expires_at)
    S.store_cookies("str-account", string_cookies, expires_at)

    assert S.get_cookies("list-account")["cookies"] == list_cookies
    assert S.get_cookies("str-account")["cookies"] == string_cookies
    assert S.is_expired("list-account") is False
    assert S.is_expired("str-account") is False


def test_is_expired_for_missing_past_and_future(tmp_path, monkeypatch):
    _patch_path(tmp_path, monkeypatch)
    now = datetime.now()

    assert S.is_expired("missing") is True

    S.store_cookies("past", {"token": "old"}, now - timedelta(hours=1))
    S.store_cookies("future", {"token": "new"}, now + timedelta(hours=1))

    assert S.is_expired("past") is True
    assert S.is_expired("future") is False


def test_needs_refresh_threshold_behavior(tmp_path, monkeypatch):
    _patch_path(tmp_path, monkeypatch)
    now = datetime.now()

    S.store_cookies("two-hours", {"token": "a"}, now + timedelta(hours=2))
    S.store_cookies("ten-hours", {"token": "b"}, now + timedelta(hours=10))

    assert S.needs_refresh("two-hours") is True
    assert S.needs_refresh("ten-hours") is False
    assert S.needs_refresh("two-hours", threshold_hours=1) is False


def test_malformed_store_is_expired_and_missing(tmp_path, monkeypatch):
    path = _patch_path(tmp_path, monkeypatch)
    path.write_text("{ not json", encoding="utf-8")

    assert S.is_expired("any") is True
    assert S.get_cookies("any") is None


def test_get_all_expiring_soon_includes_expired_and_window(tmp_path, monkeypatch):
    _patch_path(tmp_path, monkeypatch)
    now = datetime.now()

    S.store_cookies("expired", {"token": "a"}, now - timedelta(hours=1))
    S.store_cookies("soon", {"token": "b"}, now + timedelta(hours=2))
    S.store_cookies("far", {"token": "c"}, now + timedelta(hours=10))

    expiring = S.get_all_expiring_soon()

    assert {record["account_id"] for record in expiring} == {"expired", "soon"}
