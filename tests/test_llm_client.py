#!/usr/bin/env python3
"""llm_client chat-first with responses fallback tests. Fakes only, no network."""

import os
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core"))
import llm_client as L  # noqa: E402


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeChatResponse:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class _FakeResponsesResponse:
    def __init__(self, text):
        self.output_text = text


def _install_fake(chat_behavior, responses_behavior, client_raises=False):
    """chat_behavior/responses_behavior: value to return or Exception to raise."""
    saved = sys.modules.get("openai")
    state = {"chat_called": False, "responses_called": False}

    class FakeCompletions:
        def create(self, **kwargs):
            state["chat_called"] = True
            if isinstance(chat_behavior, Exception):
                raise chat_behavior
            return _FakeChatResponse(chat_behavior)

    class FakeResponses:
        def create(self, **kwargs):
            state["responses_called"] = True
            if isinstance(responses_behavior, Exception):
                raise responses_behavior
            return _FakeResponsesResponse(responses_behavior)

    class FakeClient:
        def __init__(self, *a, **k):
            if client_raises:
                raise RuntimeError("init boom")
            self.chat = types.SimpleNamespace(completions=FakeCompletions())
            self.responses = FakeResponses()

    module = types.ModuleType("openai")
    module.OpenAI = FakeClient
    sys.modules["openai"] = module
    return saved, state


@pytest.fixture()
def restore_openai():
    saved = sys.modules.get("openai")
    yield
    if saved is None:
        sys.modules.pop("openai", None)
    else:
        sys.modules["openai"] = saved


def test_chat_content_returned_without_responses(restore_openai):
    saved, state = _install_fake("hello", "fallback-text")
    try:
        assert L.call_llm("sys", "user") == "hello"
        assert state["chat_called"] is True
        assert state["responses_called"] is False
    finally:
        if saved is None:
            sys.modules.pop("openai", None)
        else:
            sys.modules["openai"] = saved


def test_chat_none_content_falls_back_to_responses(restore_openai):
    saved, state = _install_fake(None, "resp-text")
    try:
        assert L.call_llm("sys", "user") == "resp-text"
        assert state["chat_called"] is True
        assert state["responses_called"] is True
    finally:
        if saved is None:
            sys.modules.pop("openai", None)
        else:
            sys.modules["openai"] = saved


def test_chat_empty_string_falls_back_to_responses(restore_openai):
    saved, state = _install_fake("   ", "resp-text")
    try:
        assert L.call_llm("sys", "user") == "resp-text"
        assert state["responses_called"] is True
    finally:
        if saved is None:
            sys.modules.pop("openai", None)
        else:
            sys.modules["openai"] = saved


def test_chat_raises_falls_back_to_responses(restore_openai):
    saved, state = _install_fake(RuntimeError("chat boom"), "resp-text")
    try:
        assert L.call_llm("sys", "user") == "resp-text"
        assert state["responses_called"] is True
    finally:
        if saved is None:
            sys.modules.pop("openai", None)
        else:
            sys.modules["openai"] = saved


def test_both_raise_returns_empty(restore_openai):
    saved, state = _install_fake(RuntimeError("chat boom"), RuntimeError("resp boom"))
    try:
        assert L.call_llm("sys", "user") == ""
    finally:
        if saved is None:
            sys.modules.pop("openai", None)
        else:
            sys.modules["openai"] = saved


def test_client_construction_raises_returns_empty(restore_openai):
    saved, state = _install_fake("hello", "resp", client_raises=True)
    try:
        assert L.call_llm("sys", "user") == ""
    finally:
        if saved is None:
            sys.modules.pop("openai", None)
        else:
            sys.modules["openai"] = saved
