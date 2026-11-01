#!/usr/bin/env python3
"""seed_test_comments.py 的安全护栏回归测试。

TEST-ACCOUNT-ONLY try-out 工具：默认 DRY RUN、端口 allowlist、
kill-switch、每日硬上限。全部用注入 fake，不触网、不耗 quota。
运行：python3 -m pytest tests/test_seed_guardrails.py -q（项目根目录）
"""

import importlib.util
import json
import os
import sys
import types
from types import SimpleNamespace

import pytest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
CORE = os.path.join(ROOT, "core")
sys.path.insert(0, CORE)

_spec = importlib.util.spec_from_file_location(
    "seed_test_comments", os.path.join(ROOT, "bin", "seed_test_comments.py"))
seed = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(seed)


class FakeCDPError(Exception):
    pass


class FakePublisher:
    instances: list = []
    constructed: list = []

    def __init__(self, **kwargs) -> None:
        FakePublisher.constructed.append(kwargs)
        FakePublisher.instances.append(self)
        self.kwargs = kwargs
        self.posted: list = []
        self.replied: list = []
        self.connected = False
        self.disconnected = False

    def connect(self) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.disconnected = True

    def post_comment_to_feed(self, feed_id: str, xsec_token: str, content: str):
        self.posted.append((feed_id, xsec_token, content))
        return {"ok": True}

    def respond_comment(self, feed_id: str, xsec_token: str, content: str, **kwargs):
        self.replied.append((feed_id, xsec_token, content))
        return {"ok": True}


def _fake_cdp_module() -> types.ModuleType:
    module = types.ModuleType("cdp_publish")
    module.CDPError = FakeCDPError
    module.XiaohongshuPublisher = FakePublisher
    return module


PICKED = "姐妹说得太对了，收藏了"


def _stub_commenting(monkeypatch) -> None:
    """Pre-scored candidate passes the real select_best_comment threshold."""
    monkeypatch.setattr(
        seed, "generate_comment_candidates",
        lambda **kwargs: [SimpleNamespace(content=PICKED, score=SimpleNamespace(average=8.0))],
    )
    monkeypatch.setattr(seed, "score_comment", lambda candidate: candidate)


@pytest.fixture()
def isolated(tmp_path, monkeypatch):
    """tmp paths + fake CDP + stubbed LLM + recorded sleeps."""
    monkeypatch.setattr(seed, "COUNTER_PATH", str(tmp_path / "engagement_counter.json"))
    monkeypatch.setattr(seed, "LOG_PATH", str(tmp_path / "engagement_log.jsonl"))
    monkeypatch.setattr(seed, "STOP_PATH", str(tmp_path / "ENGAGEMENT_STOP"))
    _stub_commenting(monkeypatch)
    sleeps: list = []
    monkeypatch.setattr(seed, "_sleep", lambda seconds: sleeps.append(seconds))

    saved = sys.modules.get("cdp_publish")
    sys.modules["cdp_publish"] = _fake_cdp_module()
    FakePublisher.instances = []
    FakePublisher.constructed = []
    try:
        yield sleeps
    finally:
        if saved is None:
            sys.modules.pop("cdp_publish", None)
        else:
            sys.modules["cdp_publish"] = saved


BASE_ARGS = ["--feed-id", "feed123", "--xsec-token", "token123"]


def test_main_port_refused(isolated, capsys):
    rc = seed.main(BASE_ARGS + ["--port", "9224", "--live"])
    out = capsys.readouterr().out
    assert rc == 1
    assert ("main" in out or "9224" in out)
    assert FakePublisher.constructed == []


def test_main_port_9222_refused(isolated, capsys):
    rc = seed.main(BASE_ARGS + ["--port", "9222", "--live"])
    out = capsys.readouterr().out
    assert rc == 1
    assert ("main" in out or "9222" in out)
    assert FakePublisher.constructed == []


def test_dry_run_posts_nothing(isolated):
    rc = seed.main(BASE_ARGS)
    assert rc == 0
    assert FakePublisher.constructed == []
    with open(seed.LOG_PATH, encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]
    assert lines, "dry run must append a log line"
    assert all(entry["dry_run"] is True for entry in lines)


def test_daily_cap_enforced(isolated, capsys):
    with open(seed.COUNTER_PATH, "w", encoding="utf-8") as f:
        json.dump({seed._today_key(): seed.TRYOUT_HARD_CAP_PER_DAY}, f)
    rc = seed.main(BASE_ARGS + ["--live"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "cap" in out.lower()
    assert FakePublisher.constructed == []


def test_kill_switch(isolated, capsys):
    with open(seed.STOP_PATH, "w", encoding="utf-8") as f:
        f.write("stop\n")
    rc = seed.main(BASE_ARGS + ["--live"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "kill" in out.lower() or "STOP" in out
    assert FakePublisher.constructed == []


def test_live_happy_path_records_counter(isolated):
    rc = seed.main(BASE_ARGS + ["--port", "9229", "--live"])
    assert rc == 0
    assert len(FakePublisher.constructed) == 1
    assert FakePublisher.constructed[0].get("port") == 9229
    assert FakePublisher.constructed[0].get("account_name") == seed.TEST_ACCOUNT_SCOPE
    inst = FakePublisher.instances[0]
    assert inst.posted == [("feed123", "token123", PICKED)]
    with open(seed.COUNTER_PATH, encoding="utf-8") as f:
        data = json.load(f)
    assert data[seed._today_key()] == 1
    with open(seed.LOG_PATH, encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]
    assert lines and all(entry["dry_run"] is False for entry in lines)
    assert inst.disconnected is True


def test_jitter_bounds():
    for _ in range(200):
        assert 600.0 <= seed.apply_jitter(10) <= 900.0
