#!/usr/bin/env python3
"""
情绪树洞 — HTML 卡片 → JPG 截图渲染
通过 Chrome CDP 打开每个 HTML 文件并截图保存为 JPG。
自动更新 manifest.json 中的 card file 引用和 images_rendered 标记。
"""
import sys, os, json, time, glob, base64

# CDP 模块已 vendored 到项目内 vendor/xhs/（2026-09-27，原 ~/.hermes/xhs_skills/scripts）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xhs_paths import add_cdp_to_path  # noqa: E402

add_cdp_to_path()
from tab_lifecycle import ManagedPublisher  # 关掉自己新建的标签页（M3）
from chrome_launcher import ensure_chrome
from io_utils import atomic_write_json  # noqa: E402


def _try_comfyui(html_path: str, jpg_path: str) -> bool:
    """Try ComfyUI rendering via local API http://127.0.0.1:8188.
    Uses comfy_xhs_card workflow if available. Returns True on success.
    Stub: health-check only; full POST workflows/comfy_xhs_card.json not yet wired,
    so always falls back to CDP. Safe: returns False, CDP is primary.
    """
    try:
        import urllib.request, urllib.error
        # Health check
        urllib.request.urlopen("http://127.0.0.1:8188/system_stats", timeout=2).read()
        # For now ComfyUI HTML→image is background generation; if workflow not loaded,
        # fall back to CDP. This stub ensures the primary path is attempted before CDP.
        # Full integration: POST workflows/comfy_xhs_card.json with theme tokens + text,
        # poll /history, download result. If anything fails, return False for CDP fallback.
        return False
    except Exception as e:
        print(f"[DBG] ComfyUI probe failed: {e}", file=sys.stderr)
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: render_xhs_cards.py <v2_dir>")
        sys.exit(1)

    v2_dir = sys.argv[1]
    images_dir = os.path.join(v2_dir, "images")
    manifest_path = os.path.join(v2_dir, "manifest.json")

    if not os.path.isdir(images_dir):
        print(f"❌ images dir not found: {images_dir}")
        sys.exit(1)
    if not os.path.isfile(manifest_path):
        print(f"❌ manifest not found: {manifest_path}")
        sys.exit(1)

    p = None
    # Try ComfyUI first (local, no network)
    # If ComfyUI succeeds for all cards, CDP will be skipped entirely.
    # 下面用 `if p:` 判断走哪条渲染路径 —— 原先还有个 use_cdp=True 的
    # 变量，赋值后从未被读取（pyflakes 长期报警），容易让人误以为
    # CDP 与 ComfyUI 有两条独立的开关路径。删掉以免误导。
    comfy_ok = False  # placeholder — when comfy workflow is wired, set True on success

    if not comfy_ok:
        # Ensure Chrome is running with CDP (fallback / current primary)
        ensure_chrome()
        p = ManagedPublisher()
        p.connect()

    if p:
        # Block external font fetches: Google Fonts is unreachable in CN and a
        # DNS/network outage can stall the renderer on the fetch so that
        # Page.captureScreenshot stops answering (seen 2026-08-14, card 2).
        # Cards always render with fallback fonts, so this changes nothing
        # visually but removes the stall risk.
        p._send("Network.enable")
        p._send("Network.setBlockedURLs", {"urls": [
            "*fonts.googleapis.com*",
            "*fonts.gstatic.com*",
        ]})

        # Start from blank page
        p._navigate("about:blank")
        time.sleep(1)

    rendered = 0
    skipped = 0

    for i in range(1, 7):
        html_files = sorted(glob.glob(os.path.join(images_dir, f"card_v2_{i}_*.html")))
        if not html_files:
            print(f"  Card {i}: no HTML file found, skipping")
            skipped += 1
            continue

        # 同一卡位有多个 HTML 变体时取最新修改的，不是字典序首个
        html_path = max(html_files, key=os.path.getmtime)
        jpg_path = html_path.rsplit(".", 1)[0] + ".jpg"

        # Skip if JPG already exists and is newer than HTML
        if os.path.isfile(jpg_path) and os.path.getmtime(jpg_path) > os.path.getmtime(html_path):
            print(f"  Card {i}: {os.path.basename(jpg_path)} already up-to-date")
            skipped += 1  # 记账为 skipped：不是本次渲染出来的，虚报 rendered 会误导排查
            continue

        # Layered render: try ComfyUI first, then CDP fallback (p guaranteed when comfy not used)
        if _try_comfyui(html_path, jpg_path) and os.path.isfile(jpg_path):
            print(f"  Card {i}: {os.path.basename(jpg_path)} via ComfyUI {os.path.getsize(jpg_path)//1024} KB")
            rendered += 1
            continue

        if not p:
            print(f"  Card {i}: no renderer available (ComfyUI failed, CDP not connected), skipping")
            skipped += 1
            continue
        # CDP fallback (current primary — proven 2160×2880)
        # 单卡失败不许炸掉整个循环：旧实现里一次 STALL/KeyError 会让
        # 前面已渲染的 JPG 全部不回写 manifest（manifest 更新在循环之后），
        # 白渲染。逐卡 try/except，失败计入 skipped，最后按实际产物决定 manifest。
        try:
            file_url = "file://" + os.path.abspath(html_path)
            print(f"  Card {i}: {os.path.basename(html_path)} → JPG...", end=" ", flush=True)
            p._navigate(file_url)
            time.sleep(1.5)
            p._send("Emulation.setDeviceMetricsOverride", {
                "width": 1080,
                "height": 1440,
                "deviceScaleFactor": 2,
                "mobile": False,
            })
            time.sleep(0.3)
            result = p._send("Page.captureScreenshot", {"format": "jpeg", "quality": 92})
            data = result.get("data") if isinstance(result, dict) else None
            if not data:
                raise ValueError("captureScreenshot 未返回 data（页面可能未加载完）")
            blob = base64.b64decode(data)
            if not blob:
                raise ValueError("截图内容为空")
            with open(jpg_path, "wb") as f:
                f.write(blob)
            sz = os.path.getsize(jpg_path)
            print(f"{sz // 1024} KB")
            rendered += 1
        except Exception as e:
            # 失败的半截文件不能留下，否则下次 skip 判断会误认为已渲染
            if os.path.isfile(jpg_path):
                try:
                    os.remove(jpg_path)
                except OSError:
                    pass
            print(f"  Card {i}: 渲染失败 — {type(e).__name__}: {e}")
            skipped += 1

    if p:
        p.disconnect()

    # Update manifest.json —— 只反映「磁盘上真实存在」的 JPG。
    # 旧实现无条件把所有 .html 引用翻成 .jpg 且置 images_rendered=True，
    # 哪怕某张卡渲染失败/被跳过：下游 assemble 照 manifest 去读 .jpg，
    # 拿到的路径不存在，合成时才炸，失败点离病因很远。
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    def _jpg_for(card_file: str):
        """manifest 里记的 .html 对应的真实 JPG 路径（None = 磁盘上没有）。"""
        if not card_file:
            return None
        base = os.path.splitext(card_file)[0]
        p_jpg = os.path.join(images_dir, os.path.basename(base) + ".jpg")
        return p_jpg if (os.path.isfile(p_jpg) and os.path.getsize(p_jpg) > 0) else None

    needs_update = False
    missing = []
    for card in manifest.get("cards", []):
        old_file = card.get("file", "")
        new_file = os.path.basename(os.path.splitext(old_file)[0]) + ".jpg"
        if _jpg_for(new_file):
            if old_file != new_file:
                card["file"] = new_file
                needs_update = True
        else:
            missing.append(new_file)
            # JPG 不在盘上 → 引用必须保持 .html，不能翻成不存在的 .jpg
            if old_file != os.path.basename(os.path.splitext(old_file)[0]) + ".html":
                card["file"] = os.path.basename(os.path.splitext(old_file)[0]) + ".html"
                needs_update = True

    all_rendered = bool(manifest.get("cards")) and not missing
    if manifest.get("images_rendered") is not all_rendered:
        manifest["images_rendered"] = all_rendered
        needs_update = True

    if missing:
        print(f"  ⚠️ {len(missing)} 张 JPG 缺失，images_rendered 保持 false：{missing}")
        print("     → 02:15/06:00 会拦截；请重跑本步骤")

    if needs_update:
        manifest["renderer"] = "html-fallback"
        atomic_write_json(manifest_path, manifest)
        print(f"  ✅ manifest updated (images_rendered: {all_rendered})")
    else:
        print("  ✅ manifest already up-to-date")

    print(f"\nDone: {rendered} rendered, {skipped} skipped")
    return 0 if all_rendered else 1


if __name__ == "__main__":
    sys.exit(main())
