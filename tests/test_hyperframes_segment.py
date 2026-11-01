import os
import sys
from types import SimpleNamespace

import pytest


sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core"))
import ffmpeg_build as F  # noqa: E402


@pytest.fixture
def fake_run(monkeypatch):
    calls = []

    def fake(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(F.subprocess, "run", fake)
    monkeypatch.setattr(F, "hyperframes_available", lambda: True)
    return calls


def test_success_nonempty_returns_true(tmp_path, fake_run):
    out = tmp_path / "seg.mp4"
    out.write_bytes(b"x")

    assert F.render_segment("card.jpg", 6.0, str(out)) is True


def test_zero_byte_counts_as_failure(tmp_path, fake_run):
    out = tmp_path / "seg.mp4"
    out.touch()

    assert F.render_segment("card.jpg", 6.0, str(out)) is False


def test_nonzero_rc_returns_false(tmp_path, monkeypatch):
    monkeypatch.setattr(F.subprocess, "run", lambda cmd, **kwargs: SimpleNamespace(returncode=1))
    monkeypatch.setattr(F, "hyperframes_available", lambda: True)
    out = tmp_path / "seg.mp4"
    out.write_bytes(b"x")

    assert F.render_segment("card.jpg", 6.0, str(out)) is False


def test_cli_missing_returns_false(tmp_path, monkeypatch):
    def fail_run(cmd, **kwargs):
        raise AssertionError("subprocess.run must not be called")

    monkeypatch.setattr(F.subprocess, "run", fail_run)
    monkeypatch.setattr(F, "hyperframes_available", lambda: False)
    out = tmp_path / "seg.mp4"

    assert F.render_segment("card.jpg", 6.0, str(out)) is False


def test_run_raises_returns_false(tmp_path, monkeypatch):
    """subprocess.run raising (missing binary) → False via except branch."""
    out = tmp_path / "seg.mp4"
    out.write_bytes(b"x")

    def boom(cmd, **kwargs):
        raise FileNotFoundError("no hyperframes binary")

    monkeypatch.setattr(F, "hyperframes_available", lambda: True)
    monkeypatch.setattr(F.subprocess, "run", boom)

    assert F.render_segment("in.jpg", 6.9, str(out)) is False
