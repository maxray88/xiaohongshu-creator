#!/usr/bin/env python3
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core"))

from cdp_retry import run_with_retries  # noqa: E402


def test_succeeds_on_third_try():
    calls = []

    def fn():
        calls.append(len(calls) + 1)
        if len(calls) < 3:
            raise ValueError("not ready")
        return "ok"

    assert run_with_retries(fn, backoff=0) == "ok"
    assert calls == [1, 2, 3]


def test_reraises_last_error_after_attempts():
    calls = []
    errors = [ValueError("first"), ValueError("second"), ValueError("third")]

    def fn():
        error = errors[len(calls)]
        calls.append(len(calls) + 1)
        raise error

    try:
        run_with_retries(fn, attempts=3, backoff=0)
    except ValueError as exc:
        assert exc is errors[2]
    else:
        raise AssertionError("run_with_retries must re-raise the last error")
    assert calls == [1, 2, 3]


def test_success_first_try_calls_once(capsys):
    calls = []

    def fn():
        calls.append(len(calls) + 1)
        return "ok"

    assert run_with_retries(fn, backoff=0) == "ok"
    assert calls == [1]
    assert capsys.readouterr().out == ""


def test_zero_attempts_raises_valueerror():
    calls = []

    def fn():
        calls.append(len(calls) + 1)

    with pytest.raises(ValueError):
        run_with_retries(fn, attempts=0)

    assert calls == []
