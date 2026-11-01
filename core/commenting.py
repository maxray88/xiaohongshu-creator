#!/usr/bin/env python3
"""评论区候选生成、评分与互动节拍。

本模块只提供决策与时间线，不做浏览器或 CDP 操作。
"""
import json
import logging
import os
import random
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from content_scorer import QualityScore, score_content
from xhs_config import (
    ENGAGEMENT_DELAYS,
    HOSTILE_STOP_HOURS,
    LIKE_SAVE_WAIT_MAX_SEC,
    LIKE_SAVE_WAIT_MIN_SEC,
    QUALITY_SCORE_THRESHOLD,
    REPLY_DELAY_MAX_MIN,
    REPLY_DELAY_MIN_MIN,
    REPLY_MAX_PER_THREAD,
)

logger = logging.getLogger(__name__)


@dataclass
class CommentCandidate:
    content: str
    score: QualityScore | None = None


COMMENT_SYSTEM_PROMPT = (
    "You are a commenter on Xiaohongshu (小红书). "
    "Generate comments that are emoji-rich, supportive, and conversational. "
    "Use XHS-specific expressions: 姐妹说得太对了, 收藏了, 代入感太强了. "
    "Comments should be 1-2 sentences, natural, and persona-consistent."
)


def _build_comment_prompt(post_title: str, post_body: str, persona: str) -> str:
    return (
        f"Post title: {post_title}\n"
        f"Post body: {post_body}\n"
        f"Your persona: {persona}\n\n"
        f"Generate 3 different comment candidates. Return a JSON array of 3 strings."
    )


def _call_llm(system_prompt: str, user_prompt: str) -> str:
    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=os.environ.get("LLM_API_KEY", ""),
            base_url=os.environ.get("LLM_API_URL", ""),
        )
        response = client.chat.completions.create(
            model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.9,
        )
        return response.choices[0].message.content or "[]"
    except Exception:
        logger.error("LLM call failed", exc_info=True)
        return "[]"


def generate_comment_candidates(
    post_title: str,
    post_body: str,
    persona: str,
    llm_caller: Callable[[str, str], str] | None = None,
) -> list[CommentCandidate]:
    prompt = _build_comment_prompt(post_title, post_body, persona)
    if llm_caller is not None:
        raw = llm_caller(COMMENT_SYSTEM_PROMPT, prompt)
    else:
        raw = _call_llm(COMMENT_SYSTEM_PROMPT, prompt)

    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])

    try:
        data = json.loads(text)
        return [CommentCandidate(content=item) for item in data if isinstance(item, str)]
    except (json.JSONDecodeError, TypeError):
        logger.error("Failed to parse comment candidates")
        return []


def score_comment(
    candidate: CommentCandidate,
    series: str = "",
    llm_caller: Callable[[str, str], str] | None = None,
) -> CommentCandidate:
    candidate.score = score_content(
        title="",
        body=candidate.content,
        hashtags=[],
        series=series,
        llm_caller=llm_caller,
    )
    return candidate


def select_best_comment(candidates: list[CommentCandidate]) -> CommentCandidate | None:
    scored = [candidate for candidate in candidates if candidate.score is not None]
    if not scored:
        return None

    best = max(scored, key=lambda candidate: candidate.score.average)
    if best.score.average >= QUALITY_SCORE_THRESHOLD:
        return best
    return None


class EngagementSequence:
    def __init__(self, post_id: str, post_url: str):
        self.post_id = post_id
        self.post_url = post_url
        self.actions: list[dict] = []

    def build_timeline(self, num_commenters: int = 3) -> list[dict]:
        timeline: list[dict] = []
        timeline.append({
            "role": "creator_prompt",
            "delay_min": random.randint(
                ENGAGEMENT_DELAYS["creator_prompt_min"],
                ENGAGEMENT_DELAYS["creator_prompt_max"],
            ),
            "action": "comment",
        })

        commenter_slots = [
            (
                "commenter_a",
                ENGAGEMENT_DELAYS["commenter_a_min"],
                ENGAGEMENT_DELAYS["commenter_a_max"],
            ),
            (
                "commenter_b",
                ENGAGEMENT_DELAYS["commenter_b_min"],
                ENGAGEMENT_DELAYS["commenter_b_max"],
            ),
            (
                "commenter_c",
                ENGAGEMENT_DELAYS["commenter_c_min"],
                ENGAGEMENT_DELAYS["commenter_c_max"],
            ),
        ]
        for role, min_delay, max_delay in commenter_slots[:max(0, num_commenters)]:
            timeline.append({
                "role": role,
                "delay_min": random.randint(min_delay, max_delay),
                "actions": ["like", "save", "wait", "comment"],
            })

        timeline.append({
            "role": "creator_reply",
            "delay_min": random.randint(
                ENGAGEMENT_DELAYS["creator_reply_min"],
                ENGAGEMENT_DELAYS["creator_reply_max"],
            ),
            "action": "reply_to_commenter_a",
        })

        if num_commenters == 1:
            # 保留 prompt → commenter → reply 的阅读顺序。
            timeline[2]["delay_min"] = max(timeline[2]["delay_min"], timeline[1]["delay_min"])
        else:
            timeline.sort(key=lambda item: item["delay_min"])

        self.actions = timeline
        return timeline

    def get_like_save_wait(self) -> int:
        return random.randint(LIKE_SAVE_WAIT_MIN_SEC, LIKE_SAVE_WAIT_MAX_SEC)


HOSTILE_KEYWORDS = [
    "骗子", "广告", "举报", "恶心", "滚", "傻", "fake", "scam",
]


def is_hostile(text: str) -> bool:
    lower = text.lower()
    return any(keyword in lower for keyword in HOSTILE_KEYWORDS)


def generate_reply_delay() -> int:
    return random.randint(REPLY_DELAY_MIN_MIN, REPLY_DELAY_MAX_MIN)


def should_stop_replying(thread_reply_count: int) -> bool:
    return thread_reply_count >= REPLY_MAX_PER_THREAD


def calculate_hostile_stop_until() -> datetime:
    return datetime.now() + timedelta(hours=HOSTILE_STOP_HOURS)


def check_reply_thread(reply_count: int, last_reply_text: str) -> dict:
    if is_hostile(last_reply_text):
        return {
            "action": "stop",
            "reason": "hostile_detected",
            "stop_until": calculate_hostile_stop_until().isoformat(),
        }
    if should_stop_replying(reply_count):
        return {
            "action": "stop",
            "reason": "max_replies_reached",
        }
    return {
        "action": "reply",
        "delay_min": generate_reply_delay(),
    }
