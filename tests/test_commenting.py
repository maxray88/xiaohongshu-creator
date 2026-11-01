#!/usr/bin/env python3
"""commenting 的候选解析、评分与互动节拍测试。

全部用注入 llm_caller，不触网、不耗 quota。
运行：python3 -m pytest tests/test_commenting.py -q
"""

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core"))
import commenting as C  # noqa: E402
from content_scorer import QualityScore  # noqa: E402


def _caller(payload):
    return lambda _system, _user: payload


def _score(value):
    return QualityScore(value, value, value, value, value)


def test_generate_parses_three_candidates():
    payload = json.dumps(["说得太对了", "收藏了", "代入感太强了"])
    candidates = C.generate_comment_candidates(
        "标题", "正文。", "情绪树洞", llm_caller=_caller(payload)
    )

    assert len(candidates) == 3
    assert candidates[0].content == "说得太对了"
    assert candidates[1].content == "收藏了"
    assert candidates[2].content == "代入感太强了"
    assert all(candidate.score is None for candidate in candidates)


def test_generate_malformed_returns_empty():
    candidates = C.generate_comment_candidates(
        "标题", "正文。", "情绪树洞", llm_caller=_caller("oops")
    )
    assert candidates == []


def test_score_comment_attaches_score():
    payload = json.dumps({key: 8.0 for key in (
        "relevance", "naturalness", "persona_consistency",
        "platform_fit", "engagement_potential",
    )})
    candidate = C.CommentCandidate("这条真的戳到我了")

    scored = C.score_comment(candidate, "情绪树洞", llm_caller=_caller(payload))

    assert scored is candidate
    assert candidate.score is not None
    assert candidate.score.average == 8.0


def test_select_best_threshold():
    high = C.CommentCandidate("高", score=_score(8.0))
    low = C.CommentCandidate("低", score=_score(6.0))
    unscored = C.CommentCandidate("未评分")
    assert C.select_best_comment([high, low, unscored]) is high

    below = [C.CommentCandidate("第一", score=_score(6.0)), C.CommentCandidate("第二", score=_score(6.9))]
    assert C.select_best_comment(below) is None
    assert C.select_best_comment([]) is None


def test_timeline_structure_and_order():
    sequence = C.EngagementSequence("post-id", "https://example.com/post")
    timeline = sequence.build_timeline(3)

    assert len(timeline) == 5
    assert {item["role"] for item in timeline} == {
        "creator_prompt", "creator_reply", "commenter_a",
        "commenter_b", "commenter_c",
    }
    delays = [item["delay_min"] for item in timeline]
    assert delays == sorted(delays)
    assert "commenter_c" in {item["role"] for item in timeline}
    assert sequence.post_id == "post-id"
    assert sequence.post_url == "https://example.com/post"

    one = sequence.build_timeline(1)
    assert [item["role"] for item in one] == [
        "creator_prompt", "commenter_a", "creator_reply"
    ]
    one_delays = [item["delay_min"] for item in one]
    assert one_delays == sorted(one_delays)


def test_hostile_stops_thread():
    result = C.check_reply_thread(0, "你是骗子")

    assert result["action"] == "stop"
    assert result["reason"] == "hostile_detected"
    assert "stop_until" in result
    assert isinstance(datetime.fromisoformat(result["stop_until"]), datetime)


def test_max_replies_stops():
    result = C.check_reply_thread(2, "谢谢你的支持")
    assert result == {"action": "stop", "reason": "max_replies_reached"}


def test_normal_reply():
    result = C.check_reply_thread(0, "谢谢你的支持")

    assert result["action"] == "reply"
    assert 15 <= result["delay_min"] <= 60
