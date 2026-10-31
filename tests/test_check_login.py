"""Regression tests for the XHS publish-page login probe."""

import importlib.util
import os
import sys
import types

import pytest


ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
CORE = os.path.join(ROOT, "core")
sys.path.insert(0, CORE)

_spec = importlib.util.spec_from_file_location(
    "check_xhs_login", os.path.join(ROOT, "bin", "check_xhs_login.py"))
check_login = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_login)

from xhs_config import PUBLISH_URL  # noqa: E402


class CDPError(Exception):
    pass


class ManagedPublisher:
    script: dict[str, list[object]] = {}
    cookie_response: dict | None = {}
    constructor_args: list[dict] = []
    evaluate_calls: list[str] = []

    def __init__(self, **kwargs) -> None:
        self.constructor_args = kwargs
        self.connect_called = False
        self.navigated_urls: list[str] = []
        self.sent_commands: list[tuple[str, dict]] = []
        self.disconnected = False

    def connect(self) -> None:
        self.connect_called = True

    def _navigate(self, url: str) -> None:
        self.navigated_urls.append(url)

    def _evaluate(self, snippet: str) -> object:
        self.evaluate_calls.append(snippet)
        return self.script[snippet].pop(0)

    def _send(self, command: str, params: dict) -> object:
        self.sent_commands.append((command, params))
        return self.cookie_response

    def disconnect(self) -> None:
        self.disconnected = True


def _fake_chrome_launcher() -> types.ModuleType:
    module = types.ModuleType("chrome_launcher")
    calls: list[tuple[str, int]] = []

    def ensure_chrome(port: int, headless: bool) -> bool:
        calls.append(("ensure_chrome", port))
        return True

    def is_port_open(port: int) -> bool:
        calls.append(("is_port_open", port))
        return False

    def kill_chrome(port: int) -> None:
        calls.append(("kill_chrome", port))

    module.ensure_chrome = ensure_chrome
    module.is_port_open = is_port_open
    module.kill_chrome = kill_chrome
    module.calls = calls
    return module


@pytest.fixture()
def fake_dependencies() -> list[tuple[str, int]]:
    saved: dict[str, object] = {}
    names = ("chrome_launcher", "tab_lifecycle", "cdp_publish")
    for name in names:
        saved[name] = sys.modules.get(name)

    chrome_module = _fake_chrome_launcher()
    lifecycle_module = types.ModuleType("tab_lifecycle")
    lifecycle_module.ManagedPublisher = ManagedPublisher
    cdp_module = types.ModuleType("cdp_publish")
    cdp_module.CDPError = CDPError
    sys.modules.update({
        "chrome_launcher": chrome_module,
        "tab_lifecycle": lifecycle_module,
        "cdp_publish": cdp_module,
    })

    ManagedPublisher.script = {}
    ManagedPublisher.cookie_response = {}
    ManagedPublisher.constructor_args = []
    ManagedPublisher.evaluate_calls = []
    yield chrome_module.calls

    for name in names:
        previous = saved[name]
        if previous is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous


def test_logged_in_stays_silent(fake_dependencies: list[tuple[str, int]]) -> None:
    ManagedPublisher.script = {
        "window.location.href": [PUBLISH_URL, PUBLISH_URL],
        "document.readyState": ["complete"],
    }

    rc = check_login.main()

    assert rc == 0
    assert ManagedPublisher.evaluate_calls.count("window.location.href") >= 2


def test_classic_login_redirect_fails(
    fake_dependencies: list[tuple[str, int]], capsys: pytest.CaptureFixture[str]
) -> None:
    login_url = "https://creator.xiaohongshu.com/login?redirect=%2Fpublish"
    ManagedPublisher.script = {
        "window.location.href": [login_url, login_url],
        "document.readyState": ["complete"],
    }

    rc = check_login.main()
    out = capsys.readouterr().out

    assert rc == 1
    assert "登录" in out


def test_captcha_without_login_word_fails(
    fake_dependencies: list[tuple[str, int]], capsys: pytest.CaptureFixture[str]
) -> None:
    captcha_url = "https://creator.xiaohongshu.com/captcha?x=1"
    ManagedPublisher.script = {
        "window.location.href": [captcha_url, captcha_url],
        "document.readyState": ["complete"],
    }

    rc = check_login.main()

    assert rc == 1


def test_unexpected_origin_fails(
    fake_dependencies: list[tuple[str, int]], capsys: pytest.CaptureFixture[str]
) -> None:
    other_url = "https://www.xiaohongshu.com/"
    ManagedPublisher.script = {
        "window.location.href": [other_url, other_url],
        "document.readyState": ["complete"],
    }

    rc = check_login.main()
    out = capsys.readouterr().out

    assert rc == 1
    assert other_url in out


def test_weak_network_retries_then_passes(
    fake_dependencies: list[tuple[str, int]],
) -> None:
    ManagedPublisher.script = {
        "window.location.href": ["", "", PUBLISH_URL, PUBLISH_URL],
        "document.readyState": ["", "", "complete"],
    }

    rc = check_login.main()

    assert rc == 0
    assert ManagedPublisher.evaluate_calls.count("window.location.href") >= 3


def test_failure_reports_cookie_count(
    fake_dependencies: list[tuple[str, int]], capsys: pytest.CaptureFixture[str]
) -> None:
    login_url = "https://creator.xiaohongshu.com/login"
    ManagedPublisher.script = {
        "window.location.href": [login_url, login_url],
        "document.readyState": ["complete"],
    }
    ManagedPublisher.cookie_response = {"cookies": [{}, {}]}

    rc = check_login.main()
    out = capsys.readouterr().out

    assert rc == 1
    assert "Cookie" in out
    assert "2" in out
