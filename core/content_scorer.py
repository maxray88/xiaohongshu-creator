#!/usr/bin/env python3
"""V1 内容 5 维 LLM 评分（relevance / naturalness / persona_consistency /
platform_fit / engagement_potential），均值 >= QUALITY_SCORE_THRESHOLD 通过。

与 02:15 的确定性红线门互补：红线门零 LLM 开销做硬拦截，本模块打分做
 graduated 质量评估。llm_caller 注入供测试与上游复用（design 原案模式）；
缺省 _call_llm 走 OpenAI-compatible endpoint。
"""
import json
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass

from xhs_config import QUALITY_SCORE_THRESHOLD

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QualityScore:
    relevance: float
    naturalness: float
    persona_consistency: float
    platform_fit: float
    engagement_potential: float

    @property
    def average(self) -> float:
        return (self.relevance + self.naturalness + self.persona_consistency
                + self.platform_fit + self.engagement_potential) / 5.0

    @property
    def passed(self) -> bool:
        return self.average >= QUALITY_SCORE_THRESHOLD


SCORING_SYSTEM_PROMPT = (
    "You are a content quality scorer for Xiaohongshu (小红书). "
    "Score the given content on 5 dimensions, each from 1-10:\n"
    "1. relevance: How relevant is the content to the niche and topic?\n"
    "2. naturalness: Does it sound like a real person wrote it?\n"
    "3. persona_consistency: Is the tone consistent with the niche persona?\n"
    "4. platform_fit: Does it fit XHS style (emoji, conversational, relatable)?\n"
    "5. engagement_potential: Will it drive comments and saves?\n"
)


def _build_scoring_prompt(
    title: str,
    body: str,
    hashtags: list,
    series_or_niche: str,
) -> str:
    body_text = (body or "")[:2000]
    return (
        f"Niche: {series_or_niche}\n"
        f"Title: {title}\n"
        f"Content:\n{body_text}\n"
        f"Hashtags: {hashtags}\n\n"
        f'Return JSON: {{"relevance": <float>, "naturalness": <float>, '
        f'"persona_consistency": <float>, "platform_fit": <float>, '
        f'"engagement_potential": <float>}}'
    )


def _call_llm(system_prompt: str, user_prompt: str) -> str:
    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=os.environ.get("LLM_API_KEY", ""),
            base_url=os.environ.get("LLM_API_URL", ""),
        )
        # 02:15 集成会显式传 llm_caller；这里是仅用于直接调用的兜底默认。
        response = client.chat.completions.create(
            model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content or "{}"
    except Exception:
        logger.error("LLM call failed", exc_info=True)
        return "{}"


def score_content(
    title: str,
    body: str,
    hashtags: list,
    series: str,
    llm_caller: Callable[[str, str], str] | None = None,
) -> QualityScore:
    if not (body or "").strip() and not (title or "").strip():
        return QualityScore(0, 0, 0, 0, 0)

    title = title or ""
    hashtags = hashtags or []
    prompt = _build_scoring_prompt(title, body, hashtags, series)

    if llm_caller is not None:
        raw = llm_caller(SCORING_SYSTEM_PROMPT, prompt)
    else:
        raw = _call_llm(SCORING_SYSTEM_PROMPT, prompt)

    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])

    try:
        data = json.loads(text)
        return QualityScore(
            relevance=float(data.get("relevance", 0)),
            naturalness=float(data.get("naturalness", 0)),
            persona_consistency=float(data.get("persona_consistency", 0)),
            platform_fit=float(data.get("platform_fit", 0)),
            engagement_potential=float(data.get("engagement_potential", 0)),
        )
    except (json.JSONDecodeError, ValueError, TypeError, AttributeError) as e:
        logger.error("Failed to parse score", exc_info=True)
        return QualityScore(0, 0, 0, 0, 0)


def score_day(v1_dir: str, llm_caller: Callable[[str, str], str] | None = None) -> QualityScore:
    try:
        with open(os.path.join(v1_dir, "post_data.json"), encoding="utf-8") as f:
            post_data = json.load(f)
    except (OSError, json.JSONDecodeError, TypeError, AttributeError) as e:
        logger.error(f"Failed to read post_data.json: {e}")
        return QualityScore(0, 0, 0, 0, 0)

    series = (post_data.get("series") or "").strip()
    emotion_tag = (post_data.get("emotion_tag") or "").strip()
    series_or_niche = " / ".join(part for part in (emotion_tag, series) if part)
    return score_content(
        post_data.get("title", ""),
        post_data.get("content_text", ""),
        post_data.get("hashtags", []),
        series_or_niche,
        llm_caller=llm_caller,
    )
