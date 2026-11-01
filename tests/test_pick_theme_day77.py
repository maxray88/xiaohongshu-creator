#!/usr/bin/env python3
"""day77 回归：当天 V1 已撞近 3 天 V2 时，V2 仍必须可构建。"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core"))

from build_v2_local import pick_theme  # noqa: E402
import build_v2_local as bv  # noqa: E402


FAKE_THEMES = {
    "苔藓墨绿": {"bg": ["#111111"]},
    "莓果粉": {"bg": ["#222222"]},
    "海盐汽水": {"bg": ["#333333"]},
    "雾蓝海湾": {"bg": ["#444444"]},
}


@pytest.fixture
def fake_tokens(tmp_path, monkeypatch):
    d = tmp_path / "design"
    d.mkdir()
    (d / "design_tokens.json").write_text(
        json.dumps({"themes": FAKE_THEMES}, ensure_ascii=False),
        encoding="utf-8")
    monkeypatch.setattr(bv, "PROJ", tmp_path)
    return FAKE_THEMES


def test_day77_v1_duplicated_v2_still_buildable(fake_tokens):
    v1_cs = "苔藓墨绿"
    name, palette = pick_theme(v1_cs, [], [v1_cs])

    assert name != v1_cs
    assert name == "莓果粉"
    assert palette == fake_tokens[name]


def test_normal_case_unchanged(fake_tokens):
    v1_cs = "苔藓墨绿"
    name, palette = pick_theme(v1_cs, [], ["莓果粉"])

    assert name != v1_cs
    assert name == "海盐汽水"
    assert palette == fake_tokens[name]


def test_exhausted_pool_raises_loud(fake_tokens):
    v1_cs = "苔藓墨绿"
    last_v2 = ["莓果粉", "海盐汽水", "雾蓝海湾"]

    with pytest.raises(RuntimeError):
        pick_theme(v1_cs, [], last_v2)
