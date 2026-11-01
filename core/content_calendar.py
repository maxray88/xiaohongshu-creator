#!/usr/bin/env python3
"""Xiaohongshu weekly content calendar planner.

Generates post concepts across emotional sub-pillars through an
OpenAI-compatible LLM, validates niche rotation, and stores the result as
JSON so the surrounding workflow can advance each entry independently.
"""
import json
import logging
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from collections.abc import Callable
from typing import Any

from io_utils import atomic_write_json
from xhs_config import (
    CALENDAR_AUTO_APPROVE_HOURS,
    CALENDAR_MAX_POSTS,
    CALENDAR_MIN_POSTS,
    DATA_BASE,
)

logger = logging.getLogger(__name__)


CALENDAR_PATH = os.path.join(DATA_BASE, "calendar.json")


@dataclass(frozen=True)
class Niche:
    name_zh: str
    posts_per_week: int


DEFAULT_NICHES = [
    Niche("情绪树洞", 2),
    Niche("说说话，被听见", 2),
    Niche("职场反内耗", 2),
    Niche("恋爱清醒脑", 2),
    Niche("社交焦虑自救", 2),
    Niche("当地年轻人精神状态实录", 3),
]


CALENDAR_SYSTEM_PROMPT = (
    "You are a content calendar planner for Xiaohongshu."
)


def _build_calendar_prompt(
    niches: list[Niche],
    last_week_titles: list[str],
    week_start: str,
) -> str:
    niche_descriptions = "\n".join(
        f"- {niche.name_zh}: posts/week={niche.posts_per_week}"
        for niche in niches
    )
    last_titles = "\n".join(f"- {title}" for title in last_week_titles[-20:]) or "(none)"
    return (
        f"Generate a content calendar for the week of {week_start}.\n\n"
        f"Niches:\n{niche_descriptions}\n\n"
        f"Last week's titles (avoid repetition):\n{last_titles}\n\n"
        f"Generate {CALENDAR_MIN_POSTS}-{CALENDAR_MAX_POSTS} post concepts.\n"
        f"Constraints:\n"
        f"- Each niche gets at least 1 post in a week\n"
        f"- No niche gets more than its posts/week quota\n"
        f"- Total posts: {CALENDAR_MIN_POSTS}-{CALENDAR_MAX_POSTS}\n\n"
        f"Return a JSON array. Each element must have:\n"
        f'  "niche": "<Chinese niche name>",\n'
        f'  "title": "<post title in Chinese>",\n'
        f'  "slide_outline": [<7 slide text descriptions>],\n'
        f'  "comfyui_prompt": "<English image style prompt>",\n'
        f'  "edge_tts_script": "<narration script in Chinese>",\n'
        f'  "xhs_topics": "<comma-separated XHS topic tags>"\n'
    )


def _call_llm(prompt: str) -> str:
    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=os.environ.get("LLM_API_KEY", ""),
            base_url=os.environ.get("LLM_API_URL", ""),
        )
        response = client.chat.completions.create(
            model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": CALENDAR_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.8,
        )
        return response.choices[0].message.content or "[]"
    except Exception:
        logger.error("LLM call failed", exc_info=True)
        return "[]"


def _parse_calendar_response(raw: str) -> list[dict[str, Any]]:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    return []


def _validate_niche_rotation(
    entries: list[dict[str, Any]],
    niches: list[Niche],
) -> list[dict[str, Any]]:
    from collections import Counter

    niche_names = {niche.name_zh: niche for niche in niches}
    counts: Counter[str] = Counter()
    valid: list[dict[str, Any]] = []

    for entry in entries:
        niche_name = entry.get("niche", "")
        if niche_name not in niche_names:
            logger.warning(f"Unknown niche: {niche_name}, skipping")
            continue
        niche = niche_names[niche_name]
        if counts[niche_name] >= niche.posts_per_week:
            logger.warning(
                f"Niche {niche_name} already at max "
                f"({niche.posts_per_week}), skipping"
            )
            continue
        counts[niche_name] += 1
        valid.append(entry)

    for niche in niches:
        if counts[niche.name_zh] == 0:
            logger.warning(f"Niche {niche.name_zh} has 0 posts this week")

    return valid


def _read_last_week_titles() -> list[str]:
    path = os.path.join(DATA_BASE, "published_content.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("published content must be a list")
        return [
            str(entry["title"])
            for entry in data
            if isinstance(entry, dict) and "title" in entry
        ]
    except (OSError, json.JSONDecodeError, ValueError, TypeError, KeyError) as e:
        logger.error("Failed to read published_content.json", exc_info=True)
        return []


def generate_weekly_calendar(
    week_start: date | None = None,
    niches: list[Niche] | None = None,
    last_week_titles: list[str] | None = None,
    llm_caller: Callable[[str], str] | None = None,
) -> list[dict[str, Any]]:
    if week_start is None:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
    if niches is None:
        niches = DEFAULT_NICHES
    if last_week_titles is None:
        last_week_titles = _read_last_week_titles()

    prompt = _build_calendar_prompt(niches, last_week_titles, week_start.isoformat())
    if llm_caller is not None:
        raw = llm_caller(prompt)
    else:
        raw = _call_llm(prompt)

    entries = _parse_calendar_response(raw)
    entries = _validate_niche_rotation(entries, niches)
    created_at = datetime.now().isoformat()
    persisted = [
        {
            "week_start_date": week_start.isoformat(),
            "niche": entry.get("niche", ""),
            "title": entry.get("title", ""),
            "slide_outline": entry.get("slide_outline", []),
            "comfyui_prompt": entry.get("comfyui_prompt", ""),
            "edge_tts_script": entry.get("edge_tts_script", ""),
            "xhs_topics": entry.get("xhs_topics", ""),
            "status": "pending",
            "created_at": created_at,
        }
        for entry in entries
    ]

    os.makedirs(os.path.dirname(CALENDAR_PATH), exist_ok=True)
    atomic_write_json(CALENDAR_PATH, persisted)
    logger.info(
        f"Generated {len(persisted)} calendar entries for week {week_start}"
    )
    return persisted


def auto_approve_calendar(week_start: date | None = None) -> int:
    if week_start is None:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())

    if not os.path.isfile(CALENDAR_PATH):
        return 0
    try:
        with open(CALENDAR_PATH, encoding="utf-8") as f:
            entries = json.load(f)
    except (OSError, json.JSONDecodeError):
        return 0
    if not isinstance(entries, list):
        return 0

    now = datetime.now()
    approved = 0
    week_key = week_start.isoformat()
    for entry in entries:
        if not (
            isinstance(entry, dict)
            and entry.get("week_start_date") == week_key
            and entry.get("status") == "pending"
        ):
            continue
        created_at_str = entry.get("created_at")
        if not created_at_str:
            continue
        try:
            created = datetime.fromisoformat(created_at_str)
        except (ValueError, TypeError):
            logger.warning("Invalid created_at in calendar entry, skipping")
            continue
        elapsed_hours = (now - created).total_seconds() / 3600
        if elapsed_hours >= CALENDAR_AUTO_APPROVE_HOURS:
            entry["status"] = "approved"
            approved += 1

    if approved:
        atomic_write_json(CALENDAR_PATH, entries)
        logger.info(
            f"Auto-approved {approved} calendar entries older than "
            f"{CALENDAR_AUTO_APPROVE_HOURS}h"
        )
    return approved
