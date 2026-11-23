#!/usr/bin/env python3
"""seed_test_comments.py 的安全护栏回归测试。

TEST-ACCOUNT-ONLY try-out 工具：默认 DRY RUN、端口 allowlist、
kill-switch、每日硬上限。全部用注入 fake，不触网、不耗 quota。
运行：python3 -m pytest tests/test_seed_guardrails.py -q（项目根目录）
"""

import importlib.util
import json
import os
import pathlib
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

    def probe_current_nickname(self):
        return getattr(self, "_probe_nick", None)


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
    monkeypatch.setattr(seed, "JOB_PATH", str(tmp_path / "engagement_job.json"))
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
    rc = seed.main(BASE_ARGS + ["--live", "--pool", pool_path])
    out = capsys.readouterr().out
    assert rc == 1
    assert "exhausted" in out.lower()
    assert FakePublisher.constructed == []


def test_pool_dry_run_marks_nothing(isolated, tmp_path, monkeypatch):
    pool_path = _write_pool(tmp_path, [{"text": "dry-run pool text"}])
    monkeypatch.setattr(seed, "generate_comment_candidates", _boom_llm)
    monkeypatch.setattr(seed, "score_comment", _boom_llm)
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


# ---- New regression tests for 2026-11-15 auto-comment fixes (additive only) ----

def _three_candidates():
    return [
        SimpleNamespace(content="cand best", score=SimpleNamespace(average=8.5)),
        SimpleNamespace(content="cand mid", score=SimpleNamespace(average=8.0)),
        SimpleNamespace(content="cand low", score=SimpleNamespace(average=7.5)),
    ]


def test_fix1_commenter_tempo_excludes_creator_prompt(isolated, capsys):
    """Fix 1: --max-comments 1 dry-run must wait on commenter_a (10-20min), not creator_prompt (0-5min)."""
    rc = seed.main(BASE_ARGS + ["--max-comments", "1"])
    out = capsys.readouterr().out
    assert rc == 0
    import re
    m = re.search(r"after ~([\d.]+)min", out)
    assert m, out
    assert float(m.group(1)) >= 10, out


def test_fix2_llm_path_posts_distinct_candidates(isolated, tmp_path, monkeypatch):
    """Fix 2: --max-comments 2 posts the top-2 distinct passing candidates, not best twice."""
    monkeypatch.setattr(seed, "generate_comment_candidates", lambda **kwargs: _three_candidates())
    monkeypatch.setattr(seed, "score_comment", lambda candidate: candidate)
    rc = seed.main(BASE_ARGS + ["--live", "--max-comments", "2"])
    assert rc == 0
    inst = FakePublisher.instances[-1]
    assert [c for (_, _, c) in inst.posted] == ["cand best", "cand mid"]


def test_fix2_llm_path_fewer_passing_posts_available(isolated, tmp_path, monkeypatch, capsys):
    """Fix 2: fewer passing candidates than slots → post available only, rc 0, note printed."""
    cands = [
        SimpleNamespace(content="only good", score=SimpleNamespace(average=8.5)),
        SimpleNamespace(content="bad one", score=SimpleNamespace(average=5.0)),
        SimpleNamespace(content="bad two", score=SimpleNamespace(average=4.0)),
    ]
    monkeypatch.setattr(seed, "generate_comment_candidates", lambda **kwargs: cands)
    monkeypatch.setattr(seed, "score_comment", lambda candidate: candidate)
    rc = seed.main(BASE_ARGS + ["--live", "--max-comments", "3"])
    out = capsys.readouterr().out
    assert rc == 0
    inst = FakePublisher.instances[-1]
    assert [c for (_, _, c) in inst.posted] == ["only good"]
    assert "only 1 candidate" in out


def test_fix3_two_phase_mark_keeps_attempt_and_posted_at(isolated, tmp_path):
    """Fix 3 (success): pool entry ends with used + posted_attempt + posted_at."""
    pool_path = _write_pool(tmp_path, [{"text": "two-phase me"}])
    rc = seed.main(BASE_ARGS + ["--live", "--pool", pool_path])
    assert rc == 0
    with open(pool_path, encoding="utf-8") as f:
        pool = json.load(f)
    assert pool[0].get("used") is True
    assert pool[0].get("posted_attempt")
    assert pool[0].get("posted_at")


def test_fix3_crash_warning_for_used_without_posted_at(isolated, tmp_path, capsys):
    """Fix 3 (scan): used-without-posted_at entry warns but does not block."""
    pool_path = _write_pool(tmp_path, [
        {"text": "crashed?", "used": True},
        {"text": "fresh one"},
    ])
    rc = seed.main(BASE_ARGS + ["--live", "--pool", pool_path])
    out = capsys.readouterr().out
    assert rc == 0
    assert "without posted_at" in out
    inst = FakePublisher.instances[-1]
    assert [c for (_, _, c) in inst.posted] == ["fresh one"]


def test_fix3_cdperror_rolls_back_claim(isolated, tmp_path, monkeypatch):
    """Fix 3 (rollback): failed post resets used/posted_at/posted_attempt and returns 1."""
    pool_path = _write_pool(tmp_path, [{"text": "doomed"}])

    def boom(self, feed_id, xsec_token, content):
        raise FakeCDPError("post exploded")

    monkeypatch.setattr(FakePublisher, "post_comment_to_feed", boom)
    rc = seed.main(BASE_ARGS + ["--live", "--pool", pool_path])
    assert rc == 1
    with open(pool_path, encoding="utf-8") as f:
        pool = json.load(f)
    assert pool[0].get("used") is False
    assert "posted_at" not in pool[0]
    assert "posted_attempt" not in pool[0]


def test_fix5_identity_match_passes(isolated, tmp_path, monkeypatch):
    """Fix 5: expected nick matches probe → rc 0."""
    monkeypatch.setenv("XHS_EXPECT_NICK", "复活君")
    monkeypatch.setattr(FakePublisher, "_probe_nick", "复活君", raising=False)
    rc = seed.main(BASE_ARGS + ["--live"])
    assert rc == 0
    assert FakePublisher.instances[-1].posted == [("feed123", "token123", PICKED)]


def test_fix5_identity_mismatch_refuses(isolated, tmp_path, monkeypatch, capsys):
    """Fix 5: expected nick differs from probe → rc 1, fail-closed, nothing posted."""
    monkeypatch.setenv("XHS_EXPECT_NICK", "复活君")
    monkeypatch.setattr(FakePublisher, "_probe_nick", "主号大号", raising=False)
    rc = seed.main(BASE_ARGS + ["--live"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "identity check failed; refusing to post" in out
    assert FakePublisher.instances[-1].posted == []


def test_fix5_identity_probe_none_refuses(isolated, tmp_path, monkeypatch, capsys):
    """Fix 5: probe returns None while expected configured → rc 1."""
    monkeypatch.setenv("XHS_EXPECT_NICK", "复活君")
    monkeypatch.setattr(FakePublisher, "_probe_nick", None, raising=False)
    rc = seed.main(BASE_ARGS + ["--live"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "identity check failed; refusing to post" in out
    assert FakePublisher.instances[-1].posted == []


def test_fix5_identity_unconfigured_warns_and_continues(isolated, tmp_path, monkeypatch, capsys):
    """Fix 5: no expected nick → warning printed, run continues (rc 0)."""
    monkeypatch.delenv("XHS_EXPECT_NICK", raising=False)
    monkeypatch.setattr(seed, "JOB_PATH", str(tmp_path / "no_such_job.json"))
    rc = seed.main(BASE_ARGS + ["--live"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "WITHOUT identity verification" in out
    assert FakePublisher.instances[-1].posted == [("feed123", "token123", PICKED)]


def test_fix5_identity_job_file_expect_nick(isolated, tmp_path, monkeypatch, capsys):
    """Fix 5: expect_nick from engagement_job.json is honored (mismatch → rc 1)."""
    monkeypatch.delenv("XHS_EXPECT_NICK", raising=False)
    job_path = _write_job(tmp_path / "engagement_job.json",
                           {"feed_id": "feed123", "xsec_token": "token123",
                            "expect_nick": "复活君"})
    monkeypatch.setattr(seed, "JOB_PATH", job_path)
    monkeypatch.setattr(FakePublisher, "_probe_nick", "别人", raising=False)
    rc = seed.main(["--live"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "identity check failed; refusing to post" in out


def test_fix7_counter_prunes_keys_older_than_45_days(isolated, tmp_path):
    """Fix 7: _write_counter drops keys older than 45 days."""
    from datetime import date, timedelta
    old = (date.today() - timedelta(days=60)).isoformat()
    recent = (date.today() - timedelta(days=10)).isoformat()
    with open(seed.COUNTER_PATH, "w", encoding="utf-8") as f:
        json.dump({old: 3, recent: 1, seed._today_key(): 0}, f)
    pool_path = _write_pool(tmp_path, [{"text": "prune check"}])
    rc = seed.main(BASE_ARGS + ["--live", "--pool", pool_path])
    assert rc == 0
    with open(seed.COUNTER_PATH, encoding="utf-8") as f:
        data = json.load(f)
    assert old not in data
    assert recent in data
    assert data[seed._today_key()] == 1


def test_fix6_wip_cap_counter_one_allows_single_post(isolated, tmp_path):
    """Fix 6: WIP semantics — counter=1, --max-comments 1 pool run succeeds."""
    with open(seed.COUNTER_PATH, "w", encoding="utf-8") as f:
        json.dump({seed._today_key(): 1}, f)
    pool_path = _write_pool(tmp_path, [{"text": "c1"}, {"text": "c2"}])
    rc = seed.main(BASE_ARGS + ["--live", "--pool", pool_path, "--max-comments", "1"])
    assert rc == 0
    inst = FakePublisher.instances[-1]
    assert [c for (_, _, c) in inst.posted] == ["c1"]
    with open(seed.COUNTER_PATH, encoding="utf-8") as f:
        data = json.load(f)
    assert data[seed._today_key()] == 2


def test_fix6_wip_cap_counter_at_cap_refuses(isolated, tmp_path, capsys):
    """Fix 6: WIP semantics — counter at TRYOUT_HARD_CAP_PER_DAY refuses with daily cap."""
    with open(seed.COUNTER_PATH, "w", encoding="utf-8") as f:
        json.dump({seed._today_key(): seed.TRYOUT_HARD_CAP_PER_DAY}, f)
    pool_path = _write_pool(tmp_path, [{"text": "c1"}])
    rc = seed.main(BASE_ARGS + ["--live", "--pool", pool_path, "--max-comments", "1"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "cap" in out.lower()
    assert FakePublisher.constructed == []


# ---- Round 2 nits (additive) ----

def test_r2_nit1_llm_respects_remaining_cap(isolated, tmp_path, monkeypatch):
    """Nit 1: counter=2 (cap 3), --max-comments 3 LLM path posts only 1."""
    with open(seed.COUNTER_PATH, "w", encoding="utf-8") as f:
        json.dump({seed._today_key(): 2}, f)
    cands = [
        SimpleNamespace(content=f"good {i}", score=SimpleNamespace(average=8.0))
        for i in range(3)
    ]
    monkeypatch.setattr(seed, "generate_comment_candidates", lambda **kw: cands)
    monkeypatch.setattr(seed, "score_comment", lambda c: c)
    rc = seed.main(BASE_ARGS + ["--live", "--max-comments", "3"])
    assert rc == 0
    inst = FakePublisher.instances[-1]
    assert len(inst.posted) == 1
    with open(seed.COUNTER_PATH, encoding="utf-8") as f:
        data = json.load(f)
    assert data[seed._today_key()] == 3


def test_r2_nit2_cli_flags_job_mismatch_refuses(isolated, tmp_path, monkeypatch, capsys):
    """Nit 2a: both CLI flags + job expect_nick mismatch → rc 1."""
    monkeypatch.delenv("XHS_EXPECT_NICK", raising=False)
    job_path = _write_job(tmp_path / "engagement_job.json",
                           {"feed_id": "other", "xsec_token": "other",
                            "expect_nick": "复活君"})
    monkeypatch.setattr(seed, "JOB_PATH", job_path)
    monkeypatch.setattr(FakePublisher, "_probe_nick", "别人", raising=False)
    rc = seed.main(BASE_ARGS + ["--live"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "identity check failed" in out


def test_r2_nit2_cli_flags_job_match_passes(isolated, tmp_path, monkeypatch):
    """Nit 2b: both CLI flags + job expect_nick match → rc 0."""
    monkeypatch.delenv("XHS_EXPECT_NICK", raising=False)
    job_path = _write_job(tmp_path / "engagement_job.json",
                           {"feed_id": "other", "xsec_token": "other",
                            "expect_nick": "复活君"})
    monkeypatch.setattr(seed, "JOB_PATH", job_path)
    monkeypatch.setattr(FakePublisher, "_probe_nick", "复活君", raising=False)
    rc = seed.main(BASE_ARGS + ["--live"])
    assert rc == 0
    assert FakePublisher.instances[-1].posted == [("feed123", "token123", PICKED)]


def test_r2_nit2_unreadable_job_with_cli_flags_fails(isolated, tmp_path, monkeypatch, capsys):
    """Nit 2: unreadable job file → rc 1 even when CLI flags are given."""
    job_path = _write_job(tmp_path / "engagement_job.json", raw="{not json!!!")
    monkeypatch.setattr(seed, "JOB_PATH", job_path)
    rc = seed.main(BASE_ARGS + ["--live"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "unreadable" in out.lower()


def test_r2_nit6_max_comments_zero_noop(isolated, tmp_path, monkeypatch, capsys):
    """Nit 6a: --max-comments 0 prints nothing-planned, rc 0."""
    rc = seed.main(BASE_ARGS + ["--max-comments", "0"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "nothing planned" in out
    assert FakePublisher.constructed == []


def test_r2_nit6_max_comments_zero_live_noop(isolated, tmp_path, monkeypatch, capsys):
    """Nit 6a (live): --max-comments 0 prints nothing-planned, rc 0, no posts."""
    rc = seed.main(BASE_ARGS + ["--live", "--max-comments", "0"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "nothing planned" in out


def test_r2_nit6_with_reply_empty_skips(isolated, tmp_path, monkeypatch, capsys):
    """Nit 6b: --max-comments 0 --with-reply → rc 0, respond_comment NOT called."""
    rc = seed.main(BASE_ARGS + ["--live", "--max-comments", "0", "--with-reply"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "nothing planned" in out
    if FakePublisher.instances:
        assert FakePublisher.instances[-1].replied == []


def test_r2_nit7_pool_underfill_note(isolated, tmp_path, monkeypatch, capsys):
    """Nit 7a: fewer usable entries than requested → under-fill note."""
    pool_path = _write_pool(tmp_path, [{"text": "only one"}])
    capsys.readouterr()
    rc = seed.main(BASE_ARGS + ["--live", "--pool", pool_path, "--max-comments", "3"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "only 1 pool entr" in out


def test_r2_nit8_llm_zero_passing_fails(isolated, tmp_path, monkeypatch, capsys):
    """Nit 8.1: LLM zero-passing path → rc 1 with failure message."""
    monkeypatch.setattr(
        seed, "generate_comment_candidates",
        lambda **kw: [SimpleNamespace(content="meh", score=None)],
    )
    def _low(c, *a, **k):
        c.score = SimpleNamespace(average=1.0)
        return c
    monkeypatch.setattr(seed, "score_comment", _low)
    rc = seed.main(BASE_ARGS + ["--live"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "no comment met the bar" in out


def test_r2_nit8_rollback_preserves_fields(isolated, tmp_path, monkeypatch):
    """Nit 8.2: rollback preserves source/score/text, clears claim keys."""
    pool_path = _write_pool(tmp_path, [{"text": "keep me", "source": "auto", "score": 8.5}])
    def boom(self, feed_id, xsec_token, content):
        raise FakeCDPError("boom")
    monkeypatch.setattr(FakePublisher, "post_comment_to_feed", boom)
    rc = seed.main(BASE_ARGS + ["--live", "--pool", pool_path])
    assert rc == 1
    pool = json.loads(pathlib.Path(pool_path).read_text(encoding="utf-8"))
    assert pool[0].get("source") == "auto"
    assert pool[0].get("score") == 8.5
    assert pool[0].get("text") == "keep me"
    assert pool[0].get("used") is False
    assert "posted_at" not in pool[0]
    assert "posted_attempt" not in pool[0]


def test_r2_nit8_crashed_entry_refill_empty_fails(isolated, tmp_path, monkeypatch, capsys):
    """Nit 8.3: crashed (used, no posted_at) + empty usable, refill yields nothing → rc 1, crash warned, crashed entry not posted."""
    pool_path = _write_pool(tmp_path, [{"text": "crashed", "used": True}])
    monkeypatch.setattr(seed, "generate_comment_candidates", lambda **kw: [])
    rc = seed.main(BASE_ARGS + ["--live", "--pool", pool_path, "--auto-refill"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "possible crash" in out
    for inst in FakePublisher.instances:
        for (_, _, c) in inst.posted:
            assert c != "crashed"


def test_r2_nit8_with_reply_logs_creator_reply(isolated, tmp_path, monkeypatch):
    """Nit 8.4: --with-reply after pool post → respond_comment once, kind == creator_reply."""
    pool_path = _write_pool(tmp_path, [{"text": "hello pool"}])
    rc = seed.main(BASE_ARGS + ["--live", "--pool", pool_path, "--with-reply"])
    assert rc == 0
    inst = FakePublisher.instances[-1]
    assert len(inst.replied) == 1
    assert inst.replied[0][2] == "hello pool"
    with open(seed.LOG_PATH, encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]
    kinds = [e.get("kind") for e in lines]
    assert "creator_reply" in kinds
