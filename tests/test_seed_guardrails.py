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


def _write_pool(tmp_path, entries):
    pool_path = tmp_path / "engagement_pool.json"
    pool_path.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")
    return str(pool_path)


def _boom_llm(*args, **kwargs):
    raise AssertionError("LLM must not be called in pool mode")


def test_pool_mode_posts_without_llm(isolated, tmp_path, monkeypatch):
    pool_path = _write_pool(tmp_path, [{"text": "人工审核过的暖心评论"}])
    monkeypatch.setattr(seed, "generate_comment_candidates", _boom_llm)
    monkeypatch.setattr(seed, "score_comment", _boom_llm)
    monkeypatch.setattr(seed, "select_best_comment", _boom_llm)
    rc = seed.main(BASE_ARGS + ["--live", "--pool", pool_path])
    assert rc == 0
    inst = FakePublisher.instances[-1]
    assert inst.posted == [("feed123", "token123", "人工审核过的暖心评论")]
    data = json.loads(open(pool_path, encoding="utf-8").read())
    assert data[0].get("used") is True
    assert data[0].get("posted_at")
    with open(seed.LOG_PATH, encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]
    assert lines and all(entry["dry_run"] is False for entry in lines)


def test_pool_exhausted_fails_loud(isolated, tmp_path, monkeypatch, capsys):
    pool_path = _write_pool(tmp_path, [{"text": "used one", "used": True}])
    monkeypatch.setattr(seed, "generate_comment_candidates", _boom_llm)
    monkeypatch.setattr(seed, "score_comment", _boom_llm)
    monkeypatch.setattr(seed, "select_best_comment", _boom_llm)
    rc = seed.main(BASE_ARGS + ["--live", "--pool", pool_path])
    out = capsys.readouterr().out
    assert rc == 1
    assert "exhausted" in out.lower()
    assert FakePublisher.constructed == []


def test_pool_dry_run_marks_nothing(isolated, tmp_path, monkeypatch):
    pool_path = _write_pool(tmp_path, [{"text": "dry-run pool text"}])
    monkeypatch.setattr(seed, "generate_comment_candidates", _boom_llm)
    monkeypatch.setattr(seed, "score_comment", _boom_llm)
    monkeypatch.setattr(seed, "select_best_comment", _boom_llm)
    rc = seed.main(BASE_ARGS + ["--pool", pool_path])
    assert rc == 0
    data = json.loads(open(pool_path, encoding="utf-8").read())
    assert data[0].get("used") is not True
    assert "posted_at" not in data[0]
    assert FakePublisher.constructed == []
    with open(seed.LOG_PATH, encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]
    assert lines and all(entry["dry_run"] is True for entry in lines)


def test_pool_malformed_entry_skipped(isolated, tmp_path):
    pool_path = _write_pool(tmp_path, [{"nonsense": 1}, {"text": ""}, {"text": "ok"}])
    rc = seed.main(BASE_ARGS + ["--live", "--pool", pool_path])
    assert rc == 0
    inst = FakePublisher.instances[-1]
    assert inst.posted == [("feed123", "token123", "ok")]


def test_pool_multi_entry_max_comments(isolated, tmp_path):
    pool_path = _write_pool(tmp_path, [{"text": "c1"}, {"text": "c2"}, {"text": "c3"}])
    rc = seed.main(BASE_ARGS + ["--live", "--pool", pool_path, "--max-comments", "3"])
    assert rc == 0
    inst = FakePublisher.instances[-1]
    assert inst.posted == [
        ("feed123", "token123", "c1"),
        ("feed123", "token123", "c2"),
        ("feed123", "token123", "c3"),
    ]
    with open(seed.COUNTER_PATH, encoding="utf-8") as f:
        data = json.load(f)
    assert data[seed._today_key()] == 3
    pool = json.loads(open(pool_path, encoding="utf-8").read())
    assert all(e.get("used") is True and e.get("posted_at") for e in pool)


def test_pool_partial_cap_posts_remainder(isolated, tmp_path):
    pool_path = _write_pool(tmp_path, [{"text": "c1"}, {"text": "c2"}, {"text": "c3"}])
    with open(seed.COUNTER_PATH, "w", encoding="utf-8") as f:
        json.dump({seed._today_key(): 1}, f)
    rc = seed.main(BASE_ARGS + ["--live", "--pool", pool_path, "--max-comments", "3"])
    assert rc == 0
    inst = FakePublisher.instances[-1]
    assert inst.posted == [
        ("feed123", "token123", "c1"),
        ("feed123", "token123", "c2"),
    ]
    with open(seed.COUNTER_PATH, encoding="utf-8") as f:
        data = json.load(f)
    assert data[seed._today_key()] == 3
    pool = json.loads(open(pool_path, encoding="utf-8").read())
    assert pool[0].get("used") is True and pool[0].get("posted_at")
    assert pool[1].get("used") is True and pool[1].get("posted_at")
    assert pool[2].get("used") is not True
    assert "posted_at" not in pool[2]


def test_pool_mid_batch_failure_keeps_first_marked(isolated, tmp_path, monkeypatch):
    pool_path = _write_pool(tmp_path, [{"text": "c1"}, {"text": "c2"}])
    orig = FakePublisher.post_comment_to_feed

    def flaky(self, feed_id, xsec_token, content):
        if len(self.posted) >= 1:
            raise FakeCDPError("boom")
        return orig(self, feed_id, xsec_token, content)

    monkeypatch.setattr(FakePublisher, "post_comment_to_feed", flaky)
    rc = seed.main(BASE_ARGS + ["--live", "--pool", pool_path, "--max-comments", "2"])
    assert rc == 1
    inst = FakePublisher.instances[-1]
    assert inst.posted == [("feed123", "token123", "c1")]
    with open(seed.COUNTER_PATH, encoding="utf-8") as f:
        data = json.load(f)
    assert data[seed._today_key()] == 1
    pool = json.loads(open(pool_path, encoding="utf-8").read())
    assert pool[0].get("used") is True and pool[0].get("posted_at")
    assert pool[1].get("used") is not True
    assert "posted_at" not in pool[1]


def _write_job(path, obj=None, raw=None):
    if raw is not None:
        path.write_text(raw, encoding="utf-8")
    else:
        path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    return str(path)


def test_job_file_supplies_target(isolated, tmp_path, monkeypatch, capsys):
    job_path = _write_job(tmp_path / "engagement_job.json",
                           {"feed_id": "jobfeed", "xsec_token": "jobtoken"})
    monkeypatch.setattr(seed, "JOB_PATH", job_path)
    rc = seed.main([])
    out = capsys.readouterr().out
    assert rc == 0
    assert "engagement_job.json" in out
    assert FakePublisher.constructed == []


def test_job_file_unreadable_fails_loud(isolated, tmp_path, monkeypatch, capsys):
    job_path = _write_job(tmp_path / "engagement_job.json", raw="{not json!!!")
    monkeypatch.setattr(seed, "JOB_PATH", job_path)
    rc = seed.main([])
    out = capsys.readouterr().out
    assert rc == 1
    assert "unreadable" in out.lower()
    assert FakePublisher.constructed == []


def test_cli_flags_override_job_file(isolated, tmp_path, monkeypatch):
    job_path = _write_job(tmp_path / "engagement_job.json",
                           {"feed_id": "feedAAA", "xsec_token": "tokenAAA"})
    monkeypatch.setattr(seed, "JOB_PATH", job_path)
    rc = seed.main(BASE_ARGS + ["--live"])
    assert rc == 0
    inst = FakePublisher.instances[-1]
    assert inst.posted == [("feed123", "token123", PICKED)]


def _autorefill_candidates():
    return [
        SimpleNamespace(content="auto good 1", score=None),
        SimpleNamespace(content="auto good 2", score=None),
        SimpleNamespace(content="auto bad", score=None),
    ]


def _autorefill_scorer(candidate, *args, **kwargs):
    if "bad" in candidate.content:
        candidate.score = SimpleNamespace(average=5.0)
    else:
        candidate.score = SimpleNamespace(average=8.0)
    return candidate


def test_autorefill_keeps_passing_scores(isolated, tmp_path, monkeypatch, capsys):
    pool_path = _write_pool(tmp_path, [{"text": "used one", "used": True}])
    monkeypatch.setattr(seed, "generate_comment_candidates", lambda **kwargs: _autorefill_candidates())
    monkeypatch.setattr(seed, "score_comment", _autorefill_scorer)
    rc = seed.main(BASE_ARGS + ["--live", "--pool", pool_path, "--auto-refill"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "auto-refill kept 2/3" in out
    pool = json.loads(open(pool_path, encoding="utf-8").read())
    auto_entries = [e for e in pool if e.get("source") == "auto"]
    assert len(auto_entries) == 2
    by_text = {e.get("text"): e for e in auto_entries}
    assert by_text["auto good 1"].get("used") is True and by_text["auto good 1"].get("posted_at")
    assert by_text["auto good 2"].get("used") is not True
    assert "posted_at" not in by_text["auto good 2"]
    assert all("score" in e for e in auto_entries)
    assert all(e["score"] >= seed.QUALITY_SCORE_THRESHOLD for e in auto_entries)
    # 1 posted (max-comments default 1)
    inst = FakePublisher.instances[-1]
    assert len(inst.posted) == 1
    assert inst.posted[0][2] == "auto good 1"
    # used entry got marked after posting
    pool_after = json.loads(open(pool_path, encoding="utf-8").read())
    assert pool_after[1].get("used") is True


def test_autorefill_none_pass_loud_fail(isolated, tmp_path, monkeypatch, capsys):
    before = [{"text": "used one", "used": True}]
    pool_path = _write_pool(tmp_path, before)
    monkeypatch.setattr(
        seed, "generate_comment_candidates",
        lambda **kwargs: [SimpleNamespace(content="bad 1", score=None),
                          SimpleNamespace(content="bad 2", score=None)],
    )

    def _low(candidate, *args, **kwargs):
        candidate.score = SimpleNamespace(average=5.0)
        return candidate

    monkeypatch.setattr(seed, "score_comment", _low)
    rc = seed.main(BASE_ARGS + ["--live", "--pool", pool_path, "--auto-refill"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "none met the bar" in out.lower()
    pool = json.loads(open(pool_path, encoding="utf-8").read())
    assert pool == before
    assert FakePublisher.constructed == []


def test_autorefill_llm_down_loud_fail(isolated, tmp_path, monkeypatch, capsys):
    before = [{"text": "used one", "used": True}]
    pool_path = _write_pool(tmp_path, before)

    def _boom(**kwargs):
        raise RuntimeError("proxy down")

    monkeypatch.setattr(seed, "generate_comment_candidates", _boom)
    rc = seed.main(BASE_ARGS + ["--live", "--pool", pool_path, "--auto-refill"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "produced no candidates" in out.lower()
    pool = json.loads(open(pool_path, encoding="utf-8").read())
    assert pool == before
    assert FakePublisher.constructed == []
