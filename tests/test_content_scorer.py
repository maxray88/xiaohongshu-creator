#!/usr/bin/env python3
"""content_scorer 的 5 维评分解析与零开销降级测试。

全部用注入 llm_caller，不触网、不耗 quota。
运行：python3 -m pytest tests/test_content_scorer.py -q
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core"))
import content_scorer as S  # noqa: E402


def _caller(payload):
    return lambda _system, _user: payload


def test_full_scores_pass():
    payload = json.dumps({key: 8.0 for key in (
        "relevance", "naturalness", "persona_consistency",
        "platform_fit", "engagement_potential",
    )})
    score = S.score_content("标题", "正文。", ["#情绪"], "情绪树洞", llm_caller=_caller(payload))
    assert score.average == 8.0
    assert score.passed is True


def test_fenced_json_parsed():
    payload = '''```json
{"relevance": 8, "naturalness": 7, "persona_consistency": 7,
 "platform_fit": 7, "engagement_potential": 7}
```'''
    score = S.score_content("标题", "正文。", [], "情绪树洞", llm_caller=_caller(payload))
    assert score.relevance == 8.0
    assert score.naturalness == 7.0
    assert score.engagement_potential == 7.0


def test_malformed_response_scores_zero():
    score = S.score_content("标题", "正文。", [], "情绪树洞", llm_caller=_caller("not json"))
    assert score.average == 0.0
    assert score.passed is False


def test_missing_keys_default_zero():
    payload = json.dumps({"relevance": 8, "naturalness": 7})
    score = S.score_content("标题", "正文。", [], "情绪树洞", llm_caller=_caller(payload))
    assert score.relevance == 8.0
    assert score.naturalness == 7.0
    assert score.persona_consistency == 0.0
    assert score.platform_fit == 0.0
    assert score.engagement_potential == 0.0


def test_empty_content_skips_llm():
    calls = []
    def recording_caller(_system, _user):
        calls.append((_system, _user))
        return "{}"

    score = S.score_content("", "", [], "情绪树洞", llm_caller=recording_caller)
    assert score.average == 0.0
    assert calls == []


def test_threshold_boundary():
    exact = S.QualityScore(8.0, 6.0, 7.0, 7.0, 7.0)
    below = S.QualityScore(7.0, 7.0, 7.0, 7.0, 6.5)
    assert exact.average == 7.0
    assert exact.passed is True
    assert below.average == 6.9
    assert below.passed is False


def test_score_day_missing_post_data(tmp_path):
    calls = []
    def recording_caller(_system, _user):
        calls.append((_system, _user))
        return "{}"

    score = S.score_day(str(tmp_path), llm_caller=recording_caller)
    assert score.average == 0.0
    assert calls == []


def test_short_form_calibration_present():
    short_prompt = S._build_scoring_prompt("t", "short", [], "s", short_form=True)
    long_prompt = S._build_scoring_prompt("t", "short", [], "s", short_form=False)
    assert "SHORT social media comment" in short_prompt
    assert "SHORT social media comment" not in long_prompt


def test_short_form_flag_plumbed():
    import commenting as C

    captured: list = []

    def recording_caller(_system: str, user: str) -> str:
        captured.append(user)
        return json.dumps({key: 8.0 for key in (
            "relevance", "naturalness", "persona_consistency",
            "platform_fit", "engagement_potential",
        )})

    S.score_content("t", "short", [], "s", llm_caller=recording_caller)
    assert captured and "SHORT" not in captured[-1]

    captured.clear()
    candidate = C.CommentCandidate("short and warm")
    C.score_comment(candidate, "s", llm_caller=recording_caller)
    assert captured and "SHORT" in captured[-1]
    assert "Do NOT penalize brevity" in captured[-1]
