#!/usr/bin/env python3
"""content_calendar 的 niche 配额与 JSON 持久化测试。"""

import json
import logging
import os
import sys
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core"))
import content_calendar as C  # noqa: E402


def _entry(niche, title="标题"):
    return {
        "niche": niche,
        "title": title,
        "slide_outline": ["一", "二", "三", "四", "五", "六", "七"],
        "comfyui_prompt": "soft illustration",
        "edge_tts_script": "台词",
        "xhs_topics": "情绪",
    }


def _calendar_path(tmp_path):
    return tmp_path / "calendar.json"


def test_validate_caps_quota_and_drops_unknown():
    niches = [C.Niche("情绪树洞", 1), C.Niche("职场反内耗", 2)]
    entries = [
        _entry("情绪树洞", "第一"),
        _entry("情绪树洞", "超额"),
        _entry("职场反内耗", "第一"),
        _entry("职场反内耗", "第二"),
        _entry("不存在的niche", "丢弃"),
    ]

    valid = C._validate_niche_rotation(entries, niches)

    assert [entry["title"] for entry in valid] == ["第一", "第一", "第二"]


def test_validate_warns_for_empty_niche(caplog):
    niches = [C.Niche("情绪树洞", 1), C.Niche("职场反内耗", 2)]

    valid = C._validate_niche_rotation([_entry("情绪树洞")], niches)

    assert len(valid) == 1
    assert "Niche 职场反内耗 has 0 posts this week" in caplog.text
    assert caplog.records[-1].levelno == logging.WARNING


def test_generate_persists_pending_with_dates(tmp_path, monkeypatch):
    calendar_path = _calendar_path(tmp_path)
    monkeypatch.setattr(C, "CALENDAR_PATH", str(calendar_path))
    payload = json.dumps([_entry("情绪树洞"), _entry("职场反内耗")])

    result = C.generate_weekly_calendar(
        week_start=date(2026, 11, 2),
        niches=[C.Niche("情绪树洞", 1), C.Niche("职场反内耗", 1)],
        last_week_titles=[],
        llm_caller=lambda _prompt: payload,
    )

    assert len(result) == 2
    assert all(entry["status"] == "pending" for entry in result)
    assert all(entry["week_start_date"] == "2026-11-02" for entry in result)
    assert all(entry["created_at"] for entry in result)
    assert json.loads(calendar_path.read_text()) == result


def test_malformed_response_persists_empty_list(tmp_path, monkeypatch):
    calendar_path = _calendar_path(tmp_path)
    monkeypatch.setattr(C, "CALENDAR_PATH", str(calendar_path))

    result = C.generate_weekly_calendar(
        week_start=date(2026, 11, 2),
        last_week_titles=[],
        llm_caller=lambda _prompt: "not json",
    )

    assert result == []
    assert json.loads(calendar_path.read_text()) == []


def test_auto_approve_flips_only_old_entries(tmp_path, monkeypatch):
    calendar_path = _calendar_path(tmp_path)
    monkeypatch.setattr(C, "CALENDAR_PATH", str(calendar_path))
    now = datetime.now()
    week = date(2026, 11, 2)
    old = _entry("情绪树洞", "旧")
    fresh = _entry("情绪树洞", "新")
    old.update({
        "week_start_date": week.isoformat(),
        "status": "pending",
        "created_at": (now - timedelta(hours=3)).isoformat(),
    })
    fresh.update({
        "week_start_date": week.isoformat(),
        "status": "pending",
        "created_at": now.isoformat(),
    })
    calendar_path.write_text(json.dumps([old, fresh]), encoding="utf-8")

    approved = C.auto_approve_calendar(week)

    saved = json.loads(calendar_path.read_text())
    assert approved == 1
    assert saved[0]["status"] == "approved"
    assert saved[1]["status"] == "pending"


def test_auto_approve_skips_bad_created_at(tmp_path, monkeypatch):
    calendar_path = _calendar_path(tmp_path)
    monkeypatch.setattr(C, "CALENDAR_PATH", str(calendar_path))
    now = datetime.now()
    week = date(2026, 11, 2)
    missing = _entry("情绪树洞", "缺失")
    malformed = _entry("职场反内耗", "异常")
    nonstring = _entry("情绪树洞", "非字符串")
    old = _entry("当地年轻人精神状态实录", "有效")
    missing.update({
        "week_start_date": week.isoformat(),
        "status": "pending",
    })
    malformed.update({
        "week_start_date": week.isoformat(),
        "status": "pending",
        "created_at": "not-a-date",
    })
    nonstring.update({
        "week_start_date": week.isoformat(),
        "status": "pending",
        "created_at": 12345,
    })
    old.update({
        "week_start_date": week.isoformat(),
        "status": "pending",
        "created_at": (now - timedelta(hours=3)).isoformat(),
    })
    calendar_path.write_text(json.dumps([missing, malformed, nonstring, old]), encoding="utf-8")

    approved = C.auto_approve_calendar(week)

    saved = json.loads(calendar_path.read_text())
    assert approved == 1
    assert saved[0]["status"] == "pending"
    assert saved[1]["status"] == "pending"
    assert saved[2]["status"] == "pending"
    assert saved[3]["status"] == "approved"


def test_default_titles_read_from_published_content(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "DATA_BASE", str(tmp_path))
    monkeypatch.setattr(C, "CALENDAR_PATH", str(_calendar_path(tmp_path)))
    (tmp_path / "published_content.json").write_text(
        json.dumps([{"title": "上周的标题"}], ensure_ascii=False),
        encoding="utf-8",
    )
    prompts = []

    def caller(prompt):
        prompts.append(prompt)
        return "not json"

    C.generate_weekly_calendar(date(2026, 11, 2), llm_caller=caller)

    assert len(prompts) == 1
    assert "上周的标题" in prompts[0]
