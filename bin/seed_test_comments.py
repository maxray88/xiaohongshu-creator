#!/usr/bin/env python3
"""TEST-ACCOUNT-ONLY try-out comment seeding tool.

Cron-reused CLI for try-out auto-commenting against the TEST account
(无限复复复复活, XHS 95561786168, CDP 9229) during the try-out phase.
Cron may only invoke this tool in --pool mode (human pre-approved
comments, zero LLM calls); --auto-refill additionally requires the
operator's LLM proxy env. The non-pool LLM-generation path is for
interactive try-out runs only (and dry runs still cost LLM quota —
see below).

Safety:
  - Port allowlist: only CDP 9229 (test account) is accepted. The main
    account port (CDP 9224, and 9222) is refused — see BLOCKED_CDP_PORTS.
  - Kill-switch file ENGAGEMENT_STOP refuses every run while present.
  - Daily hard cap TRYOUT_HARD_CAP_PER_DAY refuses further live posts.

LLM quota note: candidate generation calls the real LLM path
(`llm_caller=None`, i.e. the operator's LLM env must be configured).
DRY RUNS STILL CALL THE LLM — even a dry run costs LLM quota. That is
intended for try-out observability (verify the LLM path works end to
end); dry runs only skip the CDP/browser side effects.

Pool mode (--pool PATH): cron-safe path with zero LLM calls. Reads a JSON
list of human-approved comments from PATH and posts the first unused
entries (up to --max-comments, still bounded by TRYOUT_HARD_CAP_PER_DAY).
Cron context has no LLM env, so scheduled runs must use --pool; the
default (no --pool) LLM-generation path is kept for interactive dry-runs
and try-out observability only. Pool entries are pre-approved by a human;
scoring is bypassed by design.

Exit codes: 0 ok (posted / planned); 1 safety refusal or CDP/LLM failure;
2 usage error.
"""

import argparse
import json
import os
import random
import sys
import time
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core"))

from commenting import (  # noqa: E402
    EngagementSequence,
    generate_comment_candidates,
    score_comment,
)
from xhs_config import QUALITY_SCORE_THRESHOLD  # noqa: E402

try:
    from io_utils import atomic_write_json  # noqa: E402
except ImportError:  # pragma: no cover - fallback for unusual path setups
    atomic_write_json = None  # type: ignore[assignment]

# NOTE: this base dir is a deliberate explicit literal, NOT
# `from xhs_config import DATA_BASE`. A config change must never be able to
# silently redirect this try-out tool at another data dir — the safety
# review greps for these paths.
_DATA_DIR = os.path.join(os.path.expanduser("~"), ".hermes", "data", "xhs_treehole")

TEST_ONLY_CDP_PORT = 9229
BLOCKED_CDP_PORTS = (9222, 9224)
TEST_ACCOUNT_SCOPE = "test_seed"
COUNTER_PATH = os.path.join(_DATA_DIR, "engagement_counter.json")
DEFAULT_POOL_PATH = os.path.join(_DATA_DIR, "engagement_pool.json")
LOG_PATH = os.path.join(_DATA_DIR, "engagement_log.jsonl")
STOP_PATH = os.path.join(_DATA_DIR, "ENGAGEMENT_STOP")
# Local-only cron target file (operator-created, chmod 600, NOT repo-tracked).
# Secrets must not live in repo-tracked wrappers, so cron passes no flags and
# this tool reads feed_id/xsec_token from here as a fallback. CLI flags win.
JOB_PATH = os.path.join(_DATA_DIR, "engagement_job.json")
TRYOUT_HARD_CAP_PER_DAY = 3


def apply_jitter(delay_min: float) -> float:
    """Jittered wait for a timeline delay (minutes) → seconds."""
    return delay_min * 60 * random.uniform(1.0, 1.5)


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


def _today_key() -> str:
    return date.today().isoformat()


def _read_counter() -> int:
    """Today's posted-comment count; missing/corrupt file → 0 (fail open)."""
    try:
        with open(COUNTER_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"• [seed] counter file not found at {COUNTER_PATH}, starting fresh.")
        return 0
    except (ValueError, OSError) as e:
        print(f"• [seed] warning: counter file unreadable ({e}), starting fresh.")
        return 0
    try:
        return int(data.get(_today_key(), 0))
    except (AttributeError, TypeError, ValueError):
        print("• [seed] warning: counter file has unexpected shape, starting fresh.")
        return 0


def _write_counter(count: int) -> None:
    """Persist today's count (atomic when core.io_utils is importable)."""
    try:
        with open(COUNTER_PATH, encoding="utf-8") as f:
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
        atomic_write_json(COUNTER_PATH, data)
    else:  # plain write + fsync fallback
        tmp = f"{COUNTER_PATH}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, COUNTER_PATH)


def _write_pool_file(pool_path: str, data: list) -> None:
    # Same atomic-or-fallback pattern as _write_counter (duplicated by
    # design; do not refactor _write_counter).
    if atomic_write_json is not None:
        atomic_write_json(pool_path, data)
    else:  # plain write + fsync fallback
        tmp = f"{pool_path}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, pool_path)


def _append_log(entry: dict) -> None:
    parent = os.path.dirname(LOG_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _select_passing_comments(scored: list) -> list:
    """Scored candidates at/above QUALITY_SCORE_THRESHOLD, best first."""
    passing = [
        c for c in scored
        if getattr(getattr(c, "score", None), "average", None) is not None
        and c.score.average >= QUALITY_SCORE_THRESHOLD
    ]
    passing.sort(key=lambda c: c.score.average, reverse=True)
    return passing


def _warn_crashed_pool_entries(pool_data: list) -> None:
    """Warn about used-without-posted_at entries (possible pre-write crash)."""
    crashed = sum(
        1 for e in pool_data
        if isinstance(e, dict) and e.get("used") is True and not e.get("posted_at")
    )
    if crashed:
        print(
            f"[seed] warning: {crashed} pool entries marked used without posted_at "
            "— possible crash; review engagement_pool.json manually"
        )


def _parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="seed_test_comments.py",
        description="TEST-ACCOUNT-ONLY try-out comment seeding (cron-reused; cron must use --pool).",
    )
    parser.add_argument("--feed-id", default=None)
    parser.add_argument("--xsec-token", default=None)
    parser.add_argument("--persona", default="supportive peer follower")
    parser.add_argument("--port", type=int, default=TEST_ONLY_CDP_PORT)
    parser.add_argument("--max-comments", type=int, default=1)
    parser.add_argument(
        "--pool",
        default=None,
        metavar="PATH",
        help=(
            "pool mode: read human-approved comments from JSON list file at PATH "
            "instead of generating via LLM (zero LLM calls). "
            "Pool entries are pre-approved by a human; scoring is bypassed by design."
        ),
    )
    parser.add_argument(
        "--auto-refill",
        action="store_true",
        default=False,
        help=(
            "when the usable pool is empty, generate candidates via LLM "
            "and keep only those passing the quality bar; without this flag "
            "an empty pool is a loud failure (Gate: pool exhausted)."
        ),
    )
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--with-reply", action="store_true")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)

    # Cron fallback: bare zero-arg runs read the target from the local-only
    # job file under DATA_DIR (operator-created, chmod 600). Secrets must
    # not live in repo-tracked wrappers, so the job file supplies ONLY
    # feed_id + xsec_token plus the optional expect_nick key consumed by the
    # identity gate; --max-comments/--persona stay CLI-only (their
    # argparse defaults are indistinguishable from explicit flags).
    # CLI flags win over the job file. Runs before Gate 1 so usage errors
    # still report correctly.
    job_cfg = {}
    # Intent: an unreadable/invalid job file fails closed (rc 1) even when both CLI flags suffice.
    if os.path.isfile(JOB_PATH):
        try:
            with open(JOB_PATH, encoding="utf-8") as f:
                job_cfg = json.load(f)
        except (OSError, ValueError) as e:
            print(f"❌ engagement_job.json unreadable: {e}")
            return 1
        if not isinstance(job_cfg, dict):
            print("❌ engagement_job.json must be a JSON object")
            return 1
        from_job = False
        if not args.feed_id and job_cfg.get("feed_id"):
            args.feed_id = job_cfg.get("feed_id")
            from_job = True
        if not args.xsec_token and job_cfg.get("xsec_token"):
            args.xsec_token = job_cfg.get("xsec_token")
            from_job = True
        if from_job:
            print("• [seed] target from engagement_job.json")

    # Gate 1: port allowlist (checked first — main-account protection).
    if args.port != TEST_ONLY_CDP_PORT or args.port in BLOCKED_CDP_PORTS:
        print(f"❌ XHS try-out seeding refused: port {args.port} is not the test-account port.")
        print("=" * 46)
        print("• main-account protection: this tool may only drive the TEST account (CDP 9229).")
        print(f"• blocked main-account ports: {BLOCKED_CDP_PORTS}. Allowlisted port: {TEST_ONLY_CDP_PORT}.")
        return 1

    # Gate 2: kill switch.
    if os.path.exists(STOP_PATH):
        print("❌ XHS try-out seeding refused: kill-switch active.")
        print("=" * 46)
        print(f"• {STOP_PATH} exists — remove it to re-enable try-out runs.")
        return 1

    # Gate 3: daily cap.
    used = _read_counter()
    allowed = TRYOUT_HARD_CAP_PER_DAY
    if used >= allowed:
        print("❌ XHS try-out seeding refused: daily cap reached.")
        print("=" * 46)
        print(f"• used {used}/{allowed} today (max-comments={args.max_comments}, hard cap={TRYOUT_HARD_CAP_PER_DAY}).")
        return 1

    # Gate 4: required target arguments (usage error, exit 2).
    if not args.feed_id or not args.xsec_token:
        print("usage: seed_test_comments.py --feed-id FEED_ID --xsec-token XSEC_TOKEN [options]", file=sys.stderr)
        print("❌ missing required --feed-id / --xsec-token.", file=sys.stderr)
        return 2

    # Candidate source: --pool (zero LLM) vs LLM generation path.
    # Pool entries are pre-approved by a human; scoring is bypassed by design.
    pool_data: list | None = None
    pool_picks: list = []  # [(pool index, text)]
    passing: list = []
    if args.pool is not None:
        try:
            with open(args.pool, encoding="utf-8") as f:
                pool_data = json.load(f)
        except FileNotFoundError:
            print(f"❌ XHS try-out seeding: pool file not found: {args.pool}.")
            print("=" * 46)
            print(f"• [seed] expected a JSON list at {args.pool}.")
            return 1
        except (ValueError, OSError) as e:
            print("❌ XHS try-out seeding: pool file unreadable.")
            print("=" * 46)
            print(f"• [seed] {e}")
            return 1
        if not isinstance(pool_data, list):
            print("❌ XHS try-out seeding: pool file unreadable.")
            print("=" * 46)
            print(f"• [seed] expected a JSON list at {args.pool}.")
            return 1
        _warn_crashed_pool_entries(pool_data)
        usable = []
        for idx, entry in enumerate(pool_data):
            if not isinstance(entry, dict):
                continue
            if entry.get("used") is True:
                continue
            text = entry.get("text")
            if not isinstance(text, str) or not text.strip():
                continue
            usable.append((idx, text))
        if not usable:
            if not args.auto_refill:
                print("❌ XHS try-out seeding: pool exhausted — add approved comments.")
                print("=" * 46)
                print(f"• [seed] no unused entries in {args.pool}.")
                return 1
            # Auto-refill: LLM-generate, score, keep only passing ones.
            try:
                candidates = generate_comment_candidates(
                    post_title="",
                    post_body="(auto-refill seeding — generic supportive comment)",
                    persona=args.persona,
                    llm_caller=None,
                )
            except Exception as e:
                print("❌ XHS try-out seeding: auto-refill produced no candidates.")
                print("=" * 46)
                print(f"• [seed] {e}")
                return 1
            if not candidates:
                print("❌ XHS try-out seeding: auto-refill produced no candidates.")
                print("=" * 46)
                print(f"• [seed] no unused entries in {args.pool}; LLM returned nothing.")
                return 1
            total = len(candidates)
            scored_ok = []
            for c in candidates:
                try:
                    scored_ok.append(score_comment(c, series=""))
                except Exception as e:
                    print(f"• [seed] auto-refill scoring failed for a candidate ({e}), skipping.")
                    continue
            kept = [
                c for c in scored_ok
                if c.score is not None and c.score.average >= QUALITY_SCORE_THRESHOLD
            ][:TRYOUT_HARD_CAP_PER_DAY]
            if not kept:
                print("❌ XHS try-out seeding: auto-refill: none met the bar.")
                print("=" * 46)
                print(f"• [seed] scored {len(scored_ok)}/{total}, none met the bar.")
                return 1
            for c in kept:
                pool_data.append({
                    "text": c.content,
                    "used": False,
                    "source": "auto",
                    "score": round(c.score.average, 2),
                })
            _write_pool_file(args.pool, pool_data)
            print(f"• [seed] auto-refill kept {len(kept)}/{total}.")
            usable = []
            for idx, entry in enumerate(pool_data):
                if not isinstance(entry, dict):
                    continue
                if entry.get("used") is True:
                    continue
                text = entry.get("text")
                if not isinstance(text, str) or not text.strip():
                    continue
                usable.append((idx, text))
            if not usable:
                print("❌ XHS try-out seeding: pool exhausted — add approved comments.")
                print("=" * 46)
                print(f"• [seed] no unused entries in {args.pool}.")
                return 1
        pool_picks = usable[: max(0, min(args.max_comments, allowed - used))]
    else:
        # NOTE: core.commenting names these params post_title/post_body.
        # llm_caller=None uses the real _call_llm — live runs need the
        # operator's LLM env, and dry runs cost quota too (intended).
        try:
            candidates = generate_comment_candidates(
                post_title="",
                post_body="(try-out seeding — body intentionally empty; comments are generic supportive notes, not post-specific claims)",
                persona=args.persona,
                llm_caller=None,
            )
        except Exception as e:
            print("❌ XHS try-out seeding: LLM candidate generation failed.")
            print("=" * 46)
            print(f"• [seed] {e}")
            return 1

        try:
            scored = [score_comment(c) for c in candidates]
        except Exception as e:
            print("❌ XHS try-out seeding: comment scoring failed.")
            print("=" * 46)
            print(f"• [seed] {e}")
            return 1

        passing = _select_passing_comments(scored)
        if not passing:
            print("❌ XHS try-out seeding: no comment met the bar — nothing posted.")
            print("=" * 46)
            print(f"• quality threshold (QUALITY_SCORE_THRESHOLD): {QUALITY_SCORE_THRESHOLD}.")
            return 1

    seq = EngagementSequence(post_id=args.feed_id, post_url="")
    timeline = seq.build_timeline(num_commenters=min(args.max_comments, 3))
    comment_actions = [
        item for item in timeline
        if "comment" in item.get("actions", [])
    ]
    planned = comment_actions[: max(0, min(args.max_comments, allowed - used))]

    if not planned:
        print("• [seed] nothing planned (--max-comments resolved to 0; nothing to do)")
        return 0
    effective = min(args.max_comments, allowed - used)
    if pool_data is not None and len(usable) < effective:
        print(f"• [seed] only {len(pool_picks)} pool entries available for {effective} requested slot(s); pool is the constraint.")
    elif pool_data is not None and effective < args.max_comments:
        print(f"• [seed] daily cap allows only {effective} more comment(s) today; posting {len(pool_picks)}.")
    if pool_data is not None and len(pool_picks) > len(planned):
        print(f"• [seed] note: {len(pool_picks) - len(planned)} extra comment(s) post with delay 0 (beyond timeline slots)")

    if not args.live:
        # DRY RUN: no publisher instantiation at all — no CDP contact.
        if pool_data is not None:
            # Pool dry-run plans without marking entries used (log only).
            for i, (pool_idx, text) in enumerate(pool_picks):
                delay = planned[i].get("delay_min", 0) if i < len(planned) else 0
                print(f"[DRY-RUN] would post (pool #{pool_idx}): {text!r} after ~{delay}min")
                _append_log({
                    "ts": datetime.now().isoformat(),
                    "feed_id": args.feed_id,
                    "content": text,
                    "delay_min": delay,
                    "dry_run": True,
                })
            return 0
        for action, cand in zip(planned, passing):
            delay = action.get("delay_min", 0)
            print(f"[DRY-RUN] would post: {cand.content!r} after ~{delay}min")
            _append_log({
                "ts": datetime.now().isoformat(),
                "feed_id": args.feed_id,
                "content": cand.content,
                "delay_min": delay,
                "dry_run": True,
            })
        if len(passing) < len(planned):
            print(f"• [seed] only {len(passing)} candidate(s) passed the bar for {len(planned)} slot(s); posting available only.")
        return 0

    # LIVE: construct the publisher lazily, only here, after all gates pass.
    from xhs_paths import add_cdp_to_path  # noqa: E402

    add_cdp_to_path()
    from cdp_publish import CDPError, XiaohongshuPublisher  # noqa: E402

    try:
        pub = XiaohongshuPublisher(
            host="127.0.0.1", port=args.port, account_name=TEST_ACCOUNT_SCOPE
        )
    except Exception as e:
        print("❌ XHS try-out seeding: publisher init failed.")
        print("=" * 46)
        print(f"• [seed] {e}")
        return 1

    posted = used
    try:
        try:
            pub.connect()
        except CDPError as e:
            print("❌ XHS try-out seeding: CDP connect failed.")
            print("=" * 46)
            print(f"• [seed] {e}")
            return 1
        expect_nick = os.environ.get("XHS_EXPECT_NICK") or job_cfg.get("expect_nick")
        if expect_nick:
            try:
                probe = getattr(pub, "probe_current_nickname", None)
                actual_nick = probe() if callable(probe) else None
            except Exception as e:  # noqa: BLE001 — probe must be fail-closed per spec
                print("❌ XHS try-out seeding: identity check failed; refusing to post.")
                print("=" * 46)
                print(f"• [seed] nickname probe raised ({e}).")
                return 1
            if actual_nick != expect_nick:
                print("❌ XHS try-out seeding: identity check failed; refusing to post.")
                print("=" * 46)
                print(f"• [seed] expected {expect_nick!r}, probed {actual_nick!r} — refusing to post as the wrong account.")
                return 1
        else:
            print("[seed] warning: no expect_nick configured — posting WITHOUT identity verification; set XHS_EXPECT_NICK or expect_nick in engagement_job.json")
        if pool_data is not None:
            for i, (pool_idx, text) in enumerate(pool_picks):
                delay = planned[i].get("delay_min", 0) if i < len(planned) else 0
                # Two-phase mark: claim the entry BEFORE posting so a crash
                # between post and write-back can never cause a duplicate
                # public post (fail-closed: a crashed entry needs manual review).
                pool_data[pool_idx]["used"] = True
                pool_data[pool_idx]["posted_at"] = None
                pool_data[pool_idx]["posted_attempt"] = datetime.now().isoformat()
                _write_pool_file(args.pool, pool_data)
                _sleep(apply_jitter(delay))
                try:
                    pub.post_comment_to_feed(args.feed_id, args.xsec_token, text)
                except CDPError as e:
                    pool_data[pool_idx]["used"] = False
                    pool_data[pool_idx].pop("posted_at", None)
                    pool_data[pool_idx].pop("posted_attempt", None)
                    _write_pool_file(args.pool, pool_data)
                    print("❌ XHS try-out seeding: post_comment_to_feed failed — stopping.")
                    print("=" * 46)
                    print(f"• [seed] {e}")
                    return 1
                pool_data[pool_idx]["posted_at"] = datetime.now().isoformat()
                _write_pool_file(args.pool, pool_data)
                posted += 1
                _write_counter(posted)
                _append_log({
                    "ts": datetime.now().isoformat(),
                    "feed_id": args.feed_id,
                    "content": text,
                    "delay_min": delay,
                    "dry_run": False,
                })
            reply_content = pool_picks[-1][1] if pool_picks else ""
        else:
            posted_contents: list = []
            for action, cand in zip(planned, passing):
                delay = action.get("delay_min", 0)
                _sleep(apply_jitter(delay))
                try:
                    pub.post_comment_to_feed(args.feed_id, args.xsec_token, cand.content)
                except CDPError as e:
                    print("❌ XHS try-out seeding: post_comment_to_feed failed — stopping.")
                    print("=" * 46)
                    print(f"• [seed] {e}")
                    return 1
                posted += 1
                _write_counter(posted)
                posted_contents.append(cand.content)
                _append_log({
                    "ts": datetime.now().isoformat(),
                    "feed_id": args.feed_id,
                    "content": cand.content,
                    "delay_min": delay,
                    "dry_run": False,
                })
            if len(passing) < len(planned):
                print(f"• [seed] only {len(passing)} candidate(s) passed the bar for {len(planned)} slot(s); posting available only.")
            reply_content = posted_contents[-1] if posted_contents else ""
        if args.with_reply:
            if not reply_content:
                print("• [seed] note: --with-reply skipped (nothing posted; empty reply content).")
            elif not hasattr(pub, "respond_comment"):
                print("❌ XHS try-out seeding: vendor respond_comment unavailable — REPORT, no DIY DOM.")
                print("=" * 46)
                print("• [seed] XiaohongshuPublisher has no respond_comment; creator reply skipped by design.")
                return 1
            else:
                replies = [item for item in timeline if item.get("action") == "reply_to_commenter_a"]
                if replies:
                    _sleep(apply_jitter(replies[0].get("delay_min", 0)))
                    try:
                        pub.respond_comment(args.feed_id, args.xsec_token, reply_content)
                    except CDPError as e:
                        print("❌ XHS try-out seeding: respond_comment failed.")
                        print("=" * 46)
                        print(f"• [seed] {e}")
                        return 1
                    _append_log({
                        "ts": datetime.now().isoformat(),
                        "feed_id": args.feed_id,
                        "content": reply_content,
                        "delay_min": replies[0].get("delay_min", 0),
                        "dry_run": False,
                        "kind": "creator_reply",
                    })
    finally:
        try:
            pub.disconnect()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
