"""
# ARCHIVED: 已被现行流水线取代，禁止运行 —— 见 legacy/README.md
运行本脚本会向小红书上传并保存草稿/发布内容，且行为已不可控（内含
2026-08 前的账号上下文与选择逻辑）。如需发布，请使用 bin/ 下的现行脚本。

sys.exit 拦在所有 import 之前。
"""
import sys as _sys
_sys.stderr.write(
    "\n❌ xhs_draft_video.py 已归档，禁止运行。\n"
    "   现行发布脚本：bin/publish_xhs_video.sh / bin/publish_xhs_image.sh\n"
    "   背景见 legacy/README.md\n\n"
)
_sys.exit(2)

#!/usr/bin/env python3
"""
情绪树洞 — 视频笔记自动保存草稿到小红书
使用 XiaohongshuSkills (CDP) 替代 Playwright

流程：
  1. 启动 Chrome（真实 profile + 远程调试端口 9222）
  2. 连接 CDP，检查登录态
  3. 导航到创作者中心发布页
  4. 切换到「上传视频」tab
  5. 上传视频 + 等待处理
  6. 填写标题和正文
  7. 点击「存草稿」按钮
  8. 关闭 Chrome
"""

import json, os, sys, time, subprocess, signal

# ─── 配置 ───────────────────────────────────────────────────
BASE_DIR = os.path.expanduser("~/.hermes/data/xhs_treehole")
XHS_SKILLS = os.path.expanduser("~/.hermes/xhs_skills")
VENV_PYTHON = os.path.join(XHS_SKILLS, "venv", "bin", "python3")
CDP_PORT = 9222

sys.path.insert(0, os.path.join(XHS_SKILLS, "scripts"))
from cdp_publish import XiaohongshuPublisher, CDPError

# ─── 1. 找到最新视频 ─────────────────────────────────────────
def find_latest_video():
    dirs = sorted(
        [d for d in os.listdir(BASE_DIR)
         if os.path.isdir(os.path.join(BASE_DIR, d)) and d.endswith("_v2")],
        reverse=True
    )
    if not dirs:
        print("❌ No _v2 directories found")
        sys.exit(1)

    v2_name = dirs[0]
    v2_dir = os.path.join(BASE_DIR, v2_name)
    v1_name = v2_name.replace("_v2", "")
    v1_dir = os.path.join(BASE_DIR, v1_name)

    # Find the video file
    video_path = os.path.join(v2_dir, "video", "video_note.mp4")
    if not os.path.isfile(video_path):
        for r, dirs, fs in os.walk(v2_dir):
            for f in fs:
                if f.endswith(".mp4"):
                    video_path = os.path.join(r, f)
                    break

    if not os.path.isfile(video_path):
        print(f"❌ No MP4 found in {v2_dir}")
        sys.exit(1)

    # Read title
    title = "情绪树洞"
    p1 = os.path.join(v1_dir, "post_data.json")
    if os.path.isfile(p1):
        with open(p1) as f:
            d = json.load(f)
        pc = d.get("post_content", d)
        title = pc.get("title", d.get("title", title))

    day_label = v2_name.replace("day_", "").replace("_v2", "")
    print(f"  Date:  {day_label}")
    print(f"  Title: {title}")
    print(f"  Video: {video_path} ({os.path.getsize(video_path)/1024/1024:.1f} MB)")
    return title, video_path


# ─── 2. 启动 Chrome（真实 profile + CDP）─────────────────────
def start_chrome():
    """Start Chrome with remote debugging using the real profile."""
    # Kill any existing Chrome on our port
    subprocess.run(
        "pkill -f 'remote-debugging-port=9222' 2>/dev/null; sleep 1",
        shell=True, capture_output=True
    )

    chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    profile_dir = os.path.expanduser("~/Library/Application Support/Google/Chrome")

    proc = subprocess.Popen(
        [
            chrome_path,
            f"--remote-debugging-port={CDP_PORT}",
            "--no-first-run",
            "--no-default-browser-check",
            f"--user-data-dir={profile_dir}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait for CDP to be ready
    import urllib.request
    for i in range(15):
        time.sleep(1)
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json/version", timeout=3)
            print(f"  ✅ Chrome ready on port {CDP_PORT}")
            return proc
        except Exception:
            continue

    print("❌ Chrome failed to start")
    proc.kill()
    sys.exit(1)


# ─── 3. 保存草稿（点击存草稿按钮）────────────────────────────
def _click_save_draft(publisher):
    """Click the '存草稿' (Save Draft) button on the publish page."""
    print("\n[cdp_publish] Looking for '存草稿' button...")
    publisher._sleep(2, minimum_seconds=1.0)

    # Try finding the draft button by text content
    result = publisher._evaluate("""
        (function() {
            // Search all buttons and elements for 存草稿 text
            var all = document.querySelectorAll('button, span, div, a');
            for (var el of all) {
                var text = (el.textContent || '').trim();
                if (text === '存草稿' || text === '保存草稿') {
                    var rect = el.getBoundingClientRect();
                    return {
                        text: text,
                        x: rect.x + rect.width / 2,
                        y: rect.y + rect.height / 2,
                        tag: el.tagName,
                        visible: rect.width > 0 && rect.height > 0
                    };
                }
            }
            return null;
        })()
    """)

    if result and result.get("visible"):
        cx, cy = int(result["x"]), int(result["y"])
        print(f"  ✅ Found '{result['text']}' button at ({cx}, {cy})")
        publisher._click_mouse(cx, cy)
        publisher._sleep(3, minimum_seconds=1.0)
        print("  ✅ Save draft clicked!")
        return True

    # Fallback: try aria-label or data-* attributes
    print("  ⚠ Text search failed, trying attribute-based search...")
    result2 = publisher._evaluate("""
        (function() {
            var candidates = document.querySelectorAll(
                '[class*="draft"], [class*="save"], ' +
                'button:not([class*="publish"]):not([class*="submit"])'
            );
            var best = null;
            for (var el of candidates) {
                var text = (el.textContent || '').trim();
                if (/存草稿|保存草稿|草稿/.test(text)) {
                    var rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        return {
                            text: text,
                            x: rect.x + rect.width / 2,
                            y: rect.y + rect.height / 2,
                            tag: el.tagName
                        };
                    }
                }
            }
            return null;
        })()
    """)

    if result2:
        cx, cy = int(result2["x"]), int(result2["y"])
        print(f"  ✅ Found (attr) '{result2['text']}' at ({cx}, {cy})")
        publisher._click_mouse(cx, cy)
        publisher._sleep(3, minimum_seconds=1.0)
        return True

    print("  ❌ Could not find save draft button")
    print("  ℹ  The form content was filled. You can manually save as draft in the browser.")
    return False


# ─── Main ────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("📹 情绪树洞 · 视频笔记 → 小红书草稿 (CDP)")
    print("=" * 60)

    # 1. Find video
    print("\n[1/6] Locating latest video...")
    title, video_path = find_latest_video()

    # 2. Start Chrome
    print("\n[2/6] Starting Chrome with CDP...")
    chrome_proc = start_chrome()

    # 3. Connect & check login
    print("\n[3/6] Checking login status...")
    publisher = XiaohongshuPublisher(host="127.0.0.1", port=CDP_PORT, timing_jitter=0.25)
    try:
        publisher.connect()
        logged_in = publisher.check_login()
        if not logged_in:
            print("❌ Not logged in. Please login first via:")
            print(f"   cd {XHS_SKILLS}/scripts && {VENV_PYTHON} cdp_publish.py login")
            publisher.disconnect()
            chrome_proc.kill()
            sys.exit(1)
        print("  ✅ Logged in!")
    except CDPError as e:
        print(f"❌ CDP Error: {e}")
        chrome_proc.kill()
        sys.exit(1)

    # 4. Upload video & fill form
    print("\n[4/6] Uploading video and filling form...")
    try:
        publisher.publish_video(title=title, content="", video_path=video_path)
        print("  ✅ Video uploaded & form filled!")
    except CDPError as e:
        print(f"❌ Video upload/fill failed: {e}")
        publisher.disconnect()
        chrome_proc.kill()
        sys.exit(1)

    # 5. Click save draft
    print("\n[5/6] Saving as draft...")
    saved = _click_save_draft(publisher)
    if saved:
        print("  ✅ Saved as draft!")
    else:
        print("  ⚠ Form filled but draft button not found — form is ready for manual save.")

    # 6. Cleanup
    print("\n[6/6] Cleanup...")
    publisher.disconnect()
    chromium_proc = chrome_proc
    chrome_proc.terminate()
    time.sleep(1)
    try:
        chrome_proc.kill()
    except:
        pass
    # Also kill stray Chrome on that port
    subprocess.run("pkill -f 'remote-debugging-port=9222' 2>/dev/null", shell=True)

    print("\n✅ Done!")
    sys.exit(0)


if __name__ == "__main__":
    main()
