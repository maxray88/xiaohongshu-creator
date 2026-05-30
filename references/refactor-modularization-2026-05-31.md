# Refactor: Shared Module Modularization (2026-05-31)

## What changed

Three new shared modules were introduced to eliminate ~80+ lines of copy-paste
across `xhs_login.py`, `xhs_analytics.py`, `xhs_comments.py`, and `xhs_engage.py`:

```
scripts/
├── xhs_config.py   # All constants (URLs, paths, selectors, timeouts)
├── xhs_browser.py  # Cookie I/O, CDP resolution, browser factory
└── xhs_utils.py    # Human-like delays, screenshots, force_click fallback
```

### Module contracts

`xhs_config.py` — single source of truth for:
- `COOKIES_PATH`, `SCREENSHOT_DIR`, `ENGAGEMENT_HISTORY_FILE`
- `CREATOR_HOME`, `NOTE_MANAGER_URL`, `INSPIRATION_URL`, `PUBLISH_URL`, `PUBLIC_HOME`, `PUBLIC_SEARCH` (template string)
- `LOGIN_URL_FRAGMENTS`, `SUCCESS_URL_FRAGMENTS`
- `CHROME_LAUNCH_ARGS`, `VIEWPORT`, `LOCALE`, `PAGE_TIMEOUT_MS`, `PAGE_NAV_WAIT_AFTER_S`
- `SELECTOR_*` constants for all shared selectors
- `CATEGORY_URLS` dict for hashtag/inspiration scraping

`xhs_browser.py` — shared helpers:
- `load_cookies(file)` — unified error handling + sys.exit
- `save_cookies(context, file)` — persists cookies with UTF-8
- `resolve_cdp_ws_url(endpoint)` — HTTP `/json/version` → ws URL
- `is_logged_in(page)` / `wait_for_login(page, minutes, manual)` — login detection
- `make_browser_page(cookies, headless, cdp_url, chrome_bin)` — sync factory returning `(browser, context, page)`
- `make_browser_page_async(...)` — async factory for `xhs_publish.py`
- `goto_and_wait(page, url, wait)` — commute + login check idiom

`xhs_utils.py` — shared interaction helpers:
- `human_delay(min_s, max_s)` / `bezier_move(page, x, y)` / `human_click(page, x, y)`
- `human_click_element(page, element)` / `human_type_text(page, element, text)`
- `bring_chrome_to_front()` — AppleScript, macOS only
- `screenshot_path(name)` / `screenshot(page, name)` — timestamped shots
- `force_click(page, selector)` — `force=True` + JS fallback in one call

### Import convention

Each script adds its own `scripts/` directory to `sys.path` at startup so the
package-style imports work regardless of working directory:

```python
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
```

Then:
```python
from xhs_config import CREATOR_HOME, SELECTOR_SEND_BTN
from xhs_browser import load_cookies, make_browser_page
from xhs_utils import force_click
```

All new script imports follow this convention. Do not use relative imports.

### What each script lost (safe removal targets)

| Removed from | Lines saved | Why safe to remove |
|---|---|---|
| `xhs_login.py` | ~60 | `is_logged_in`, `wait_for_login`, `save_cookies` body, URL constants, SUCCESS_URLS, LOGIN_URLS moved to `xhs_browser.py`/`xhs_config.py` |
| `xhs_analytics.py` | ~20 | `load_cookies()` duplicate removed; `re()` local import replaced with top-level; `HOME_URL`/`NOTE_MANAGER_URL` from config |
| `xhs_comments.py` | ~30 | `load_cookies()`, CDP connect boilerplate, duplicate comment-posting flow replaced with shared helpers |
| `xhs_engage.py` | ~40 | `load_cookies()`, CDP connect, inline login checks, click fallbacks replaced |

### Bug fixes embedded in the refactor

1. **xhs_login.py double `browser.close()`** — timeout branch already closed browser; success path tried to close again. Removed the redundant close at end, added explicit close only in `else` failure branch.
2. **xhs_analytics.py `import re` inside `re_match()`** — local import on every call; moved `import re` to top of file.
3. **URL inconsistency** — `xhs_publish.py` used `www.xiaohongshu.com/new/home` while others used `creator.xiaohongshu.com/new/home`. Now both exist as distinct constants in `xhs_config.py` (`PUBLIC_HOME` vs `CREATOR_HOME`); every script imports the correct one.
4. **Scripts without required `import json` after refactor** — `xhs_analytics.py` and `xhs_engage.py` lost their top-level `json` imports during refactor; restored.

### Not touched (out of scope for this refactor)

`xhs_publish.py`, `xhs_hashtags.py`, `render_covers.py`, `cron_notify.py`
still declare their own constants and helpers. Revisit when editing any of
those scripts — first import `xhs_config`/`xhs_browser` if touching them.
