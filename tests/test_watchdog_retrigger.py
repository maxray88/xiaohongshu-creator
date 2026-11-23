#!/usr/bin/env python3
"""01:20 重触发看门狗回归测试。

背景（2026-11-08）：01:00 生成因模型 repetition-loop RuntimeError 失败
（Hermes 分类器只对 API 异常触发 provider fallback，生成流截断不属于
该类），整日流水线零草稿。看门狗 01:20 检查当天 V1 目录，缺失则
`hermes cron run 250be2028330` 重触发，下游照常开跑。

运行：python3 -m pytest tests/test_watchdog_retrigger.py -v
"""

import importlib.util
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
_spec = importlib.util.spec_from_file_location(
    "watchdog_retrigger_0100",
    os.path.join(ROOT, "bin", "watchdog_retrigger_0100.py"),
)
wd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wd)


class _FakeRunner:
    def __init__(self, rc=0, out="ok"):
        self.rc = rc
        self.out = out
        self.calls = []

    def __call__(self, cmd):
        self.calls.append(cmd)
        return self.rc, self.out


def _mk(base, name):
    d = os.path.join(str(base), name)
    os.makedirs(d)
    return d


def test_v1_present_exits_zero_without_trigger(tmp_path):
    _mk(tmp_path, "day_20261108_day112")
    r = _FakeRunner()
    assert wd.main(base=str(tmp_path), today="20261108", runner=r) == 0
    assert r.calls == []


def test_only_v2_dir_counts_as_missing(tmp_path):
    _mk(tmp_path, "day_20261108_day112_v2")
    r = _FakeRunner()
    assert wd.main(base=str(tmp_path), today="20261108", runner=r) == 0
    assert r.calls == [[wd.HERMES, "cron", "run", wd.JOB_ID]]


def test_missing_triggers_hermes_and_exit_zero_on_success(tmp_path):
    r = _FakeRunner(rc=0, out="Ran now: succeeded.")
    assert wd.main(base=str(tmp_path), today="20261108", runner=r) == 0
    assert wd.JOB_ID == "250be2028330"
    assert r.calls == [[wd.HERMES, "cron", "run", "250be2028330"]]


def test_trigger_failure_exits_one_and_shows_output(tmp_path, capsys):
    r = _FakeRunner(rc=1, out="boom")
    assert wd.main(base=str(tmp_path), today="20261108", runner=r) == 1
    out = capsys.readouterr().out
    assert "boom" in out
    assert "重触发" in out


def test_other_dates_dirs_are_ignored(tmp_path):
    _mk(tmp_path, "day_20261107_day111")
    r = _FakeRunner()
    assert wd.main(base=str(tmp_path), today="20261108", runner=r) == 0
    assert len(r.calls) == 1


def test_find_today_v1_returns_none_for_empty_base(tmp_path):
    assert wd.find_today_v1(str(tmp_path), "20261108") is None
