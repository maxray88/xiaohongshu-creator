#!/usr/bin/env python3
"""V2 本地确定性构建（无 LLM）。

V2 的本质是「V1 原文逐字 + 换一套视觉」。这不需要 LLM：沿用 day64/day65
验证过的 luminance-remap——把 V1 HTML 里全部 hex 颜色按亮度排序，
映射到目标主题的同长度渐变带，文字一字不动。

主题选择：按 design_tokens.json 的既定顺序，取第一个满足
「≠当天 V1 且不在最近 3 天 V2 里」的主题（pick_theme 内自实现该校验，
不调 theme_rotation.validate_rotation——那个函数额外把 V1 历史重复
当作 error，会让候选全军覆没）。全程确定性：同样的 V1 + 同样的历史
→ 同样的 V2。

替代 02:00 LLM agent 的原因（day71 事故）：
Hermes 调度层 provider 熬断（offline/429/?warming）时 agent 根本起不来，
V2 缺 manifest → 02:15/02:30/04:00/05:00 连环误报。本地脚本零配额、
零网络（除已验证的 TTS 无关），把这一整类单点消除。

输出：day_YYYYMMDD_dayN_v2/{images/card_v2_*_*.html, manifest.json}
注意 manifest.cards[].file 故意写 .html、images_rendered=False——
渲染与 .html→.jpg 翻转是 02:30 的职责（已硬化 skip 分支回填）。

用法：python3 build_v2_local.py [day_20260916_day71]
无参数则取今天（本人时区）的 V1 目录。
"""
import json
import os
import re
import shutil
import sys
import time
import glob

PROJ = os.path.join(os.path.expanduser("~"), "02_Cronjobs_Projects", "01_XHS_Daily_Post")
sys.path.insert(0, os.path.join(PROJ, "core"))
from theme_rotation import pick_today_v1, recent_schemes  # noqa: E402  (pick_theme 自实现校验，不用 validate_rotation)
from xhs_config import DATA_BASE  # noqa: E402

BASE = DATA_BASE

# 逻辑卡位 → V1 文件名后缀。文件名本身不写死：
# 01:00 LLM 历史上产出过两种命名（card1_cover.html 与 card_01_cover.html，
# day82 首次变卦），写死任何一种都会让 V2 整条链断在 02:00。
# 改为按后缀 glob 解析（见 _resolve_cards），两种命名都吃。
CARD_SLOTS = ["cover", "scene", "insight", "method", "gentle", "cta"]


def _resolve_cards(v1_images):
    """(suffix, v1_path) 列表，按 card 编号排序；找不到即返回 None 让调用方报错。"""
    out = []
    for i, slot in enumerate(CARD_SLOTS, 1):
        hits = glob.glob(os.path.join(v1_images, f"card*{slot}*.html"))
        if not hits:
            return None, f"card*{slot}*.html"
        # 同卡位多份命名（残留的 card1_cover.html + 新的 card_01_cover.html）
        # 属于上游状态脏，不许悄悄挑一个——与缺卡同等级 loud fail。
        if len(hits) > 1:
            return None, f"card*{slot}*.html 有 {len(hits)} 个候选: {sorted(map(os.path.basename, hits))}"
        out.append((slot, hits[0]))
    return out, None


def _hx(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def _lum(h):
    r, g, b = _hx(h)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _ramp(anchors, n):
    """anchors 按亮度排好序的 hex 列表 → 插值出 n 级渐变带。"""
    pts = [_hx(a) for a in anchors]
    if len(pts) == 1:
        return anchors * n
    out, segs = [], len(pts) - 1
    for i in range(n):
        x = i / max(n - 1, 1) * segs
        k = min(int(x), segs - 1)
        f = x - k
        rgb = tuple(round(pts[k][c] + (pts[k + 1][c] - pts[k][c]) * f) for c in range(3))
        out.append("#%02X%02X%02X" % rgb)
    return out


def pick_theme(v1_cs, last_v1, last_v2):
    tokens = json.load(open(os.path.join(PROJ, "design", "design_tokens.json"),
                            encoding="utf-8"))["themes"]
    # 只校验 V2 候选（≠当天 V1、不在近 3 天 V2 里）。
    # 当天 V1 若已与历史重复（01:00 LLM 误读导致，如 day77 玫瑰暮云撞 day74_v2），
    # 那是既成事实：此处只告警、不阻断。旧代码调 validate_rotation(v1_cs, name, ...)
    # 会把当天 V1 的重复问题带进每个候选的判定 → 全军覆没 → V2 永远建不出来。
    if v1_cs and v1_cs in (set(last_v1) | set(last_v2)):
        print(f"⚠️ 当天 V1 主题「{v1_cs}」已与近 3 天重复——V2 仍继续构建（降级），02:15/06:00 会合规告警")
    for name in tokens:  # 文件既定顺序 = 确定性优先级
        if v1_cs and name == v1_cs:
            continue
        if name in set(last_v2):
            continue
        return name, tokens[name]
    raise RuntimeError(f"无可用 V2 主题（V1={v1_cs}，近3天V2={sorted(last_v2)}）")


def main() -> int:
    today_c = time.strftime("%Y%m%d")
    if len(sys.argv) > 1:
        v1_name = sys.argv[1]
    else:
        days = sorted(d for d in os.listdir(BASE)
                      if d.startswith("day_") and not d.endswith("_v2")
                      and os.path.isdir(os.path.join(BASE, d)))
        v1_name = pick_today_v1(days, today_c)
        if not v1_name:
            print(f"❌ 今天（{today_c}）没有 V1 目录——01:00 未产出，V2 无法构建")
            return 1

    v1_dir = os.path.join(BASE, v1_name)
    v2_dir = os.path.join(BASE, v1_name + "_v2")
    v2_mf = os.path.join(v2_dir, "manifest.json")

    # 幂等保护：02:30 已渲染过的 V2 不许被覆盖。
    # 覆盖会做两件坏事——(a) 02:15/06:00 看到 images_rendered 翻回 False 而误报；
    # (b) 若新抽到不同主题，.html 与已渲染的 .jpg 主题对不上，04:00 合成的
    # 视频是「新主题的 HTML + 旧主题的 JPG」的错配。
    # 例：2026-09-27 调试时用 day_20260926_day81 跑回归，manifest 被重写。
    if os.path.isfile(v2_mf):
        try:
            if json.load(open(v2_mf, encoding="utf-8")).get("images_rendered"):
                print(f"⏭ {v1_name}_v2 已渲染，跳过（防覆盖：保 images_rendered 与主题一致性）。"
                      f"如需重建请先删 {v2_mf}")
                return 0
        except (ValueError, OSError):
            pass  # manifest 损坏则照常重建

    v1_mf = os.path.join(v1_dir, "manifest.json")
    # V1 manifest 是 LLM agent 产出的单点（今天 day75 因此缺失）。
    # 从 post_data.json 读取元信息，从 HTML 卡的主题色推导 V1 主题，
    # manifest 缺失时按"无 V1 主题"处理，V2 pick_theme 仍保证不重复。
    post_data = json.load(open(os.path.join(v1_dir, "post_data.json"), encoding="utf-8"))
    if os.path.isfile(v1_mf):
        v1_cs = json.load(open(v1_mf, encoding="utf-8")).get("v1_color_scheme") or \
                json.load(open(v1_mf, encoding="utf-8")).get("color_scheme")
    else:
        v1_cs = None
        print(f"⚠️ V1 manifest 缺失（{v1_mf}）——跳过 V1 主题校验，V2 仍保证与近 3 天不重复")
    last_v1, last_v2 = recent_schemes(BASE, v1_name[4:12], n=3)
    theme_name, theme = pick_theme(v1_cs, last_v1, last_v2)
    print(f"🎨 V2 主题：{theme_name} · {theme.get('vibe', '')}（V1={v1_cs}，近3天V2={sorted(last_v2)}）")

    anchors = sorted({c.upper() for c in
                      theme["bg"] + [theme["accent"], theme["text"], theme["muted"], "#FFFFFF"]},
                     key=_lum)
    v2_name = v1_name + "_v2"
    img_out = os.path.join(v2_dir, "images")
    os.makedirs(img_out, exist_ok=True)

    v1_images = os.path.join(v1_dir, "images")
    cards, missing = _resolve_cards(v1_images)
    if cards is None:
        print(f"❌ V1 缺 {missing}——01:00 产出不完整，先修 01:00")
        return 1

    for idx, (slot, src_p) in enumerate(cards, 1):
        dst = f"card_v2_{idx}_{slot}.html"
        t = open(src_p, encoding="utf-8").read()
        palette = sorted({c.upper() for c in re.findall(r"#[0-9A-Fa-f]{6}", t)}, key=_lum)
        swaps = dict(zip(palette, _ramp(anchors, len(palette)))) if palette else {}
        t = re.sub(r"#[0-9A-Fa-f]{6}",
                   lambda m: swaps.get(m.group(0).upper(), m.group(0)), t)
        t = t.replace("</style>",
                      f"\n/* V2 {theme_name} · {theme.get('vibe', '')} "
                      f"(luminance remap of V1 {v1_cs}, text untouched) */\n</style>")
        open(os.path.join(img_out, dst), "w", encoding="utf-8").write(t)
        print(f"  ✅ {dst}（{len(t)} 字节，文字逐字保留）")

    v1_assets = os.path.join(v1_images, "assets")
    v2_assets = os.path.join(img_out, "assets")
    if os.path.isdir(v1_assets):
        shutil.copytree(v1_assets, v2_assets, dirs_exist_ok=True)
        n_assets = sum(len(fs) for _, _, fs in os.walk(v2_assets))
        print(f"  ✅ assets 随卡携带（{n_assets} 个文件，V1 照片不破图）")
    else:
        print("  ⏭ 无 assets 目录，跳过携带（旧照片-free 天）")

    day_num = post_data.get("day_num", 0)
    manifest = {
        "title": post_data["title"],
        "series": post_data["series"],
        "day_num": day_num,
        "emotion_tag": post_data.get("emotion_tag", ""),
        "v1_color_scheme": v1_cs,
        "color_scheme": theme_name,
        "v2_angle": f"{theme_name} · {theme.get('vibe', '')}",
        "images_rendered": False,
        "builder": "build_v2_local.py (deterministic, no LLM)",
        "cards": [
            # enumerate(cards, 1) 已经产出 1..6；此处不要再 +1。
            # 契约：index 必须 1..6（_cron_assemble.py 用 durations.get(i) 按
            # TTS 输出的 card_1..6.wav 索引，check_content_quality.py 的
            # 自愈 manifest 也是 1..6）。写成 i+1 会让 index 变成 2..7，
            # 卡 6 永远取不到时长并静默回退 3.0s。
            {"index": i, "file": f"card_v2_{i}_{slot}.html", "type": slot}
            for i, (slot, _) in enumerate(cards, 1)
        ],
    }
    json.dump(manifest, open(os.path.join(v2_dir, "manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"✅ V2 就绪：{v2_name}（title/series 与 V1 逐字一致，待 02:30 渲染）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
