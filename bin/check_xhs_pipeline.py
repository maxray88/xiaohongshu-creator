#!/usr/bin/env python3
"""XHS 情绪树洞流水线完整性自检。

配合 hermes no_agent cron 使用：
  - 全部通过 → 无 stdout、exit 0 → 静默（不投递）
  - 任何缺失/失败 → 输出 ❌ 报告、exit 1 → 作为告警投递到 feishu

验证对象：最新一天素材目录的完整性 + 各脚本 cron 步骤今天的运行状态。
图文草稿(03:00)存于 XHS 草稿箱，本地无法验证，仅作提示。
"""

import glob
import json
import os
import re
import sys
import urllib.request
import urllib.error
from collections import Counter
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core"))
from theme_rotation import manifest_color_scheme as _manifest_cs
from theme_rotation import parse_day_dir, recent_schemes, validate_rotation
from manifest_title import manifest_title, plain_title, plain_series
from content_checks import has_emoji as _has_emoji
from content_checks import load_json_tolerant
from xhs_config import TITLE_MAX

BASE = os.path.join(os.path.expanduser("~"), ".hermes", "data", "xhs_treehole")
JOBS_JSON = os.path.join(os.path.expanduser("~"), ".hermes", "cron", "jobs.json")

# 脚本 cron 步骤：按 jobs.json 的 script 字段匹配，校验“今天运行过且状态 ok”
SCRIPT_STEPS = [
    ("内容质量门 (02:15)", "check_content_quality.py"),
    ("V2 卡片渲染 (02:30)", "render_xhs_cards.sh"),
    ("登录健康探针 (02:45)", "check_xhs_login.py"),
    ("视频合成 (04:00)", "assemble_xhs_treehole.sh"),
    ("视频发布草稿 (05:00)", "publish_xhs_video.sh"),
    ("清理旧素材 (05:30)", "cleanup_xhs_treehole.py"),
]

# 每一步的「可验证产物」。用于 06:00 判定 last_status=error 是否为陈旧状态：
# 产物齐全即说明该步骤实质成功过（哪怕当时跑的是错误分支、之后被重跑修复），
# 此时报 error 是误报。只有产物可验的步骤才享受这个降级。
#
# 关键：判据必须是「这一步自己产出的东西」，不能借用上一步的产物 ——
# 否则降级恒成立、把该步骤的检查架空（Reviewer 2026-09-27 抓出）。
#   - publish_xhs_video.sh 刻意不在表内：它的产物是**云端草稿**，
#     本地无从验证；mp4 是 assemble 的产物，publish 失败时照样在盘上，
#     用它当判据会让 publish 的 error 永远被降成 note。
#   - 登录探针、清理同理，没有本地可验产物。
STEP_ARTIFACTS = {
    # 02:15 质量门：不产出文件，判据是内容合规 + V2 就绪，
    # 已由本脚本的 _content_compliance 与 V2 检查覆盖。
    "check_content_quality.py": "content_compliance",
    # 02:30 渲染：V2 六卡 JPG（这一步自己的产物）
    "render_xhs_cards.sh": "v2_jpgs",
    # 04:00 合成：video_note.mp4（这一步自己的产物）
    "assemble_xhs_treehole.sh": "video_mp4",
}


def _artifact_ok(script: str, v1: str, v2: str) -> bool:
    """该步骤的产物是否齐全可信。未知步骤 → False（仍信 last_status）。"""
    kind = STEP_ARTIFACTS.get(script)
    if kind == "v2_jpgs":
        imgs = os.path.join(v2, "images")
        if not os.path.isdir(imgs):
            return False
        # 六个卡位各要有一张图，不只数总数（6 张重复也应判不合格）
        for slot in ("cover", "scene", "insight", "method", "gentle", "cta"):
            if not glob.glob(os.path.join(imgs, f"card*{slot}*.jpg")):
                return False
        return True
    if kind == "video_mp4":
        return os.path.isfile(os.path.join(v2, "video", "video_note.mp4"))
    if kind == "content_compliance":
        return os.path.isfile(os.path.join(v1, "post_data.json"))
    return False


def _latest_day() -> str | None:
    """最新的 day_YYYYMMDD_dayN 目录（排除 _v2）。

    旧实现 key 只取 d[4:12]：同一天重生成出现两个 dayN 时 max() 返回的
    是 listdir 先遇到的那个（非确定）；畸形名 day_broken 切出 'broke'，
    ASCII 'b' > '2' 会打败所有正常日期被当成最新。
    """
    try:
        names = os.listdir(BASE)
    except FileNotFoundError:
        return None
    parsed = []
    for name in names:
        p = parse_day_dir(name)
        if p and not p[2]:  # 排除 _v2
            parsed.append((p[0], p[1]))
    if not parsed:
        return None
    date_c, day_num = max(parsed)  # 日期优先，同日再比 day_num（数值比较）
    # 找回目录名：同一 (date, day_num) 理论上唯一
    for name in names:
        p = parse_day_dir(name)
        if p and not p[2] and (p[0], p[1]) == (date_c, day_num):
            return name
    return None


def _ran_today(last_run_at, today: str):
    """True/False = 今天跑没跑；None = 时间戳无法解析（格式漂移，非「没跑」）。

    旧实现用 `(last_run_at or "").startswith(today)`：字段缺失、格式漂移
    （UTC 变体、ISO 变体）都会被误报成「今天没有运行」，把排查方向
    引偏。解析失败要单独说，而不是混进「没跑」。
    """
    s = (last_run_at or "").strip()
    if not s:
        return False
    # 允许裸日期（YYYY-MM-DD）或后面跟 T/空格 + 时间部分
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})(?:[T ]|$)", s)
    if not m:
        # 兜底：允许 YYYYMMDD 前缀（某些字段是紧凑格式）
        m2 = re.match(r"^(\d{4})(\d{2})(\d{2})$", s)
        if m2:
            return f"{m2.group(1)}-{m2.group(2)}-{m2.group(3)}" == today
        return None
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" == today


def _report(problems: list, notes: list) -> int:
    if not problems:
        return 0
    print(f"❌ XHS 流水线自检：发现 {len(problems)} 项问题")
    print("=" * 46)
    for p in problems:
        print(f"• {p}")
    if notes:
        print("=" * 46)
        print("备注：")
        for n in notes:
            print(f"  · {n}")
    return 1


def _probe_http(url: str, timeout: int = 3) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return 200 <= r.status < 400
    except Exception:
        return False


def _content_compliance(v1_dir, v2_dir, day_name, problems):
    """Enforce the prompt red lines (SEO/tags/theme) on today's fresh content.

    The 01:00/02:00 prompts state these as 硬性要求; the watchdog now hard-gates
    them so a regression alerts the day it happens instead of being found later
    (day39's 25-char title and day35's theme collision both passed a green check).
    """
    pd_path = os.path.join(v1_dir, "post_data.json")
    if not os.path.isfile(pd_path):
        return  # existence already flagged
    try:
        pd = json.load(open(pd_path, encoding="utf-8"))
    except Exception:
        problems.append("[合规] post_data.json 无法解析")
        return

    title = (pd.get("title") or "").strip()
    if not title:
        problems.append("[合规] 标题缺失/为空（03:00 图文与 05:00 视频草稿都依赖它）")
    elif len(title) > TITLE_MAX:
        problems.append(f"[合规] 标题 {len(title)} 字（应 ≤{TITLE_MAX} 字）：{title[:24]}")
    if title and (_has_emoji(title) or "#" in title or title.endswith(("?", "？"))):
        problems.append("[合规] 标题含 emoji/# 或以问号结尾（prompt 明确禁止）")
    tags = pd.get("hashtags") or []
    if not (6 <= len(tags) <= 10):
        problems.append(f"[合规] hashtags {len(tags)} 个（应 6–10）")
    etag = (pd.get("emotion_tag") or "").strip()
    if etag and not any(etag in t for t in tags):
        problems.append(f"[合规] hashtags 未包含 emotion_tag「{etag}」")
    if any("#" in t for t in tags):
        problems.append("[合规] 有 hashtag 含 # 符号（prompt 要求纯中文词不带 #）")
    if not any("情绪树洞" in t for t in tags):
        problems.append("[合规] hashtags 未包含品牌词「情绪树洞」")
    body = (pd.get("content_text") or "").strip()
    if not body:
        problems.append("[合规] content_text 缺失/为空（03:00 fill 会发仅标题的图文草稿）")
    elif not (400 <= len(body) <= 900):
        problems.append(f"[合规] content_text {len(body)} 字（应 400–900）")
    if body and _has_emoji(body):
        problems.append("[合规] content_text 含 emoji（prompt 要求纯文字）")
    if body and "？" not in body:
        problems.append("[合规] content_text 无任何问句（prompt 要求中段至少一句反问句）")
    first_line = body.splitlines()[0].strip() if body else ""
    if etag and first_line and etag not in first_line:
        problems.append(f"[合规] 正文首句未逐字包含 emotion_tag「{etag}」：{first_line[:24]}")
    bpt = (pd.get("best_post_time") or "").strip()
    if bpt:
        try:
            hour = int(bpt[11:13])
            if not (20 <= hour <= 23):
                problems.append(f"[合规] best_post_time {bpt} 不在 20:00–23:00")
        except (ValueError, IndexError):
            problems.append(f"[合规] best_post_time 格式异常：{bpt}")

    # Cross-artifact identity: the day's title/series flows through V1
    # manifest (03:00 image draft titles the post from it), V1 post_data
    # (video description + card-1 voiceover), and V2 manifest (TTS fallback).
    # A split would give one day two differently-titled posts — enforcement
    # mirrors the theme gate (prompt rules are not self-enforcing).
    # 读 manifest。损坏时必须报出来，不能静默当空。
    # 旧实现返回 {} —— mtitle 为空 → 一致性检查全跳过，06:00 一片绿，
    # 但图文与视频可能各用各的标题。
    def _on_err(path, e):
        problems.append(f"[合规] manifest 无法解析：{os.path.basename(path)} — {e}")
    v1m = load_json_tolerant(os.path.join(v1_dir, "manifest.json"), default={}, on_error=_on_err)
    v2m = load_json_tolerant(os.path.join(v2_dir, "manifest.json"), default={}, on_error=_on_err)
    # V1 manifest 的 title 有两种落法（扁平 / 嵌套 post_data.title），
    # 嵌套里的 title 还可能不是 str —— 统一交给 manifest_title，
    # 崩溃路径与落法兼容只有一份实现（core/manifest_title.py）。
    # 曾经这段逻辑复制在三处，2026-09-27 补两处漏了一处（MED-2）。
    mtitle = manifest_title(v1m)
    ptitle = plain_title(pd)
    pseries = plain_series(pd)
    v2title = plain_title(v2m)
    v2series = plain_series(v2m)
    if mtitle and ptitle and mtitle != ptitle:
        problems.append(f"[合规] 标题不一致：V1 manifest「{mtitle}」≠ post_data「{ptitle}」")
    if ptitle and v2title and ptitle != v2title:
        problems.append(f"[合规] 图文/视频标题不一致：V1「{ptitle}」≠ V2「{v2title}」")
    if pseries and v2series and pseries != v2series:
        problems.append(f"[合规] 系列名不一致：V1「{pseries}」≠ V2「{v2series}」")

    today_date = day_name[4:12]
    last3_v1, last3_v2 = recent_schemes(BASE, today_date, n=3)
    v1_cs = _manifest_cs(v1_dir, want_v2=False)
    v2_cs = _manifest_cs(v2_dir, want_v2=True)
    problems.extend(validate_rotation(v1_cs, v2_cs, last3_v1, last3_v2))


def main() -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    today_c = today.replace("-", "")
    problems, notes = [], []

    if not os.path.isdir(BASE):
        problems.append(f"数据目录不存在：{BASE}")
        return _report(problems, notes)

    day = _latest_day()
    if day is None:
        problems.append("没有任何 day_* 素材目录——内容生成从未成功")
        return _report(problems, notes)

    latest_date = day[4:12]
    if latest_date != today_c:
        problems.append(
            f"最新素材是 {latest_date}，今天({today})没有生成新内容（01:00/02:00 生成未跑或失败）"
        )
    else:
        notes.append(f"最新素材：{day}")

    v1 = os.path.join(BASE, day)
    v2 = os.path.join(BASE, day + "_v2")

    # V1
    for f in ("manifest.json", "post_data.json"):
        p = os.path.join(v1, f)
        if not os.path.isfile(p):
            problems.append(f"[V1] {f} 缺失：{p}")

    # V2
    if not os.path.isdir(v2):
        problems.append(f"[V2] 目录缺失：{v2}")
    else:
        v2_manifest = os.path.join(v2, "manifest.json")
        if not os.path.isfile(v2_manifest):
            problems.append("[V2] manifest.json 缺失")
        else:
            try:
                with open(v2_manifest, encoding="utf-8") as f:
                    json.load(f)  # 仅验证可解析
            except FileNotFoundError:
                pass  # 上面已报缺失
            except Exception as e:
                problems.append(f"[V2] manifest.json 无法解析：{e}")
            else:
                # 按卡位校验，不只数总数：6 张重复也该判不合格。
                # 扩展名按实际渲染器可能产出的都收（.jpg/.jpeg/.png，
                # macOS 文件系统大小写不敏感，别只认小写）。
                imgs_dir = os.path.join(v2, "images")
                slot_re = re.compile(
                    r"^card.*?(cover|scene|insight|method|gentle|cta).*\.(jpe?g|png)$",
                    re.IGNORECASE)
                found = set()
                if os.path.isdir(imgs_dir):
                    for fn in os.listdir(imgs_dir):
                        m = slot_re.match(fn)
                        if m:
                            found.add(m.group(1).lower())
                missing = [s for s in ("cover", "scene", "insight",
                                       "method", "gentle", "cta") if s not in found]
                if missing:
                    problems.append(
                        f"[V2] 卡片渲染不完整：缺 {len(missing)} 个卡位 {missing}（{v2}/images）"
                    )
                else:
                    notes.append("[V2] 卡片：6 个卡位齐全")
        video = os.path.join(v2, "video", "video_note.mp4")
        if not os.path.isfile(video):
            problems.append(f"[视频] video_note.mp4 缺失：{video}")

    # 内容红线（SEO/标签/主题）——只校验今天刚生成的内容，避免历史违规每天重复告警
    if latest_date == today_c:
        _content_compliance(v1, v2, day, problems)

    # 已发布主题追踪表字段一致性：published_content.json 是 01:00 prompt 与 05:00
    # video-draft tracker 双写账本，day26 曾同一 day_num 两行（重生成未覆盖）+ 日期
    # 格式混写（LLM 写 '-'，tracker 写紧凑）。prompt 已要求按 day_num 幂等覆盖、
    # 紧凑 YYYYMMDD；此处硬门防回归（格式/重复会当天 feishu 告警而非静默漂移）。
    tc_path = os.path.join(BASE, "published_content.json")
    if os.path.isfile(tc_path):
        try:
            tc = json.load(open(tc_path, encoding="utf-8"))
        except Exception:
            problems.append("[追踪] published_content.json 无法解析")
        else:
            if isinstance(tc, dict):
                problems.append("[追踪] published_content.json 应为列表")
            elif isinstance(tc, list):
                dups = [
                    k for k, v in Counter(
                        str(e.get("day_num")) for e in tc
                        if isinstance(e, dict) and e.get("day_num") is not None
                    ).items() if v > 1
                ]
                if dups:
                    problems.append(f"[追踪] published_content.json 重复 day_num：{dups}")
                if not all(
                    isinstance(e, dict) and isinstance(e.get("date"), str)
                    and len(e.get("date", "")) == 8 and e.get("date", "").isdigit()
                    for e in tc
                ):
                    problems.append("[追踪] published_content.json 存在非紧凑(YYYYMMDD)日期")

    # 脚本 cron 步骤运行状态
    #
    # last_status 只反映「最后一次运行」的结果，而流水线是高度可修复的：
    # 02:00 崩了 → 02:15/02:30/04:00/05:00 连锁 error → 人工重跑修好 →
    # 06:00 却仍按 02:15 那次的陈旧 last_status 报 error（2026-09-27 实测：
    # 质量门当场跑 exit 0，06:00 仍报「状态异常：'error'」）。
    # 这类告警会把注意力从真问题上引开，是用户反复投诉的「06:00 误报」。
    #
    # 因此：产物可验证的步骤以产物为权威，last_status 只作参考。
    # 产物齐全却 last_status=error → note（状态未刷新），不是 problem。
    # 无产物可验的步骤（登录探针、清理）仍以 last_status 为准。
    if os.path.isfile(JOBS_JSON):
        try:
            jobs = json.load(open(JOBS_JSON, encoding="utf-8"))["jobs"]
        except Exception:
            problems.append(f"无法读取 {JOBS_JSON}")
        else:
            if not isinstance(jobs, list):
                problems.append(f"{JOBS_JSON} 的 jobs 字段不是列表（结构漂移）")
                jobs = []
            for label, script in SCRIPT_STEPS:
                j = next((x for x in jobs if x.get("script") == script), None)
                if j is None:
                    problems.append(f"[Cron] 找不到脚本任务 {script}")
                    continue
                ran = _ran_today(j.get("last_run_at"), today)
                status = j.get("last_status")
                if ran is False:
                    problems.append(f"[Cron] {label} 今天({today})没有运行（{script}）")
                elif ran is None:
                    problems.append(
                        f"[Cron] {label} 的 last_run_at 格式无法解析："
                        f"{(j.get('last_run_at') or 'None')!r}（{script}）"
                    )
                elif _artifact_ok(script, v1, v2) and status != "ok":
                    # 产物齐全 → 数据层已验证通过，陈旧的 last_status 只作提示
                    notes.append(
                        f"[Cron] {label}：产物齐全（但 last_status 仍为 {status!r}，"
                        f"应为事后重跑修复，状态未刷新）"
                    )
                elif status != "ok":
                    problems.append(f"[Cron] {label} 状态异常：{status!r}（{script}）")
                else:
                    notes.append(f"[Cron] {label}：ok")

            # 03:00 图文存草稿是 LLM job（无 script 字段），脚本步校验看不到它，
            # 素材检查也覆盖不到它的产出（草稿存在云端草稿箱）。单查它今天跑过且 ok，
            # 否则一次静默失败 = 当天没有图文草稿，无人知晓。
            # 本地无法验证草稿是否存在，故仍以 last_status 为准。
            ff = next((x for x in jobs if x.get("id") == "ebf775e37292"), None)
            if ff is None:
                problems.append("[Cron] 找不到图文存草稿任务 ebf775e37292")
            else:
                fr = _ran_today(ff.get("last_run_at"), today)
                fst = ff.get("last_status")
                if fr is False:
                    problems.append("[Cron] 图文存草稿 (03:00) 今天没有运行")
                elif fr is None:
                    problems.append(
                        f"[Cron] 图文存草稿 (03:00) 的 last_run_at 格式无法解析："
                        f"{(ff.get('last_run_at') or 'None')!r}"
                    )
                elif fst != "ok":
                    problems.append(f"[Cron] 图文存草稿 (03:00) 状态异常：{fst!r}")
                else:
                    notes.append("[Cron] 图文存草稿 (03:00)：ok")

    # 探针：ComfyUI + Chrome CDP 可达性（按需拉起，检查时未运行属正常 → 仅备注告警，不计入失败）
    if _probe_http("http://127.0.0.1:8188/system_stats", timeout=3):
        notes.append("[探针] ComfyUI 127.0.0.1:8188 可达")
    else:
        notes.append("[探针] ⚠️ ComfyUI 127.0.0.1:8188 不可达（渲染将回退到 CDP，检查时未运行属正常）")
    if _probe_http("http://127.0.0.1:9222/json", timeout=3):
        notes.append("[探针] Chrome CDP 127.0.0.1:9222 可达")
    else:
        notes.append("[探针] ⚠️ Chrome CDP 127.0.0.1:9222 不可达（发布时按需拉起，检查时未运行属正常）")

    notes.append("[提示] 图文草稿(03:00)存于 XHS 草稿箱，本地无法验证，请人工确认")

    return _report(problems, notes)


if __name__ == "__main__":
    sys.exit(main())
