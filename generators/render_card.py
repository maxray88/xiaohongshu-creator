#!/usr/bin/env python3
"""
render_card.py — HTML → JPG card rendering using Playwright.

Usage:
    python3 render_card.py input.html output.jpg

Renders a 1080×1440 card at 2x device scale factor.
Google Fonts is aborted: cards always render with fallback fonts (fonts are
unreachable in CN, and a DNS/network outage would otherwise stall rendering),
mirroring the CDP render path in core/render_xhs_cards.py.
"""
import sys, os
from playwright.sync_api import sync_playwright

FONT_PATTERNS = [
    "**/fonts.googleapis.com/**",
    "**/fonts.gstatic.com/**",
]


def main():
    if len(sys.argv) < 3:
        print("Usage: render_card.py input.html output.jpg")
        sys.exit(1)

    html_path = os.path.abspath(sys.argv[1])
    jpg_path = os.path.abspath(sys.argv[2])

    if not os.path.isfile(html_path):
        print(f"❌ Input HTML not found: {html_path}")
        sys.exit(1)

    out_dir = os.path.dirname(jpg_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    file_url = "file://" + html_path

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": 1080, "height": 1440},
            device_scale_factor=2,
        )
        page.set_default_timeout(30000)
        for pattern in FONT_PATTERNS:
            page.route(pattern, lambda route: route.abort())
        # domcontentloaded + bounded settle instead of networkidle: the only
        # external fetches are the (now aborted) font requests, so this is both
        # faster on healthy days and immune to font-fetch stalls on outage days.
        page.goto(file_url, wait_until="domcontentloaded")
        page.wait_for_timeout(1200)
        # 必须 full_page=True。
        # full_page=False 只截 viewport（1440 CSS px）；卡片一旦超过这个高度，
        # 底部内容被**静默切掉**——实测 2040px 高的页面只出 1440px 的图，
        # 底部 600px 直接消失，没有任何报错。
        # 卡片模板目前正好 1440px，所以一直没暴露，但文案变长（01:00 是 LLM
        # 生成，长度不可控）就会踩中。
        #
        # 同时校验实际产出尺寸：page_body 高度 > viewport 时 full_page 才有意义，
        # 否则 Playwright 会退回 viewport 截图。下面的 post-check 兜住这点。
        page.screenshot(path=jpg_path, full_page=True, type="jpeg", quality=92)
        browser.close()

    size_kb = os.path.getsize(jpg_path) // 1024
    print(f"✅ {os.path.basename(jpg_path)} ({size_kb} KB)")

    # 裁切自检：图片物理高度必须 ≥ 页面内容高度。
    # 万一某天 Playwright 退回 viewport 截图，这里大声失败而不是
    # 交出一张底部缺失的图去发布。
    _check_not_clipped(html_path, jpg_path)


def _page_height(html_path):
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1440},
                        device_scale_factor=2)
        pg.goto("file://" + html_path, wait_until="domcontentloaded")
        pg.wait_for_timeout(300)
        h = pg.evaluate(
            "Math.max(document.body.scrollHeight,"
            " document.documentElement.scrollHeight)")
        dsf = pg.evaluate("window.devicePixelRatio") or 1
        b.close()
    return h, dsf


def _check_not_clipped(html_path, jpg_path):
    """图片高度不够页面内容高度 → 说明底部被裁掉了。"""
    try:
        css_h, dsf = _page_height(html_path)
        expected_px = int(css_h * dsf)
        from PIL import Image  # 可选依赖，缺失时跳过
        with Image.open(jpg_path) as im:
            actual_px = im.height
    except ImportError:
        return  # 无 PIL，跳过校验（sips 兜底见 main）
    except Exception as e:
        print(f"  (裁切自检跳过: {e})")
        return
    if actual_px + 10 < expected_px:
        print(f"❌ 裁切自检失败：图片 {actual_px}px < 页面内容 {expected_px}px"
              f"（底部 {expected_px - actual_px}px 被切掉）")
        sys.exit(1)
    print(f"  ✔ 未裁切（{actual_px}px ≥ 内容 {expected_px}px）")


if __name__ == "__main__":
    main()
