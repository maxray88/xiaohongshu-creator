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


def test_pick_today_v1_numeric_not_lexicographic():
    assert cq._pick_today_v1(
        ["day_20260101_day9", "day_20260101_day10"], "20260101"
    ) == "day_20260101_day10"


def test_pick_today_v1_max_and_other_dates_ignored():
    assert cq._pick_today_v1(
        ["day_20260101_day104", "day_20260101_day99", "day_20251231_day200"],
        "20260101",
    ) == "day_20260101_day104"


def test_pick_today_v1_none_and_malformed():
    assert cq._pick_today_v1(
        ["day_20251231_day1", "day_bogus", "day_2026010_day5", "notes"],
        "20260101",
    ) is None


# ── 硬门：任一失败即拦截（day105 回归） ──────────────────────────

def test_failed_helper_lists_failures_only():
    checks = [("a", True, ""), ("b", False, "detail"), ("c", False, ""),
              ("d", True, "x")]
    assert cq._failed(checks) == ["b", "c"]


def test_single_red_line_fails_gate(monkeypatch, tmp_path, capsys):
    """day105 回归：398 字正文（<400 红线）在旧评分制下能以高分混过
    02:15（exit 0），硬门下必须 exit 1 且报告点名长度项。

    红线隔离：正文恰好 398 字（<400 唯一红线），其余检查全绿——
    5 段式（空行分隔）、含？、首行含 etag「反PUA」、
    标题/标签/manifest/系列/主题/TTS 切片沿用 _mkday 默认装配。
    注：spec 写的是 body = "正文。" * 199，但那是 597 字（3×199），
    反而落在 400–900 区间内、长度项会通过。这里是真正的红线用例。"""
    base = str(tmp_path)
    v1, _, _ = _mkday(base, "20260101")
    pd_path = os.path.join(v1, "post_data.json")
    pd = json.load(open(pd_path, encoding="utf-8"))
    paras = [
        "反PUA第一课：你并没有做错什么，你只是太久没有被好好对待了，对吗？"
        "你把他的冷漠都归咎于自己不够好，可明明你已经做到了满分还要继续加试，"
        "请别再苛责自己了好吗？",
        "上周深夜你加班到十一点，拖着疲惫的身子回到家，他只回了一句多喝热水，"
        "你盯着屏幕看了很久很久，眼泪差点掉进泡面碗里，却还是回了一句没事，"
        "其实你多想被抱抱啊。",
        "心理学上这不是你的错，而是煤气灯操控在起作用，你的感受一直都是真的，"
        "他先否定你的情绪再扮演拯救者，这套路不是爱而是控制，你要看清楚，"
        "别再自我怀疑了好吗。",
        "下次当你又开始自责时，试着把这句话写下来贴在床头，每天读一遍提醒自己，"
        "你值得被认真对待，从今天起把他的评价放在一边，先听听你自己的声音吧，"
        "好吗？",
        "今晚早点睡吧，愿你梦里全是偏爱，明早醒来记得先抱抱自己再出门，"
        "天冷了记得加衣，情绪树洞会一直陪着每一个深夜emo却依然用力的你，"
        "晚安好梦，愿明天的你更勇敢，自信又闪闪发光！",
    ]
    body = "\n\n".join(paras)
    assert len(body) == 398, f"用例漂移：正文 {len(body)} 字，不再是 398 字红线"
    assert len(paras) >= 5
    assert "？" in body
    assert "反PUA" in body.splitlines()[0]
    pd["content_text"] = body
    json.dump(pd, open(pd_path, "w", encoding="utf-8"), ensure_ascii=False)
    _patch_base(monkeypatch, base)
    rc = cq.main()
    out = capsys.readouterr().out
    assert rc == 1
    failing = [ln for ln in out.splitlines() if "[✗]" in ln]
    assert len(failing) == 1, f"红线未隔离，同时失败：{failing}"
    assert "400" in failing[0], f"唯一失败项不是长度项：{failing}"
