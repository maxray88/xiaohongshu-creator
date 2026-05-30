"""
Human-like interaction helpers shared across xiaohongshu-creator scripts.

Provides async simulations for mouse movement, clicks, typing, and screenshots
used by the anti-detection flows in xhs_publish.py and friends.
"""
from __future__ import annotations

import asyncio
import os
import random
import time as time_module
from typing import Optional


# ── Async human primitives ─────────────────────────────────────────────────────


async def human_delay(min_s: float = 0.5, max_s: float = 2.0) -> None:
    """Random pause between actions."""
    await asyncio.sleep(random.uniform(min_s, max_s))


async def bezier_move(page, end_x: int, end_y: int, steps: Optional[int] = None) -> None:
    """Move the mouse along a Bezier curve to mimic human movement."""
    from xhs_config import BEZIER_STEPS_RANGE, DEFAULT_MOVE_DELAY_S, VIEWPORT

    if steps is None:
        steps = random.randint(*BEZIER_STEPS_RANGE)

    viewport = page.viewport_size or VIEWPORT
    start_x = random.randint(200, max(201, viewport["width"] - 100))
    start_y = random.randint(100, max(101, viewport["height"] - 100))

    dx, dy = end_x - start_x, end_y - start_y
    cp1x = start_x + dx * random.uniform(0.2, 0.5) + random.uniform(-60, 60)
    cp1y = start_y + dy * random.uniform(0.1, 0.4) + random.uniform(-60, 60)
    cp2x = start_x + dx * random.uniform(0.5, 0.8) + random.uniform(-60, 60)
    cp2y = start_y + dy * random.uniform(0.5, 0.9) + random.uniform(-60, 60)

    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        x = (
            u**3 * start_x
            + 3 * u**2 * t * cp1x
            + 3 * u * t**2 * cp2x
            + t**3 * end_x
        )
        y = (
            u**3 * start_y
            + 3 * u**2 * t * cp1y
            + 3 * u * t**2 * cp2y
            + t**3 * end_y
        )
        await page.mouse.move(int(x), int(y))
        await asyncio.sleep(random.uniform(*DEFAULT_MOVE_DELAY_S))

    # Small overshoot ~30% of the time
    if random.random() < 0.3:
        await page.mouse.move(end_x + random.randint(-5, 5), end_y + random.randint(-5, 5))
        await asyncio.sleep(random.uniform(0.03, 0.12))
        await page.mouse.move(end_x, end_y)
        await asyncio.sleep(random.uniform(0.03, 0.10))


async def human_click(page, x: int, y: int) -> None:
    """Click at screen coordinates after a Bezier approach."""
    from xhs_config import DEFAULT_CLICK_DELAY_S

    await bezier_move(page, x, y)
    await asyncio.sleep(random.uniform(*DEFAULT_CLICK_DELAY_S))
    await page.mouse.down()
    await asyncio.sleep(random.uniform(0.10, 0.30))
    await page.mouse.up()
    await asyncio.sleep(random.uniform(0.05, 0.15))


async def human_click_element(page, element, steps: Optional[int] = None) -> None:
    """Click a Playwright locator/element with human-like movement."""
    await element.scroll_into_view_if_needed()
    await asyncio.sleep(random.uniform(0.1, 0.3))
    box = await element.bounding_box()
    if not box:
        await element.click()
        return
    x = int(box["x"] + box["width"] / 2)
    y = int(box["y"] + box["height"] / 2)
    await human_click(page, x, y)


async def human_type_text(
    page,
    element,
    text: str,
    char_delay: tuple[float, float] = (0.04, 0.12),
) -> None:
    """Type text character-by-character with randomized delays."""
    await element.click()
    await asyncio.sleep(random.uniform(0.15, 0.4))
    await page.keyboard.press("Control+a")
    await asyncio.sleep(random.uniform(0.05, 0.15))
    await page.keyboard.press("Backspace")
    await asyncio.sleep(random.uniform(0.08, 0.2))
    for char in text:
        await page.keyboard.type(char, delay=random.uniform(*char_delay))
        await asyncio.sleep(random.uniform(0.005, 0.02))
    await asyncio.sleep(random.uniform(0.1, 0.3))


# ── Browser chrome helpers ─────────────────────────────────────────────────────


async def bring_chrome_to_front() -> None:
    """Bring Google Chrome to the foreground on macOS."""
    import subprocess

    try:
        subprocess.run(
            ['osascript', '-e', 'tell application "Google Chrome" to activate'],
            timeout=5,
            capture_output=True,
        )
    except Exception:
        pass


# ── Screenshot helpers ─────────────────────────────────────────────────────────


def screenshot_path(name: str, directory: Optional[str] = None) -> str:
    """Build a timestamped screenshot path under ``directory``."""
    from xhs_config import SCREENSHOT_DIR

    directory = directory or SCREENSHOT_DIR
    os.makedirs(directory, exist_ok=True)
    return os.path.join(directory, f"{name}_{int(time_module.time())}.png")


async def screenshot(page, name: str, directory: Optional[str] = None) -> str:
    """Take a screenshot and return the file path."""
    path = screenshot_path(name, directory)
    await page.screenshot(path=path)
    return path


# ── Sync click fallback helpers ────────────────────────────────────────────────


def force_click(page, selector: str) -> None:
    """Click with force=True, falling back to JS click on failure."""
    import time

    try:
        page.click(selector, force=True, timeout=5000)
    except Exception:
        page.evaluate(
            "() => { const el = document.querySelector(arg); if (el) el.click(); }",
            selector,
        )
        time.sleep(1)


def js_click(page, selector: str) -> None:
    """JS click without Playwright selector (for tricky elements)."""
    import time

    page.evaluate("() => { const el = document.querySelector(arg); if (el) el.click(); }", selector)
    time.sleep(1)
