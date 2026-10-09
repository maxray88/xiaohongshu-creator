#!/usr/bin/env python3
"""
情绪树洞 — 竖版视频笔记合成器 (1080×1920, 9:16)
Edge-TTS 主引擎，全卡统一声音。
自动找到最新的 day 目录，支持 v1/v2。

S1 重构：TTS 切片移至 tts_slicing.py，ffmpeg 合成移至 ffmpeg_build.py。
本文件只保留目录解析 + 主编排。

用法:
  python3 _cron_assemble.py              # 自动找最新 day
  python3 _cron_assemble.py --day 20260723  # 指定日期
"""
import json, os, re, subprocess, sys, time

from ffmpeg_build import build_segments, cleanup, concat_segments, generate_tts
from tts_slicing import get_card_texts

# ── 向后兼容 re-export（tests/test_tts_slicing.py 仍从此模块取）──
from tts_slicing import clean_tts_text, _truncate_tts
from ffmpeg_build import (
    get_audio_duration, _valid_mp4, TTS_VOICE, TTS_RATE,
)

__all__ = ["clean_tts_text", "_truncate_tts",
           "get_audio_duration", "_valid_mp4", "TTS_VOICE", "TTS_RATE"]


BASE = os.path.expanduser("~/.hermes/data/xhs_treehole")


def find_latest_day():
    """Find the latest day_{date}_day{N}_v2 directory."""
    dirs = sorted([
        d for d in os.listdir(BASE)
        if os.path.isdir(os.path.join(BASE, d)) and d.startswith("day_") and d.endswith("_v2")
    ], reverse=True)
    if not dirs:
        print("[FATAL] No day directories found")
        sys.exit(1)
    return dirs[0]


def resolve_dirs(day_spec):
    """Given a v2 dir name, find v1 counterpart. Fallback to latest V1 if today V1 missing (01:00 offline)."""
    v2_dir = os.path.join(BASE, day_spec)
    v1_name = re.sub(r"_v2$", "", day_spec)
    v1_dir = os.path.join(BASE, v1_name)
    if not os.path.isdir(v1_dir):
        # 01:00 offline → V2 exists (created from previous day's V1) but V1 dir missing
        # Fallback to the most recent V1 that has post_data.json, so video can still be built
        candidates = sorted([d for d in os.listdir(BASE) if os.path.isdir(os.path.join(BASE, d)) and d.startswith("day_") and not d.endswith("_v2")], reverse=True)
        for cand in candidates:
            cand_path = os.path.join(BASE, cand)
            if os.path.isfile(os.path.join(cand_path, "post_data.json")):
                print(f"[WARN] v1 dir not found: {v1_dir} → fallback to latest V1: {cand_path}")
                return cand_path, v2_dir
        print(f"[FATAL] v1 dir not found: {v1_dir} and no fallback V1 available")
        sys.exit(1)
    return v1_dir, v2_dir


def read_manifest(v2_dir):
    """Read manifest.json from v2 dir."""
    m2_path = os.path.join(v2_dir, "manifest.json")
    if not os.path.isfile(m2_path):
        print(f"[FATAL] No manifest.json in {v2_dir}")
        sys.exit(1)
    with open(m2_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--day":
        day_date = sys.argv[2]
        candidates = sorted([
            d for d in os.listdir(BASE)
            if os.path.isdir(os.path.join(BASE, d))
            and d.startswith(f"day_{day_date}") and d.endswith("_v2")
        ], reverse=True)
        if not candidates:
            print(f"[FATAL] Day {day_date} v2 not found")
            sys.exit(1)
        v2_name = candidates[0]
    else:
        v2_name = find_latest_day()
        # 自动路径只合成「今天」的素材。01:00/02:00 生成历史上有 ~13% 的天数失败，
        # 这时最新 _v2 会落到昨天——重编码昨天视频纯属浪费（05:00 发布/03:00 填表/
        # 02:30 渲染已有同样守卫），且产物无人消费；直接跳过，06:00 watchdog 仍会
        # 以「今天没有生成新内容」告警。显式 --day 的历史目录不受影响（手动重合成保留）。
        v2_date = re.search(r"day_(\d{8})", v2_name)
        if not v2_date or v2_date.group(1) != time.strftime("%Y%m%d"):
            print(f"  ⏭ 最新素材是 {v2_name}（日期 {v2_date.group(1) if v2_date else '?'}），"
                  f"不是今天——跳过合成，避免对昨天视频做无谓重编码")
            sys.exit(0)

    v1_dir, v2_dir = resolve_dirs(v2_name)
    date_match = re.search(r"day_(\d{8})", v2_name)
    day_date = date_match.group(1) if date_match else "?"
    day_num_match = re.search(r"day(\d+)$", re.sub(r"_v2$", "", v2_name))
    day_num = day_num_match.group(1) if day_num_match else "?"

    print(f"[INFO] v2: {v2_name}")
    print(f"[INFO] v1: {os.path.basename(v1_dir)}")

    manifest = read_manifest(v2_dir)
    images_dir = os.path.join(v2_dir, "images")
    video_dir = os.path.join(v2_dir, "video")
    os.makedirs(video_dir, exist_ok=True)

    # Step 1: Verify images
    print(f"\n[STEP 1] Verifying images in {images_dir}...")
    missing = []
    for card in manifest.get("cards", []):
        p = os.path.join(images_dir, card["file"])
        ok = os.path.isfile(p)
        print(f"  {card.get('file','?')}: {'✓' if ok else '✗'}")
        if not ok:
            missing.append(card.get('file','?'))
    # Self-heal: if 02:30 render was skipped (V2 born after 02:30), JPGs will be missing
    # but HTML exists — render inline so 04:00 never fails on pad_*.png
    if missing:
        # 原先这里还有一个 has_html 变量，算了却从不用（pyflakes 长期报警）——
        # 它试图用「缺失文件名换成 .html 是否存在」来推断，但那种推断在
        # 目录里同时残留 HTML 和 JPG 时会给出误导性结论。下面的
        # html_count 是更直接的判据。
        html_count = len([f for f in os.listdir(images_dir) if f.endswith('.html')]) if os.path.isdir(images_dir) else 0
        if html_count >= 6:
            print(f"  ⚠️  {len(missing)} JPG missing but {html_count} HTML present — triggering inline render (02:30 was skipped)")
            try:
                proj = os.path.expanduser("~/02_Cronjobs_Projects/01_XHS_Daily_Post")
                r = subprocess.run(["bash", os.path.join(proj, "bin/render_xhs_cards.sh")], capture_output=True, text=True, timeout=180)
                print(r.stdout[-800:] if r.stdout else "")
                if r.stderr:
                    print(r.stderr[-400:])
                # reload manifest after render (flips .html→.jpg, images_rendered:true)
                manifest = read_manifest(v2_dir)
                # re-verify
                for card in manifest.get("cards", []):
                    p = os.path.join(images_dir, card["file"])
                    if not os.path.isfile(p):
                        print(f"  [FATAL] Still missing after inline render: {p}")
                        sys.exit(1)
                print("  ✅ Inline render succeeded")
            except Exception as e:
                print(f"  [FATAL] Inline render failed: {e}")
                sys.exit(1)
        else:
            print(f"  [FATAL] {len(missing)} images missing and no HTML to render from")
            sys.exit(1)

    # Step 2: Derive TTS texts from content_text (post_data.json) — one slice per card role
    print(f"\n[STEP 2] Deriving TTS texts from content_text (post_data.json)...")
    texts, title, series, emotion_tag = get_card_texts(v1_dir, manifest)
    for i, t in sorted(texts.items()):
        preview = t[:60] + ("…" if len(t) > 60 else "")
        print(f"  Card {i}: {len(t)} chars — {preview}")

    # Step 3: TTS — Edge-TTS（唯一引擎，全卡统一声音）
    durations, engine_used = generate_tts(texts, video_dir)
    print(f"  Durations: { {k: f'{v:.2f}s' for k, v in durations.items()} }")

    # Step 4-5: Build + concat
    segments, card_types = build_segments(manifest, images_dir, video_dir, durations)
    expected_duration = sum(durations.values())
    output_path, fdur, fsize, vw, vh = concat_segments(segments, video_dir, expected_duration)

    # Step 6: Cleanup
    cleanup(video_dir)

    # ── Report ──
    print("\n" + "=" * 64)
    print("📹 情绪树洞 · 竖版视频笔记合成报告")
    print("=" * 64)
    print(f"  日期:         {day_date} (Day {day_num})")
    print(f"  系列:         {series}")
    print(f"  标题:         {title}")
    print(f"  情绪标签:     {emotion_tag}")
    print(f"  版本:         v2")
    print(f"  画布:         {vw}×{vh} (9:16 竖版)")
    print(f"  TTS 引擎:     {engine_used}")
    print(f"  配音一致性:   ✅ 同一声音（同一引擎同一参数）")
    print("-" * 64)
    print(f"  视频时长:     {fdur:.2f}s ({fdur/60:.1f} 分钟)")
    print(f"  文件大小:     {fsize/1024/1024:.1f} MB")
    print(f"  输出路径:     {output_path}")
    print("-" * 64)
    print("  TTS 时长分布:")
    total = sum(durations.values())
    for card in manifest.get("cards", []):
        i = card["index"]
        dur = durations.get(i, 0)
        pct = dur / total * 100 if total > 0 else 0
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        ctype = card_types.get(i, f"card{i}")
        print(f"    Card {i} ({ctype:8s}): {dur:6.2f}s  {bar}  {pct:3.0f}%")
    print(f"    {'─' * 48}")
    print(f"    总 TTS: {total:.2f}s")
    print("=" * 64)


if __name__ == "__main__":
    main()
