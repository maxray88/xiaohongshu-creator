#!/usr/bin/env python3
"""TTS 切片回归测试（新 TTS 口径：content_text → 六卡）。

覆盖核心不变量：
- 六卡齐全、非空、≤300 字
- method(4) 与 gentle(5) 不重复（day46 曾因此返工）
- cover 含品牌与标题；cta 围绕 emotion_tag 生成
- 边界：空正文、单段正文、缺字段时不抛异常且仍有 6 卡

运行：python3 -m pytest tests/ -v（项目根目录）
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core"))
import _cron_assemble
from _cron_assemble import clean_tts_text, get_card_texts

BASE = os.path.join(os.path.expanduser("~"), ".hermes", "data", "xhs_treehole")
MANIFEST = {"series": "情绪树洞 · 与自己和解", "title": "测试标题",
            "emotion_tag": "测试情绪",
            "cards": [{"index": i} for i in range(1, 7)]}

BODY_8PARA = "\n\n".join([
    "测试情绪，是你明明想说不却说了好的那一刻。",
    "中午同事让你帮忙，你嘴比脑子快，先说了好呀。",
    "你不是不会说不，你只是太怕气氛变冷了。",
    "心理学上这叫测试情绪，你不是没边界，你只是太善良。",
    "你也是这样的吗？明明心里在大喊，脸上还挂着笑？",
    "试试这个小练习，下次先做三次深呼吸，再回答对方。",
    "不会拒绝不是你的错，是你太想被喜欢了。今晚对自己温柔一点。",
])


def _texts(body, **kw):
    pd = {"series": "情绪树洞 · 与自己和解", "title": "测试标题",
          "emotion_tag": "测试情绪", "content_text": body}
    pd.update(kw)
    return get_card_texts("no_such_dir", MANIFEST, post_data=pd)


def test_six_cards_present_and_bounded():
    texts, title, series, tag = _texts(BODY_8PARA)
    assert sorted(texts.keys()) == [1, 2, 3, 4, 5, 6]
    assert all(t and t.strip() for t in texts.values())
    assert all(len(t) <= 300 for t in texts.values())
    assert (title, series, tag) == ("测试标题", "情绪树洞 · 与自己和解", "测试情绪")


def test_method_gentle_distinct():
    texts, _, _, _ = _texts(BODY_8PARA)
    assert texts[4].strip() != texts[5].strip()
    assert "深呼吸" in texts[4]
    assert "温柔" in texts[5]


def test_cover_and_cta_roles():
    texts, _, _, _ = _texts(BODY_8PARA)
    assert "情绪树洞" in texts[1] and "测试标题" in texts[1]
    assert "测试情绪" in texts[6] and "评论区" in texts[6]


def test_empty_body_falls_back_without_crash():
    texts, _, _, _ = _texts("")
    assert sorted(texts.keys()) == [1, 2, 3, 4, 5, 6]
    assert all(t and t.strip() for t in texts.values())


def test_single_paragraph_body():
    texts, _, _, _ = _texts("只有一段话，测试情绪在其中。")
    assert sorted(texts.keys()) == [1, 2, 3, 4, 5, 6]
    assert all(t and t.strip() for t in texts.values())


def test_missing_keys_use_manifest():
    texts, title, series, tag = get_card_texts(
        "no_such_dir", MANIFEST, post_data={"content_text": BODY_8PARA})
    assert title == "测试标题" and series == "情绪树洞 · 与自己和解" and tag == "测试情绪"


def test_clean_tts_strips_branding_but_keeps_content():
    out = clean_tts_text("情绪树洞 · 今天聊聊测试情绪。")
    assert "情绪树洞" not in out and "测试情绪" in out


def test_real_day62_slices_are_distinct():
    day = os.path.join(BASE, "day_20260907_day62")
    v2m_path = os.path.join(BASE, "day_20260907_day62_v2", "manifest.json")
    if not os.path.isdir(day) or not os.path.isfile(v2m_path):
        import pytest
        pytest.skip("day62 fixture absent")
    v2m = json.load(open(v2m_path, encoding="utf-8"))
    texts, _, _, _ = get_card_texts(day, v2m)
    assert sorted(texts.keys()) == [1, 2, 3, 4, 5, 6]
    assert texts[4].strip() != texts[5].strip()


# ── 段落认领（2026-09-27 day82）────────────────────────────────────
# 旧测试只断言 method(4) != gentle(5)，那是 day46 的单点；
# day82 撞的是 scene(2) vs insight(3)，day81 撞的是 method(4) vs
# gentle(5) 的兜底路径。共同成因是各卡独立选段、允许重复认领同一段。
# 这里按不变量断言：任意两张卡不得喂同一段。

BODY_DAY82 = "\n\n".join([
    "反PUA，是你终于能听见自己内心那句「这不对」的时候。",
    "你有没有这样的瞬间？上司的语气不低不高，什么都没说，"
    "但不是你的性格有问题，而是你已经替他否定了整整一天的你。",
    "你真的不够好吗？不是。你只是听惯了「差一点」这个鬼话。",
    "先试试这个有点傻但真的有用的小练习：当你听见「不够好」四个字的时候，"
    "在脑子里立刻加一句「够做什么」。",
    "够让别人舒服？一旦「够」后面有个具体东西，魔鬼的伪装就破了。",
    "反PUA，不是变成反抗的人，而是你不再默认别人的标准是你的唯一尺子。",
    "你不是不够好，你只是太久没给自己一个机会。",
    "今天的事，就到此为止吧。",
])


def test_no_two_cards_share_the_same_paragraph_day82():
    texts, _, _, _ = _texts(BODY_DAY82)
    vals = [texts[i].strip() for i in range(1, 7)]
    assert len(set(vals)) == 6, f"卡位文本重复: {[v[:30] for v in vals]}"


def test_scene_and_insight_distinct_when_scene_contains_insight_pattern():
    """day82 卡2 的场景段本身含「不是…而是」，正是卡3 的选取条件。"""
    texts, _, _, _ = _texts(BODY_DAY82)
    assert texts[2].strip() != texts[3].strip()
    assert "同事" not in texts[3] and "上司" in texts[2]


def test_no_two_cards_share_the_same_paragraph_day81():
    """day81：method 关键词未命中时兜底到 paragraphs[-1]，与 gentle 撞车。"""
    body = "\n\n".join([
        "存在感稀薄，是你发了一条消息，三个小时没人回复。",
        "你说你理解每个人都有自己的节奏，但群里有人@所有人而你不是。",
        "成年人的孤独，有时候不是没人陪。",
        "你不是不得别人，你只是怕别人不得你。",
        "你有没有想过，那些没人得我的时刻，也许只是别人在处理自己的事。",
        "今天试试这个练习：写下三件你做了但从没人夸过的事。",
        "你不得每时每刻都被看见，才证明你在这里。",
        "你也是这样的吗？那些没人接的话，听听看，其实并不少见。",
    ])
    texts, _, _, _ = _texts(body)
    vals = [texts[i].strip() for i in range(1, 7)]
    assert len(set(vals)) == 6, f"卡位文本重复: {[v[:30] for v in vals]}"


def test_sparse_body_never_raises_and_still_yields_six_cards():
    """段落不够 6 段时必然复用内容，但必须 6 卡齐全非空。"""
    for body in ["只有一段。", "第一段。\n\n第二段。", "A。\n\nB。\n\nC。"]:
        texts, _, _, _ = _texts(body)
        assert sorted(texts.keys()) == [1, 2, 3, 4, 5, 6]
        assert all(t and t.strip() for t in texts.values())


def test_every_retained_day_has_six_distinct_slices():
    """对 05:30 清理后仍在盘的每一天跑一遍，回归护栏。"""
    import glob
    days = sorted(d for d in glob.glob(os.path.join(BASE, "day_*"))
                  if os.path.isdir(d) and not d.endswith("_v2"))
    if not days:
        import pytest
        pytest.skip("no retained day dirs")
    for day in days:
        pf = os.path.join(day, "post_data.json")
        if not os.path.isfile(pf):
            continue
        pd = json.load(open(pf, encoding="utf-8"))
        texts, _, _, _ = get_card_texts(day, MANIFEST, post_data=pd)
        vals = [texts[i].strip() for i in range(1, 7)]
        assert len(set(vals)) == 6, f"{os.path.basename(day)} 卡位重复"
