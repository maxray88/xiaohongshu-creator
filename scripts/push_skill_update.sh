#!/bin/bash
# Push xiaohongshu-creator skill updates to GitHub
cd ~/.hermes/skills/xiaohongshu-creator
git add -A
git commit -m "skill update: xhs_engage fix + new troubleshooting entries

- Fixed xhs_engage.py auto-engage note card click → navigation flow
- Root cause: getBoundingClientRect() returns nan for .note-item
- Fix: use offsetWidth/offsetHeight for card dimensions
- Navigation: page.mouse.click() instead of page.goto() (returns 404)
- Added wait_for_selector() before like/comment interactions
- Updated SKILL.md troubleshooting with 4 new entries
- Updated session-learnings-2026-05-19.md with complete findings
- Key Python Playwright gotcha: no arguments[0] syntax in page.evaluate()"
git push origin main
