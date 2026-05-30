"""
Shared constants for all xiaohongshu-creator scripts.

Import everything from here instead of redefining per-file.
"""
from __future__ import annotations

import os

# ── Paths ──────────────────────────────────────────────────────────────────────

COOKIES_PATH: str = os.path.expanduser("~/.xiaohongshu-creator/cookies.json")
CDP_URL_FILE: str = "/tmp/xhs_cdp_url.txt"
SCREENSHOT_DIR: str = "/tmp/xhs_screenshots"
ENGAGEMENT_HISTORY_FILE: str = os.path.expanduser(
    "~/.xiaohongshu-creator/engagement_history.json"
)

# ── CDP ────────────────────────────────────────────────────────────────────────

DEFAULT_CDP_URL: str = "http://127.0.0.1:9222"
DEFAULT_CDP_ENDPOINT: str = DEFAULT_CDP_URL  # alias used by xhs_publish

# ── URLs ───────────────────────────────────────────────────────────────────────

# Creator platform
LOGIN_URL: str = "https://creator.xiaohongshu.com/login"
CREATOR_HOME: str = "https://creator.xiaohongshu.com/new/home"
NOTE_MANAGER_URL: str = "https://creator.xiaohongshu.com/new/note-manager"
INSPIRATION_URL: str = "https://creator.xiaohongshu.com/new/inspiration"
PUBLISH_URL: str = "https://creator.xiaohongshu.com/publish/publish?from=menu&target=image"

# Public platform (CDP mode)
PUBLIC_HOME: str = "https://www.xiaohongshu.com/new/home"
PUBLIC_SEARCH: str = "https://www.xiaohongshu.com/search_result?keyword={keyword}&source=web_search_result_notes"

# Login state detection
SUCCESS_URL_FRAGMENTS: list[str] = [
    "creator.xiaohongshu.com/publish",
    "creator.xiaohongshu.com/home",
    "creator.xiaohongshu.com/creator",
    "creator.xiaohongshu.com/new",
]

LOGIN_URL_FRAGMENTS: list[str] = [
    "creator.xiaohongshu.com/login",
    "creator.xiaohongshu.com/passport",
]

# ── Browser / Playwright defaults ──────────────────────────────────────────────

VIEWPORT: dict = {"width": 1280, "height": 900}
LOCALE: str = "zh-CN"
TIMEZONE: str = "Asia/Shanghai"
PAGE_TIMEOUT_MS: int = 60000
ELEMENT_TIMEOUT_MS: int = 5000
PAGE_NAV_WAIT_AFTER_S: float = 8.0  # fixed wait after commit; tune as needed

CHROME_LAUNCH_ARGS: list[str] = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-web-security",
    "--disable-features=IsolateOrigins,site-per-process",
    "--window-size=1280,900",
]

CHROME_HEADLESS_ARGS: list[str] = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
]

CHROME_USER_AGENT: str = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# ── Selectors ──────────────────────────────────────────────────────────────────

SELECTOR_COMMENT_INPUT: str = "#content-textarea"
SELECTOR_SEND_BTN: str = "button.btn.submit"
SELECTOR_LIKE_BTN: str = ".like-wrapper"
SELECTOR_NOTE_ITEM: str = ".note-item"
SELECTOR_TAB_ACTIVE: str = (
    ".tabs .tab.active, .tab-item.active, [class*='tab'][class*='active']"
)

# ── Anti-bot / human interaction defaults ─────────────────────────────────────

DEFAULT_CHAR_DELAY: tuple[float, float] = (0.04, 0.12)
DEFAULT_CLICK_DELAY_S: tuple[float, float] = (0.08, 0.25)
DEFAULT_MOVE_DELAY_S: tuple[float, float] = (0.003, 0.015)
BEZIER_STEPS_RANGE: tuple[int, int] = (20, 35)

# ── Publish defaults ───────────────────────────────────────────────────────────

PUBLISH_TITLE_MAX_CHARS: int = 20
PUBLISH_DEFAULT_TIMEOUT_MS: int = 30000
PUBLISH_WAIT_AFTER_NAV_S: tuple[float, float] = (3.0, 5.0)

# ── Category URLs (hashtag / inspiration) ─────────────────────────────────────

CATEGORY_URLS: dict[str, str] = {
    "全部": INSPIRATION_URL,
    "美食": f"{INSPIRATION_URL}?category=food",
    "美妆": f"{INSPIRATION_URL}?category=beauty",
    "时尚": f"{INSPIRATION_URL}?category=fashion",
    "出行": f"{INSPIRATION_URL}?category=travel",
    "知识": f"{INSPIRATION_URL}?category=knowledge",
    "兴趣爱好": f"{INSPIRATION_URL}?category=hobby",
}
