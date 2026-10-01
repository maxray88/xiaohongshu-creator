#!/usr/bin/env python3
"""Tab 生命周期（M3）测试。

## bug 的形态

`vendor/xhs/cdp_publish.py` 的 `_find_or_create_tab()`（L522-568）默认
`reuse_existing_tab=False`，走 L553-562 **无条件新建标签页**；`connect()`
（L570-581）拿到 ws_url 后**不记录自己建了哪个**，`disconnect()`（L583-587）
只关 WebSocket、**不关标签页**。

后果：每跑一次 cron 留一个标签页，永不回收。2026-09-30 实测堆到 11 个
（全是 `creator.xiaohongshu.com/login?...401`）。它自己不报错，只是慢慢堆积。

## 为什么本测试不碰真实 Chrome

关标签页是不可逆的外部副作用，测试里必须用假 publisher，不能拿用户的
浏览器做实验。所以这里全部走 mock —— 断言的是「我们的封装记得关自己
开的那一个，且不碰别人的」这个逻辑，而不是「Chrome 真的关掉了」。

真实端到端验证另有一处（PM 用变异体验证过：关掉 `_close_created_tab`
后标签页 4→5 累积，恢复后 5→5 持平）。
"""
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

PROJ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJ / "core"))
sys.path.insert(0, str(PROJ / "vendor" / "xhs"))

import cdp_publish  # noqa: E402
from tab_lifecycle import ManagedPublisher  # noqa: E402


def _fake_targets(*ids):
    return [
        {"id": i, "type": "page", "url": "about:blank", "webSocketDebuggerUrl": f"ws://x/{i}"}
        for i in ids
    ]


@pytest.fixture
def patched(monkeypatch):
    """把 XiaohongshuPublisher 换成可控假货，并记录 close 调用。"""
    state = {"closed": [], "instantiated": []}

    class FakePub:
        def __init__(self, *a, **kw):
            self.host = "127.0.0.1"
            self.port = 9222
            state["instantiated"].append((a, kw))

        # connect() 会先取 before 快照、再在 connect 后取 after。
        # 用 before_ids 驱动：connect 前只有 A/B，之后才有 A/B/C。
        def _get_targets(self):
            ids = getattr(self, "_ids", ["A", "B"])
            return _fake_targets(*ids)

        def connect(self, target_url_prefix="", reuse_existing_tab=False):
            # 模拟：只有「新建」路径才会多出 C
            if not target_url_prefix and not reuse_existing_tab:
                self._ids = ["A", "B", "NEW"]
            return "connected"

        def disconnect(self):
            state["disconnected"] = True

        # cdp_publish 的常用方法，供转发测试断言可达
        def _evaluate(self, expr):
            return f"eval:{expr}"

        def _navigate(self, url):
            return f"nav:{url}"

        def _send(self, method, params=None):
            return f"send:{method}"

    monkeypatch.setattr(cdp_publish, "XiaohongshuPublisher", FakePub)

    # 拦截 requests.get，记录 /json/close/<id> 调用
    import requests

    real_get = requests.get

    def fake_get(url, *a, **kw):
        if "/json/close/" in url:
            state["closed"].append(url.rsplit("/", 1)[-1])
            return SimpleNamespace(ok=True, status_code=200)
        return real_get(url, *a, **kw)

    monkeypatch.setattr(requests, "get", fake_get)
    return state


# ── 核心：关掉自己新建的那一个 ───────────────────────────────────

def test_closes_only_the_tab_it_created(patched):
    """connect 前 2 个 tab，connect 后 3 个 —— 多出来的那个是我们建的。"""
    patched["next_after"] = lambda *a: _fake_targets("A", "B", "C")

    pub = ManagedPublisher()
    pub.connect()
    assert pub.created_tab_id == "NEW", patched

    pub.disconnect()
    assert patched["closed"] == ["NEW"], patched


def test_created_tab_id_is_reset_on_every_connect(patched):
    """回归防护：第二次 connect 走复用路径时，不能沿用第一次的 tab id。

    Reviewer 报告 R3（2026-10-01，claude -p 发现）：
    `connect()` 原本只在「认领成功」时写 `created_tab_id`。
    认领不发生的三条路（prefix 非空 / reuse_existing_tab / 新建页不唯一）
    都会让它保持原值 —— 于是上一次的 tab id 残留在对象上。

    后果是 disconnect 关掉一个早已失效的旧 tab，同时**本次新建的 tab
    反而泄漏** —— 正是 M3 要消除的那个问题。

    修法：进入任何逻辑前无条件清零。
    """
    pub = ManagedPublisher()
    pub.connect()  # 新建路径 → 认领成功
    assert pub.created_tab_id == "NEW", patched

    # 第二次走复用路径：实现必须先清零，不能沿用 "NEW"
    pub.connect(target_url_prefix="https://creator.xiaohongshu.com/")
    assert pub.created_tab_id == "", (
        f"第二次 connect 沿用了上次的 tab id：{pub.created_tab_id!r} —— "
        f"disconnect 会关错页面并泄漏本次新建的 tab"
    )


def test_created_tab_id_is_reset_even_when_reuse_existing_tab(patched):
    """同一条，但走 reuse_existing_tab=True 这条守卫分支。

    分开写是因为守卫有两条独立的短路路径：`target_url_prefix` 非空、
    以及 `reuse_existing_tab=True`（实现在 `_claim_created_tab` 开头，
    命中任一即提前 return、不认领）。两条路各自可能被改坏。
    """
    pub = ManagedPublisher()
    pub.connect()
    assert pub.created_tab_id == "NEW", patched

    pub.connect(reuse_existing_tab=True)
    assert pub.created_tab_id == "", (
        f"reuse_existing_tab 分支未清零：{pub.created_tab_id!r}"
    )


def test_ws_connect_failure_still_claims_orphan_tab(patched):
    """R4 回归防护：ws 连接失败时，vendor 已建的 tab 仍要被认领。

    claude -p Reviewer 报告 R4（2026-10-02）。vendor 的 `connect()` 是两步的：
    L572 的 `_find_or_create_tab()` 先把标签页建出来，L580 才去
    `ws_client.connect()` 连 WebSocket。若后者抛异常，标签页**已经存在**，
    但认领块在异常传播中跑不到 → `created_tab_id` 停在空串 →
    `disconnect()` 认为「没建过任何页面」而什么都不关 → 那个 tab 成孤儿泄漏。

    修法：认领放进 `finally`。本测试用独立 fake（fixture 的 FakePub 不抛异常），
    并检查异常仍原样向上传播、且认领照样发生。
    """
    state = patched

    class FailingWsPub:
        def __init__(self, *a, **kw):
            self._ids = ["A", "B"]

        def _get_targets(self):
            return _fake_targets(*self._ids)

        def connect(self, target_url_prefix="", reuse_existing_tab=False):
            # L572：先把 tab 建出来
            self._ids = self._ids + ["ORPHAN"]
            # L580：再连 ws —— 这里失败
            raise RuntimeError("ws boom")

        def disconnect(self):
            pass

    pub = ManagedPublisher()
    pub._pub = FailingWsPub()

    # 1) 异常必须原样传播（finally 不能吞掉它）
    with pytest.raises(RuntimeError, match="ws boom"):
        pub.connect()

    # 2) 但认领必须已经发生 —— 孤儿 tab 不能泄漏
    assert pub.created_tab_id == "ORPHAN", (
        f"ws 失败后未认领已建成的 tab：{pub.created_tab_id!r} —— "
        f"该 tab 会成为孤儿泄漏"
    )

    # 3) disconnect 真的把它关掉了
    pub.disconnect()
    assert state["closed"] == ["ORPHAN"], patched


def test_claim_failure_does_not_mask_original_error(patched):
    """R4 的第二面：认领自己失败时，不能覆盖调用方真正的错误原因。

    `_claim_created_tab()` 跑在 `finally` 里。若它抛异常，会**替换**掉
    `connect()` 原本要抛的真实错误（Chrome 中途关闭、CDP 端口不通……），
    调用方看到的是一句莫名其妙的认领错误，真正的原因被彻底埋掉。
    """
    state = patched

    class BothFailPub:
        def __init__(self, *a, **kw):
            self._ids = ["A", "B"]
            self.calls = 0

        def _get_targets(self):
            self.calls += 1
            if self.calls > 1:
                # after 快照阶段失败（模拟 Chrome 中途关闭）
                raise ConnectionError("chrome gone")
            return _fake_targets(*self._ids)

        def connect(self, target_url_prefix="", reuse_existing_tab=False):
            self._ids = self._ids + ["ORPHAN"]
            raise RuntimeError("the real error")

        def disconnect(self):
            pass

    pub = ManagedPublisher()
    pub._pub = BothFailPub()

    # 调用方必须看到「真实的那个」异常，而不是认领阶段的 ConnectionError
    with pytest.raises(RuntimeError, match="the real error"):
        pub.connect()

    # 认领失败 → 不认领任何 tab（fail-safe：宁可不关，也不关错）
    assert pub.created_tab_id == "", patched
    pub.disconnect()
    assert state["closed"] == [], "认领失败时不应关闭任何页面"


def test_claim_failure_on_success_path_does_not_raise_or_close(patched):
    """BUG-7：connect 成功、但 after 快照失败时，调用方应拿到可用的 publisher。

    这是 BUG-1 描述的泄漏复发主场景：两个异常路径测试都覆盖不到它。
    成功连接 + 认领失败时，caller 拿到一个能正常用的 publisher，但
    `created_tab_id == ""` → 那个 tab 永不关闭。

    修 BUG-1 之后这条路径会在 stderr 留痕；本测试锁住行为契约：
    **不抛异常**（连接本身是成功的，不该因清理失败而失败）、
    **不认领**（fail-safe：宁可不关，也不关错）、**不关任何页**。
    """
    class SuccessButClaimFailsPub:
        def __init__(self, *a, **kw):
            self._ids = ["A", "B"]
            self.phase = "before"

        def _get_targets(self):
            if self.phase == "after":
                raise ConnectionError("chrome gone during claim")
            return _fake_targets(*self._ids)

        def connect(self, target_url_prefix="", reuse_existing_tab=False):
            # 模拟 vendor L572 建 tab，然后成功返回
            self._ids = self._ids + ["ORPHAN"]
            self.phase = "after"
            return "connected"

        def disconnect(self):
            pass

    pub = ManagedPublisher()
    pub._pub = SuccessButClaimFailsPub()

    # 1) 连接成功就是成功 —— 认领失败不该把它变成异常
    assert pub.connect() == "connected", "连接成功时不应抛异常"

    # 2) 认领失败 → 不认领任何 tab（fail-safe：宁可不关，也不关错）
    assert pub.created_tab_id == "", patched

    # 3) disconnect 不应关闭任何页面（不能凭猜测去关）
    pub.disconnect()
    assert patched["closed"] == [], "认领失败时不应关闭任何页面"


def test_claim_failure_is_reported_to_stderr(patched, capsys):
    """BUG-1 配套：认领失败必须留痕，否则 M3 泄漏会无声回归。

    M3 泄漏的特征恰恰是「它自己不报错，只是慢慢堆积」。所以静默吞掉
    认领失败等于把唯一的预警信号也丢了。本测试锁住告警行为。
    """
    class FailingClaimPub:
        def __init__(self, *a, **kw):
            self._ids = ["A", "B"]
            self.phase = "before"

        def _get_targets(self):
            if self.phase == "after":
                raise ConnectionError("profile locked")
            return _fake_targets(*self._ids)

        def connect(self, target_url_prefix="", reuse_existing_tab=False):
            self.phase = "after"
            return "connected"

        def disconnect(self):
            pass

    pub = ManagedPublisher()
    pub._pub = FailingClaimPub()
    pub.connect()

    captured = capsys.readouterr()
    err = captured.err
    assert err, "认领失败必须写 stderr —— 静默吞掉等于丢掉 M3 唯一的预警信号"
    assert "认领" in err, f"告警信息应点明是认领失败，实际: {err!r}"
    assert "M3" in err, f"告警信息应点明后果（M3 可能回归），实际: {err!r}"


def test_created_tab_id_is_reset_when_new_page_not_unique(patched):
    """第三条路：守卫为真、但块内 len(new_pages) != 1 判定失败。

    Reviewer 报告 R5（2026-10-01）：前两个测试只覆盖了「守卫为假 →
    整个认领块被跳过」，没覆盖这条 —— 守卫为**真**、认领块执行了，
    但块内判定失败。后果与被修的 bug 同构（残留旧 id → disconnect 关错页面）。

    生产可达路径：vendor `_find_or_create_tab`（L559-566）在 PUT /json/new
    失败时会回退复用旧页 → 0 个新页；并发开标签页 → ≥2 个新页。
    """
    pub = ManagedPublisher()
    pub.connect()  # 新建路径 → 认领成功
    assert pub.created_tab_id == "NEW", patched

    # 让第二次 connect 产生**2 个**新页（并发场景）→ 块内 len != 1 判定失败。
    # 守卫仍为真（不传 prefix / reuse_existing_tab），所以认领块会执行，
    # 失败点在块内而不是「块被跳过」—— 这正是前两个测试没覆盖的那条路。
    def connect_creating_two(*a, **k):
        pub._pub._ids = ["A", "B", "N1", "N2"]
        return "connected"

    pub._pub.connect = connect_creating_two
    pub.connect()

    assert pub.created_tab_id == "", (
        f"新建页不唯一时未清零：{pub.created_tab_id!r} —— "
        f"disconnect 会关错页面"
    )


def test_disconnect_after_never_connecting_does_not_raise(patched):
    """从未 connect 就 disconnect —— 属性必须存在，否则 AttributeError。

    守护 Builder 保留 __init__ 里 `created_tab_id = ""` 那个决定：
    清零只发生在 connect()，对象刚构造时仍需要这个属性。
    """
    pub = ManagedPublisher()
    assert pub.created_tab_id == ""
    pub.disconnect()  # 不应抛
    assert patched["closed"] == [], patched


def test_does_not_close_when_reusing_existing_tab(patched):
    """复用已有标签页时不能关 —— 那是用户自己的页面。"""
    patched["next_after"] = lambda *a: _fake_targets("A", "B")

    pub = ManagedPublisher()
    pub.connect(reuse_existing_tab=True)
    assert pub.created_tab_id == "", "复用时不该认领任何 tab"

    pub.disconnect()
    assert patched["closed"] == [], f"复用了别人的 tab 还去关：{patched['closed']}"


def test_reuse_path_must_not_claim_a_tab_even_if_one_appears(patched, monkeypatch):
    """回归防护：把「只在新建路径认领 tab」的判断改成恒真，必须失败。

    变异实验发现 —— 把它改成 `if True:` 时全部测试依然通过，
    因为当时的 mock 在复用路径下不会凭空多出 tab，测不出差别。
    这里让复用路径**也**多出一个 tab：若实现错误地认领了它，
    就会去关一个本该留着的页面。
    """

    def connect_creating_extra(self, target_url_prefix="", reuse_existing_tab=False):
        self._ids = ["A", "B", "SOMEONE_ELSES"]
        return "connected"

    monkeypatch.setattr(
        cdp_publish.XiaohongshuPublisher, "connect", connect_creating_extra
    )

    pub = ManagedPublisher()
    pub.connect(reuse_existing_tab=True)
    assert pub.created_tab_id == "", \
        f"复用路径不该认领 tab，却认领了 {pub.created_tab_id}"

    pub.disconnect()
    assert "SOMEONE_ELSES" not in patched["closed"], \
        f"关掉了不属于我们的 tab：{patched['closed']}"


def test_does_not_close_when_target_prefix_given(patched):
    """指定 target_url_prefix 时是复用已有页面，同样不能关。"""
    pub = ManagedPublisher()
    pub.connect(target_url_prefix="https://creator.xiaohongshu.com")
    assert pub.created_tab_id == ""
    pub.disconnect()
    assert patched["closed"] == []


# ── 幂等与容错 ─────────────────────────────────────────────────

def test_disconnect_is_idempotent(patched):
    """重复 disconnect 不会重复关同一个 tab。"""
    patched["next_after"] = lambda *a: _fake_targets("A", "B")

    pub = ManagedPublisher()
    pub.connect()
    pub.disconnect()
    pub.disconnect()
    pub.disconnect()
    assert patched["closed"] == ["NEW"], patched


def test_close_failure_does_not_propagate(patched, monkeypatch):
    """关标签页失败绝不能让调用方的正常流程变成异常。"""
    patched["next_after"] = lambda *a: _fake_targets("A", "B", "C")

    import requests

    def boom(url, *a, **kw):
        if "/json/close/" in url:
            raise RuntimeError("chrome went away")
        raise AssertionError("unexpected url")

    monkeypatch.setattr(requests, "get", boom)

    pub = ManagedPublisher()
    pub.connect()
    pub.disconnect()          # 不应抛
    assert pub.created_tab_id == "", "失败后应清空，避免下次重试关同一个"


def test_disconnect_closes_ws_even_if_tab_close_fails(patched, monkeypatch):
    """关键顺序：先关连接，再关 tab。tab 关不掉也不影响连接已关。"""
    patched["next_after"] = lambda *a: _fake_targets("A", "B", "C")

    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError()))

    pub = ManagedPublisher()
    pub.connect()
    pub.disconnect()
    assert patched.get("disconnected") is True, "WebSocket 必须已关闭"


# ── 转发完整性 ─────────────────────────────────────────────────

def test_attributes_forward_to_wrapped_publisher(patched):
    """包装类必须把未知属性原样转发，否则调用方会 AttributeError。"""
    patched["next_after"] = lambda *a: _fake_targets("A")
    pub = ManagedPublisher(host="127.0.0.1", port=9222, timing_jitter=0.25)
    assert pub.host == "127.0.0.1"
    assert pub.port == 9222
    # cdp_publish 的方法应可达
    assert callable(pub._evaluate)
    assert callable(pub._navigate)


def test_constructor_args_pass_through(patched):
    patched["next_after"] = lambda *a: _fake_targets("A")
    ManagedPublisher(host="h", port=1234, timing_jitter=0.5)
    assert patched["instantiated"] == [((), {"host": "h", "port": 1234, "timing_jitter": 0.5})]


# ── 所有生产调用点都已接线 ───────────────────────────────────────

@pytest.mark.parametrize("rel", [
    "bin/check_xhs_login.py",
    "core/xhs_image_draft.py",
    "core/xhs_video_draft.py",
    "core/xhs_performance_tracker.py",
    "core/render_xhs_cards.py",
])
def test_callsite_uses_managed_publisher(rel):
    """每个建 publisher 的地方都必须用 ManagedPublisher。

    漏一处就等于那个 cron 仍在泄漏标签页 —— 而泄漏是静默的，
    不会让任何测试变红。

    注意 legacy/ 下还有 3 处直接建上游类，但它们被 legacy/_archived_guard.py
    的 sys.exit(2) 拦住且 bin/、core/ 零引用，不在本检查范围。
    """
    src = (PROJ / rel).read_text(encoding="utf-8")
    assert "XiaohongshuPublisher(" not in src, \
        f"{rel} 还在直接建上游 XiaohongshuPublisher —— 标签页会泄漏"
    assert re.search(r"ManagedPublisher\(", src), \
        f"{rel} 没有真的构造 ManagedPublisher"
    # 不得残留语义别名：名字是上游、值是我们的，读起来像在用上游类
    assert "XiaohongshuPublisher = ManagedPublisher" not in src, \
        f"{rel} 残留误导性别名 XiaohongshuPublisher = ManagedPublisher"


def test_vendor_untouched():
    """vendor 必须保持上游原样，否则将来 git pull 同步会冲突。"""
    src = (PROJ / "vendor" / "xhs" / "cdp_publish.py").read_text(encoding="utf-8")
    # 上游 disconnect 仍然只关 ws、不关 tab —— 我们没改它
    assert "def disconnect(self):" in src
    assert "ManagedPublisher" not in src, "vendor 被污染了"
