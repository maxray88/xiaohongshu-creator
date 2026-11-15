#!/usr/bin/env python3
"""Reply to comments on your own notes (creator auto-reply, Round B).

Dry-run (no --live): read-only CDP discovery — construct publisher (lazy),
connect, per-note scan, print [DRY-RUN] plan, write reply_ledger.jsonl
(dry_run: true, status planned). Never writes reply_counter.json.
Live (--live): US2 publish path — LLM generation + quality gate +
respond_comment two-phase ledger + counter/hostile-stop enforcement.

Gate order: port 9229 allowlist -> ENGAGEMENT_STOP kill-switch ->
reply daily cap (reply_counter.json, 3/day, corrupt -> rc 1) ->
hostile stop window (reply_state.json, bad ISO/type -> rc 1) ->
config gates (own_profile_url|own_user_id plus expect_nick required) ->
publisher lazy -> connect -> per-note scan -> thread-fact filter ->
hostile abort (48h) -> LLM generate/score -> publish.

Exit codes: 0 ok (incl. all-skipped, incl. partial failure);
1 safety refusal/CDP failure/all-eligible-failed; 2 usage error.
"""

import argparse
import json
import os
import random
import re
import sys
import time
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core"))

from commenting import is_hostile

try:
    from content_scorer import score_content
except ImportError:  # pragma: no cover
    score_content = None  # type: ignore[assignment]

try:
    from llm_client import call_llm as _default_llm_caller
except ImportError:  # pragma: no cover
    _default_llm_caller = None  # type: ignore[assignment]

try:
    from xhs_config import QUALITY_SCORE_THRESHOLD
except ImportError:  # pragma: no cover
    QUALITY_SCORE_THRESHOLD = 7.0

try:
    from io_utils import atomic_write_json
except ImportError:  # pragma: no cover - fallback for unusual path setups
    atomic_write_json = None  # type: ignore[assignment]

CREATOR_REPLY_SYSTEM_PROMPT = (
    "You are the creator of this Xiaohongshu (小红书) post, replying to a fan's comment. "
    "Reply in a warm, colloquial XHS tone, 1-2 sentences, echoing the post title and "
    "the comment. Never invent facts, never include links or contact info."
)

_DEFAULT_DATA_DIR = os.path.join(os.path.expanduser("~"), ".hermes", "data", "xhs_treehole")

TEST_ONLY_CDP_PORT = 9229
BLOCKED_CDP_PORTS = (9222, 9224)
REPLY_HARD_CAP_PER_DAY = 3
HOSTILE_STOP_HOURS = 48
NOTE_ID_RE = re.compile(r"[0-9a-zA-Z]{24}\Z")

PUBLISHER_FACTORY = None
LLM_CALLER = None


class _FailClosed(Exception):
    """Internal: fail-closed gate refusal carrying (message, rc)."""

    def __init__(self, message: str, rc: int = 1):
        super().__init__(message)
        self.message = message
        self.rc = rc


def _data_dir() -> str:
    return os.environ.get("XHS_TREEHOLE_DATA_DIR", _DEFAULT_DATA_DIR)


def _counter_path() -> str:
    return os.path.join(_data_dir(), "reply_counter.json")


def _state_path() -> str:
    return os.path.join(_data_dir(), "reply_state.json")


def _ledger_path() -> str:
    return os.path.join(_data_dir(), "reply_ledger.jsonl")


def _stop_path() -> str:
    return os.path.join(_data_dir(), "ENGAGEMENT_STOP")


def _job_path() -> str:
    return os.path.join(_data_dir(), "engagement_job.json")


def _today_key() -> str:
    return date.today().isoformat()


def _read_counter() -> int:
    """Today's reply count; missing file -> 0. Unreadable/corrupt -> raise _FailClosed (rc 1)."""
    try:
        with open(_counter_path(), encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return 0
    except (ValueError, OSError) as e:
        raise _FailClosed(f"reply_counter.json unreadable ({e}); refusing.") from e
    if not isinstance(data, dict):
        raise _FailClosed("reply_counter.json is not a JSON object; refusing.")
    try:
        return int(data.get(_today_key(), 0))
    except (TypeError, ValueError) as e:
        raise _FailClosed(f"reply_counter.json has unexpected shape ({e}); refusing.") from e


def _write_counter(count: int) -> None:
    """Persist today's count, trimming keys older than 45 days."""
    try:
        with open(_counter_path(), encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            data = {}
    except (FileNotFoundError, ValueError, OSError):
        data = {}
    data[_today_key()] = int(count)
    cutoff = (date.today() - timedelta(days=45)).isoformat()
    for key in [k for k in data if isinstance(k, str) and k < cutoff]:
        del data[key]
    if atomic_write_json is not None:
        atomic_write_json(_counter_path(), data)
    else:  # plain write + fsync fallback
        tmp = f"{_counter_path()}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, _counter_path())


def _read_hostile_stop() -> str | None:
    """Return hostile_stop_until ISO string when set, else None.

    Raises _FailClosed (rc 1) on JSON parse failure or non-object shape.
    """
    try:
        with open(_state_path(), encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return None
    except (ValueError, OSError) as e:
        raise _FailClosed(f"reply_state.json unreadable ({e}); refusing.") from e
    if not isinstance(data, dict):
        raise _FailClosed("reply_state.json is not a JSON object; refusing.")
    value = data.get("hostile_stop_until")
    if value is None:
        return None
    if not isinstance(value, str):
        raise _FailClosed("reply_state.json hostile_stop_until is not a string; refusing.")
    return value if value else None


def _hostile_stop_active() -> bool:
    stop_until = _read_hostile_stop()
    if not stop_until:
        return False
    try:
        return datetime.fromisoformat(stop_until) > datetime.now()
    except ValueError as e:
        raise _FailClosed("reply_state.json hostile_stop_until is not valid ISO8601; refusing.") from e


def _write_hostile_stop(until: datetime) -> None:
    payload = {"hostile_stop_until": until.isoformat()}
    if atomic_write_json is not None:
        atomic_write_json(_state_path(), payload)
    else:
        tmp = f"{_state_path()}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, _state_path())


def _read_posted_index() -> set:
    """(feed_id, comment_id) pairs already replied (live done lines only).

    Skips dry_run lines, intent lines (posted_at None), failed/skipped lines.
    Legacy live rows without a posted_at key still count as done.
    """
    posted = set()
    try:
        with open(_ledger_path(), encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return posted
    except OSError as e:
        print(f"• [reply] warning: ledger unreadable ({e}).")
        return posted
    for lineno, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            print(f"• [reply] warning: skipping malformed ledger line {lineno}.")
            continue
        if not isinstance(entry, dict):
            print(f"• [reply] warning: skipping malformed ledger line {lineno}.")
            continue
        if entry.get("dry_run"):
            continue
        if entry.get("status") not in (None, "posted"):
            continue
        if "posted_at" in entry and entry.get("posted_at") is None:
            continue  # intent row without matching done row
        feed_id = entry.get("feed_id")
        comment_id = entry.get("comment_id")
        if feed_id and comment_id:
            posted.add((str(feed_id), str(comment_id)))
    return posted


def _warn_orphan_intents() -> None:
    """Warn about intent rows that never got a done/failed row (crash suspicion)."""
    try:
        with open(_ledger_path(), encoding="utf-8") as f:
            lines = f.readlines()
    except (FileNotFoundError, OSError):
        return
    intents: set = set()
    dones: set = set()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if not isinstance(entry, dict) or entry.get("dry_run"):
            continue
        key = (str(entry.get("feed_id") or ""), str(entry.get("comment_id") or ""))
        if not key[0] or not key[1]:
            continue
        if entry.get("status") == "posted" and entry.get("posted_at") is None:
            intents.add(key)
        elif entry.get("status") in ("posted", "failed") and not (
            "posted_at" in entry and entry.get("posted_at") is None
        ):
            dones.add(key)
    orphans = sorted(intents - dones)
    for feed_id, comment_id in orphans:
        print(
            f"• [reply] warning: suspected incomplete publish "
            f"(intent without done) for {feed_id[:8]}/{comment_id[:8]} — "
            f"manual review required; will NOT auto-retry."
        )


def _append_ledger(entry: dict) -> None:
    with open(_ledger_path(), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def _load_job_config() -> dict | None:
    """Return job-file dict, {} when absent, None when unreadable."""
    path = _job_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        print(f"❌ engagement_job.json unreadable: {e}")
        return None
    if not isinstance(data, dict):
        print("❌ engagement_job.json must be a JSON object")
        return None
    return data


def _resolve_config(args: argparse.Namespace):
    """Merge CLI > env > job file. Returns (cfg, rc) with rc 0 ok."""
    job_cfg = _load_job_config()
    if job_cfg is None:
        return None, 1
    own_profile_url = (
        args.own_profile_url or os.environ.get("XHS_OWN_PROFILE_URL") or job_cfg.get("own_profile_url")
    )
    own_user_id = (
        args.own_user_id or os.environ.get("XHS_OWN_USER_ID") or job_cfg.get("own_user_id")
    )
    expect_nick = (
        args.expect_nick or os.environ.get("XHS_EXPECT_NICK") or job_cfg.get("expect_nick")
    )
    if own_profile_url and own_user_id:
        print("❌ --own-profile-url and --own-user-id are mutually exclusive.", file=sys.stderr)
        return None, 2
    if not own_profile_url and not own_user_id:
        print("❌ missing required identity: --own-profile-url or --own-user-id.", file=sys.stderr)
        return None, 2
    if not (expect_nick or "").strip():
        print("❌ missing required expect_nick (CLI --expect-nick, env XHS_EXPECT_NICK, or job expect_nick).", file=sys.stderr)
        return None, 2
    return {
        "own_profile_url": own_profile_url,
        "own_user_id": own_user_id,
        "expect_nick": expect_nick.strip(),
    }, 0


def _gates(args: argparse.Namespace):
    """CDP-free gate pack. Returns (cfg, used, rc); rc != 0 refuses."""
    if args.port != TEST_ONLY_CDP_PORT or args.port in BLOCKED_CDP_PORTS:
        print(f"❌ creator auto-reply refused: port {args.port} is not the test-account port.")
        print("=" * 46)
        print(f"• main-account protection: this tool may only drive the TEST account (CDP {TEST_ONLY_CDP_PORT}).")
        return None, 0, 1
    if os.path.exists(_stop_path()):
        print("❌ creator auto-reply refused: kill-switch active.")
        print("=" * 46)
        print(f"• {_stop_path()} exists — remove it to re-enable runs.")
        return None, 0, 1
    try:
        used = _read_counter()
    except _FailClosed as e:
        print(f"❌ creator auto-reply refused: {e.message}")
        return None, 0, 1
    if used >= REPLY_HARD_CAP_PER_DAY:
        print("❌ creator auto-reply refused: daily cap reached.")
        print("=" * 46)
        print(f"• used {used}/{REPLY_HARD_CAP_PER_DAY} today.")
        return None, used, 1
    try:
        hostile_active = _hostile_stop_active()
    except _FailClosed as e:
        print(f"❌ creator auto-reply refused: {e.message}")
        return None, used, 1
    if hostile_active:
        print("❌ creator auto-reply refused: hostile stop window active.")
        print("=" * 46)
        print(f"• reply_state.json hostile_stop_until={_read_hostile_stop()} — cooling down.")
        return None, used, 1
    cfg, rc = _resolve_config(args)
    if rc != 0:
        return None, used, rc
    return cfg, used, 0


def _default_publisher_factory(args):
    from xhs_paths import add_cdp_to_path

    add_cdp_to_path()
    from cdp_publish import XiaohongshuPublisher

    return XiaohongshuPublisher(host="127.0.0.1", port=args.port, account_name="reply_own")


def _discover_pending(publisher, cfg: dict, max_posts: int, limit_comments: int, max_replies=None):
    """Scan own notes; return (scanned, pending, skipped).

    Hostile comments are NOT filtered here — they stay in pending so the
    reply loop can abort the round on them (FR-008). max_replies None/negative
    is clamped to 0 via max(0, ...).
    """
    max_replies = max(0, max_replies or 0)
    pending = []
    skipped = 0
    scanned = 0
    try:
        notes_res = publisher.list_profile_notes(
            profile_url=cfg.get("own_profile_url"),
            user_id=cfg.get("own_user_id"),
            limit=max_posts,
        )
    except Exception as e:  # noqa: BLE001 — per-note fail-open, warn and continue
        print(f"• [reply] warning: profile scan failed ({e}); nothing to do.")
        return 0, [], 0
    notes = notes_res.get("notes", []) if isinstance(notes_res, dict) else []
    if not isinstance(notes, list):
        notes = []
    posted_index = _read_posted_index()
    expect_nick = (cfg.get("expect_nick") or "").strip()
    for note in notes[: max(0, max_posts)]:
        if not isinstance(note, dict):
            continue
        feed_id = str(note.get("id") or "").strip()
        if not NOTE_ID_RE.fullmatch(feed_id):
            print(f"• [reply] warning: skipping note with bad id {feed_id!r}.")
            continue
        scanned += 1
        xsec_token = str(note.get("xsec_token") or "")
        title = str(note.get("title") or "")
        try:
            publisher.get_feed_detail(feed_id, xsec_token, load_all_comments=True)
        except Exception as e:  # noqa: BLE001 — FR-014: skip the note, continue
            print(f"• [reply] warning: note {feed_id[:8]} unreachable ({e}); skipped.")
            continue
        try:
            comments_res = publisher.list_feed_comments(feed_id, creator_nick=expect_nick or None)
        except Exception as e:  # noqa: BLE001 — FR-014: skip the note, continue
            print(f"• [reply] warning: note {feed_id[:8]} comments unreadable ({e}); skipped.")
            continue
        if not isinstance(comments_res, dict) or not comments_res.get("ok"):
            print(f"• [reply] warning: note {feed_id[:8]} comments unreadable; skipped.")
            continue
        comments = comments_res.get("comments", [])
        if not isinstance(comments, list):
            comments = []
        taken = 0
        for item in comments:
            if not isinstance(item, dict):
                continue
            comment_id = str(item.get("comment_id") or "").strip()
            author = str(item.get("author") or "").strip()
            content = str(item.get("content") or "")
            if not comment_id:
                continue
            if expect_nick and author == expect_nick:
                skipped += 1
                continue
            if item.get("has_creator_reply"):
                skipped += 1
                continue
            if (feed_id, comment_id) in posted_index:
                skipped += 1
                continue
            if taken >= max(0, limit_comments) or len(pending) >= max_replies:
                skipped += 1
                continue
            taken += 1
            pending.append({
                "feed_id": feed_id,
                "xsec_token": xsec_token,
                "title": title,
                "comment_id": comment_id,
                "author": author,
                "content": content,
                "created_at": str(item.get("created_at") or ""),
            })
    return scanned, pending, skipped


def _generate_reply_text(title: str, content: str, llm_caller=None) -> str:
    caller = llm_caller or LLM_CALLER or _default_llm_caller
    if caller is None:
        return ""
    user_prompt = f"Post title: {title}\nComment: {content}\nReply as the creator (1-2 sentences):"
    try:
        return (caller(CREATOR_REPLY_SYSTEM_PROMPT, user_prompt, temperature=0.7) or "").strip()
    except TypeError:
        try:
            return (caller(CREATOR_REPLY_SYSTEM_PROMPT, user_prompt) or "").strip()
        except Exception:  # noqa: BLE001 — fake/real LLM callers vary; generation failure = empty
            return ""
    except Exception:  # noqa: BLE001 — LLM outage must not crash the round; caller sees ""
        return ""


def _reply_passes_quality(reply: str) -> bool:
    if not (reply or "").strip():
        return False
    if score_content is None:
        return False
    try:
        return score_content(title="", body=reply, hashtags=[], series="", short_form=True).average >= QUALITY_SCORE_THRESHOLD
    except Exception:  # noqa: BLE001 — scorer failure = below threshold, skip the comment
        return False


def _parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="reply_to_own_comments.py",
        description="Creator auto-reply for your own notes (dry-run by default, --live to publish).",
    )
    parser.add_argument("--live", action="store_true", help="live publish path (US2)")
    parser.add_argument("--max-posts", type=int, default=5)
    parser.add_argument("--limit-comments", type=int, default=10)
    parser.add_argument("--max-replies", type=int, default=None)
    parser.add_argument("--report", action="store_true", help="print reply_ledger.jsonl summary (read-only)")
    parser.add_argument("--port", type=int, default=TEST_ONLY_CDP_PORT)
    parser.add_argument("--own-profile-url", default=None)
    parser.add_argument("--own-user-id", default=None)
    parser.add_argument("--expect-nick", default=None)
    return parser.parse_args(argv)


def _print_report() -> int:
    try:
        with open(_ledger_path(), encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        print("• [reply] report: no ledger yet.")
        return 0
    except OSError as e:
        print(f"❌ reply report: ledger unreadable ({e}).")
        return 1
    rows = 0
    print("ts | feed | comment | dry_run | status")
    for lineno, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            print(f"• [reply] warning: skipping malformed ledger line {lineno}.")
            continue
        if not isinstance(entry, dict):
            print(f"• [reply] warning: skipping malformed ledger line {lineno}.")
            continue
        print(
            f"{entry.get('ts', '-')}"
            f" | {str(entry.get('feed_id', '-'))[:8]}"
            f" | {str(entry.get('comment_id', '-'))[:8]}"
            f" | {entry.get('dry_run', False)}"
            f" | {entry.get('status', '-')}"
        )
        rows += 1
    print(f"• [reply] report: {rows} row(s).")
    return 0


def _jitter_sleep() -> None:
    """Inter-reply jitter (anti-flurry): sleep random 20-45s. No-op patch point in tests."""
    time.sleep(random.uniform(20, 45))


def _run_dry(publisher, cfg: dict, args, used: int) -> int:
    remaining = max(0, REPLY_HARD_CAP_PER_DAY - used)
    max_replies = remaining if args.max_replies is None else min(args.max_replies, remaining)
    scanned, pending, skipped = _discover_pending(
        publisher, cfg, args.max_posts, args.limit_comments, max_replies
    )
    print(f"• [reply] notes scanned={scanned}, pending={len(pending)}")
    if not pending and skipped == 0:
        return 0
    planned = 0
    for item in pending:
        if is_hostile(str(item.get("content") or "")):
            _write_hostile_stop(datetime.now() + timedelta(hours=HOSTILE_STOP_HOURS))
            print("⚠️ [reply] hostile comment detected — aborting round, 48h stop set.")
            print(f"• [reply] done: planned={planned} posted=0 aborted=hostile")
            return 0
        preview = " ".join(str(item["content"]).split())[:80]
        print(
            f"[DRY-RUN] would reply to {item['feed_id'][:8]}"
            f" comment {item['comment_id'][:8]} by {item['author']}: {preview}"
        )
        _append_ledger({
            "ts": datetime.now().isoformat(),
            "feed_id": item["feed_id"],
            "comment_id": item["comment_id"],
            "author": item["author"],
            "content": item["content"],
            "dry_run": True,
            "status": "planned",
        })
        planned += 1
    print(f"• [reply] done: planned={planned} skipped={skipped} failed=0")
    return 0


def _run_live(publisher, cfg: dict, args, used: int, llm_caller=None) -> int:
    _warn_orphan_intents()
    remaining = max(0, REPLY_HARD_CAP_PER_DAY - used)
    max_replies = remaining if args.max_replies is None else min(args.max_replies, remaining)
    scanned, pending, skipped = _discover_pending(
        publisher, cfg, args.max_posts, args.limit_comments, max_replies
    )
    print(f"• [reply] notes scanned={scanned}, pending={len(pending)}")
    posted = 0
    failed = 0
    count = used
    attempts = 0
    for item in pending:
        content = str(item.get("content") or "")
        if is_hostile(content):
            _write_hostile_stop(datetime.now() + timedelta(hours=HOSTILE_STOP_HOURS))
            print("⚠️ [reply] hostile comment detected — aborting round, 48h stop set.")
            print(f"• [reply] done: planned={len(pending)} posted={posted} aborted=hostile")
            return 0
        reply = _generate_reply_text(str(item.get("title") or ""), content, llm_caller)
        if not (reply or "").strip():
            _append_ledger({
                "ts": datetime.now().isoformat(),
                "feed_id": item["feed_id"],
                "comment_id": item["comment_id"],
                "author": item["author"],
                "content": content,
                "dry_run": False,
                "status": "failed",
                "error": "empty_generation",
                "posted_at": None,
            })
            failed += 1
            continue
        if not _reply_passes_quality(reply):
            _append_ledger({
                "ts": datetime.now().isoformat(),
                "feed_id": item["feed_id"],
                "comment_id": item["comment_id"],
                "author": item["author"],
                "content": content,
                "dry_run": False,
                "status": "skipped",
                "reason": "below_threshold",
            })
            continue
        intent = {
            "ts": datetime.now().isoformat(),
            "feed_id": item["feed_id"],
            "comment_id": item["comment_id"],
            "author": item["author"],
            "content": reply,
            "dry_run": False,
            "status": "posted",
            "posted_at": None,
        }
        _append_ledger(intent)
        if attempts:
            _jitter_sleep()
        attempts += 1
        try:
            publisher.respond_comment(
                item["feed_id"],
                item.get("xsec_token") or "",
                reply,
                comment_id=item["comment_id"],
                comment_author=item["author"],
                comment_snippet=reply[:40],
            )
        except Exception as e:  # noqa: BLE001 — per-comment fail-open, no counter扣
            _append_ledger({
                "ts": datetime.now().isoformat(),
                "feed_id": item["feed_id"],
                "comment_id": item["comment_id"],
                "author": item["author"],
                "content": reply,
                "dry_run": False,
                "status": "failed",
                "error": str(e)[:200],
                "posted_at": None,
            })
            failed += 1
            continue
        _append_ledger({
            "ts": datetime.now().isoformat(),
            "feed_id": item["feed_id"],
            "comment_id": item["comment_id"],
            "author": item["author"],
            "content": reply,
            "dry_run": False,
            "status": "posted",
            "posted_at": datetime.now().isoformat(),
        })
        posted += 1
        count += 1
        _write_counter(count)
    eligible = len(pending)
    print(f"• [reply] done: planned={eligible} posted={posted} skipped={skipped} failed={failed}")
    if eligible > 0 and posted == 0 and failed == eligible:
        # Whole batch failed (nothing posted, no clean below-threshold skips): FR-017 rc 1.
        return 1
    return 0


def run(argv=None, publisher_factory=None, llm_caller=None) -> int:
    args = _parse_args(argv)
    if args.report:
        return _print_report()
    if args.max_posts is not None and args.max_posts <= 0:
        print("❌ --max-posts must be positive.", file=sys.stderr)
        return 2
    if args.limit_comments is not None and args.limit_comments <= 0:
        print("❌ --limit-comments must be positive.", file=sys.stderr)
        return 2
    if args.max_replies is not None and args.max_replies < 0:
        print("❌ --max-replies must be non-negative.", file=sys.stderr)
        return 2
    cfg, used, rc = _gates(args)
    if rc != 0:
        return rc
    assert cfg is not None
    factory = publisher_factory or PUBLISHER_FACTORY or _default_publisher_factory
    try:
        publisher = factory(args)
    except Exception as e:  # noqa: BLE001 — fail closed on construction
        print(f"❌ creator auto-reply refused: publisher construction failed ({e}).")
        return 1
    try:
        connect = getattr(publisher, "connect", None)
        if callable(connect):
            connect()
    except Exception as e:  # noqa: BLE001 — fail closed on connect
        print(f"❌ creator auto-reply refused: CDP connect failed ({e}).")
        return 1
    if args.live:
        return _run_live(publisher, cfg, args, used, llm_caller)
    return _run_dry(publisher, cfg, args, used)


def main(argv=None) -> int:
    return run(argv)


if __name__ == "__main__":
    sys.exit(main())
