"""
# ARCHIVED: 已被现行流水线取代，禁止运行 —— 见 legacy/README.md
运行本脚本会向小红书上传并保存草稿/发布内容，且行为已不可控（内含
2026-08 前的账号上下文与选择逻辑）。如需发布，请使用 bin/ 下的现行脚本。

sys.exit 拦在所有 import 之前。
"""
import sys as _sys
_sys.stderr.write(
    "\n❌ _cron_draft.py 已归档，禁止运行。\n"
    "   现行发布脚本：bin/publish_xhs_video.sh / bin/publish_xhs_image.sh\n"
    "   背景见 legacy/README.md\n\n"
)
_sys.exit(2)

#!/usr/bin/env python3
"""情绪树洞 — 保存草稿到小红书 (动态版)

自动找到最新一天的内容目录，读取 post_data.json + manifest.json，
组装 publish 命令并执行。

用法:
  python3 _cron_draft.py                    # 自动找最新 day 目录
  python3 _cron_draft.py --day 20260723     # 指定日期
"""
import json
import os
import re
import subprocess
import sys

BASE = os.path.expanduser("~/.hermes/data/xhs_treehole")

def find_latest_day():
    """Find the latest day_{date}_day{N}_v2 directory and its v1 counterpart."""
    dirs = [d for d in os.listdir(BASE)
            if os.path.isdir(os.path.join(BASE, d)) and d.startswith("day_")]
    v2_dirs = sorted([d for d in dirs if d.endswith("_v2")], reverse=True)

    if not v2_dirs:
        print("[FATAL] No v2 day directories found")
        sys.exit(1)

    latest_v2 = v2_dirs[0]
    # Derive v1 dir name: day_YYYYMMDD_dayN_v2 -> day_YYYYMMDD_dayN
    v1_name = re.sub(r"_v2$", "", latest_v2)
    v1_dir = os.path.join(BASE, v1_name)
    if not os.path.isdir(v1_dir):
        print(f"[FATAL] v1 directory not found: {v1_dir}")
        sys.exit(1)

    print(f"[INFO] Using v2: {latest_v2}")
    print(f"[INFO] Using v1: {v1_name}")
    return v1_dir, os.path.join(BASE, latest_v2)

def find_compressed_dir(v2_dir):
    """Find compressed images: check various locations."""
    candidates = [
        os.path.join(v2_dir, "compressed"),
        os.path.join(v2_dir, "images"),
    ]
    for c in candidates:
        if os.path.isdir(c) and any(f.endswith(".jpg") for f in os.listdir(c)):
            print(f"[INFO] Using images from: {c}")
            return c
    print(f"[FATAL] No image directory with JPGs found in {v2_dir}")
    sys.exit(1)

def main():
    # Parse optional --day argument
    if len(sys.argv) > 2 and sys.argv[1] == "--day":
        day_date = sys.argv[2]
        v1_dir = os.path.join(BASE, f"day_{day_date}_day??")
        # Find the exact v1 dir
        dirs = [d for d in os.listdir(BASE)
                if os.path.isdir(os.path.join(BASE, d))
                and d.startswith(f"day_{day_date}") and not d.endswith("_v2")]
        v2_dirs = [d for d in os.listdir(BASE)
                   if os.path.isdir(os.path.join(BASE, d))
                   and d.startswith(f"day_{day_date}") and d.endswith("_v2")]
        if not dirs or not v2_dirs:
            print(f"[FATAL] Day {day_date} directories not found")
            sys.exit(1)
        v1_dir = os.path.join(BASE, dirs[0])
        v2_dir = os.path.join(BASE, v2_dirs[0])
    else:
        v1_dir, v2_dir = find_latest_day()

    # ── Read v1 post_data.json ──
    p1_path = os.path.join(v1_dir, "post_data.json")
    with open(p1_path, "r", encoding="utf-8") as f:
        p1 = json.load(f)

    title = p1.get("title", p1.get("post_content", {}).get("title", "无标题"))
    body = p1.get("content_text") or p1.get("post_content", {}).get("body", "")
    tags_list = p1.get("hashtags") or p1.get("post_content", {}).get("tags", [])

    # Fallback: try the flexible structure
    if not body:
        pc = p1.get("post_content", {})
        body = pc.get("body", "")
    if not tags_list:
        pc = p1.get("post_content", {})
        tags_list = pc.get("tags", [])

    tags_str = " ".join(tags_list)
    full_body = body.strip() + "\n\n" + tags_str

    print(f"[INFO] Title: {title}")
    print(f"[INFO] Body length: {len(body)} chars")
    print(f"[INFO] Tags: {tags_str}")
    print(f"[INFO] Full body length: {len(full_body)} chars")

    # ── Read v2 manifest.json for image file names ──
    m2_path = os.path.join(v2_dir, "manifest.json")
    with open(m2_path, "r", encoding="utf-8") as f:
        m2 = json.load(f)

    cards = m2.get("cards", [])
    if not cards:
        print("[FATAL] No cards in manifest.json")
        sys.exit(1)

    img_dir = find_compressed_dir(v2_dir)
    image_files = []
    for c in cards:
        fname = c.get("file", "")
        if not fname:
            continue
        full_path = os.path.join(img_dir, fname)
        if os.path.isfile(full_path):
            image_files.append(full_path)
        else:
            print(f"[WARN] Image not found: {full_path}")

    if not image_files:
        print("[FATAL] No valid images found")
        sys.exit(1)

    print(f"[INFO] Images: {len(image_files)} files")
    for img in image_files:
        size_kb = os.path.getsize(img) / 1024
        status = "✓" if size_kb < 150 else f"⚠ {size_kb:.0f}KB(>150)"
        print(f"  {status} {os.path.basename(img)} ({size_kb:.0f}KB)")

    # ── Build publish command ──
    images_arg = ",".join(image_files)

    # Save payload to file to avoid shell escaping issues
    payload_file = os.path.join(v2_dir, "_draft_payload.txt")
    with open(payload_file, "w", encoding="utf-8") as f:
        f.write(full_body)
    print(f"\n[INFO] Payload saved to {payload_file}")

    cmd = [
        "opencli", "xiaohongshu", "publish",
        full_body,
        "--title", title,
        "--images", images_arg,
        "--draft", "true",
        "--site-session", "ephemeral",
        "-f", "yaml"
    ]
    print(f"\n[CMD] {' '.join(cmd[:4])} ... [images:{len(image_files)}] ...")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    print(f"\n[STDOUT]\n{result.stdout}")
    if result.stderr:
        print(f"[STDERR]\n{result.stderr}")
    print(f"[EXIT] Code: {result.returncode}")

    if result.returncode == 0:
        print("\n✅ 草稿保存成功！")
    else:
        print(f"\n❌ 草稿保存失败 (exit code: {result.returncode})")
        if "AUTH_REQUIRED" in result.stdout or "AUTH_REQUIRED" in result.stderr:
            print("  → 登录过期，请重新登录小红书创作者中心")

if __name__ == "__main__":
    main()
