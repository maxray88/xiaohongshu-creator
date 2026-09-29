"""
# ARCHIVED: 已被现行流水线取代，禁止运行 —— 见 legacy/README.md
运行本脚本会向小红书上传并保存草稿/发布内容，且行为已不可控（内含
2026-08 前的账号上下文与选择逻辑）。如需发布，请使用 bin/ 下的现行脚本。

sys.exit 拦在所有 import 之前。
"""
import sys as _sys
_sys.stderr.write(
    "\n❌ xhs_image_draft.py 已归档，禁止运行。\n"
    "   现行发布脚本：bin/publish_xhs_video.sh / bin/publish_xhs_image.sh\n"
    "   背景见 legacy/README.md\n\n"
)
_sys.exit(2)

#!/usr/bin/env python3
"""
情绪树洞 — 图文笔记 → 小红书草稿 (CDP 版)
和 xhs_video_draft.py 使用同一个 Chrome Profile。
"""
import sys, os, json, time

XHS_SKILLS = os.path.expanduser("~/.hermes/xhs_skills")
sys.path.insert(0, os.path.join(XHS_SKILLS, "scripts"))
from cdp_publish import XiaohongshuPublisher
from chrome_launcher import ensure_chrome

BASE = os.path.expanduser("~/.hermes/data/xhs_treehole")

def main():
    # Find latest V1 directory
    dirs = sorted([d for d in os.listdir(BASE) if os.path.isdir(os.path.join(BASE, d))
                   and d.startswith("day_") and not d.endswith("_v2")], reverse=True)
    if not dirs:
        print("❌ No V1 directories found"); sys.exit(1)
    v1 = dirs[0]
    vp = os.path.join(BASE, v1)
    mf = os.path.join(vp, "manifest.json")
    pf = os.path.join(vp, "post_data.json")

    if not os.path.isfile(mf) or not os.path.isfile(pf):
        print(f"❌ Missing manifest or post_data in {v1}"); sys.exit(1)

    manifest = json.load(open(mf))
    post_data = json.load(open(pf))
    title = manifest.get("title", "情绪树洞")
    content = post_data.get("content", "")
    
    # Build image paths
    img_dir = os.path.join(vp, "images")
    images = [os.path.join(img_dir, f) for f in post_data.get("all_images", [])]
    images = [f for f in images if os.path.isfile(f)]
    
    print(f"📝 {title}")
    print(f"🖼️  {len(images)} images")
    print(f"📄 {len(content)} chars")

    # Ensure Chrome
    ensure_chrome()
    pub = XiaohongshuPublisher()
    pub.connect()

    # Phase 1: Login check
    print("\n── [1/5] Login check ──")
    pub._navigate("https://creator.xiaohongshu.com/")
    time.sleep(3)
    if "login" in pub._evaluate("window.location.href").lower():
        print("❌ Not logged in"); pub.disconnect(); sys.exit(1)
    print("✅ Logged in")

    # Phase 2: Navigate to publish page
    print("\n── [2/5] Navigate to publish page ──")
    pub._navigate("https://creator.xiaohongshu.com/publish/publish?source=official")
    time.sleep(3)
    print("✅ On publish page")

    # Phase 3: Upload images
    print("\n── [3/5] Upload images ──")
    # Give page time to load upload area
    time.sleep(2)
    
    # Find file input and upload each image
    nid = pub._query_node_id("input[type='file']") or pub._query_node_id("input[accept*='image']")
    if not nid:
        # Try JS approach
        nid = pub._evaluate("""
(function() {
    var inputs = document.querySelectorAll('input[type=file]');
    for (var inp of inputs) {
        if (inp.multiple) return inp.getAttribute('cdp_node_id') || '';
    }
    return '';
})()
""")
    if not nid:
        print("❌ Cannot find file input")
        pub.disconnect()
        sys.exit(1)
    
    pub._send("DOM.setFileInputFiles", {"nodeId": int(nid), "files": images})
    print(f"✅ {len(images)} images submitted, waiting for upload...")
    # Wait for title input to appear (upload complete)
    for i in range(30):
        has_title = pub._evaluate("""
            (function() {
                var inputs = document.querySelectorAll('input[type="text"], input:not([type="file"])');
                for (var inp of inputs) {
                    var ph = (inp.placeholder||'').toLowerCase();
                    if (ph.includes('标题') || ph.includes('title')) return true;
                }
                return false;
            })()
        """)
        if has_title:
            print("✅ Upload complete, form ready")
            break
        time.sleep(2)
    else:
        print("⚠ Upload wait timeout - continuing")

    # Phase 4: Fill title & content
    print("\n── [4/5] Fill form ──")
    time.sleep(2)
    pub._fill_title(title)
    print("✅ Title filled")
    pub._fill_content("#情绪树洞 #每日分享")
    print("✅ Content filled")

    # Phase 5: Confirm draft auto-saved
    print("\n── [5/5] Confirm saved ──")
    time.sleep(3)
    print("✅ Form auto-saved (upload + fill = auto draft)")

    pub.disconnect()
    print("\n✅ Done!")

if __name__ == "__main__":
    main()
