#!/usr/bin/env python3
"""
情绪树洞 — 图文笔记 → 小红书草稿 (存草稿)
和 xhs_video_draft.py 使用同一个 Chrome Profile (XiaohongshuProfile)。
不依赖 LLM — 纯 CDP 操作，避开 03:00 的 weekly quota 429 风险。
"""
import sys, os, json, time, glob, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xhs_paths import add_cdp_to_path  # noqa: E402

# CDP 模块已 vendored 到项目内 vendor/xhs/（2026-09-27，原 ~/.hermes/xhs_skills/scripts）
add_cdp_to_path()
from publish_guard import require_publishable
from draft_shared import (
    save_confirmed_in, get_draft_count,
    find_latest_dir, navigate_publish_page,
)
from tab_lifecycle import ManagedPublisher  # 关掉自己新建的标签页（M3）
from xhs_config import CDP_HOST, CDP_PORT, CREATOR_HOST_FRAGMENT, PUBLISH_URL  # noqa: E402

BASE = os.path.expanduser("~/.hermes/data/xhs_treehole")


def find_latest_v1_dir(wait_seconds=30, attempts=3):
    """Latest day_* (non-_v2) dir. Thin wrapper around draft_shared.find_latest_dir."""
    import draft_shared
    # find_latest_dir 读的是 draft_shared.BASE；把本模块 BASE（含测试 monkeypatch）同步过去。
    draft_shared.BASE = BASE
    return find_latest_dir(is_v2=False, wait_seconds=wait_seconds, attempts=attempts)


def main():
    v1 = find_latest_v1_dir()
    if not v1:
        print("❌ No V1 directories found")
        sys.exit(1)

    # Today-guard: same as the 03:00 prompt's guard — don't re-draft yesterday
    # when 01:00 generation failed (~13% of days).
    v1_date = v1[4:12]
    if v1_date != time.strftime("%Y%m%d"):
        print(f"  ⏭ 最新素材是 {v1}（日期 {v1_date}），不是今天——跳过发布避免重复草稿")
        sys.exit(0)

    v1_path = os.path.join(BASE, v1)
    mf = os.path.join(v1_path, "manifest.json")
    pf = os.path.join(v1_path, "post_data.json")

    # V1 manifest 缺失但 post_data.json + 图片都在 → 兜底继续（01:00 LLM agent 写 manifest 前崩了）
    if not os.path.isfile(mf):
        images_check = sorted(glob.glob(os.path.join(v1_path, "images", "card*.jpg")))
        if os.path.isfile(pf) and len(images_check) >= 1:
            print(f"  ⚠ manifest.json 缺失，但 post_data.json + {len(images_check)} 张图片在 → 兜底继续")
        else:
            print(f"❌ Missing manifest or post_data in {v1}")
            sys.exit(1)
    if not os.path.isfile(pf):
        print(f"❌ Missing post_data in {v1}")
        sys.exit(1)

    d = json.load(open(pf, encoding="utf-8"))
    title = d.get("title", "").strip() or "情绪树洞"
    content_text = (d.get("content_text") or "").strip()
    hashtags = d.get("hashtags") or []
    if not hashtags:
        hashtags = ["情绪树洞", "每日分享", "情感共鸣"]
    content_body = content_text + "\n\n" + " ".join("#" + t for t in hashtags) if content_text else " ".join("#" + t for t in hashtags)

    images = sorted(glob.glob(os.path.join(v1_path, "images", "card*.jpg")))
    images = [f for f in images if os.path.isfile(f) and os.path.getsize(f) > 0]
    if len(images) < 1:
        print(f"❌ No card images in {v1}/images/")
        sys.exit(1)
    # 图片不全也要说出来：只传 2 张也能发出草稿，读者看到的是残缺笔记。
    # 不阻断（宁可少图也别当天没有草稿），但必须显式告警。
    if len(images) < 6:
        print(f"⚠ 只有 {len(images)}/6 张卡片图（{v1}）—— "
              f"01:00 渲染可能未完成，草稿会是残缺笔记")
    zero_byte = [f for f in glob.glob(os.path.join(v1_path, "images", "card*.jpg"))
                 if os.path.isfile(f) and os.path.getsize(f) == 0]
    if zero_byte:
        print(f"⚠ {len(zero_byte)} 张卡片图是 0 字节（渲染失败残留），已跳过："
              f"{[os.path.basename(f) for f in zero_byte]}")

    print(f"\U0001f4dd {title}")
    print(f"\U0001f5bc️  {len(images)} images")
    print(f"\U0001f4c4 {len(content_body)} chars")

    pub = ManagedPublisher(host=CDP_HOST, port=CDP_PORT, timing_jitter=0.25)
    pub.connect()

    print("\n── [1/4] Login + Navigate ──")
    navigate_publish_page(pub, PUBLISH_URL)
    pub._sleep(3, minimum_seconds=1.0)
    # 按路径段判登录态（与 xhs_video_draft 一致）：/auth、/passport、
    # 验证码页 URL 里没有 'login'，只查 'login' 会误判成已登录。
    href = (pub._evaluate("window.location.href") or "").lower()
    path = re.sub(r"^https?://[^/]+", "", href)
    segs = {s for s in re.split(r"[/?#&]", path) if s}
    auth_markers = {"login", "passport", "auth", "sso", "captcha", "verify",
                    "signin", "sign-in", "sign_in"}
    if segs & auth_markers or "login" in path:
        print(f"❌ Not logged in (redirected to {href[:80]})")
        print("   → 打开 Chrome 窗口手动扫码登录后重试")
        pub.disconnect()
        sys.exit(1)
    if CREATOR_HOST_FRAGMENT not in href:
        print(f"❌ Unexpected redirect: {href[:120]}")
        print("   → 可能被风控或跳转异常，暂不发布以免误操作")
        pub.disconnect()
        sys.exit(1)
    print("✅ Logged in (on publish page)")

    draft_before = get_draft_count(pub)
    print(f"\U0001f4e6 Draft box before: {'草稿箱(' + str(draft_before) + ')' if draft_before >= 0 else 'unknown'}")

    print("\n── [2/4] Upload images ──")
    # Use the publisher's image-tab + upload flow
    try:
        pub._click_image_text_tab()
        print("✅ Image tab activated")
    except Exception as e:
        print(f"  ⚠ _click_image_text_tab failed: {e} — trying direct upload")

    # Find file input and submit images
    from cdp_publish import SELECTORS
    nid = pub._query_node_id(SELECTORS.get("upload_input", "input[type='file']")) or \
          pub._query_node_id(SELECTORS.get("upload_input_alt", "input[accept*='image']"))
    if not nid:
        # Fallback: any file input
        nid = pub._query_node_id("input[type='file']")
    if not nid:
        print("❌ Cannot find file input"); pub.disconnect(); sys.exit(1)
    pub._send("DOM.setFileInputFiles", {"nodeId": nid, "files": images})
    print(f"✅ {len(images)} images submitted, waiting for upload...")

    # Wait for upload to settle (title input appears)
    for i in range(15):
        has_title = pub._evaluate("""
            (function() {
                var inputs = document.querySelectorAll('input[type="text"], input:not([type="file"])');
                for (var inp of inputs) {
                    var ph = (inp.placeholder||'').toLowerCase();
                    if (ph.includes('\\u6807\\u9898') || ph.includes('title')) return true;
                }
                return false;
            })()
        """)
        if has_title:
            print("✅ Upload complete, form ready")
            break
        time.sleep(2)
    else:
        print("  ⚠ Upload wait: title input not detected — continuing anyway")
        time.sleep(2)

    print("\n── [3/4] Fill form ──")
    pub._sleep(1, minimum_seconds=0.5)
    # 出口前的最后一道红线闸。02:15 质量门只覆盖当天那一次运行 ——
    # 它失败、被忽略、或事后单独重跑 03:00 时，超长标题会一路走到
    # _fill_title()，而平台是**静默截断**：本地检查照样 PASS，
    # 用户看到的却是标题被砍半的笔记。不要依赖上游一定跑。
    try:
        require_publishable(title, content_body)
        print("✅ 发布前红线自检通过")
    except ValueError as e:
        print(str(e))
        pub.disconnect()
        sys.exit(1)
    pub._fill_title(title)
    print("✅ Title filled")
    pub._fill_content(content_body)
    print(f"✅ Content filled ({len(content_body)} chars)")

    print("  ⏳ Waiting for auto-save...")
    time.sleep(5)

    print("\n── [4/4] Verify save ──")
    draft_after = get_draft_count(pub)
    page_snippet = pub._evaluate("document.body.innerText.substring(0, 500)") or ""
    # 只有页面上的保存指示才是硬证据。裸「草稿」永远匹配到侧边栏标签，恒真。
    # marker 列表与 video 侧共用（xhs_video_draft.SAVE_MARKERS）——
    # 曾经各写一份，日后必然分叉成「图文能验、验不了视频」。
    save_confirmed = save_confirmed_in(page_snippet)
    if draft_after > draft_before:
        print(f"✅ Draft saved! 草稿箱({draft_before}) → 草稿箱({draft_after})")
    elif draft_after == draft_before and draft_before >= 0:
        # 计数不变 ≠ 保存成功：可能是覆盖旧草稿，也可能是彻底失败。
        # 旧实现无条件打印 ✅，这是「显示成功实际没存」的来源。
        if save_confirmed:
            print(f"✅ Draft count unchanged ({draft_after}) 且页面有「已保存」"
                  f"—— 确认保存（覆盖了同一天的旧草稿）")
        else:
            print(f"❌ 草稿箱计数未变 ({draft_after}) 且页面无「已保存」指示"
                  f"—— 保存很可能失败，请人工确认")
    elif draft_after >= 0:
        print(f"⚠ Draft count: before={draft_before}, after={draft_after}（计数下降）")
        print("  ✅ 页面有「已保存」指示" if save_confirmed
              else "  ❌ 无保存指示，保存可能失败")
    else:
        print("  ⚠ 草稿箱计数不可读(-1)——改用页面保存指示确认")
        print("  ✅ Found save indicator on page (counter unreadable)" if save_confirmed
              else "  ❌ No save indicator found — save may have failed")
        print(f"  Page sample: {page_snippet[:200]}")
    if not save_confirmed and draft_after <= draft_before:
        print("  [NOTE] 未取得保存硬证据，草稿需人工在 XHS 草稿箱确认")

    pub.disconnect()
    print("\n✅ Done!")


if __name__ == "__main__":
    main()
