"""
# ARCHIVED: 已被现行流水线取代，禁止运行 —— 见 legacy/README.md
运行本脚本会向小红书上传并保存草稿/发布内容，且行为已不可控（内含
2026-08 前的账号上下文与选择逻辑）。如需发布，请使用 bin/ 下的现行脚本。

sys.exit 拦在所有 import 之前。
"""
import sys as _sys
_sys.stderr.write(
    "\n❌ render_xhs_cards_v1.py 已归档，禁止运行。\n"
    "   现行发布脚本：bin/publish_xhs_video.sh / bin/publish_xhs_image.sh\n"
    "   背景见 legacy/README.md\n\n"
)
_sys.exit(2)

#!/usr/bin/env python3
"""渲染 V1 图文卡片 HTML → JPG（CDP 截图），并更新 V1 manifest。"""
import sys, os, json, time, glob, base64

sys.path.insert(0, os.path.expanduser("~/.hermes/xhs_skills/scripts"))
from cdp_publish import XiaohongshuPublisher
from chrome_launcher import ensure_chrome


def main():
    v1_dir = sys.argv[1] if len(sys.argv) > 1 else None
    if not v1_dir:
        base = os.path.expanduser("~/.hermes/data/xhs_treehole")
        dirs = sorted([d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))
                       and d.startswith("day_") and not d.endswith("_v2")], reverse=True)
        v1_dir = os.path.join(base, dirs[0])
    images_dir = os.path.join(v1_dir, "images")
    manifest_path = os.path.join(v1_dir, "manifest.json")

    ensure_chrome()
    p = XiaohongshuPublisher()
    p.connect()
    p._navigate("about:blank")
    time.sleep(1)

    rendered = 0
    for i in range(1, 7):
        html_files = sorted(glob.glob(os.path.join(images_dir, f"card_{i}*.html")))
        if not html_files:
            print(f"  Card {i}: no HTML, skip")
            continue
        html_path = html_files[0]
        jpg_path = html_path.rsplit(".", 1)[0] + ".jpg"
        if os.path.isfile(jpg_path) and os.path.getmtime(jpg_path) > os.path.getmtime(html_path):
            print(f"  Card {i}: up-to-date")
            rendered += 1
            continue
        p._navigate("file://" + os.path.abspath(html_path))
        time.sleep(1.5)
        p._send("Emulation.setDeviceMetricsOverride", {
            "width": 1080, "height": 1440, "deviceScaleFactor": 2, "mobile": False,
        })
        time.sleep(0.3)
        result = p._send("Page.captureScreenshot", {"format": "jpeg", "quality": 92})
        with open(jpg_path, "wb") as f:
            f.write(base64.b64decode(result["data"]))
        sz = os.path.getsize(jpg_path)
        print(f"  Card {i}: {os.path.basename(jpg_path)} {sz//1024} KB")
        rendered += 1

    p.disconnect()

    # Update manifest: .html → .jpg
    if os.path.isfile(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        changed = False
        for card in manifest.get("cards", []):
            old = card.get("file", "")
            if old.endswith(".html"):
                card["file"] = old.rsplit(".", 1)[0] + ".jpg"
                changed = True
        if not manifest.get("images_rendered"):
            manifest["images_rendered"] = True
            changed = True
        if changed:
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            print("  ✅ V1 manifest updated")
    print(f"Done: {rendered} rendered")


if __name__ == "__main__":
    main()
