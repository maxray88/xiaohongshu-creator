#!/usr/bin/env python3
"""Shared OpenAI-compatible LLM caller.

Tries chat.completions first, falls back to the responses API when chat
returns no content (this machine's gateway only serves responses properly).
Returns "" when both fail — callers treat "" as empty/malformed and fall
back to their zero/empty defaults. Never raises, never logs secrets.
"""
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def _client():
    from openai import OpenAI
    return OpenAI(
        api_key=os.environ.get("LLM_API_KEY", ""),
        base_url=os.environ.get("LLM_API_URL", ""),
    )


def call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.3,
             model: str | None = None) -> str:
    model = model or os.environ.get("LLM_MODEL", "gpt-4o-mini")
    try:
        client = _client()
    except Exception:
        logger.error("LLM client init failed", exc_info=True)
        return ""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system_prompt},
                      {"role": "user", "content": user_prompt}],
            temperature=temperature,
        )
        content = (response.choices[0].message.content or "").strip()
        if content:
            return content
    except Exception:
        logger.error("LLM chat call failed", exc_info=True)
    try:
        response = client.responses.create(
            model=model,
            instructions=system_prompt,
            input=user_prompt,
            temperature=temperature,
        )
        return (response.output_text or "").strip()
    except Exception:
        logger.error("LLM responses call failed", exc_info=True)
        return ""
