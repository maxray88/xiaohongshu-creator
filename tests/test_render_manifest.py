#!/usr/bin/env python3
"""render_xhs_cards 的 manifest 回填逻辑回归测试。

H6（2026-09-27 审计）：旧实现无条件把所有 card file 从 .html 翻成 .jpg
并置 images_rendered=True，哪怕某张卡渲染失败/被跳过。下游 assemble
照 manifest 去读 .jpg，拿到的路径不存在，合成时才炸 —— 失败点离病因很远。

这里直接驱动 main() 的 manifest 段，验证它只反映「磁盘上真实存在」的 JPG。
"""

import json
import os
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


def _run_with_fake_cdp(v2, monkey_fail=True):
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
    fake = _FakePublisher()
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
    assert fake.shots == 6, "六次截图尝试"
    assert jpgs == [], f"失败渲染留下了残留：{jpgs}"
    m = json.load(open(mf))
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
