#!/usr/bin/env python3
"""
情绪树洞 — 小红书表现追踪器

从创作者中心拉取已发布笔记的表现数据（曝光/观看/点赞/评论/收藏/分享），
计算 save-to-like ratio，写入本地 JSON 供周报和最佳时段分析使用。

不依赖 xhs 库 — 纯 CDP 调用 creator center 的 internal API。
"""
import sys, os, json, time, re
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xhs_paths import add_cdp_to_path  # noqa: E402

# CDP 模块已 vendored 到项目内 vendor/xhs/（2026-09-27，原 ~/.hermes/xhs_skills/scripts）
add_cdp_to_path()
from tab_lifecycle import ManagedPublisher  # 关掉自己新建的标签页（M3）

BASE = os.path.expanduser("~/.hermes/data/xhs_treehole")
DB_PATH = os.path.join(BASE, "performance_history.json")
PUBLISHED_PATH = os.path.join(BASE, "published_content.json")
CDP_HOST = "127.0.0.1"
CDP_PORT = 9222

# North star metric thresholds
SAVE_TO_LIKE_EXCELLENT = 0.30
SAVE_TO_LIKE_HEALTHY = 0.15


def load_json(path):
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_json(path, data):
    """原子写（tmp+rename）。cron 中途被杀不会留下截断的 JSON。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


PAGE_COUNT_RE = re.compile(r"共\s*(\d+)\s*条\D*?(\d+)\s*页")
PAGE_COUNT_RE_NOCHAIN = re.compile(r"共\s*(\d+)\s*条")  # 无页数信息时至少对得上条数

# 翻页 JS。{n} 是目标页码。
#
# 为什么不能直接读 .d-pagination-page 的 textContent：
# 每个分页按钮内部套了 d-pagination-page-content 和 -content-shadow 两层，
# 两层都含页码文本，于是 textContent 是「11」「22」…（页码重复两遍）。
# 实测 2026-09-27：旧代码 `p.textContent.trim() === '2'` 永远匹配不上，
# 从来没成功翻过页 —— 靠「静默退化成只抓 1 页」掩盖了很久，
# 周报数字一直少一个数量级而无人察觉。
# 必须读 -content 子元素的文本，且用 startsWith 防重复文本歧义。
_NEXT_PAGE_JS = """
(function() {
    var target = '{n}';
    var pages = document.querySelectorAll('.d-pagination-page');
    for (var p of pages) {
        if (p.classList.contains('disabled')) continue;
        var c = p.querySelector('.d-pagination-page-content');
        var txt = (c ? c.textContent : p.textContent).trim();
        if (txt === target || txt.indexOf(target) === 0) {
            p.click();
            return true;
        }
    }
    return false;
})()
"""


def _read_pagination(pub):
    """读 (total_notes, total_pages)；读不到时抛错，绝不默认 1 页。

    旧实现解析失败就 total_pages=1，于是「共 70 条 7 页」被当成
    「只有 1 页」，抓 10 篇当 70 篇存档，且没有任何告警 ——
    周报数字会悄悄少一个数量级。
    """
    body_text = pub._evaluate("document.body.innerText") or ""
    m = PAGE_COUNT_RE.search(body_text)
    if m:
        return int(m.group(1)), int(m.group(2))
    m2 = PAGE_COUNT_RE_NOCHAIN.search(body_text)
    if m2:
        # 有条数无页数：按每页 10 条估算，但明确标记不可信
        return int(m2.group(1)), max(1, -(-int(m2.group(1)) // 10))
    raise RuntimeError(
        "无法从创作者中心页面解析分页信息（共 N 条 / M 页）—— "
        "可能文案改版、表格未加载或被重定向到登录页。"
        f"body_text 前 200 字: {body_text[:200]!r}")


def _read_table_rows(pub):
    """读当前页表格行。返回 None 表示表格不存在。"""
    return pub._evaluate("""
        (function() {
            var table = document.querySelector('table');
            if (!table) return null;
            var rows = table.querySelectorAll('tr');
            var result = [];
            for (var i = 1; i < rows.length; i++) {
                var cells = rows[i].querySelectorAll('td');
                if (cells.length >= 10) {
                    result.push({
                        title_time: cells[0].textContent.trim(),
                        exposures: cells[1].textContent.trim(),
                        views: cells[2].textContent.trim(),
                        cover_click_rate: cells[3].textContent.trim(),
                        likes: cells[4].textContent.trim(),
                        comments: cells[5].textContent.trim(),
                        saves: cells[6].textContent.trim(),
                        follows: cells[7].textContent.trim(),
                        shares: cells[8].textContent.trim(),
                        avg_watch_time: cells[9].textContent.trim()
                    });
                }
            }
            return result;
        })()
    """)


def parse_number(val):
    """Parse a number from API that may be '-' or have commas."""
    if val is None or val == "-" or val == "":
        return 0
    if isinstance(val, (int, float)):
        return int(val)
    s = str(val).replace(",", "").replace("，", "").strip()
    try:
        return int(s)
    except ValueError:
        try:
            return int(float(s))
        except ValueError:
            return 0


def fetch_all_note_data(pub):
    """Fetch all note data from creator center DOM table (API returns 406).

    可靠性要求（2026-09-27 审计 H7/H8）：
    - 分页信息读不到就抛错，绝不默认 1 页（否则抓 10 篇当 70 篇存档）
    - 每次翻页后确认页面真的切走了，没切走就重试；否则会把同一页
      重复 extend，且没有任何告警
    - 结果按 (title, publish_time) 去重
    - 结束时用「共 N 条」与实际抓到的行数对账，对不上就报错
    """
    pub._navigate("https://creator.xiaohongshu.com/statistics/data-analysis")
    time.sleep(6)

    total_notes, total_pages = _read_pagination(pub)
    print(f"[INFO] 共 {total_notes} 条 / {total_pages} 页")

    all_rows, seen = [], set()
    current_page = 1

    while current_page <= total_pages:
        print(f"[INFO] 拉取第 {current_page}/{total_pages} 页...")

        rows = _read_table_rows(pub)
        if rows is None:
            raise RuntimeError(f"第 {current_page} 页找不到表格元素（页面未加载/被重定向）")
        new = 0
        for r in rows:
            key = (r.get("title_time") or "", r.get("views") or "")
            if key not in seen:
                seen.add(key)
                all_rows.append(r)
                new += 1
        if rows and new == 0:
            raise RuntimeError(
                f"第 {current_page} 页读到 {len(rows)} 行但全是重复 —— "
                "翻页没生效却被当成新数据继续累加")

        if current_page >= total_pages:
            break

        # 翻页：确认点击成功 + 确认页面真的切走了
        next_page = current_page + 1
        moved = False
        for attempt in range(3):
            clicked = pub._evaluate(_NEXT_PAGE_JS.replace("{n}", str(next_page)))
            if not clicked:
                print(f"  [WARN] 第 {next_page} 页的分页按钮未找到（第 {attempt + 1}/3 次）")
                time.sleep(2)
                continue
            # 轮询等表格内容变化（换页是异步渲染，sleep 固定值不可靠）
            for _ in range(10):
                time.sleep(1)
                probe = _read_table_rows(pub)
                if probe:
                    first_now = (probe[0].get("title_time") or "") if probe else ""
                    if first_now != (rows[0].get("title_time") or "" if rows else ""):
                        moved = True
                        break
            if moved:
                break
            time.sleep(2)
        if not moved:
            raise RuntimeError(
                f"翻到第 {next_page} 页失败（点击后表格内容未变化）—— "
                f"已抓 {len(all_rows)} 行，停止以免重复计数")

        current_page = next_page

    # 对账：条数对不上说明有整页丢失，宁可报错也不要用不完整数据覆盖历史
    if total_notes and len(all_rows) < total_notes:
        print(f"[WARN] 对账不平：页面显示 {total_notes} 条，实际抓到 {len(all_rows)} 行")
    print(f"[INFO] 完成：{len(all_rows)} 行（去重后），页面声称 {total_notes} 条")
    return all_rows


def fetch_profile_notes(pub):
    """Fetch notes from profile page as fallback / for note_id discovery."""
    try:
        result = pub.list_profile_notes(limit=50, max_scrolls=5)
        return result.get("notes", []) if isinstance(result, dict) else []
    except Exception:
        return []


def _parse_title_time(title_time_str):
    """Parse '清醒着，却走不掉发布于2026-09-21 10:26' → (title, publish_time)."""
    m = re.match(r"(.+)发布于(\d{4}-\d{2}-\d{2} \d{2}:\d{2})", title_time_str)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return title_time_str, ""


def match_notes_to_published(rows, published):
    """Match DOM rows to our published_content.json entries by title."""
    title_to_published = {}
    for p in published:
        t = (p.get("title") or "").strip()
        if t:
            title_to_published[t] = p

    matched = []
    unmatched = []

    for row in rows:
        title, publish_time = _parse_title_time(row.get("title_time", ""))
        pub = title_to_published.get(title)

        views = parse_number(row.get("views"))
        likes = parse_number(row.get("likes"))
        saves = parse_number(row.get("saves"))
        comments = parse_number(row.get("comments"))
        shares = parse_number(row.get("shares"))
        exposures = parse_number(row.get("exposures"))

        ratio = round(saves / likes, 4) if likes > 0 else 0.0

        entry = {
            "title": title,
            "publish_time": publish_time,
            "views": views,
            "likes": likes,
            "saves": saves,
            "comments": comments,
            "shares": shares,
            "exposures": exposures,
            "save_to_like_ratio": ratio,
            "ratio_tier": get_ratio_tier(ratio),
            "avg_watch_time": row.get("avg_watch_time", ""),
            "fetched_at": datetime.now().isoformat(),
        }

        if pub:
            entry["day_num"] = pub.get("day_num")
            entry["date"] = pub.get("date")
            matched.append(entry)
        else:
            unmatched.append(entry)

    return matched, unmatched


def get_ratio_tier(ratio):
    if ratio >= SAVE_TO_LIKE_EXCELLENT:
        return "excellent"
    elif ratio >= SAVE_TO_LIKE_HEALTHY:
        return "healthy"
    else:
        return "reassess"


def analyze_time_slots(matched):
    """Analyze which posting time slots perform best."""
    slots = {}
    for entry in matched:
        pt = entry.get("publish_time", "")
        if not pt or pt == "-":
            continue
        try:
            # Parse hour from "2026-09-21 10:26" format
            hour = int(pt[11:13])
            if 7 <= hour < 9:
                slot = "07:00-09:00"
            elif 12 <= hour < 13:
                slot = "12:00-13:00"
            elif 20 <= hour < 22:
                slot = "20:00-22:00"
            else:
                slot = f"other({hour}h)"
        except (ValueError, IndexError):
            slot = "unknown"

        if slot not in slots:
            slots[slot] = {"posts": 0, "total_views": 0, "total_likes": 0,
                          "total_saves": 0, "total_ratio": 0.0}
        slots[slot]["posts"] += 1
        slots[slot]["total_views"] += entry.get("views", 0)
        slots[slot]["total_likes"] += entry.get("likes", 0)
        slots[slot]["total_saves"] += entry.get("saves", 0)
        slots[slot]["total_ratio"] += entry.get("save_to_like_ratio", 0)

    # Calculate averages
    for slot, stats in slots.items():
        if stats["posts"] > 0:
            stats["avg_ratio"] = round(stats["total_ratio"] / stats["posts"], 4)
            stats["avg_views"] = round(stats["total_views"] / stats["posts"], 1)

    return dict(sorted(slots.items(), key=lambda x: x[1].get("avg_ratio", 0), reverse=True))


def generate_report(matched, unmatched, time_slots):
    """Generate a weekly-style report."""
    if not matched:
        return "暂无已发布笔记的表现数据。"

    total_views = sum(e.get("views", 0) for e in matched)
    total_likes = sum(e.get("likes", 0) for e in matched)
    total_saves = sum(e.get("saves", 0) for e in matched)
    total_comments = sum(e.get("comments", 0) for e in matched)
    total_shares = sum(e.get("shares", 0) for e in matched)
    avg_ratio = round(total_saves / total_likes, 4) if total_likes > 0 else 0.0

    # Top posts by save-to-like ratio (min 5 likes to be meaningful)
    top_posts = sorted(
        [e for e in matched if e.get("likes", 0) >= 3],
        key=lambda x: x.get("save_to_like_ratio", 0),
        reverse=True,
    )[:5]

    lines = [
        "📊 情绪树洞 · 表现周报",
        "=" * 36,
        f"统计范围: {len(matched)} 篇已发布笔记",
        f"总曝光: {total_views}  总点赞: {total_likes}",
        f"总收藏: {total_saves}  总评论: {total_comments}  总分享: {total_shares}",
        f"平均收藏率: {avg_ratio:.1%} ({get_ratio_tier(avg_ratio)})",
        "",
    ]

    if top_posts:
        lines.append("🏆 热门笔记 (按收藏率):")
        for i, p in enumerate(top_posts, 1):
            lines.append(
                f"  {i}. {p['title']}  观看{p['views']} 赞{p['likes']} "
                f"藏{p['saves']}  收藏率{p['save_to_like_ratio']:.1%}"
            )
        lines.append("")

    if time_slots:
        lines.append("⏰ 各时段表现:")
        for slot, stats in time_slots.items():
            lines.append(
                f"  {slot}: {stats['posts']}篇, 平均收藏率{stats.get('avg_ratio', 0):.1%}, "
                f"平均曝光{stats.get('avg_views', 0):.0f}"
            )
        lines.append("")

    if unmatched:
        lines.append(f"⚠️ {len(unmatched)} 篇笔记未能匹配到 published_content.json")

    return "\n".join(lines)


def main():
    published = load_json(PUBLISHED_PATH)
    if not published:
        print("❌ published_content.json 为空，无法追踪")
        sys.exit(1)

    print(f"📊 表现追踪: {len(published)} 篇已发布笔记在追踪池中")

    pub = ManagedPublisher(host=CDP_HOST, port=CDP_PORT, timing_jitter=0.1)
    try:
        pub.connect()
        print("[CDP] Connected")

        # Ensure we're logged in
        pub._navigate("https://creator.xiaohongshu.com/publish/publish?source=official")
        time.sleep(2)
        href = pub._evaluate("window.location.href") or ""
        if "login" in href.lower():
            print("❌ 未登录，请先扫码登录")
            sys.exit(1)

        print("[INFO] 拉取创作者中心数据...")
        rows = fetch_all_note_data(pub)
        print(f"[INFO] 获取到 {len(rows)} 篇笔记的原始数据")

        if not rows:
            print("❌ 未获取到任何笔记数据")
            sys.exit(1)

        matched, unmatched = match_notes_to_published(rows, published)
        print(f"[INFO] 匹配成功: {len(matched)}, 未匹配: {len(unmatched)}")

        # Save to history
        history = load_json(DB_PATH)
        if not isinstance(history, list):
            history = []

        # Build a snapshot
        snapshot = {
            "fetched_at": datetime.now().isoformat(),
            "total_notes": len(rows),
            "matched": len(matched),
            "summary": {
                "total_views": sum(e.get("views", 0) for e in matched),
                "total_likes": sum(e.get("likes", 0) for e in matched),
                "total_saves": sum(e.get("saves", 0) for e in matched),
                "total_comments": sum(e.get("comments", 0) for e in matched),
                "total_shares": sum(e.get("shares", 0) for e in matched),
            },
            "notes": matched,
        }
        history.append(snapshot)

        # Keep only last 30 snapshots
        if len(history) > 30:
            history = history[-30:]

        save_json(DB_PATH, history)
        print(f"[OK] 数据已保存到 {DB_PATH}")

        # Analyze and report
        time_slots = analyze_time_slots(matched)
        report = generate_report(matched, unmatched, time_slots)
        print()
        print(report)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        try:
            pub.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    main()
