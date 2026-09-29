#!/usr/bin/env python3
"""check_content_quality 的 V2 manifest 自愈回归测试。

H1/H2/H3（2026-09-27 审计）：旧自愈实现
- 要求 HTML 以 `card_v2_` 开头，01:00 改用 card_01_ 风格后永不触发
- 重建的 manifest 硬编码 6 个 card_v2_* 文件名，与磁盘真实文件名不符
  → 重建出指向不存在文件的 manifest，失败点移到 02:30/04:00
- 配色池硬编码 10 个名字，与 design_tokens.json 必然分叉
- except: pass —— 自愈失败完全静默

新实现：文件名从磁盘实测枚举；配色读 design_tokens；异常记进 checks。

全部在 tempfile 沙盒里跑，不碰真实数据。BASE 会被 monkeypatch 到沙盒。
运行：python3 -m pytest tests/ -q（项目根目录）
"""

import importlib.util
import json
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
_spec = importlib.util.spec_from_file_location(
    "check_content_quality", os.path.join(ROOT, "bin", "check_content_quality.py"))
cq = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cq)

SLOTS = ["cover", "scene", "insight", "method", "gentle", "cta"]


def _mkday(base, date_c, day_num=99, naming="card_v2_{i}_{s}.html", njhtml=6):
    """造一天：V1（post_data + manifest）+ V2（只放 HTML，不放 manifest）。"""
    v1 = os.path.join(base, f"day_{date_c}_day{day_num}")
    v2 = v1 + "_v2"
    os.makedirs(os.path.join(v1, "images"), exist_ok=True)
    os.makedirs(os.path.join(v2, "images"), exist_ok=True)
    json.dump({"title": "你不是不够好", "series": "情绪树洞",
               "content_text": "正文。" * 120, "emotion_tag": "反PUA",
               "day_num": day_num, "hashtags": ["情绪树洞", "反PUA", "自我价值",
                                                "情绪疗愈", "心理成长", "深夜emo"],
               "best_post_time": "2026-01-01 22:00:00"},
              open(os.path.join(v1, "post_data.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    json.dump({"title": "你不是不够好", "series": "情绪树洞",
               "day_num": day_num, "color_scheme": "海盐汽水",
               "v1_color_scheme": "海盐汽水"},
              open(os.path.join(v1, "manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    made = []
    for i, sl in enumerate(SLOTS, 1):
        if i > njhtml:
            break
        fn = naming.format(i=i, s=sl)
        open(os.path.join(v2, "images", fn), "w").write("<html>x</html>")
        made.append(fn)
    return v1, v2, made


class _FakeDT:
    """只提供 strftime('%Y%m%d')，够 main() 用来找今天的目录。"""
    def __init__(self, date_c):
        self._d = date_c

    def strftime(self, fmt):
        if fmt == "%Y%m%d":
            return self._d
        raise AssertionError(f"未预期的 strftime 格式: {fmt}")


def _patch_base(monkeypatch, base, date_c="20260101"):
    monkeypatch.setattr(cq, "BASE", base)
    monkeypatch.setattr(cq, "datetime", type("D", (), {
        "now": staticmethod(lambda: _FakeDT(date_c))}))


# ── H1：卡名风格变化后自愈仍要触发 ──────────────────────────────

def test_selfheal_works_with_padded_card_names(monkeypatch, tmp_path):
    """旧实现要求 card_v2_ 前缀；card_01_ 风格下永不触发。"""
    base = str(tmp_path)
    _, v2, made = _mkday(base, "20260101",
                         naming="card_{i:02d}_{s}.html")
    _patch_base(monkeypatch, base)
    rc = cq.main()
    mf = os.path.join(v2, "manifest.json")
    assert os.path.isfile(mf), "card_01_ 风格下自愈没触发"
    m = json.load(open(mf, encoding="utf-8"))
    assert len(m["cards"]) == 6
    # 关键：manifest 里的文件名必须是磁盘上真实存在的那些
    on_disk = set(os.listdir(os.path.join(v2, "images")))
    for c in m["cards"]:
        assert c["file"] in on_disk, f"manifest 指向不存在的文件: {c['file']}"
    assert m["images_rendered"] is False


def test_selfheal_works_with_v2_prefixed_names(monkeypatch, tmp_path):
    base = str(tmp_path)
    _, v2, _ = _mkday(base, "20260101", naming="card_v2_{i}_{s}.html")
    _patch_base(monkeypatch, base)
    cq.main()
    m = json.load(open(os.path.join(v2, "manifest.json"), encoding="utf-8"))
    on_disk = set(os.listdir(os.path.join(v2, "images")))
    assert all(c["file"] in on_disk for c in m["cards"])


# ── H1 负向：数据不全时绝不瞎重建 ───────────────────────────────

def test_no_rebuild_when_fewer_than_six_html(monkeypatch, tmp_path):
    base = str(tmp_path)
    _, v2, _ = _mkday(base, "20260101", njhtml=4)
    _patch_base(monkeypatch, base)
    cq.main()
    assert not os.path.isfile(os.path.join(v2, "manifest.json")), \
        "HTML 不全却重建了 manifest —— 会造出指向缺失文件的假 manifest"


def test_no_rebuild_when_slot_names_unrecognizable(monkeypatch, tmp_path):
    base = str(tmp_path)
    v1, v2, _ = _mkday(base, "20260101", njhtml=0)
    imgs = os.path.join(v2, "images")
    for i in range(6):
        open(os.path.join(imgs, f"random_{i}.html"), "w").close()
    _patch_base(monkeypatch, base)
    cq.main()
    assert not os.path.isfile(os.path.join(v2, "manifest.json")), \
        "认不出卡位却重建了"


# ── H3：配色来自 design_tokens 而非硬编码 ──────────────────────

def test_healed_theme_comes_from_design_tokens(monkeypatch, tmp_path):
    base = str(tmp_path)
    _, v2, _ = _mkday(base, "20260101")
    _patch_base(monkeypatch, base)
    cq.main()
    m = json.load(open(os.path.join(v2, "manifest.json"), encoding="utf-8"))
    tokens = json.load(open(os.path.join(cq.PROJ, "design", "design_tokens.json"),
                            encoding="utf-8"))["themes"]
    assert m["color_scheme"] in tokens, \
        f"自愈挑了 design_tokens 里不存在的配色: {m['color_scheme']}"


def test_pick_theme_avoids_excluded():
    tokens = list(json.load(open(os.path.join(cq.PROJ, "design", "design_tokens.json"),
                                 encoding="utf-8"))["themes"])
    first, second = tokens[0], tokens[1]
    assert cq._pick_theme(exclude={first}) == second
