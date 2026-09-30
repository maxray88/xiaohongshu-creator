#!/usr/bin/env python3
"""
情绪树洞 — 视频笔记 → 小红书草稿 (存草稿)
一次性完成：连接 → 导航 → 上传 → 等待处理 → 填表单 → 验证存稿
"""
import sys, os, json, time, re, re as _re

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from xhs_paths import add_cdp_to_path  # noqa: E402

# CDP 模块已 vendored 到项目内 vendor/xhs/（2026-09-27，原 ~/.hermes/xhs_skills/scripts）
add_cdp_to_path()
from cdp_publish import CDPError, SELECTORS
from tab_lifecycle import ManagedPublisher  # 关掉自己新建的标签页（M3）
from theme_rotation import parse_day_dir
from publish_guard import require_publishable

BASE = os.path.expanduser("~/.hermes/data/xhs_treehole")

# 页面上的保存指示文案。两侧 draft 脚本共用一份，避免日后分叉。
#
# 「已保存」是 2026-09-27 审计时假设的文案，Reviewer 复核未找到实证
# （实际可能是「保存成功」「草稿已保存」「自动保存于 HH:MM」），故列出多种。
# 裸「草稿」绝不能算：侧边栏标签永远含它，恒真。
SAVE_MARKERS = ("已保存", "保存成功", "已存草稿", "草稿已保存",
                "自动保存", "已自动保存", "存为草稿")


def save_confirmed_in(snippet: str) -> bool:
    return bool(snippet) and any(k in snippet for k in SAVE_MARKERS)

# ─── Config ─────────────────────────────────────
CDP_HOST = "127.0.0.1"
CDP_PORT = 9222


def get_draft_count(pub) -> int:
    """Read the '草稿箱(N)' label — handles legacy text and new icon-badge UI (2026-08)."""
    try:
        text = pub._evaluate("""
            (function() {
                var els = document.querySelectorAll('span, div, a, p, li');
                for (var i=0;i<els.length;i++) {
                    var t=(els[i].textContent||'').trim();
                    var m=t.match(/草稿箱[\\s\\(（]*([0-9]+)[\\)）]?/);
                    if(m) return parseInt(m[1],10);
                    if(t==='草稿箱'||t.includes('草稿箱')){
                        var sib=els[i].nextElementSibling||(els[i].parentElement&&els[i].parentElement.querySelector('span.badge, .count, [class*=\"badge\"], [class*=\"count\"]'));
                        if(sib){
                            var nt=(sib.textContent||'').trim();
                            var nm=nt.match(/^\\s*([0-9]+)\\s*$/);
                            if(nm) return parseInt(nm[1],10);
                        }
                    }
                }
                var badges=document.querySelectorAll('[class*=\"badge\"],[class*=\"count\"],[class*=\"num\"],sup,.ant-badge-count');
                for(var j=0;j<badges.length;j++){
                    var bt=(badges[j].textContent||'').trim();
                    if(/^\\d+$/.test(bt)){
                        var c=badges[j].closest('li, a, div');
                        if(c&&c.textContent.includes('草稿箱')) return parseInt(bt,10);
                    }
                }
                if(document.body.innerText.includes('草稿箱')) return 0;
                return -1;
            })()
        """)
        if text is not None and text != -1:
            return int(text)
    except Exception as e:
        print(f"[DBG] get_draft_count failed: {e}", file=sys.stderr)
    return -1


def find_latest_v2_dir(wait_seconds=30, attempts=3):
    """Find the newest day_*_v2 directory.

    Retries briefly when none exists yet — upstream generation/assemble may
    still be running when the 05:00 cron fires.

    目录名必须严格匹配 day_YYYYMMDD_dayN_v2：旧实现只查 startswith("day_")
    + endswith("_v2")，畸形名 day_broken_v2 会通过筛选，而 reverse 字符串
    排序里 'b' 的 ASCII 值大于任何数字 —— 它会被当成「最新」，
    于是把一个来路不明的目录当今天的素材传上小红书。
    """
    for attempt in range(1, attempts + 1):
        dirs = sorted(
            [d for d in os.listdir(BASE)
             if os.path.isdir(os.path.join(BASE, d))
             and parse_day_dir(d) and parse_day_dir(d)[2]],  # [2] = is_v2
            reverse=True,
        )
        if dirs:
            # 排序用 (date, day_num) 数值比较，字符串排序会把 day9 排在 day10 前
            return max(dirs, key=lambda d: (parse_day_dir(d)[0], parse_day_dir(d)[1]))
        if attempt < attempts:
            print(f"  ⚠ No _v2 day directory yet (attempt {attempt}/{attempts}), "
                  f"retrying in {wait_seconds}s...")
            time.sleep(wait_seconds)
    return None


def navigate_publish_page(pub, url, attempts=3, wait=8):
    """Navigate the CDP tab to `url` with bounded retries.

    A _send timeout can leave the WebSocket wedged, so reconnect (opens a
    fresh tab) before each retry instead of reusing the dead socket.
    """
    for attempt in range(1, attempts + 1):
        try:
            pub._navigate(url)
            return
        except CDPError as e:
            if attempt == attempts:
                raise
            print(f"  ⚠ Navigate attempt {attempt}/{attempts} failed: {e}")
            print(f"    → reconnecting and retrying in {wait}s...")
            try:
                pub.disconnect()
            except Exception:
                pass
            time.sleep(wait)
            pub.connect()
    raise CDPError(f"Failed to navigate to {url} after {attempts} attempts")


def main():
    # Find latest video
    v2 = find_latest_v2_dir()
    if not v2:
        print("❌ No video directories found")
        sys.exit(1)
    v2_date = v2[4:12]
    if v2_date != time.strftime("%Y%m%d"):
        # 01:00/02:00 生成失败日没有今日 _v2 目录，最新会落到昨天——此时照常上传会把
        # 昨天的视频重复存成新草稿。跳过（06:00 watchdog 的「今天没有生成新内容」仍会告警）。
        print(f"  ⏭ 最新素材是 {v2}（日期 {v2_date}），不是今天——跳过发布避免重复草稿")
        sys.exit(0)
    vp = os.path.join(BASE, v2, "video", "video_note.mp4")
    if not os.path.isfile(vp):
        # Fallback: walk but ONLY accept video_note.mp4 (reject seg_*.mp4 fragments)
        for r, _, fs in os.walk(os.path.join(BASE, v2)):
            for f in fs:
                if f == "video_note.mp4":
                    vp = os.path.join(r, f)
                    break
            if os.path.isfile(vp):
                break
    if not os.path.isfile(vp):
        # 04:00 合成可能仍在跑（TTS 6 卡 + concat 常耗时 1-4 分钟，DNS 重试时更久）。
        # 借鉴 xhs-content-pipeline 的 scheduled-gate 思想：按计划等视频就绪，
        # 而不是按 cron 开火时刻赌文件存在。有界等待，超时才大声失败。
        wait_total = int(os.environ.get("XHS_VIDEO_WAIT_SEC", "600"))
        poll = 30
        waited = 0
        while waited < wait_total:
            print(f"  ⏳ video_note.mp4 未就绪，已等 {waited}s（上限 {wait_total}s），"
                  f"{poll}s 后重试…")
            time.sleep(min(poll, wait_total - waited))
            waited += poll
            if os.path.isfile(vp):
                print(f"  ✅ 视频就绪（等待 {waited}s）")
                break
    if not os.path.isfile(vp):
        print(f"❌ No video_note.mp4 found in {v2} after {wait_total}s wait")
        sys.exit(1)

    # Read title from manifest
    title = "情绪树洞"
    m2 = os.path.join(BASE, v2, "manifest.json")
    if os.path.isfile(m2):
        d = json.load(open(m2))
        title = d.get("title", title)
    else:
        p1 = os.path.join(BASE, v2.replace("_v2", ""), "post_data.json")
        if os.path.isfile(p1):
            d = json.load(open(p1))
            title = d.get("title", title)

    print(f"📹 {os.path.basename(vp)} ({os.path.getsize(vp)/1024/1024:.1f} MB)")
    print(f"📝 {title}")

    pub = ManagedPublisher(host=CDP_HOST, port=CDP_PORT, timing_jitter=0.25)
    pub.connect()

    # Phase 1: Navigate to publish page (login check)
    print("\n── [1/5] Login + Navigate ──")
    navigate_publish_page(pub, "https://creator.xiaohongshu.com/publish/publish?source=official")
    pub._sleep(3, minimum_seconds=1.0)
    # 登录态判定不能只看 'login'：平台跳 /auth、/passport、验证码或风控页时
    # URL 里没有 'login'，会被误判成「已登录」然后在上传步骤莫名其妙失败。
    # 按路径段匹配，避免 'auth' 误伤 'author' 这类正常子串。
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
    if "creator.xiaohongshu.com" not in href:
        print(f"❌ Unexpected redirect: {href[:120]}")
        print("   → 可能被风控或跳转异常，暂不发布以免误操作")
        pub.disconnect()
        sys.exit(1)
    print("✅ Logged in (on publish page)")

    # Read draft count before upload
    draft_before = get_draft_count(pub)
    print(f"📦 Draft box before: {'草稿箱(' + str(draft_before) + ')' if draft_before >= 0 else 'unknown'}")

    # Phase 2: Click video tab
    print("\n── [2/5] Video tab ──")
    pub._click_video_tab()
    print("✅ Video tab activated")

    # Phase 3: Upload video
    print("\n── [3/5] Upload video ──")
    nid = pub._query_node_id(SELECTORS["upload_input"]) or pub._query_node_id(SELECTORS["upload_input_alt"])
    if not nid:
        print("❌ Cannot find file input"); pub.disconnect(); sys.exit(1)
    pub._send("DOM.setFileInputFiles", {"nodeId": nid, "files": [vp]})
    print("✅ File submitted, waiting for upload + processing...")

    # Phase 4: Wait for video processing (using cdp_publish's reliable method)
    print("\n── [4/5] Wait for processing ──")
    # 云端转码没完成就往下走是**有意**的：小红书草稿可以先存下，
    # 用户稍后手动发布时云端会继续处理。旧实现捕获 CDPError 后
    # 直接丢掉，害得后面的保存验证以为一切正常 —— 视频可能压根没
    # 传完，存进草稿箱的是个半成品，而日志显示「✅ Draft saved」。
    # 保留这个状态，保存结论里要如实反映。
    processing_ok = True
    try:
        pub._wait_video_processing()
        print("✅ Video processed")
    except CDPError as e:
        processing_ok = False
        print(f"⚠ Processing wait issue: {e}")
        print("  → Continuing anyway (草稿可先存下，云端会继续转码)，"
              "但这条草稿在处理完成前不保证可发布")

    # Phase 5: Fill form + verify save
    print("\n── [5/5] Fill form & save ──")
    pub._sleep(1, minimum_seconds=0.5)

    # Fill title
    # 出口前的最后一道红线闸。02:15 质量门只覆盖当天那一次运行 ——
    # 它失败、被忽略、或事后单独重跑 05:00 时，超长标题会一路走到
    # _fill_title()，而平台是**静默截断**：本地检查照样 PASS，
    # 用户看到的却是标题被砍半的笔记。不要依赖上游一定跑。
    try:
        require_publishable(title)
        print("✅ 发布前红线自检通过")
    except ValueError as e:
        print(str(e))
        pub.disconnect()
        sys.exit(1)
    pub._fill_title(title)
    print("✅ Title filled")

    # Fill content (day-specific hashtags from V1 post_data → searchable desc)
    hashtags = []
    p1 = os.path.join(BASE, v2.replace("_v2", ""), "post_data.json")
    if os.path.isfile(p1):
        try:
            hashtags = json.load(open(p1)).get("hashtags") or []
        except Exception:
            pass
    if not hashtags:
        hashtags = ["情绪树洞", "每日分享", "情感共鸣"]
    # XHS only linkifies/search-indexes #-delimited tokens — bare space-joined
    # words render as plain caption text and never become clickable tags.
    content_body = " ".join("#" + t for t in hashtags)
    pub._fill_content(content_body)
    print(f"✅ Content filled ({len(content_body)} chars): {content_body[:60]}...")

    # Wait for auto-save to complete
    print("  ⏳ Waiting for auto-save...")
    time.sleep(5)

    # Verify save by checking draft count
    draft_after = get_draft_count(pub)
    page_snippet = pub._evaluate("document.body.innerText.substring(0, 500)") or ""
    # 只有页面上的保存指示才是保存成功的硬证据。
    #
    # 「已保存」是 2026-09-27 审计时假设的文案，Reviewer 复核时未能找到
    # 实证（可能实际是「保存成功」「草稿已保存」「自动保存于 HH:MM」）。
    # 方向是 fail-safe（拿不到证据只打 NOTE、不改 exit code），
    # 但仍尽量覆盖多种已知形态，避免每次都拿不到证据。
    # 裸「草稿」绝不能算：侧边栏标签永远含它，恒真。
    SAVE_MARKERS = ("已保存", "保存成功", "已存草稿", "草稿已保存",
                    "自动保存", "已自动保存", "存为草稿")
    save_confirmed = any(k in page_snippet for k in SAVE_MARKERS)

    if draft_after > draft_before:
        print(f"✅ Draft saved! 草稿箱({draft_before}) → 草稿箱({draft_after})")
        if not processing_ok:
            print("  ⚠ 但云端转码在等待期内未完成 —— 草稿已存下，"
                  "发布前请确认视频能正常播放")
    elif draft_after == draft_before and draft_before >= 0:
        # 计数没变有两种可能：新草稿覆盖了同一天的旧草稿（正常）
        # 或保存彻底失败（计数同样不变）。旧实现无条件打印 ✅
        # —— 这正是「验证 inconclusive 却显示成功」的来源。
        if save_confirmed:
            print(f"✅ Draft count unchanged ({draft_after}) 且页面有「已保存」"
                  f"—— 确认保存（覆盖了同一天的旧草稿）")
        else:
            print(f"❌ 草稿箱计数未变 ({draft_after}) 且页面无「已保存」指示"
                  f"—— 保存很可能失败，请人工确认")
    elif draft_after >= 0:
        print(f"⚠ Draft count: before={draft_before}, after={draft_after}（计数下降）")
        if save_confirmed:
            print("  ✅ 但页面有「已保存」指示，以页面为准")
        else:
            print("  ❌ 无保存指示，保存可能失败")
    else:
        print("  ⚠ 草稿箱计数不可读(-1)——改用页面保存指示确认")
        if save_confirmed:
            print("  ✅ Found save indicator on page (counter unreadable)")
        else:
            print("  ❌ No save indicator found — save may have failed")
        print(f"  Page sample: {page_snippet[:200]}")

    if not save_confirmed and draft_after <= draft_before:
        # 记录到日志供 06:00/人工追溯，但**不改变退出码**：
        # 草稿保存在云端，本地无法可靠判定，误报 exit 1 会造成新一轮告警。
        print("  [NOTE] 未取得保存硬证据，草稿需人工在 XHS 草稿箱确认")

    pub.disconnect()

    # ── Track published content ──
    print("\n── [6/6] Track published content ──")
    tracker_path = os.path.join(BASE, "published_content.json")
    try:
        if os.path.isfile(tracker_path):
            tracker = json.load(open(tracker_path))
        else:
            tracker = []
        m = _re.search(r'day_(\d+)_day(\d+)_v2', v2)
        entry = {
            "day_num": int(m.group(2)) if m else 0,
            "title": title,
            "date": str(m.group(1)) if m else "",
        }
        if not any(e.get("title") == title for e in tracker):
            tracker.append(entry)
            # 原子写：published_content.json 是 01:00 prompt 的查重依据 +
            # 06:00 自检的合规项，写坏它两处一起炸
            tmp = f"{tracker_path}.tmp.{os.getpid()}"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(tracker, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, tracker_path)
            print(f"✅ Added to published tracker: {title}")
        else:
            print(f"⏭ Already tracked: {title}")
    except Exception as e:
        # 草稿此时已经存进云端草稿箱了。若这里 exit 1，cron 会报 error，
        # 而「重跑」就会再传一次 —— 草稿箱里多一条重复草稿。
        # 账本没写进去只影响明天的查重，不影响今天已经完成的发布，
        # 所以保持 exit 0 + 显式行动提示。
        # 旧实现只打印一行警告，看不出「草稿已存好」这个关键事实。
        print(f"❌ Tracker update failed: {e}")
        print(f"   [ACTION-REQUIRED] 草稿可能已成功存入草稿箱，但本地查重账本")
        print(f"   published_content.json 未更新。**请勿重跑 05:00**"
              f"（会再传一条重复草稿）；直接人工补记 {title!r} 即可。")

    print("\n✅ Done!")


if __name__ == "__main__":
    main()
