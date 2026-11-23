#!/usr/bin/env python3
"""Regression: CDP 1 MiB receive-frame cap broke 1080x1440@2x card screenshots.

Background (2026-11-10): 5 of 6 cards failed with
  CDPError: ... sent 1009 (message too big) frame ... exceeds limit of 1048576 bytes
because vendor/xhs/cdp_publish.py called websockets.sync.client.connect()
with the default max_size (1 MiB), while base64 screenshot payloads exceed it.
Fix: connect(..., max_size=16 MiB). No network / no Chrome in these tests.

Run: python3 -m pytest tests/test_render_frame_cap.py -v
"""

import ast
import importlib.util
import os
import re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
CDP_PATH = os.path.join(ROOT, "vendor", "xhs", "cdp_publish.py")
VENDOR_DIR = os.path.join(ROOT, "vendor")

MIN_MAX_SIZE = 8 * 1024 * 1024  # >= 8 MiB required by spec


def _load_module():
    spec = importlib.util.spec_from_file_location("cdp_publish_framecap", CDP_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_connect_passes_max_size_at_least_8mib(monkeypatch):
    """connect() must call ws_client.connect with max_size >= 8 MiB (live call)."""
    mod = _load_module()
    seen = {}

    class FakeWS:
        pass

    def fake_connect(url, **kwargs):
        seen["url"] = url
        seen["kwargs"] = kwargs
        return FakeWS()

    monkeypatch.setattr(mod.ws_client, "connect", fake_connect)
    monkeypatch.setattr(mod.XiaohongshuPublisher, "_find_or_create_tab",
                        lambda self, **kw: "ws://127.0.0.1:1/tab")
    pub = mod.XiaohongshuPublisher()
    pub.connect()
    assert "max_size" in seen["kwargs"], "connect() must pass max_size to ws_client.connect"
    assert seen["kwargs"]["max_size"] >= MIN_MAX_SIZE, (
        f"max_size {seen['kwargs']['max_size']} < required {MIN_MAX_SIZE}"
    )


def test_no_uncapped_connect_in_cdp_publish():
    """Every ws_client.connect( call in cdp_publish.py must pass max_size (AST)."""
    tree = ast.parse(open(CDP_PATH, encoding="utf-8").read())
    calls = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == "connect"
             and isinstance(n.func.value, ast.Name)
             and n.func.value.id == "ws_client"]
    assert calls, "expected at least one connect() call in cdp_publish.py"
    for call in calls:
        kws = [k.arg for k in call.keywords]
        assert "max_size" in kws, (
            f"uncapped connect() call at line {call.lineno} in cdp_publish.py"
        )
    # Numeric check on the literal: must be >= 8 MiB.
    src = open(CDP_PATH, encoding="utf-8").read()
    m = re.search(r"max_size\s*=\s*([0-9][0-9 _\*]*)", src)
    assert m, "max_size= assignment not found in cdp_publish.py"
    assert eval(m.group(1)) >= MIN_MAX_SIZE


def test_vendor_tree_connect_calls_inventory():
    """Inventory every ws_client.connect( in vendor/; all screenshot-carrying
    call sites must pass max_size.

    Exempt (documented, NOT changed per spec §2.1 'do not change any other
    vendored line'): vendor/xhs/chrome_launcher.py:272 sends a one-shot
    '{"method":"Browser.close"}' (~33 bytes, tiny reply) — it never carries
    a screenshot payload, so the 1 MiB cap cannot trip there.
    """
    uncapped = []
    for dirpath, _, filenames in os.walk(VENDOR_DIR):
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            fp = os.path.join(dirpath, fn)
            for i, line in enumerate(open(fp, encoding="utf-8"), 1):
                if "ws_client.connect(" in line and "max_size" not in line:
                    rel = os.path.relpath(fp, ROOT)
                    uncapped.append(f"{rel}:{i}:{line.strip()}")
    exempt = [u for u in uncapped if "chrome_launcher.py" in u]
    screenshot_sites = [u for u in uncapped if "chrome_launcher.py" not in u]
    assert not screenshot_sites, (
        "uncapped screenshot-capable ws_client.connect calls remain: "
        + "; ".join(screenshot_sites)
    )
    # The only allowed remainder is the Browser.close probe.
    assert all("chrome_launcher.py" in u for u in uncapped), uncapped
