#!/usr/bin/env python3
"""image 侧（03:00 图文链路）端到端覆盖 —— S2 抽 `draft_shared` 的前置条件。

只加测试，不改任何实现。全部用 tmp_path + monkeypatch + FakePub，
不依赖真实网络 / Chrome / 文件系统状态，不跑 bin/ 脚本。

FakePub 模式参照 tests/test_perf_tracker.py 与 tests/test_tab_lifecycle.py。
运行：python3 -m pytest tests/test_image_draft_e2e.py -v（项目根目录）
"""
import inspect
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "vendor", "xhs"))
import xhs_image_draft as im  # noqa: E402
import xhs_video_draft as vd  # noqa: E402
from cdp_publish import CDPError  # noqa: E402


# ── A. get_draft_count 解析（image 侧 get_draft_count）─────────

class FakeEvalPub:
    """只 stub `_evaluate` 的最小 publisher。"""

    def __init__(self, result=None, exc=None):
        self.result = result
        self.exc = exc

    def _evaluate(self, js):
        if self.exc is not None:
            raise self.exc
        return self.result


def test_a1_draft_count_int_passthrough():
    assert im.get_draft_count(FakeEvalPub(result=5)) == 5


def test_a2_draft_count_zero_is_zero():
    assert im.get_draft_count(FakeEvalPub(result=0)) == 0


def test_a3_draft_count_minus_one_stays_unknown():
    """-1 表示未知，不得当成 0。"""
    assert im.get_draft_count(FakeEvalPub(result=-1)) == -1


def test_a4_draft_count_none_is_unknown():
    assert im.get_draft_count(FakeEvalPub(result=None)) == -1


def test_a5_draft_count_evaluate_error_is_unknown():
    """_evaluate 抛异常不得向上传播。"""
    assert im.get_draft_count(FakeEvalPub(exc=RuntimeError("ws wedged"))) == -1


# ── B. find_latest_v1_dir 筛选（image 侧，选非 _v2）────────────

def _mkdir(base, name):
    os.makedirs(os.path.join(base, name), exist_ok=True)


def test_b1_malformed_v1_name_never_wins(tmp_path, monkeypatch):
    """day_broken 无 _v2 但 parse 失败，不得胜出（ASCII 'b' > 数字同理）。"""
    base = str(tmp_path)
    _mkdir(base, "day_broken")
    _mkdir(base, "day_20260927_day1")
    monkeypatch.setattr(im, "BASE", base)
    assert im.find_latest_v1_dir(wait_seconds=0, attempts=1) == "day_20260927_day1"


def test_b2_day10_sorts_after_day9_numerically(tmp_path, monkeypatch):
    """字符串排序会把 day9 排在 day10 前（'9' > '1'），必须数值比较。"""
    base = str(tmp_path)
    _mkdir(base, "day_20260927_day9")
    _mkdir(base, "day_20260927_day10")
    monkeypatch.setattr(im, "BASE", base)
    assert im.find_latest_v1_dir(wait_seconds=0, attempts=1) == "day_20260927_day10"


def test_b3_date_beats_daynum(tmp_path, monkeypatch):
    """日期优先：day_20260926_day99 vs day_20260927_day1 → 选后者。"""
    base = str(tmp_path)
    _mkdir(base, "day_20260926_day99")
    _mkdir(base, "day_20260927_day1")
    monkeypatch.setattr(im, "BASE", base)
    assert im.find_latest_v1_dir(wait_seconds=0, attempts=1) == "day_20260927_day1"


def test_b4_missing_base_dir_returns_none(tmp_path, monkeypatch):
    """目录不存在（FileNotFoundError）→ None（image 侧独有分支，video 侧没有）。"""
    monkeypatch.setattr(im, "BASE", str(tmp_path / "does_not_exist"))
    assert im.find_latest_v1_dir(wait_seconds=0, attempts=1) is None


def test_b5_v2_only_returns_none(tmp_path, monkeypatch):
    """只有 _v2 目录时 v1 筛选必须排除 _v2 → None。"""
    base = str(tmp_path)
    _mkdir(base, "day_20260927_day1_v2")
    monkeypatch.setattr(im, "BASE", base)
    assert im.find_latest_v1_dir(wait_seconds=0, attempts=1) is None


# ── C. navigate_publish_page 重试语义 ──────────────────────────

class FakeNavPub:
    """前 fail_times 次 _navigate 抛 CDPError，并记录事件顺序。"""

    def __init__(self, fail_times=0):
        self.fail_times = fail_times
        self.navigate_calls = 0
        self.events = []

    def _navigate(self, url):
        self.navigate_calls += 1
        self.events.append("navigate")
        if self.navigate_calls <= self.fail_times:
            raise CDPError("boom")

    def disconnect(self):
        self.events.append("disconnect")

    def connect(self, *a, **kw):
        self.events.append("connect")
        return "connected"


def _no_sleep(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda *a, **k: None)


def test_c1_first_try_success_no_reconnect(monkeypatch):
    _no_sleep(monkeypatch)
    pub = FakeNavPub(fail_times=0)
    im.navigate_publish_page(pub, "https://example.invalid", attempts=3, wait=0)
    assert pub.navigate_calls == 1
    assert "connect" not in pub.events


def test_c2_second_try_success_reconnects_once(monkeypatch):
    _no_sleep(monkeypatch)
    pub = FakeNavPub(fail_times=1)
    im.navigate_publish_page(pub, "https://example.invalid", attempts=3, wait=0)
    assert pub.navigate_calls == 2
    assert pub.events.count("disconnect") == 1
    assert pub.events.count("connect") == 1


def test_c3_all_fail_raises_after_exactly_attempts(monkeypatch):
    _no_sleep(monkeypatch)
    pub = FakeNavPub(fail_times=99)
    try:
        im.navigate_publish_page(pub, "https://example.invalid", attempts=3, wait=0)
    except CDPError:
        pass
    else:
        raise AssertionError("全部失败必须抛 CDPError")
    assert pub.navigate_calls == 3


def test_c4_reconnect_disconnects_before_connect(monkeypatch):
    """_send 超时会让 WebSocket 卡死，必须先断开再连，不能复用死 socket。"""
    _no_sleep(monkeypatch)
    pub = FakeNavPub(fail_times=1)
    im.navigate_publish_page(pub, "https://example.invalid", attempts=3, wait=0)
    assert pub.events == ["navigate", "disconnect", "connect", "navigate"]


# ── D. 保存验证四分支（image 侧 [4/4]，驱动完整 main）──────────

PUBLISH_URL = "https://creator.xiaohongshu.com/publish/publish?source=official"


def _build_v1_tree(base):
    """搭一个能走完全程 main 的 V1 素材目录（日期=今天，过 today-guard）。"""
    day_dir = "day_%s_day1" % time.strftime("%Y%m%d")
    d = os.path.join(base, day_dir)
    os.makedirs(os.path.join(d, "images"))
    with open(os.path.join(d, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({}, f)
    with open(os.path.join(d, "post_data.json"), "w", encoding="utf-8") as f:
        json.dump({"title": "今日情绪树洞", "content_text": "测" * 450}, f,
                  ensure_ascii=False)
    for i in range(1, 7):
        with open(os.path.join(d, "images", "card%d.jpg" % i), "wb") as f:
            f.write(b"fake-jpeg-%d" % i)
    return day_dir


def _run_image_main(monkeypatch, tmp_path, capsys, counts, snippet):
    """用 FakePub 跑完整 im.main，返回捕获的 stdout。"""
    base = str(tmp_path)
    _build_v1_tree(base)
    state = {"ci": 0}

    class FakeImagePub:
        def __init__(self, *a, **kw):
            pass

        def connect(self, *a, **kw):
            return "connected"

        def disconnect(self):
            pass

        def _sleep(self, *a, **kw):
            pass

        def _navigate(self, url):
            pass

        def _click_image_text_tab(self):
            pass

        def _query_node_id(self, sel):
            return 101

        def _send(self, method, params=None):
            return {}

        def _fill_title(self, t):
            pass

        def _fill_content(self, c):
            pass

        def _evaluate(self, js):
            if "window.location.href" in js:
                return PUBLISH_URL
            if "草稿箱" in js:  # get_draft_count 的 JS 必然含"草稿箱"
                v = counts[min(state["ci"], len(counts) - 1)]
                state["ci"] += 1
                return v
            if "placeholder" in js:  # 上传完成轮询
                return True
            return snippet  # 页面 snippet（保存指示判定用）

    monkeypatch.setattr(im, "BASE", base)
    monkeypatch.setattr(im, "ManagedPublisher", FakeImagePub)
    monkeypatch.setattr(time, "sleep", lambda *a, **k: None)
    im.main()
    out = capsys.readouterr().out
    assert "✅ Done!" in out, "main 未走完全程：\n" + out
    return out


def test_d1_count_up_prints_saved(monkeypatch, tmp_path, capsys):
    out = _run_image_main(monkeypatch, tmp_path, capsys, [3, 4], "")
    assert "Draft saved!" in out


def test_d2_count_same_with_marker_prints_overwrite_confirm(monkeypatch, tmp_path, capsys):
    out = _run_image_main(monkeypatch, tmp_path, capsys, [3, 3], "已保存")
    assert "确认保存" in out and "覆盖" in out


def test_d3_count_same_without_marker_prints_likely_failed(monkeypatch, tmp_path, capsys):
    out = _run_image_main(monkeypatch, tmp_path, capsys, [3, 3], "草稿箱 3")
    assert "保存很可能失败" in out


def test_d4_count_unreadable_with_marker_prints_counter_unreadable_confirm(
        monkeypatch, tmp_path, capsys):
    out = _run_image_main(monkeypatch, tmp_path, capsys, [-1, -1], "已保存")
    assert "counter unreadable" in out
    assert "Found save indicator" in out


def test_d5_count_unreadable_without_marker_prints_no_indicator(
        monkeypatch, tmp_path, capsys):
    out = _run_image_main(monkeypatch, tmp_path, capsys, [-1, -1], "")
    assert "No save indicator" in out


def test_d6a_draft_count_decreased_with_marker_prints_warning_and_confirm(
        monkeypatch, tmp_path, capsys):
    """D6a: 计数下降（before=5 > after=3 >= 0）+ 页面有「已保存」指示。"""
    out = _run_image_main(monkeypatch, tmp_path, capsys, [5, 3], "已保存")
    assert "计数下降" in out
    assert "页面有「已保存」指示" in out


def test_d6b_draft_count_decreased_without_marker_prints_warning_and_no_indicator(
        monkeypatch, tmp_path, capsys):
    """D6b: 计数下降（before=5 > after=3 >= 0）+ 页面无保存指示。"""
    out = _run_image_main(monkeypatch, tmp_path, capsys, [5, 3], "")
    assert "计数下降" in out
    assert "无保存指示" in out


# ── E. 两链路共享 marker（锁住任务 1 的修复）───────────────────

def test_video_main_uses_shared_helper_not_inline_markers():
    """main 里内联一份 marker 会绕过分叉防护（S2 前置修复）。"""
    src = inspect.getsource(vd.main)
    assert "SAVE_MARKERS" not in src, \
        "main 内联重定义了 SAVE_MARKERS，改模块级列表不会影响 05:00 链路"
    assert "save_confirmed_in(" in src, "main 必须调用共享 helper"
