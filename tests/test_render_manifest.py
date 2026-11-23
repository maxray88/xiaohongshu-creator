#!/usr/bin/env python3
"""render_xhs_cards 的 manifest 回填逻辑回归测试。

H6（2026-09-27 审计）：旧实现无条件把所有 card file 从 .html 翻成 .jpg
并置 images_rendered=True，哪怕某张卡渲染失败/被跳过。下游 assemble
照 manifest 去读 .jpg，拿到的路径不存在，合成时才炸 —— 失败点离病因很远。

这里直接驱动 main() 的 manifest 段，验证它只反映「磁盘上真实存在」的 JPG。
"""

import json
import os
import base64
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "core"))
from xhs_paths import add_cdp_to_path  # noqa: E402

add_cdp_to_path()  # vendor/xhs/ —— 2026-09-27 vendored

import render_xhs_cards as R  # noqa: E402

SLOTS = ["cover", "scene", "insight", "method", "gentle", "cta"]


def _mk(tmp, n_jpg):
    """造一个 V2 目录：6 个 HTML + n_jpg 张 JPG，manifest 未渲染态。"""
    v2 = str(tmp)
    imgs = os.path.join(v2, "images")
    os.makedirs(imgs, exist_ok=True)
    cards = []
    for i, sl in enumerate(SLOTS, 1):
        name = f"card_v2_{i}_{sl}"
        with open(os.path.join(imgs, name + ".html"), "w") as f:
            f.write("<html>x</html>")
        if i <= n_jpg:
            with open(os.path.join(imgs, name + ".jpg"), "wb") as f:
                f.write(b"\xff\xd8\xff\xd9" * 100)  # 非空
        cards.append({"index": i, "file": name + ".html", "type": sl})
    with open(os.path.join(v2, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"cards": cards, "images_rendered": False}, f)
    return v2, os.path.join(v2, "manifest.json")


def _mk_one(tmp):
    """造一个只有 1 张卡的 V2 目录，用于断言 reconnect 调用次数。"""
    v2 = str(tmp)
    imgs = os.path.join(v2, "images")
    os.makedirs(imgs, exist_ok=True)
    name = "card_v2_1_cover"
    with open(os.path.join(imgs, name + ".html"), "w") as f:
        f.write("<html>x</html>")
    cards = [{"index": 1, "file": name + ".html", "type": "cover"}]
    with open(os.path.join(v2, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"cards": cards, "images_rendered": False}, f)
    return v2, os.path.join(v2, "manifest.json")


class _FakePublisher:
    """不碰 Chrome 的假 publisher：每张卡的 captureScreenshot 都失败。

    about:blank 这类初始化导航要放行 —— 只让真正的文件渲染失败。
    """
    def __init__(self):
        self.navigated = 0
        self.shots = 0

    def connect(self):
        pass

    def disconnect(self):
        pass

    def _send(self, method, params=None):
        if method == "Page.captureScreenshot":
            self.shots += 1
            raise RuntimeError("模拟 CDP 断连")
        return None

    def _navigate(self, url):
        self.navigated += 1


class CDPError(Exception):
    """websockets 帧过大异常的测试替身（与 vendor/xhs/cdp_publish.CDPError 同义）。

    SUT 只按异常文本匹配 "message too big" / "exceeds limit"，与生产类同名
    让测试意图一目了然；不从 vendor 导入，避免把 vendored upstream 引入测试。
    """
    pass


class _StepdownPublisher:
    """不碰 Chrome 的假 publisher：指定 quality 档抛 oversize 帧 CDPError，
    其余返回固定 data；用于验证 92→80→70 降档与不降档的两条分支。
    """

    Q80_BYTES = b"\xff\xd8\xff\xd9 stepdown-q80"

    def __init__(self, fail_qualities=(), raise_value_error=False):
        self.fail_qualities = set(fail_qualities)
        self.raise_value_error = raise_value_error
        self.shots = []  # 记录每次 Page.captureScreenshot 的 quality

    def connect(self):
        pass

    def disconnect(self):
        pass

    def _send(self, method, params=None):
        if method == "Page.captureScreenshot":
            q = params.get("quality")
            self.shots.append(q)
            if self.raise_value_error:
                # 非 oversize 异常：不得降档，必须直接 loud-fail
                raise ValueError("captureScreenshot 未返回 data（页面可能未加载完）")
            if q in self.fail_qualities:
                raise CDPError(
                    "CDP receive failed while waiting for Page.captureScreenshot: "
                    "sent 1009 (message too big) frame with 1100887 bytes "
                    "exceeds limit of 1048576 bytes; no close frame received")
            return {"data": base64.b64encode(self.Q80_BYTES).decode("ascii")}
        return None

    def _navigate(self, url):
        pass


class ConnectionClosedError(Exception):
    """连接已死替身：文本携带 close 原因（生产铁证），不带单独 oversize 标记。

    SUT 仅按异常文本匹配 "message too big" / "exceeds limit"，与生产
    websockets 异常的文本行为一致；不从 vendor 导入。
    """

    def __init__(self, reason: str):
        super().__init__(reason)


class _ReconnectPublisher:
    """q92 抛 oversize 文本并杀死连接：死连接后 _send 抛 ConnectionClosedError，
    connect 后复活；其余质量正常返回 data。

    用于验证 oversize 档之间断开重连、重设会话后降档成功。
    """

    Q80_BYTES = b"\xff\xd8\xff\xd9 stepdown-q80"

    OVERSIZE_TEXT = (
        "CDP receive failed while waiting for Page.captureScreenshot: "
        "sent 1009 (message too big) frame with 1100887 bytes "
        "exceeds limit of 1048576 bytes; no close frame received"
    )

    def __init__(self, fail_qualities=()):
        self.fail_qualities = set(fail_qualities)
        self.shots = []
        self.connect_calls = 0
        self.disconnect_calls = 0
        self.connected = False

    def connect(self):
        self.connect_calls += 1
        self.connected = True

    def disconnect(self):
        self.disconnect_calls += 1

    def _send(self, method, params=None):
        if method == "Page.captureScreenshot":
            q = params.get("quality")
            self.shots.append(q)
            if not self.connected:
                raise ConnectionClosedError(self.OVERSIZE_TEXT)
            if q in self.fail_qualities:
                # Chrome 以 close 109 杀死连接，该连接已死
                self.connected = False
                raise CDPError(self.OVERSIZE_TEXT)
            return {"data": base64.b64encode(self.Q80_BYTES).decode("ascii")}
        # 一次性设置命令：死连接下也抛 ConnectionClosedError
        if not self.connected:
            raise ConnectionClosedError("connection closed by server")
        return None

    def _navigate(self, url):
        pass


def _run_with_fake_cdp(v2, publisher=None):
    # 注入点从 R.XiaohongshuPublisher 改为 R.ManagedPublisher（2026-09-30）。
    # 起因：生产侧为修 M3 Tab 泄漏，把 publisher 换成了自己的
    # core/tab_lifecycle.ManagedPublisher。此前本测试替换的是
    # R.XiaohongshuPublisher，而生产代码里已无这个名字 → 5 个测试报
    # AttributeError（假 publisher 根本没被注入，于是渲染走了真实 CDP）。
    #
    # 为什么不反过来在生产侧保留一个 `XiaohongshuPublisher = ManagedPublisher`
    # 的语义别名：那会让 `p = XiaohongshuPublisher()` 读起来像在用上游类，
    # 而实际不是 —— 与「两个 profile 只差一个 s」是同一类认知陷阱。
    # 改测试的注入点比给生产代码留误导性别名更诚实。
    orig_pub, orig_ensure = R.ManagedPublisher, R.ensure_chrome
    fake = publisher if publisher is not None else _FakePublisher()
    R.ManagedPublisher = lambda: fake
    R.ensure_chrome = lambda *a, **k: None
    R._try_comfyui = lambda *a, **k: False
    old_argv = sys.argv
    sys.argv = ["render_xhs_cards.py", v2]
    try:
        rc = R.main()
    finally:
        sys.argv = old_argv
        R.ManagedPublisher, R.ensure_chrome = orig_pub, orig_ensure
    return rc, fake


def test_all_six_present_manifests_complete(tmp_path, monkeypatch):
    v2, mf = _mk(tmp_path, 6)
    # 让 skip 分支全命中（jpg 比 html 新）
    for i, sl in enumerate(SLOTS, 1):
        h = os.path.join(v2, "images", f"card_v2_{i}_{sl}.html")
        j = os.path.join(v2, "images", f"card_v2_{i}_{sl}.jpg")
        os.utime(h, (1000, 1000))
        os.utime(j, (2000, 2000))
    rc, _ = _run_with_fake_cdp(v2)
    m = json.load(open(mf))
    assert rc == 0
    assert m["images_rendered"] is True
    assert all(c["file"].endswith(".jpg") for c in m["cards"])


def test_missing_jpg_manifest_not_marked_complete(tmp_path):
    """核心回归：5/6 渲染成功时，不得标 images_rendered=True。"""
    v2, mf = _mk(tmp_path, 5)  # card 6 的 jpg 不存在
    for i, sl in enumerate(SLOTS, 1):
        h = os.path.join(v2, "images", f"card_v2_{i}_{sl}.html")
        if os.path.exists(os.path.join(v2, "images", f"card_v2_{i}_{sl}.jpg")):
            j = os.path.join(v2, "images", f"card_v2_{i}_{sl}.jpg")
            os.utime(h, (1000, 1000))
            os.utime(j, (2000, 2000))
    # card 6 会尝试真渲染；用会失败的 publisher
    rc, _ = _run_with_fake_cdp(v2)
    m = json.load(open(mf))
    assert rc == 1, f"缺卡时必须 exit 1，实际 {rc}"
    assert m["images_rendered"] is False, "缺卡却标了 complete —— 这正是 H6"
    missing_card = [c for c in m["cards"] if c["index"] == 6][0]
    assert missing_card["file"].endswith(".html"), "缺失卡的引用必须保持 .html"


def test_render_failure_leaves_no_partial_jpg(tmp_path):
    """渲染失败的半截 JPG 不能留下，否则下次 skip 判断会误认为已渲染。"""
    v2, mf = _mk(tmp_path, 0)  # 一张 jpg 都没有
    for i, sl in enumerate(SLOTS, 1):
        os.utime(os.path.join(v2, "images", f"card_v2_{i}_{sl}.html"), (1000, 1000))
    rc, fake = _run_with_fake_cdp(v2)
    jpgs = [f for f in os.listdir(os.path.join(v2, "images")) if f.endswith(".jpg")]
    assert rc == 1
    # navigated 含一次 about:blank 初始化，故是 7
    assert fake.navigated == 7, "六张卡都应尝试渲染（+1 次 about:blank 初始化）"
    assert fake.shots == 12, "六卡 × q92 档 2 次尝试（非 oversize 不降档）"
    assert jpgs == [], f"失败渲染留下了残留：{jpgs}"
    m = json.load(open(mf))
    assert m["images_rendered"] is False

def test_oversize_q92_kills_connection_reconnect_then_q80(tmp_path, capsys):
    """q92 抛 oversize 并杀死连接：重连后 q80 成功。

    断言：产物为 q80 字节、connect 调用恰初始 1 次＋重连 1 次、
    打印行含 (q80)。
    """
    v2, mf = _mk_one(tmp_path)
    os.utime(os.path.join(v2, "images", "card_v2_1_cover.html"), (1000, 1000))

    fake = _ReconnectPublisher(fail_qualities={92})
    rc, _ = _run_with_fake_cdp(v2, publisher=fake)

    m = json.load(open(mf))
    assert rc == 0
    assert m["images_rendered"] is True
    assert fake.connect_calls == 2, f"期望 connect 2 次（初始 1 + 重连 1），实际 {fake.connect_calls}"
    jpg = os.path.join(v2, "images", "card_v2_1_cover.jpg")
    with open(jpg, "rb") as f:
        assert f.read() == _ReconnectPublisher.Q80_BYTES, "产物应为重连后 q80 档返回的字节"
    out = capsys.readouterr().out
    assert "(q80)" in out, f"打印行未体现实际降档质量：\n{out}"

def test_happy_path_q92_no_reconnect(tmp_path, capsys):
    """q92 一次过：不发生任何重连（connect 仅初始 1 次）。"""
    v2, mf = _mk_one(tmp_path)
    os.utime(os.path.join(v2, "images", "card_v2_1_cover.html"), (1000, 1000))

    fake = _ReconnectPublisher()  # 不失败
    rc, _ = _run_with_fake_cdp(v2, publisher=fake)

    m = json.load(open(mf))
    assert rc == 0
    assert fake.connect_calls == 1, f"happy path 不得重连，实际 connect {fake.connect_calls} 次"
    assert fake.shots == [92], f"happy path 只应截图一次 q92，实际 {fake.shots}"
    out = capsys.readouterr().out
    assert "(q92)" in out, f"打印行未体现 q92：\n{out}"

def test_all_qualities_blown_reconnect_twice_then_fail(tmp_path):
    """三档全部 oversize＋杀连接：q80 前、q70 前各重连一次，最终失败。"""
    v2, mf = _mk_one(tmp_path)
    os.utime(os.path.join(v2, "images", "card_v2_1_cover.html"), (1000, 1000))

    fake = _ReconnectPublisher(fail_qualities={92, 80, 70})
    rc, _ = _run_with_fake_cdp(v2, publisher=fake)

    m = json.load(open(mf))
    assert rc == 1, f"三档全爆必须失败，实际 rc={rc}"
    assert fake.connect_calls == 3, f"期望 connect 3 次（初始 1 + 重连 2），实际 {fake.connect_calls}"
    jpgs = [f for f in os.listdir(os.path.join(v2, "images")) if f.endswith(".jpg")]
    assert jpgs == [], f"失败渲染留下了残留：{jpgs}"
    assert m["images_rendered"] is False

def test_empty_manifest_not_marked_complete(tmp_path):
    """空 cards 列表不能被当作「全部渲染完成」。"""
    v2 = str(tmp_path)
    os.makedirs(os.path.join(v2, "images"), exist_ok=True)
    mf = os.path.join(v2, "manifest.json")
    with open(mf, "w") as f:
        json.dump({"cards": [], "images_rendered": False}, f)
    rc, _ = _run_with_fake_cdp(v2)
    m = json.load(open(mf))
    assert rc == 1
    assert m["images_rendered"] is False


def test_zero_byte_jpg_counts_as_missing(tmp_path):
    """0 字节 JPG = 渲染失败产物，不能算已渲染。"""
    v2, mf = _mk(tmp_path, 6)
    zero = os.path.join(v2, "images", "card_v2_3_insight.jpg")
    with open(zero, "wb"):
        pass  # 截断为 0 字节
    for i, sl in enumerate(SLOTS, 1):
        os.utime(os.path.join(v2, "images", f"card_v2_{i}_{sl}.html"), (1000, 1000))
    rc, _ = _run_with_fake_cdp(v2)
    m = json.load(open(mf))
    assert m["images_rendered"] is False, "0 字节 JPG 被当成有效产物"
    assert rc == 1


def test_oversize_q92_steps_down_to_q80(tmp_path, capsys):
    """q92 命中 oversize 帧 → 降到 q80 成功：产物为 q80 字节，打印行含 (q80)。"""
    v2, mf = _mk(tmp_path, 0)
    for i, sl in enumerate(SLOTS, 1):
        os.utime(os.path.join(v2, "images", f"card_v2_{i}_{sl}.html"), (1000, 1000))

    fake = _StepdownPublisher(fail_qualities={92})
    rc, _ = _run_with_fake_cdp(v2, publisher=fake)

    m = json.load(open(mf))
    assert rc == 0
    assert m["images_rendered"] is True
    assert all(c["file"].endswith(".jpg") for c in m["cards"])
    # 每张卡：q92 两次失败后 q80 成功，无进一步降档
    assert fake.shots == [92, 92, 80] * 6, f"期望 q92 降档到 q80，实际 {fake.shots}"
    jpg = os.path.join(v2, "images", "card_v2_1_cover.jpg")
    assert os.path.getsize(jpg) > 0
    with open(jpg, "rb") as f:
        assert f.read() == _StepdownPublisher.Q80_BYTES, "产物应为 q80 档返回的字节"
    out = capsys.readouterr().out
    assert "(q80)" in out, f"打印行未体现实际降档质量：\n{out}"


def test_non_oversize_error_raises_without_stepdown(tmp_path):
    """ValueError（未返回 data / 页面未加载）不降档：各卡仅试 q92 即 raise，不尝 q80/q70。"""
    v2, mf = _mk(tmp_path, 0)
    for i, sl in enumerate(SLOTS, 1):
        os.utime(os.path.join(v2, "images", f"card_v2_{i}_{sl}.html"), (1000, 1000))

    fake = _StepdownPublisher(raise_value_error=True)
    rc, _ = _run_with_fake_cdp(v2, publisher=fake)

    assert rc == 1
    assert fake.shots == [92, 92] * 6, f"非 oversize 异常不得降档，实际 {fake.shots}"
    jpgs = [f for f in os.listdir(os.path.join(v2, "images")) if f.endswith(".jpg")]
    assert jpgs == [], f"失败渲染留下了残留：{jpgs}"
    m = json.load(open(mf))
    assert m["images_rendered"] is False
