"""US1 discovery tests for bin/reply_to_own_comments.py (fake publisher only)."""

import importlib.util
import json
from typing import ClassVar

import pytest

TOOL = "bin/reply_to_own_comments.py"
FEED_A = "a" * 24
FEED_B = "b" * 24


def _load():
    spec = importlib.util.spec_from_file_location("reply_to_own_comments", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def mod():
    return _load()


@pytest.fixture()
def datadir(tmp_path, monkeypatch):
    monkeypatch.setenv("XHS_TREEHOLE_DATA_DIR", str(tmp_path))
    return tmp_path


def _write_job(datadir, payload):
    (datadir / "engagement_job.json").write_text(json.dumps(payload), encoding="utf-8")


class FakePublisher:
    constructed: ClassVar[list] = []

    def __init__(self, notes, comments_by_feed, fail_feeds=None, fail_comment_ids=None):
        type(self).constructed.append(self)
        self.notes = notes
        self.comments_by_feed = comments_by_feed
        self.fail_feeds = set(fail_feeds or [])
        self.fail_comment_ids = set(fail_comment_ids or [])
        self.responded = []
        self.connected = False

    def connect(self, *a, **k):
        self.connected = True
        return True

    def respond_comment(self, feed_id, xsec_token, content, comment_id=None,
                        comment_author=None, comment_snippet=None):
        if comment_id in self.fail_comment_ids:
            raise RuntimeError("CDP publish exploded")
        self.responded.append({
            "feed_id": feed_id, "comment_id": comment_id,
            "content": content, "author": comment_author,
        })
        return {"ok": True}

    def list_profile_notes(self, profile_url=None, user_id=None, limit=20):
        return {"notes": self.notes, "count": len(self.notes)}

    def get_feed_detail(self, feed_id, xsec_token, load_all_comments=False):
        if feed_id in self.fail_feeds:
            raise RuntimeError("note gone")
        return {"detail": {}, "comment_loading": None}

    def list_feed_comments(self, feed_id, creator_nick=None):
        if feed_id in self.fail_feeds:
            raise RuntimeError("comments gone")
        comments = self.comments_by_feed.get(feed_id, [])
        if creator_nick:
            for item in comments:
                subs = item.get("sub_reply_authors", [])
                item["has_creator_reply"] = creator_nick in subs
        return {"ok": True, "comments": comments, "raw_count": len(comments)}


@pytest.fixture(autouse=True)
def _clean_constructed():
    FakePublisher.constructed.clear()
    yield
    FakePublisher.constructed.clear()


@pytest.fixture(autouse=True)
def _no_jitter_sleep(mod, monkeypatch):
    monkeypatch.setattr(mod, "_jitter_sleep", lambda *a, **k: None)


def _std_args(**over):
    args = {
        "own_profile_url": "https://www.xiaohongshu.com/user/profile/u1",
        "expect_nick": "creator",
    }
    args.update(over)
    argv = []
    for key, value in args.items():
        argv.append("--" + key.replace("_", "-"))
        argv.append(str(value))
    return argv


def _c(cUb_id, author, content="hello", subs=None):
    return {
        "comment_id": cUb_id,
        "author": author,
        "content": content,
        "created_at": "2026-01-01",
        "sub_reply_authors": subs or [],
    }


def test_module_imports(mod):
    assert hasattr(mod, "main")
    assert hasattr(mod, "run")


def test_live_empty_notes_ok(mod, datadir, capsys):
    _write_job(datadir, {"expect_nick": "creator"})
    rc = mod.run(["--live"] + _std_args(), publisher_factory=lambda a: FakePublisher([], {}))
    assert rc == 0
    assert FakePublisher.constructed != []


def test_port_gate_refuses(mod, datadir):
    _write_job(datadir, {"expect_nick": "creator"})
    rc = mod.run(_std_args() + ["--port", "9224"], publisher_factory=lambda a: FakePublisher([], {}))
    assert rc == 1
    assert FakePublisher.constructed == []


def test_kill_switch_refuses(mod, datadir):
    _write_job(datadir, {"expect_nick": "creator"})
    (datadir / "ENGAGEMENT_STOP").write_text("stop", encoding="utf-8")
    rc = mod.run(_std_args(), publisher_factory=lambda a: FakePublisher([], {}))
    assert rc == 1
    assert FakePublisher.constructed == []


def test_daily_cap_refuses(mod, datadir):
    _write_job(datadir, {"expect_nick": "creator"})
    (datadir / "reply_counter.json").write_text(json.dumps({mod._today_key(): 3}), encoding="utf-8")
    rc = mod.run(_std_args(), publisher_factory=lambda a: FakePublisher([], {}))
    assert rc == 1
    assert FakePublisher.constructed == []


def test_hostile_stop_refuses(mod, datadir):
    _write_job(datadir, {"expect_nick": "creator"})
    (datadir / "reply_state.json").write_text(
        json.dumps({"hostile_stop_until": "2999-01-01T00:00:00"}), encoding="utf-8"
    )
    rc = mod.run(_std_args(), publisher_factory=lambda a: FakePublisher([], {}))
    assert rc == 1
    assert FakePublisher.constructed == []


def test_config_conflict_rc2(mod, datadir):
    _write_job(
        datadir,
        {"expect_nick": "creator", "own_user_id": "u1", "own_profile_url": "https://x/u"},
    )
    rc = mod.run(["--expect-nick", "creator"], publisher_factory=lambda a: FakePublisher([], {}))
    assert rc == 2
    assert FakePublisher.constructed == []


def test_config_missing_rc2(mod, datadir, monkeypatch):
    (datadir / "engagement_job.json").write_text("{}", encoding="utf-8")
    for key in ("XHS_OWN_PROFILE_URL", "XHS_OWN_USER_ID"):
        monkeypatch.delenv(key, raising=False)
    rc = mod.run(["--expect-nick", "creator"], publisher_factory=lambda a: FakePublisher([], {}))
    assert rc == 2


def test_config_unreadable_job_rc1(mod, datadir, monkeypatch):
    _write_job(datadir, {"expect_nick": "creator"})
    real_open = open
    def _boom(path, *a, **k):
        if str(path).endswith("engagement_job.json"):
            raise OSError("EACCES (monkeypatched unreadable)")
        return real_open(path, *a, **k)
    import builtins
    monkeypatch.setattr(builtins, "open", _boom)
    rc = mod.run(_std_args(), publisher_factory=lambda a: FakePublisher([], {}))
    assert rc == 1
    assert FakePublisher.constructed == []


def test_env_precedence(mod, datadir, monkeypatch):
    _write_job(datadir, {"own_user_id": "u1", "expect_nick": "job-nick"})
    monkeypatch.setenv("XHS_EXPECT_NICK", "env-nick")
    cfg, rc = mod._resolve_config(mod._parse_args(["--own-user-id", "u1"]))
    assert rc == 0
    assert cfg["expect_nick"] == "env-nick"


def test_discovery_dry_run_lists_pending(mod, datadir, capsys):
    _write_job(datadir, {"expect_nick": "creator"})
    notes = [
        {"id": FEED_A, "xsec_token": "t1", "title": "A"},
        {"id": FEED_B, "xsec_token": "t2", "title": "B"},
    ]
    comments = {
        FEED_A: [
            _c("c1", "authorA", "nice post"),
            _c("c2", "creator", "my own comment"),
            _c("c3", "authorB", "loved it"),
        ],
        FEED_B: [],
    }
    rc = mod.run(_std_args(), publisher_factory=lambda a: FakePublisher(notes, comments))
    out = capsys.readouterr().out
    assert rc == 0
    assert "notes scanned=2, pending=2" in out
    assert out.count("[DRY-RUN] would reply to") == 2
    assert "done: planned=2" in out
    assert not (datadir / "reply_counter.json").exists()


def test_thread_fact_dedup_excludes_creator_subreply(mod, datadir, capsys):
    _write_job(datadir, {"expect_nick": "creator"})
    notes = [{"id": FEED_A, "xsec_token": "t1", "title": "A"}]
    comments = {FEED_A: [_c("c9", "fan", "great", subs=["creator"])]}
    rc = mod.run(_std_args(), publisher_factory=lambda a: FakePublisher(notes, comments))
    out = capsys.readouterr().out
    assert rc == 0
    assert "pending=0" in out
    assert "[DRY-RUN]" not in out


def test_hostile_marked_not_pending(mod, datadir, capsys):
    _write_job(datadir, {"expect_nick": "creator"})
    notes = [{"id": FEED_A, "xsec_token": "t1", "title": "A"}]
    comments = {FEED_A: [_c("h1", "troll", "骗子 rubbish")]}
    rc = mod.run(_std_args(), publisher_factory=lambda a: FakePublisher(notes, comments))
    out = capsys.readouterr().out
    assert rc == 0
    assert "aborted=hostile" in out
    assert not (datadir / "reply_counter.json").exists()


def test_bad_note_id_skipped(mod, datadir, capsys):
    _write_job(datadir, {"expect_nick": "creator"})
    notes = [{"id": "short", "xsec_token": "t", "title": "bad"}]
    rc = mod.run(_std_args(), publisher_factory=lambda a: FakePublisher(notes, {}))
    assert rc == 0
    assert "bad id" in capsys.readouterr().out


def test_failing_note_continues(mod, datadir, capsys):
    _write_job(datadir, {"expect_nick": "creator"})
    notes = [
        {"id": FEED_A, "xsec_token": "t1", "title": "A"},
        {"id": FEED_B, "xsec_token": "t2", "title": "B"},
    ]
    comments = {FEED_B: [_c("c1", "fan", "hi")]}
    rc = mod.run(
        _std_args(),
        publisher_factory=lambda a: FakePublisher(notes, comments, fail_feeds={FEED_A}),
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "notes scanned=2, pending=1" in out


def test_counter_corrupt_rc1(mod, datadir):
    # Round B fail-closed: corrupt counter refuses (rc 1).
    _write_job(datadir, {"expect_nick": "creator"})
    (datadir / "reply_counter.json").write_text("not json", encoding="utf-8")
    with pytest.raises(mod._FailClosed):
        mod._read_counter()
    rc = mod.run(_std_args(), publisher_factory=lambda a: FakePublisher([], {}))
    assert rc == 1


def test_job_file_non_dict_rc1(mod, datadir):
    (datadir / "engagement_job.json").write_text('["not", "an", "object"]', encoding="utf-8")
    rc = mod.run(_std_args(), publisher_factory=lambda a: FakePublisher([], {}))
    assert rc == 1
    assert FakePublisher.constructed == []


def test_ledger_dedup_skips_live_posted(mod, datadir, capsys):
    _write_job(datadir, {"expect_nick": "creator"})
    (datadir / "reply_ledger.jsonl").write_text(
        json.dumps({"feed_id": FEED_A, "comment_id": "c1", "status": "posted"}) + "\n",
        encoding="utf-8",
    )
    notes = [{"id": FEED_A, "xsec_token": "t1", "title": "A"}]
    comments = {FEED_A: [_c("c1", "fan", "hi"), _c("c2", "fan", "yo")]}
    rc = mod.run(_std_args(), publisher_factory=lambda a: FakePublisher(notes, comments))
    out = capsys.readouterr().out
    assert rc == 0
    assert "pending=1" in out
    assert "skipped=1" in out


def test_dry_run_rerun_same_plan(mod, datadir, capsys):
    _write_job(datadir, {"expect_nick": "creator"})
    notes = [{"id": FEED_A, "xsec_token": "t1", "title": "A"}]
    comments = {FEED_A: [_c("c1", "fan", "hi")]}
    def factory(a):
        return FakePublisher(notes, comments)
    assert mod.run(_std_args(), publisher_factory=factory) == 0
    capsys.readouterr()
    assert mod.run(_std_args(), publisher_factory=factory) == 0
    assert "pending=1" in capsys.readouterr().out


def test_report_reads_ledger(mod, datadir, capsys):
    (datadir / "reply_ledger.jsonl").write_text(
        json.dumps({"ts": "t", "feed_id": FEED_A, "comment_id": "c1",
                    "dry_run": True, "status": "planned"}) + "\n"
        + "broken line\n",
        encoding="utf-8",
    )
    rc = mod.run(["--report"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "malformed ledger line 2" in out
    assert "1 row(s)" in out
    assert FakePublisher.constructed == []


# ---------------- Round B (US2/US3 + nits) ----------------

class _Avg:
    def __init__(self, average):
        self.average = average


def _pass_score(monkeypatch, mod, average=9.0):
    monkeypatch.setattr(mod, "score_content",
                        lambda **k: _Avg(average), raising=True)


def _ok_llm(text="谢谢你呀，抱抱！"):
    return lambda *a, **k: text


def _live_notes():
    return [{"id": FEED_A, "xsec_token": "t1", "title": "今日心情"}]


def test_expect_nick_missing_rc2(mod, datadir, monkeypatch):
    _write_job(datadir, {"own_user_id": "u1"})
    for key in ("XHS_EXPECT_NICK",):
        monkeypatch.delenv(key, raising=False)
    rc = mod.run(["--own-user-id", "u1"], publisher_factory=lambda a: FakePublisher([], {}))
    assert rc == 2


def test_counter_nondict_rc1(mod, datadir):
    _write_job(datadir, {"expect_nick": "creator"})
    (datadir / "reply_counter.json").write_text("[1,2]", encoding="utf-8")
    rc = mod.run(_std_args(), publisher_factory=lambda a: FakePublisher([], {}))
    assert rc == 1


def test_state_bad_iso_rc1(mod, datadir):
    _write_job(datadir, {"expect_nick": "creator"})
    (datadir / "reply_state.json").write_text(
        json.dumps({"hostile_stop_until": "not-a-date"}), encoding="utf-8")
    rc = mod.run(_std_args(), publisher_factory=lambda a: FakePublisher([], {}))
    assert rc == 1


def test_state_nondict_rc1(mod, datadir):
    _write_job(datadir, {"expect_nick": "creator"})
    (datadir / "reply_state.json").write_text("[1]", encoding="utf-8")
    rc = mod.run(_std_args(), publisher_factory=lambda a: FakePublisher([], {}))
    assert rc == 1


def test_state_bad_type_rc1(mod, datadir):
    _write_job(datadir, {"expect_nick": "creator"})
    (datadir / "reply_state.json").write_text(
        json.dumps({"hostile_stop_until": 12345}), encoding="utf-8")
    rc = mod.run(_std_args(), publisher_factory=lambda a: FakePublisher([], {}))
    assert rc == 1


def test_bad_flags_rc2(mod, datadir):
    _write_job(datadir, {"expect_nick": "creator"})
    assert mod.run(_std_args() + ["--max-posts", "0"],
                    publisher_factory=lambda a: FakePublisher([], {})) == 2
    assert mod.run(_std_args() + ["--limit-comments", "0"],
                    publisher_factory=lambda a: FakePublisher([], {})) == 2
    assert mod.run(_std_args() + ["--max-replies", "-1"],
                    publisher_factory=lambda a: FakePublisher([], {})) == 2


def test_live_happy_path_posts_two(mod, datadir, capsys, monkeypatch):
    _write_job(datadir, {"expect_nick": "creator"})
    _pass_score(monkeypatch, mod, 9.0)
    comments = {FEED_A: [_c("c1", "fan1", "好喜欢"), _c("c2", "fan2", "支持")]}
    pubs = []
    def factory(a):
        p = FakePublisher(_live_notes(), comments)
        pubs.append(p)
        return p
    rc = mod.run(["--live"] + _std_args(), publisher_factory=factory,
                 llm_caller=_ok_llm())
    out = capsys.readouterr().out
    assert rc == 0
    assert len(pubs[0].responded) == 2
    assert json.loads((datadir / "reply_counter.json").read_text())[mod._today_key()] == 2
    lines = (datadir / "reply_ledger.jsonl").read_text().strip().split("\n")
    assert len(lines) == 4  # intent + done per comment
    first, second = (json.loads(lines[0]), json.loads(lines[1]))
    assert first["status"] == "posted" and first.get("posted_at") is None
    assert second["status"] == "posted" and second.get("posted_at")
    assert "done: planned=2 posted=2" in out


def test_live_inter_reply_jitter_sleeps_once(mod, datadir, monkeypatch):
    _write_job(datadir, {"expect_nick": "creator"})
    _pass_score(monkeypatch, mod, 9.0)
    comments = {FEED_A: [_c("c1", "fan1", "好喜欢"), _c("c2", "fan2", "支持")]}
    calls = []
    monkeypatch.setattr(mod, "_jitter_sleep", lambda: calls.append(1))
    rc = mod.run(["--live"] + _std_args(),
                 publisher_factory=lambda a: FakePublisher(_live_notes(), comments),
                 llm_caller=_ok_llm())
    assert rc == 0
    assert len(calls) == 1


def test_dry_run_never_sleeps(mod, datadir, capsys, monkeypatch):
    _write_job(datadir, {"expect_nick": "creator"})
    comments = {FEED_A: [_c("c1", "fan1", "好喜欢"), _c("c2", "fan2", "支持")]}
    calls = []
    monkeypatch.setattr(mod, "_jitter_sleep", lambda: calls.append(1))
    rc = mod.run(_std_args(),
                 publisher_factory=lambda a: FakePublisher(_live_notes(), comments))
    assert rc == 0
    assert calls == []


def test_live_thread_fact_rerun_zero_posts(mod, datadir, capsys, monkeypatch):
    _write_job(datadir, {"expect_nick": "creator"})
    _pass_score(monkeypatch, mod, 9.0)
    comments = {FEED_A: [_c("c1", "fan1", "好喜欢")]}
    def factory(a):
        return FakePublisher(_live_notes(), comments)
    assert mod.run(["--live"] + _std_args(), publisher_factory=factory,
                   llm_caller=_ok_llm()) == 0
    capsys.readouterr()
    assert mod.run(["--live"] + _std_args(), publisher_factory=factory,
                   llm_caller=_ok_llm()) == 0
    assert "posted=0" in capsys.readouterr().out


def test_live_below_threshold_skipped(mod, datadir, capsys, monkeypatch):
    _write_job(datadir, {"expect_nick": "creator"})
    _pass_score(monkeypatch, mod, 1.0)
    comments = {FEED_A: [_c("c1", "fan1", "好喜欢")]}
    pubs = []
    def factory(a):
        p = FakePublisher(_live_notes(), comments)
        pubs.append(p)
        return p
    rc = mod.run(["--live"] + _std_args(), publisher_factory=factory,
                 llm_caller=_ok_llm())
    assert rc == 0
    assert pubs[0].responded == []
    rows = [json.loads(line) for line in
            (datadir / "reply_ledger.jsonl").read_text().strip().split("\n")]
    assert rows[0]["status"] == "skipped" and rows[0]["reason"] == "below_threshold"
    assert not (datadir / "reply_counter.json").exists()


def test_live_llm_all_empty_rc1_zero_posts(mod, datadir, capsys, monkeypatch):
    _write_job(datadir, {"expect_nick": "creator"})
    _pass_score(monkeypatch, mod, 9.0)
    comments = {FEED_A: [_c("c1", "fan1", "hi"), _c("c2", "fan2", "yo")]}
    pubs = []
    def factory(a):
        p = FakePublisher(_live_notes(), comments)
        pubs.append(p)
        return p
    rc = mod.run(["--live"] + _std_args(), publisher_factory=factory,
                 llm_caller=lambda *a, **k: "")
    assert rc == 1
    assert pubs[0].responded == []
    assert not (datadir / "reply_counter.json").exists()


def test_live_partial_failure_rc0(mod, datadir, capsys, monkeypatch):
    _write_job(datadir, {"expect_nick": "creator"})
    _pass_score(monkeypatch, mod, 9.0)
    comments = {FEED_A: [_c("c1", "fan1", "hi"), _c("c2", "fan2", "yo")]}
    pubs = []
    def factory(a):
        p = FakePublisher(_live_notes(), comments, fail_comment_ids={"c1"})
        pubs.append(p)
        return p
    rc = mod.run(["--live"] + _std_args(), publisher_factory=factory,
                 llm_caller=_ok_llm())
    out = capsys.readouterr().out
    assert rc == 0
    assert [r["comment_id"] for r in pubs[0].responded] == ["c2"]
    assert json.loads((datadir / "reply_counter.json").read_text())[mod._today_key()] == 1
    assert "failed=1" in out


def test_live_hostile_abort_second_comment(mod, datadir, capsys, monkeypatch):
    _write_job(datadir, {"expect_nick": "creator"})
    _pass_score(monkeypatch, mod, 9.0)
    comments = {FEED_A: [_c("c1", "fan1", "好喜欢"), _c("h9", "troll", "骗子 rubbish")]}
    pubs = []
    def factory(a):
        p = FakePublisher(_live_notes(), comments)
        pubs.append(p)
        return p
    rc = mod.run(["--live"] + _std_args(), publisher_factory=factory,
                 llm_caller=_ok_llm())
    out = capsys.readouterr().out
    assert rc == 0
    assert [r["comment_id"] for r in pubs[0].responded] == ["c1"]
    assert "aborted=hostile" in out
    state = json.loads((datadir / "reply_state.json").read_text())
    assert state["hostile_stop_until"] > mod.datetime.now().isoformat()


def test_dry_run_hostile_abort_no_counter(mod, datadir, capsys):
    _write_job(datadir, {"expect_nick": "creator"})
    comments = {FEED_A: [_c("c1", "fan1", "hi"), _c("h9", "troll", "骗子 rubbish")]}
    rc = mod.run(_std_args(), publisher_factory=lambda a: FakePublisher(_live_notes(), comments))
    out = capsys.readouterr().out
    assert rc == 0
    assert "aborted=hostile" in out
    assert out.count("[DRY-RUN] would reply to") == 1
    assert not (datadir / "reply_counter.json").exists()
    assert json.loads((datadir / "reply_state.json").read_text())["hostile_stop_until"]


def test_write_counter_trims_45_days(mod, datadir):
    from datetime import date as _d
    from datetime import timedelta as _td
    old = (_d.today() - _td(days=60)).isoformat()
    (datadir / "reply_counter.json").write_text(
        json.dumps({old: 2, mod._today_key(): 0}), encoding="utf-8")
    mod._write_counter(1)
    data = json.loads((datadir / "reply_counter.json").read_text())
    assert old not in data and data[mod._today_key()] == 1


def test_discover_max_replies_none_guard(mod, datadir):
    _write_job(datadir, {"expect_nick": "creator"})
    comments = {FEED_A: [_c("c1", "fan1", "hi")]}
    scanned, pending, _ = mod._discover_pending(
        FakePublisher(_live_notes(), comments), {"own_profile_url": "x", "expect_nick": "creator"},
        5, 10, None)
    assert scanned == 1 and pending == []


def test_orphan_intent_warning(mod, datadir, capsys, monkeypatch):
    _write_job(datadir, {"expect_nick": "creator"})
    _pass_score(monkeypatch, mod, 9.0)
    comments = {FEED_A: [_c("c1", "fan1", "hi")]}
    (datadir / "reply_ledger.jsonl").write_text(
        json.dumps({"feed_id": FEED_A, "comment_id": "cx", "status": "posted",
                    "posted_at": None, "dry_run": False}) + "\n", encoding="utf-8")
    def factory(a):
        return FakePublisher(_live_notes(), comments)
    assert mod.run(["--live"] + _std_args(), publisher_factory=factory,
                   llm_caller=_ok_llm()) == 0
    assert "suspected incomplete publish" in capsys.readouterr().out


def test_dry_run_lines_not_in_dedup(mod, datadir, capsys, monkeypatch):
    _write_job(datadir, {"expect_nick": "creator"})
    _pass_score(monkeypatch, mod, 9.0)
    comments = {FEED_A: [_c("c1", "fan1", "hi")]}
    def factory(a):
        return FakePublisher(_live_notes(), comments)
    assert mod.run(_std_args(), publisher_factory=factory) == 0
    capsys.readouterr()
    pubs = []
    def factory2(a):
        p = FakePublisher(_live_notes(), comments)
        pubs.append(p)
        return p
    assert mod.run(["--live"] + _std_args(), publisher_factory=factory2,
                   llm_caller=_ok_llm()) == 0
    assert len(pubs[0].responded) == 1


def test_report_mixed_counts(mod, datadir, capsys):
    (datadir / "reply_ledger.jsonl").write_text(
        json.dumps({"ts": "t1", "feed_id": FEED_A, "comment_id": "c1",
                    "dry_run": True, "status": "planned"}) + "\n"
        + json.dumps({"ts": "t2", "feed_id": FEED_A, "comment_id": "c2",
                      "dry_run": False, "status": "posted",
                      "posted_at": "t2"}) + "\n"
        + "broken\n",
        encoding="utf-8")
    assert mod.run(["--report"]) == 0
    out = capsys.readouterr().out
    assert "2 row(s)" in out
    assert "malformed ledger line 3" in out


def _round_e_vendor_pub(monkeypatch):
    import sys
    sys.path.insert(0, "vendor/xhs")
    import cdp_publish
    pub = cdp_publish.XiaohongshuPublisher.__new__(cdp_publish.XiaohongshuPublisher)
    pub.ws = object()
    monkeypatch.setattr(pub, "_navigate", lambda url: None)
    monkeypatch.setattr(pub, "_sleep", lambda *a, **k: None)
    return pub


def test_rounde_state_fills_dom_empty_tokens(mod, monkeypatch):
    pub = _round_e_vendor_pub(monkeypatch)
    dom = {"notes": [
        {"id": FEED_A, "xsec_token": "", "title": "tA",
         "note_url": "https://www.xiaohongshu.com/explore/" + FEED_A, "cover": ""},
        {"id": FEED_B, "xsec_token": "", "title": "",
         "note_url": "https://www.xiaohongshu.com/explore/" + FEED_B, "cover": ""},
    ], "page_url": "https://www.xiaohongshu.com/user/profile/u1"}
    monkeypatch.setattr(pub, "_extract_note_cards_from_profile_dom", lambda limit=20, **k: dom)
    def fake_eval(expr):
        if "scrollTo" in expr:
            return True
        assert "__INITIAL_STATE__" in expr
        return [
            {"id": FEED_A, "xsec_token": "tokA", "title": "tA", "cover": "cA",
             "note_url": "https://www.xiaohongshu.com/explore/" + FEED_A + "?xsec_token=tokA&xsec_source=web"},
            {"id": FEED_B, "xsec_token": "tokB", "title": "tB", "cover": "cB",
             "note_url": "https://www.xiaohongshu.com/explore/" + FEED_B + "?xsec_token=tokB&xsec_source=web"},
        ]
    monkeypatch.setattr(pub, "_evaluate", fake_eval)
    res = pub.list_profile_notes(profile_url="https://www.xiaohongshu.com/user/profile/u1",
                                 limit=5, max_scrolls=0)
    assert res["count"] == 2
    assert [n["xsec_token"] for n in res["notes"]] == ["tokA", "tokB"]
    assert all("xsec_token=tok" in n["note_url"] for n in res["notes"])


def test_rounde_dom_tokens_skip_state_branch(mod, monkeypatch):
    pub = _round_e_vendor_pub(monkeypatch)
    dom = {"notes": [
        {"id": FEED_A, "xsec_token": "tokA", "title": "tA",
         "note_url": "https://www.xiaohongshu.com/explore/" + FEED_A + "?xsec_token=tokA", "cover": "cA"},
    ], "page_url": "https://www.xiaohongshu.com/user/profile/other"}
    monkeypatch.setattr(pub, "_extract_note_cards_from_profile_dom", lambda limit=20, **k: dom)
    def fake_eval(expr):
        assert "__INITIAL_STATE__" not in expr, "state branch must not run when DOM has tokens"
        return True
    monkeypatch.setattr(pub, "_evaluate", fake_eval)
    res = pub.list_profile_notes(profile_url="https://www.xiaohongshu.com/user/profile/other",
                                 limit=5, max_scrolls=0)
    assert [n["xsec_token"] for n in res["notes"]] == ["tokA"]
    assert res["notes"][0]["cover"] == "cA"


def test_rounde_dry_run_feed_detail_gets_nonempty_token(mod, datadir):
    _write_job(datadir, {"expect_nick": "creator"})
    comments = {FEED_A: [_c("c1", "fan1", "hi")]}
    seen = []
    class RecPublisher(FakePublisher):
        def get_feed_detail(self, feed_id, xsec_token, load_all_comments=False):
            seen.append((feed_id, xsec_token))
            return super().get_feed_detail(feed_id, xsec_token, load_all_comments)
    notes = [{"id": FEED_A, "xsec_token": "tokA", "title": "t"}]
    assert mod.run(_std_args(), publisher_factory=lambda a: RecPublisher(notes, comments)) == 0
    assert seen and all(tok for _, tok in seen)


def _round_f_run_state_js_through_node(monkeypatch, expr, raw_state):
    """Execute the vendored state-extraction JS under node with stubbed window.

    Exercises the real JS passed to _evaluate (collapse/unwrap/id checks),
    not a Python reimplementation. Returns the parsed `out` list.
    """
    import json
    import shutil
    import subprocess
    node = shutil.which("node")
    if node is None:
        import pytest
        pytest.skip("node not available for Round F JS execution test")
    harness = (
        "const window = __RAW__;\n"
        "const out = (__EXPR__);\n"
        "console.log(JSON.stringify(out));"
    ).replace("__RAW__", json.dumps(raw_state)).replace("__EXPR__", expr)
    proc = subprocess.run([node, "-e", harness], capture_output=True,
                          text=True, timeout=30)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def _round_f_state_eval(monkeypatch, pub, raw_state):
    def fake_eval(expr):
        assert "__INITIAL_STATE__" in expr
        return _round_f_run_state_js_through_node(monkeypatch, expr, raw_state)
    monkeypatch.setattr(pub, "_evaluate", fake_eval)


def _round_f_item(i):
    nid = "6af92115000000001b01dd5%d" % i
    return {"id": nid,
            "noteCard": {"noteId": nid, "xsecToken": "TOKEN%d" % i,
                         "displayTitle": "t%d" % i, "time": i}}


def test_state_notes_sparse_outer_array(mod, monkeypatch):
    """Round F: MobX sparse outer array (length 5, keys 0/1/2, [0] holds cards)."""
    pub = _round_e_vendor_pub(monkeypatch)
    items = [_round_f_item(0), _round_f_item(1), _round_f_item(2)]
    # JSON nulls stand in for sparse holes; length stays 5 with [0] an array.
    raw = {"__INITIAL_STATE__": {"user": {"notes": {"_value": [items, None, None, None, None]}}}}
    _round_f_state_eval(monkeypatch, pub, raw)
    res = pub._extract_profile_notes_from_state(5)
    assert [e["id"] for e in res] == [n["id"] for n in items]
    assert [e["xsec_token"] for e in res] == ["TOKEN0", "TOKEN1", "TOKEN2"]


def test_state_notes_single_array_wrapper(mod, monkeypatch):
    """Round F: single-wrapper [[a, b]] keeps working (no regression)."""
    pub = _round_e_vendor_pub(monkeypatch)
    items = [_round_f_item(0), _round_f_item(1)]
    raw = {"__INITIAL_STATE__": {"user": {"notes": {"_value": [items]}}}}
    _round_f_state_eval(monkeypatch, pub, raw)
    res = pub._extract_profile_notes_from_state(5)
    assert [e["id"] for e in res] == [n["id"] for n in items]
    assert [e["xsec_token"] for e in res] == ["TOKEN0", "TOKEN1"]
