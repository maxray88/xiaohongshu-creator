#!/usr/bin/env python3
"""XHS 情绪树洞 02:15 内容质量门。

在 02:30 渲染之前对今天刚生成的 V1/V2 做质量拦截：06:00 watchdog 是事后
合规门，这个是事前门——同样的问题早 4 小时告警，避免浪费一次 Chrome 渲染、
一次视频合成与两份问题草稿。

评分模型借鉴 xhs-content-pipeline 设计的 5 维百分制思路，但全部用本地启发式
实现（零 LLM 开销，不碰 weekly quota）：
  8 个维度各 0/1，通过率 × 10 为总分，≥7.0 通过。

配合 hermes no_agent cron：
  - 通过 → 无 stdout、exit 0 → 静默
  - 未通过 → 输出 ❌ 报告（含分项明细）、exit 1 → feishu 告警
"""

import json
import os
import re
import sys
from datetime import datetime

BASE = os.path.join(os.path.expanduser("~"), ".hermes", "data", "xhs_treehole")

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core"))
from theme_rotation import manifest_color_scheme, recent_schemes, validate_rotation
from manifest_title import manifest_title, plain_title, plain_series
from content_checks import has_emoji as _has_emoji
from content_checks import load_json_tolerant

QUALITY_THRESHOLD = 7.0

PROJ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def _atomic_write_json(path: str, data: dict) -> None:
    """tmp + rename 原子写。写坏 manifest 会让 02:30/04:00 一起炸。"""
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _pick_theme(exclude) -> str:
    """从 design_tokens.json 取第一个不在 exclude 里的主题。

    不在代码里维护第二份配色池 —— 旧实现内嵌 10 个主题名，与
    design_tokens.json / 01:00 prompt 必然分叉，自愈时会挑到
    一个已废弃或根本不存在的名字。
    """
    try:
        tokens = json.load(open(os.path.join(PROJ, "design", "design_tokens.json"),
                               encoding="utf-8"))["themes"]
        for name in tokens:
            if name not in exclude:
                return name
        # 池子全被排除：返回第一个，让 validate_rotation 去报警，
        # 绝不静默挑一个「看起来差不多」的
        return next(iter(tokens))
    except Exception:
        # design_tokens 读不到时不能瞎猜，返回空让上层报「无法解析」
        return ""


def _load_json(path):
    return load_json_tolerant(path, default=None)


def _tts_slices_ok(v1_dir, manifest_v2):
    """TTS 切片可用性：沿用 _cron_assemble.get_card_texts 的切片逻辑，要求 6 卡非空、
    method(4) 与 gentle(5) 不重复、每卡 ≤300 字。返回 (ok, detail)。"""
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core"))
        import _cron_assemble
        texts, _, _, _ = _cron_assemble.get_card_texts(v1_dir, manifest_v2)
    except Exception as e:
        return False, f"TTS 切片异常：{e}"
    if sorted(texts.keys()) != [1, 2, 3, 4, 5, 6]:
        return False, "TTS 切片缺卡"
    if any(not (t or "").strip() for t in texts.values()):
        return False, "TTS 存在空卡"
    if any(len(t) > 300 for t in texts.values()):
        over = [i for i, t in texts.items() if len(t) > 300]
        return False, f"TTS 超长卡：{over}"
    if texts[4].strip() == texts[5].strip():
        return False, "method(4) 与 gentle(5) 文案重复"
    return True, "6 卡就绪且互不重复"


def main() -> int:
    today_c = datetime.now().strftime("%Y%m%d")
    checks = []  # (name, ok, detail)

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    days = sorted(
        [d for d in os.listdir(BASE) if d.startswith("day_") and not d.endswith("_v2")]
        if os.path.isdir(BASE) else []
    )
    today_v1 = next((d for d in reversed(days) if d[4:12] == today_c), None)
    if today_v1 is None:
        print("❌ XHS 内容质量门：今天没有生成 V1 内容（01:00 生成未跑或失败）")
        print("=" * 46)
        print("• [完整] 今天的 day_* V1 目录缺失——02:30 渲染与后续发布将全部跳过")
        return 1

    v1_dir = os.path.join(BASE, today_v1)
    v2_name = today_v1 + "_v2"
    v2_dir = os.path.join(BASE, v2_name)
    pd = _load_json(os.path.join(v1_dir, "post_data.json"))
    v1m = _load_json(os.path.join(v1_dir, "manifest.json"))
    v2m = _load_json(os.path.join(v2_dir, "manifest.json")) if os.path.isdir(v2_dir) else None
    # 自愈：02:00 偶发在 6 HTML 后崩溃漏写 manifest（输出 ?warming）
    # ——若 HTML 齐全则按 V1 重建。
    #
    # 三条硬规则（都是踩过坑才定下来的）：
    # 1. 文件名从磁盘实测枚举，不硬编码 card_v2_*/card_0*_*。
    #    01:00 曾产出 card_01_cover.html、02:00 产出 card_v2_1_cover.html，
    #    写死任何一种，自愈就会重建出指向不存在文件的 manifest ——
    #    失败点移到 02:30/04:00，离病因很远。实测不到 6 个就别猜。
    # 2. 配色从 design_tokens.json 读，不维护第二份硬编码池
    #    （原实现的 10 个名字与 prompt/design_tokens 必然分叉）。
    # 3. 写入原子（tmp+rename），异常必须记进 checks 而不是静默 pass。
    heal_detail = ""
    if v2m is None and os.path.isdir(v2_dir) and pd and v1m:
        try:
            imgs = os.path.join(v2_dir, "images")
            htmls = sorted(f for f in os.listdir(imgs)
                           if f.startswith("card") and f.endswith(".html")) \
                if os.path.isdir(imgs) else []
            if len(htmls) < 6:
                heal_detail = (f"HTML 只有 {len(htmls)} 个（需 6），不重建 manifest —— "
                               f"期望类似 card_v2_1_cover.html/card_01_cover.html，实得 {htmls[:8]}")
            else:
                slots = ["cover", "scene", "insight", "method", "gentle", "cta"]
                # 按卡位后缀归类，一个卡位一个文件（多候选取最新 mtime）
                cards, ambiguous = [], []
                for idx, slot in enumerate(slots, 1):
                    hits = [f for f in htmls if slot in f]
                    if not hits:
                        ambiguous.append(slot)
                        continue
                    best = max(hits, key=lambda f: os.path.getmtime(os.path.join(imgs, f)))
                    cards.append({"index": idx, "file": best, "type": slot})
                if ambiguous or len(cards) != 6:
                    heal_detail = (f"卡位无法唯一解析（缺/多: {ambiguous}），不重建 —— "
                                   f"HTML 列表 {htmls[:8]}")
                else:
                    v1_color = (v1m.get("color_scheme")
                                or v1m.get("v1_color_scheme") or "").strip()
                    last_v1, last_v2 = recent_schemes(BASE, today_c, n=3)
                    used = set(last_v1) | set(last_v2) | ({v1_color} if v1_color else set())
                    pick = _pick_theme(exclude=used)
                    rebuilt = {
                        "title": (pd.get("title") or "").strip(),
                        "series": (pd.get("series") or "").strip(),
                        "day_num": pd.get("day_num"),
                        "date": today_c,
                        "emotion_tag": (pd.get("emotion_tag") or "").strip(),
                        "v1_color_scheme": v1_color,
                        "color_scheme": pick,
                        "v2_angle": f"{pick} · 自愈重建",
                        "status": "v2_html_ready",
                        "cards": cards,
                        "images_rendered": False,
                        "renderer": "html-only (self-healed)",
                    }
                    _atomic_write_json(os.path.join(v2_dir, "manifest.json"), rebuilt)
                    v2m = rebuilt
                    heal_detail = f"已按磁盘实测文件名重建 manifest（{pick}，{len(cards)} 卡）"
        except Exception as e:
            heal_detail = f"自愈失败：{type(e).__name__}: {e}"
    if heal_detail:
        check("V2 manifest 自愈", v2m is not None, heal_detail)

    check("V1 素材完整", pd is not None and v1m is not None,
          "" if pd and v1m else "post_data.json 或 manifest.json 缺失/无法解析")
    check("V2 素材完整", v2m is not None,
          "" if v2m else f"{v2_name} 缺失（02:00 生成未跑或失败）")

    body = ((pd or {}).get("content_text") or "").strip()
    title = ((pd or {}).get("title") or "").strip()
    etag = ((pd or {}).get("emotion_tag") or "").strip()
    tags = (pd or {}).get("hashtags") or []
    paras = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()] if body else []

    check("正文长度 400–900 字", 400 <= len(body) <= 900, f"当前 {len(body)} 字")
    check("正文结构 ≥5 段", len(paras) >= 5, f"当前 {len(paras)} 段")
    check("含反问句", "？" in body)
    first = body.splitlines()[0].strip() if body else ""
    check("首句含 emotion_tag", bool(etag and first and etag in first),
          f"tag=「{etag}」" if not (etag and first and etag in first) else "")
    check("标题 ≤18 字且无 emoji", bool(title) and len(title) <= 18 and not _has_emoji(title),
          f"标题=「{title[:24]}」")
    check("标签 6–10 且含品牌词+tag",
          6 <= len(tags) <= 10 and any("情绪树洞" in t for t in tags)
          and (not etag or any(etag in t for t in tags)),
          f"当前 {len(tags)} 个")

    # 跨文件身份一致（图文/视频两条笔记标题分叉是最贵的错误之一）
    ptitle = title
    pseries = plain_series(pd)
    identity_ok = True
    identity_detail = ""
    # V1 manifest 的 title 有两种落法（扁平 / 嵌套 post_data.title）。
    # 这里曾只读扁平 → 嵌套 manifest 时 mtitle 为空 → 短路跳过，
    # V1 标题永不参与比对。与另两个检查器统一到 core/manifest_title.py。
    mtitle = manifest_title(v1m)
    v2title = plain_title(v2m)
    if mtitle and mtitle != ptitle:
        identity_ok, identity_detail = False, "V1 manifest 与 post_data 标题不一致"
    if v2title and v2title != ptitle:
        identity_ok, identity_detail = False, "V1 与 V2 标题不一致"
    if v2title and v2m and pseries and plain_series(v2m) != pseries:
        identity_ok, identity_detail = False, "V1 与 V2 系列名不一致"
    check("三文件标题/系列一致", identity_ok, identity_detail)

    # 主题轮换（与 06:00 同源规则）
    last_v1, last_v2 = recent_schemes(BASE, today_c, n=3)
    rot_problems = validate_rotation(
        manifest_color_scheme(v1_dir, want_v2=False) if v1m else None,
        manifest_color_scheme(v2_dir, want_v2=True) if v2m else None,
        last_v1, last_v2,
    )
    check("主题轮换无重复", not rot_problems, rot_problems[0] if rot_problems else "")

    # TTS 切片可用性（新 TTS 口径下 method/gentle 重复是最常见的切片退化）
    if v2m:
        ok, detail = _tts_slices_ok(v1_dir, v2m)
        check("TTS 六卡就绪", ok, "" if ok else detail)
    else:
        check("TTS 六卡就绪", False, "无 V2 manifest，无法切片")

    # 完整性是硬门：V1/V2 素材缺失时直接拦截（不走评分），缺什么一目了然。
    missing = [name for name, ok, detail in checks
               if name in ("V1 素材完整", "V2 素材完整") and not ok]
    passed = sum(1 for _, ok, _ in checks if ok)
    score = round(passed / len(checks) * 10, 1) if checks else 0.0
    if not missing and score >= QUALITY_THRESHOLD:
        return 0
    print(f"❌ XHS 内容质量门：{today_v1} 评分 {score}/10（阈值 {QUALITY_THRESHOLD}）")
    print("=" * 46)
    for name, ok, detail in checks:
        mark = "✓" if ok else "✗"
        line = f"• [{mark}] {name}"
        if not ok and detail:
            line += f"——{detail}"
        print(line)
    print("=" * 46)
    print("备注：")
    print("  · 在 02:30 渲染前拦截，请检查 01:00/02:00 生成日志后手动重跑对应 cron")
    return 1


if __name__ == "__main__":
    sys.exit(main())
