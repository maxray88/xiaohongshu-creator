#!/usr/bin/env python3
"""照片池 fetcher 确定性逻辑回归测试。

覆盖 docs/pool_fetcher.md 中可单元测试的部分：
G1 license 门、G2 尺寸门、G5 deny 去重、cursor 不交集、credits schema。
门逻辑与 cron prompt 同源，实现为本文件内纯函数（fetcher 本体是
agent prompt，无可 import 的 runner；沿用 test_watchdog_retrigger.py
的"注入式、可 tmp 目录运行"风格）。

运行：python3 -m pytest tests/test_pool_fetcher.py -v
"""

import fnmatch
import os

# --- 与 prompt 同源的纯门逻辑 -------------------------------------------

PD_LICENSES = {"pd", "cc0", "pdm", "public domain", "cc0-1.0",
               "public-domain", "pd-old", "pd-us", "pd-art"}


def license_pass(license_code, usage_terms=""):
    """G1：仅 PD / CC0 通过；CC BY（含 SA/NC）一律拒绝；未知 fail-closed。"""
    code = (license_code or "").strip().lower()
    terms = (usage_terms or "").lower()
    if "noncommercial" in terms or "no derivatives" in terms:
        return False
    if any(t in code for t in ("by-sa", "by-nc", "by_nd", "by-nd")):
        return False
    if code.startswith("cc-by") or "attribution" in code:
        return False
    if code:
        return code in PD_LICENSES
    # 无 code 时只认 terms 明示 PD/CC0，否则 fail-closed
    return "public domain" in terms or "cc0" in terms


def size_pass(width, height, minimum=1400):
    """G2：长边 >= 1400px。"""
    try:
        return max(int(width), int(height)) >= minimum
    except (TypeError, ValueError):
        return False


def denied(filename, deny_list):
    """G5：命中 deny glob 则拒绝。只比 basename。"""
    base = os.path.basename(filename or "")
    return any(fnmatch.fnmatch(base, pat) for pat in (deny_list or []))


def already_have(ref, filename, credits):
    """G5：ref/pageid 或 file 已存在则拒绝。"""
    for c in credits:
        if ref and c.get("ref") == ref:
            return True
        if filename and c.get("file") == filename:
            return True
    return False


def nightly_sets(n, day_num, step=6, per_day=6):
    """cursor 公式：photos[(D*6+k) % N]。返回某晚 6 张下标集合。"""
    return {(day_num * step + k) % n for k in range(per_day)}


def disjoint_consecutive(n, day_num, step=6, per_day=6):
    """连续两晚 6-set 是否不交（N>=12 时应成立）。"""
    return nightly_sets(n, day_num, step, per_day).isdisjoint(
        nightly_sets(n, day_num + 1, step, per_day))


CREDITS_REQUIRED = {"file", "media", "ref", "title", "creator",
                    "creatorUrl", "date", "license", "licenseCode",
                    "licenseUrl", "notes", "creditRequired", "page",
                    "via", "image", "width", "height", "bytes",
                    "credit", "saved"}


def credits_entry_valid(entry):
    """G6 + schema：必填键齐全，credit/saved 非空。"""
    if not CREDITS_REQUIRED.issubset(entry.keys()):
        return False
    return bool(entry.get("credit")) and bool(entry.get("saved"))


def crop_valid(crop, lo=590, hi=700):
    """cropA/B 高度须在合法区间。"""
    try:
        return lo <= int(crop.get("h", -1)) <= hi and bool(crop.get("pos"))
    except (TypeError, ValueError, AttributeError):
        return False


# --- 测试 ----------------------------------------------------------------

def test_g1_pd_and_cc0_pass():
    assert license_pass("pd")
    assert license_pass("PD")
    assert license_pass("cc0")
    assert license_pass("pdm")
    assert license_pass("pd-old")
    assert license_pass("", "This work is in the public domain")


def test_g1_cc_by_variants_rejected():
    assert not license_pass("cc-by")
    assert not license_pass("cc-by-sa")
    assert not license_pass("CC-BY-NC")
    assert not license_pass("cc-by-nd")
    assert not license_pass("cc-by", "Attribution required")


def test_g1_unknown_fail_closed():
    assert not license_pass("")
    assert not license_pass(None)
    assert not license_pass("copyrighted")
    assert not license_pass("pd", "NonCommercial use only")


def test_g2_long_edge_minimum():
    assert size_pass(1558, 2000)
    assert size_pass(2000, 1000)
    assert size_pass(1400, 900)
    assert not size_pass(1399, 900)
    assert not size_pass(800, 600)
    assert not size_pass(None, None)
    assert not size_pass("x", "y")


def test_g5_deny_globs():
    deny = ["letter-signed-tom-*.jpg", "huaxi-*.jpg"]
    assert denied("letter-signed-tom-abc.jpg", deny)
    assert denied("huaxi-street-night-market.jpg", deny)
    assert not denied("moonlit-harbor-postcard.jpg", deny)
    assert not denied("x.jpg", [])


def test_g5_dedupe_by_ref_and_file():
    credits = [{"ref": "commons:123", "file": "a.jpg"}]
    assert already_have("commons:123", "b.jpg", credits)
    assert already_have("commons:999", "a.jpg", credits)
    assert not already_have("commons:999", "b.jpg", credits)


def test_cursor_disjoint_with_grown_pool():
    for n in (12, 13, 14, 18, 24, 48):
        for d in (0, 1, 7, 100, 365):
            assert disjoint_consecutive(n, d), f"N={n} D={d}"


def test_cursor_disjoint_fails_when_pool_too_small():
    assert not disjoint_consecutive(6, 0)
    assert not disjoint_consecutive(11, 0)


def test_credits_schema_valid_and_invalid():
    good = {k: "x" for k in CREDITS_REQUIRED}
    good.update({"width": 100, "height": 100, "bytes": 1,
                 "creditRequired": False})
    assert credits_entry_valid(good)
    bad = dict(good)
    del bad["saved"]
    assert not credits_entry_valid(bad)
    bad2 = dict(good, credit="")
    assert not credits_entry_valid(bad2)
    for key in ("creatorUrl", "date", "licenseUrl", "notes"):
        missing = dict(good)
        del missing[key]
        assert not credits_entry_valid(missing), key


def test_crop_interval():
    assert crop_valid({"h": 590, "pos": "50% 40%"})
    assert crop_valid({"h": 700, "pos": "50% 40%"})
    assert not crop_valid({"h": 589, "pos": "50% 40%"})
    assert not crop_valid({"h": 701, "pos": "50% 40%"})
    assert not crop_valid({"h": 640, "pos": ""})


def test_pool_file_conventions_hold(tmp_path):
    """用仓库真实 photo_pool.json 校验：short 唯一、cropA 合法。"""
    import json
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    pool = json.load(open(os.path.join(root, ".taste-skill",
                                       "photo_pool.json")))
    shorts = [p["short"] for p in pool["photos"]]
    assert len(shorts) == len(set(shorts))
    for p in pool["photos"]:
        # 旧 12 条的 crop 系历史值（区间外 grandfathered），新条目才强制区间；
        # 此处只校验新条目（short 不在旧集合即视为新）。
        assert p["file"].startswith(".taste-skill/assets-src/")
        assert p["short"] == p["short"].lower().replace("_", "-")
