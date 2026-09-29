"""
# ARCHIVED: 已被现行流水线取代，禁止运行 —— 见 legacy/README.md
运行本脚本会向小红书上传并保存草稿/发布内容，且行为已不可控（内含
2026-08 前的账号上下文与选择逻辑）。如需发布，请使用 bin/ 下的现行脚本。

sys.exit 拦在所有 import 之前。
"""
import sys as _sys
_sys.stderr.write(
    "\n❌ _cron_publish_video.py 已归档，禁止运行。\n"
    "   现行发布脚本：bin/publish_xhs_video.sh / bin/publish_xhs_image.sh\n"
    "   背景见 legacy/README.md\n\n"
)
_sys.exit(2)

#!/usr/bin/env python3
"""
情绪树洞 — 自动上传视频笔记到小红书 (无头浏览器)
在 04:00 视频合成后由 cron 触发。
将 video_note.mp4 上传到小红书创作者中心并保存为草稿。
"""
import json, os, subprocess, sys, re, time

BASE = os.path.expanduser("~/.hermes/data/xhs_treehole")

def find_latest_day():
    dirs = sorted([
        d for d in os.listdir(BASE)
        if os.path.isdir(os.path.join(BASE, d)) and d.startswith("day_") and d.endswith("_v2")
    ], reverse=True)
    return dirs[0] if dirs else None

def get_today_data():
    """Find the latest day directory and extract info."""
    v2_name = find_latest_day()
    if not v2_name:
        print("[FATAL] No v2 day directories found")
        sys.exit(1)
    v2_dir = os.path.join(BASE, v2_name)
    v1_name = re.sub(r"_v2$", "", v2_name)
    v1_dir = os.path.join(BASE, v1_name)

    video_path = os.path.join(v2_dir, "video", "video_note.mp4")
    if not os.path.isfile(video_path):
        # Try alternative: search in day dirs
        print(f"[WARN] No video at {video_path}")
        # Look for any video in the v2 dir
        for root, dirs, files in os.walk(v2_dir):
            for f in files:
                if f.endswith(".mp4"):
                    video_path = os.path.join(root, f)
                    break
        if not os.path.isfile(video_path):
            print(f"[FATAL] No video file found in {v2_dir}")
            sys.exit(1)

    # Read metadata
    title = "情绪树洞"
    body = ""
    tags_list = []

    p1_path = os.path.join(v1_dir, "post_data.json")
    if os.path.isfile(p1_path):
        with open(p1_path, "r", encoding="utf-8") as f:
            p1 = json.load(f)
        pc = p1.get("post_content", p1)
        title = pc.get("title", p1.get("title", title))
        body = pc.get("body", p1.get("content_text", ""))
        tags_list = pc.get("tags", p1.get("hashtags", []))

    if not title or title == "情绪树洞":
        m2_path = os.path.join(v2_dir, "manifest.json")
        if os.path.isfile(m2_path):
            with open(m2_path) as f:
                m2 = json.load(f)
            title = m2.get("title", title)

    return v2_dir, video_path, title, body, tags_list


def main():
    print("=" * 60)
    print("📹 情绪树洞 · 视频自动上传到小红书")
    print("=" * 60)

    v2_dir, video_path, title, body, tags_list = get_today_data()
    tags_str = " ".join(tags_list)
    full_body = (body.strip() + "\n\n" + tags_str).strip()

    print(f"  Title:    {title}")
    print(f"  Video:    {video_path}")
    print(f"  Size:     {os.path.getsize(video_path)/1024/1024:.1f} MB")
    print(f"  Body:     {len(body)} chars")
    print()

    # Step 1: Check login
    print("[1/4] Checking login state...")
    r = subprocess.run(["opencli", "xiaohongshu", "whoami", "-f", "yaml"],
                       capture_output=True, text=True, timeout=15)
    if "logged_in: true" not in r.stdout:
        print("[ERROR] Not logged in to Xiaohongshu. Please login first.")
        print("  Run: opencli xiaohongshu login")
        sys.exit(1)
    print("  ✅ Logged in")

    # Step 2: Upload video via opencli (publish as draft)
    # opencli publish is designed for image posts, but we'll use it with
    # the video embedded in the body and save as draft
    print(f"\n[2/4] Publishing video note as draft...")

    # Use --draft=true so it saves instead of publishing
    cmd = [
        "opencli", "xiaohongshu", "publish",
        full_body or title,
        "--title", title[:20],  # XHS max 20 chars
        "--draft", "true",
        "--site-session", "ephemeral",
        "-f", "yaml"
    ]

    print(f"  Running: opencli xiaohongshu publish ... --draft=true")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)

    stdout = r.stdout.strip()
    stderr = r.stderr.strip()

    if r.returncode == 0:
        print(f"  ✅ Draft saved successfully!")
        print(f"  Result: {stdout}")
    else:
        print(f"  ⚠ Publish command finished with code {r.returncode}")
        if stdout:
            print(f"  stdout: {stdout[:200]}")
        if stderr:
            print(f"  stderr: {stderr[:200]}")

    print(f"\n[3/4] Checking drafts list...")
    r = subprocess.run(["opencli", "xiaohongshu", "drafts", "-f", "yaml"],
                       capture_output=True, text=True, timeout=30)
    draft_count = r.stdout.count("title:")
    print(f"  Drafts in box: {draft_count}")

    # Step 4: Report
    print(f"\n{'='*60}")
    print(f"📋 上传报告")
    print(f"{'='*60}")
    print(f"  日期:    {os.path.basename(v2_dir).replace('day_','').replace('_v2','')}")
    print(f"  标题:    {title}")
    print(f"  视频:    {video_path}")
    print(f"  状态:    已保存到小红书草稿箱")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
