#!/usr/bin/env python3
"""
情绪树洞 — 图文/视频草稿共享函数

从 xhs_video_draft.py 和 xhs_image_draft.py 抽出的共用逻辑：
  SAVE_MARKERS / save_confirmed_in / get_draft_count / find_latest_dir / navigate_publish_page
"""
import os, sys, time

from theme_rotation import parse_day_dir
from cdp_publish import CDPError
from xhs_config import DATA_BASE

BASE = DATA_BASE

# 页面上的保存指示文案。两侧 draft 脚本共用一份，避免日后分叉。
#
# 「已保存」是 2026-09-27 审计时假设的文案，Reviewer 复核未找到实证
# （实际可能是「保存成功」「草稿已保存」「自动保存于 HH:MM」），故列出多种。
# 裸「草稿」绝不能算：侧边栏标签永远含它，恒真。
SAVE_MARKERS = ("已保存", "保存成功", "已存草稿", "草稿已保存",
                "自动保存", "已自动保存", "存为草稿")


def save_confirmed_in(snippet: str) -> bool:
    return bool(snippet) and any(k in snippet for k in SAVE_MARKERS)


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


def find_latest_dir(is_v2=True, wait_seconds=30, attempts=3):
    """Find the newest day_* directory (V1 or V2).

    Retries briefly when none exists yet — upstream generation/assemble may
    still be running when the cron fires.

    目录名必须严格匹配 day_YYYYMMDD_dayN[_v2]：旧实现只查 startswith("day_")
    + endswith("_v2")，畸形名 day_broken_v2 会通过筛选，而 reverse 字符串
    排序里 'b' 的 ASCII 值大于任何数字 —— 它会被当成「最新」，
    于是把一个来路不明的目录当今天的素材传上小红书。
    """
    for attempt in range(1, attempts + 1):
        try:
            dirs = sorted(
                [d for d in os.listdir(BASE)
                 if os.path.isdir(os.path.join(BASE, d))
                 and parse_day_dir(d) and (parse_day_dir(d)[2] == is_v2)],
                reverse=True,
            )
        except FileNotFoundError:
            return None
        if dirs:
            # 排序用 (date, day_num) 数值比较，字符串排序会把 day9 排在 day10 前
            return max(dirs, key=lambda d: (parse_day_dir(d)[0], parse_day_dir(d)[1]))
        if attempt < attempts:
            label = "_v2" if is_v2 else "V1"
            print(f"  ⚠ No {label} day directory yet (attempt {attempt}/{attempts}), "
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
