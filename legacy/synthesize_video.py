"""
# ARCHIVED: 已被现行流水线取代，禁止运行 —— 见 legacy/README.md
运行本脚本会向小红书上传并保存草稿/发布内容，且行为已不可控（内含
2026-08 前的账号上下文与选择逻辑）。如需发布，请使用 bin/ 下的现行脚本。

sys.exit 拦在所有 import 之前。
"""
import sys as _sys
_sys.stderr.write(
    "\n❌ synthesize_video.py 已归档，禁止运行。\n"
    "   现行发布脚本：bin/publish_xhs_video.sh / bin/publish_xhs_image.sh\n"
    "   背景见 legacy/README.md\n\n"
)
_sys.exit(2)

#!/usr/bin/env python3
"""
情绪树洞 — 竖版视频笔记合成器 (1080×1920, 9:16)
每张卡片独立 TTS（edge-tts），精确时长映射。
"""
import json, os, subprocess, sys, re, math
from pathlib import Path

BASE = "/Users/maochundong/.hermes/data/xhs_treehole"
D = "20260719"  # today

# ── Decide which version to use ──
# Prefer v2 if available (more recent/polished), fall back to v1
v1_dir = os.path.join(BASE, f"day_{D}_day13")
v2_dir = os.path.join(BASE, f"day_{D}_day13_v2")

v1_manifest = os.path.join(v1_dir, "manifest.json")
v2_manifest = os.path.join(v2_dir, "manifest.json")

# Check both actual directories
if os.path.isfile(v2_manifest):
    manifest_path = v2_manifest
    day_dir = v2_dir
    is_v2 = True
    print(f"[INFO] Using v2 manifest: {v2_manifest}")
elif os.path.isfile(v1_manifest):
    manifest_path = v1_manifest
    day_dir = v1_dir
    is_v2 = False
    print(f"[INFO] Using v1 manifest: {v1_manifest}")
else:
    print(f"[FATAL] No manifest found for today ({D})")
    sys.exit(1)

images_dir = os.path.join(day_dir, "images")
video_dir = os.path.join(day_dir, "video")
os.makedirs(video_dir, exist_ok=True)

with open(manifest_path, "r", encoding="utf-8") as f:
    manifest = json.load(f)

title = manifest.get("title", "无标题")
series = manifest.get("series", "")
emotion_tag = manifest.get("emotion_tag", "")
cards_meta = manifest.get("cards", [])

print(f"[INFO] Series: {series} | Title: {title} | Tag: {emotion_tag}")
print(f"[INFO] Cards: {len(cards_meta)} | v2: {is_v2}")
print(f"[INFO] Images dir: {images_dir}")
print(f"[INFO] Video dir: {video_dir}")

# ── Verify all images exist ──
for card in cards_meta:
    img_path = os.path.join(images_dir, card["file"])
    exists = "✓" if os.path.isfile(img_path) else "✗"
    print(f"  Image {card['index']} ({card['type']}): {card['file']} [{exists}]")

print()

# ── TTS Text for each card ──
# For v2 (deep red → dusty rose), based on generate_day13_v2.py HTML content
TTS_TEXTS_V2 = {
    1: "你值得被坚定选择。别把暧昧错当成真心。清醒恋爱，自我边界。",
    2: "暧昧的信号。你是否有过这样的感觉？他只在深夜找你，消息回得忽快忽慢，从不把你介绍给朋友。你总在猜，他到底喜不喜欢你。真相是：如果你需要反复确认，那答案就是否定的。",
    3: "清醒洞察。暧昧让你内耗，真爱让你安定。暧昧是他有空时才想起你，真爱是他再忙也会告诉你。暧昧让你反复看手机等消息，真爱是他主动让你安心。暧昧是你一个人在演独角戏，真爱是你们一起写剧本。暧昧消耗你，真爱滋养你。",
    4: "设立边界。如何停止内耗？第一步，承认事实：他不找你，不是因为忙，是因为不想。第二步，停止揣摩：他的每个动作不需要你解析。第三步，收回期待：不对暧昧对象投入女友级的情感。第四步，把时间还给自己：投资自己永远不会亏。你的边界，是你最好的保护。",
    5: "想对你说。不是你不够好，是那个人不够真诚。真正爱你的人，不会让你在迷雾中寻找答案，不会让你独自消化所有委屈，不会让你怀疑自己是否值得被爱。你本来就很珍贵，不需要谁的认可来证明。",
    6: "聊聊吧。你值得明确的喜欢，而不是暧昧的观望。你有没有经历过让你内耗的暧昧？评论区说说你的故事。",
}

# For v1 (sage green → warm cream), based on generate_cards.py data structure
TTS_TEXTS_V1 = {
    1: "恋爱清醒脑。别把暧昧当爱情。清醒一点，别骗自己了。",
    2: "暧昧的场景。他偶尔找你聊天，偶尔关心你，偶尔让你觉得有希望。但你需要他的时候，他总是不在。",
    3: "清醒洞察。暧昧是他在无聊时才想起你，爱情是他需要你，也愿意被你需要。暧昧是你永远在等他的消息，爱情是你不用等，他就在。暧昧最大的残忍，是给你希望，却不给你结果。",
    4: "如何分辨。看他是否只在他方便的时候找你，看他是否愿意把你介绍给朋友，看他在你脆弱时是否在你身边，看他是否认真规划过你们的未来。行动比语言更真实。",
    5: "想对你说。不是你不够好，是对方不够真诚。真正喜欢你的人，舍不得让你猜，舍不得让你等，舍不得让你一个人在心里演完一整部戏。",
    6: "别把暧昧当爱情。你有没有经历过分不清暧昧和喜欢的时刻？评论区说说你的故事。",
}

TTS_TEXTS = TTS_TEXTS_V2 if is_v2 else TTS_TEXTS_V1

# ── Step 3: Generate TTS audio for each card ──
def get_audio_duration(mp3_path):
    """Get duration of MP3 in seconds using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of", "csv=p=0", mp3_path
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0

print("\n[STEP 3] Generating TTS audio for each card...")
durations = {}
for card in cards_meta:
    i = card["index"]
    text = TTS_TEXTS.get(i)
    if not text:
        print(f"  [WARN] No TTS text for card {i}, skipping")
        continue

    mp3_path = os.path.join(video_dir, f"card_{i}.mp3")

    # Skip if already exists and non-empty
    if os.path.isfile(mp3_path) and os.path.getsize(mp3_path) > 1000:
        dur = get_audio_duration(mp3_path)
        if dur > 0.5:
            durations[i] = dur
            print(f"  [CACHE] card_{i}.mp3 exists ({dur:.2f}s), reusing")
            continue

    print(f"  [TTS] card_{i} ({card['type']}): {text[:70]}...")
    r = subprocess.run([
        "edge-tts",
        "--voice", "zh-CN-liaoning-XiaobeiNeural",
        "--rate=+10%",
        "--text", text,
        "--write-media", mp3_path,
    ], capture_output=True, text=True, timeout=120)

    if r.returncode != 0:
        print(f"  [ERROR] edge-tts failed for card {i}: {r.stderr.strip()}")
        continue

    dur = get_audio_duration(mp3_path)
    durations[i] = dur
    print(f"  [OK] card_{i}.mp3 generated ({dur:.2f}s)")

if len(durations) < 6:
    print(f"\n[FATAL] Only {len(durations)} TTS files generated. Need 6.")
    sys.exit(1)

print(f"\n[STEP 3 DONE] TTS durations: { {k: f'{v:.2f}s' for k, v in durations.items()} }")

# ── Step 4: Build padded images and video segments ──
print("\n[STEP 4] Building video segments...")
segments = []
for card in cards_meta:
    i = card["index"]
    img_file = card["file"]
    img_path = os.path.join(images_dir, img_file)
    if not os.path.isfile(img_path):
        print(f"  [ERROR] Image not found: {img_path}")
        continue

    dur = durations.get(i, 3.0)
    padded_path = os.path.join(video_dir, f"pad_{i}.png")
    seg_path = os.path.join(video_dir, f"seg_{i}.mp4")
    mp3_path = os.path.join(video_dir, f"card_{i}.mp3")

    # Get original image dimensions
    r = subprocess.run([
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0", img_path
    ], capture_output=True, text=True)
    dims = r.stdout.strip().split(",")
    if len(dims) == 2:
        ow, oh = int(dims[0]), int(dims[1])
    else:
        ow, oh = 1080, 1440
    print(f"  [INFO] card_{i}: original {ow}×{oh}, TTS {dur:.2f}s")

    # Pad image to 1080×1920 with #1A1A2E background
    # Force_original_aspect_ratio=decrease keeps aspect ratio, pad fills rest
    pad_cmd = [
        "ffmpeg", "-y",
        "-i", img_path,
        "-vf", (
            "scale='min(1080,iw)':'min(1920,ih)':"
            "force_original_aspect_ratio=decrease,"
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=#1A1A2E"
        ),
        "-frames:v", "1",
        padded_path
    ]
    subprocess.run(pad_cmd, capture_output=True, text=True, timeout=30)

    # Build video segment: loop padded image for TTS duration
    dur_str = f"{dur:.3f}"
    seg_cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", padded_path,
        "-i", mp3_path,
        "-c:v", "libx264",
        "-t", dur_str,
        "-pix_fmt", "yuv420p",
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        seg_path
    ]
    r = subprocess.run(seg_cmd, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        print(f"  [ERROR] segment creation failed for card {i}: {r.stderr[-500:]}")
        continue

    segments.append(seg_path)
    print(f"  [OK] seg_{i}.mp4 ({dur:.2f}s) created")

if len(segments) < 6:
    print(f"[FATAL] Only {len(segments)} segments created, need 6")
    sys.exit(1)

# ── Step 5: Concat demuxer ──
print("\n[STEP 5] Concatenating segments...")
list_file = os.path.join(video_dir, "video_list.txt")
with open(list_file, "w") as f:
    for seg in segments:
        f.write(f"file '{seg}'\n")

output_path = os.path.join(video_dir, "video_note.mp4")

concat_cmd = [
    "ffmpeg", "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", list_file,
    "-c:v", "libx264",
    "-preset", "medium",
    "-crf", "23",
    "-c:a", "aac",
    "-b:a", "128k",
    "-movflags", "+faststart",
    output_path
]
r = subprocess.run(concat_cmd, capture_output=True, text=True, timeout=300)

if r.returncode != 0:
    print(f"[ERROR] Concat failed: {r.stderr[-500:]}")
    sys.exit(1)

# Get final video info
r = subprocess.run([
    "ffprobe", "-v", "error",
    "-show_entries", "format=duration,size",
    "-of", "csv=p=0", output_path
], capture_output=True, text=True)
finfo = r.stdout.strip().split(",")
final_duration = float(finfo[0]) if len(finfo) > 0 else 0
final_size = int(float(finfo[1])) if len(finfo) > 1 else 0

# Also get video resolution
r = subprocess.run([
    "ffprobe", "-v", "error",
    "-select_streams", "v:0",
    "-show_entries", "stream=width,height",
    "-of", "csv=p=0", output_path
], capture_output=True, text=True)
vdims = r.stdout.strip().split(",")
vw, vh = vdims if len(vdims) == 2 else ("1080", "1920")

# ── Step 6: Clean up temp files ──
print("\n[STEP 6] Cleaning up temporary files...")
cleaned = 0
for i in range(1, 7):
    for fname in [f"pad_{i}.png", f"seg_{i}.mp4"]:
        fp = os.path.join(video_dir, fname)
        if os.path.isfile(fp):
            os.remove(fp)
            cleaned += 1
# Also remove the list file
fp = os.path.join(video_dir, "video_list.txt")
if os.path.isfile(fp):
    os.remove(fp)
    cleaned += 1
print(f"  Removed {cleaned} temporary files.")
print(f"  Keeping: video_note.mp4 + card_*.mp3 (TTS audio)")

# ── Report ──
print("\n" + "=" * 64)
print("📹 情绪树洞 · 竖版视频笔记合成报告")
print("=" * 64)
print(f"  日期:         2026-07-19 (Day 13)")
print(f"  系列:         {series}")
print(f"  标题:         {title}")
print(f"  情绪标签:     {emotion_tag}")
print(f"  版本:         {'v2 — 深酒红→雾粉' if is_v2 else 'v1 — 浅绿→暖白'}")
print(f"  画布:         {vw}×{vh} (9:16 竖版)")
print(f"  配音:         zh-CN-liaoning-XiaobeiNeural (+10%快速, 东北话)")
print("-" * 64)
print(f"  视频时长:     {final_duration:.2f}s ({final_duration/60:.1f} 分钟)")
print(f"  文件大小:     {final_size/1024/1024:.1f} MB")
print(f"  输出路径:     {output_path}")
print("-" * 64)
print("  TTS 时长分布 (每张卡片独立配音):")
total = sum(durations.values())
for card in cards_meta:
    i = card["index"]
    dur = durations.get(i, 0)
    pct = dur / total * 100 if total > 0 else 0
    bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
    print(f"    Card {i} ({card['type']:8s}): {dur:6.2f}s  {bar}  {pct:3.0f}%")
print(f"    {'─' * 48}")
print(f"    总 TTS 配音: {total:.2f}s")
print("-" * 64)
print(f"  保留文件:")
print(f"    ✓ {output_path}")
print(f"    ✓ {video_dir}/card_1.mp3 ~ card_6.mp3")
print(f"  备注: 请手动上传至小红书 @静坐着呢的情绪树洞")
print("=" * 64)
