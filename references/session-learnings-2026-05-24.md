# Session Learnings — 2026-05-24

## Critical Findings

### 1. Chrome Instance Isolation (IMPORTANT)
The `browser_navigate` tool and `xhs_login.py` use **completely separate Chrome instances** with different user data directories:
- `browser_navigate`: Chrome at `/var/folders/.../agent-browser-chrome-*/` (Hermes's own sandboxed instance)
- `xhs_login.py`: Chrome at `/tmp/chrome-debug/` (or `--user-data-dir` flag)
- **Cookies saved by `xhs_login` are NOT available to `browser_navigate`** — they are separate browser profiles

**Implication**: After running `xhs_login`, you cannot use `browser_navigate` with those cookies. The publish script (`xhs_publish.py`) connects via CDP to the Chrome instance that ran `xhs_login`, so it CAN use those cookies.

**Workaround**: For manual browser operations after login, use the Chrome instance opened by `xhs_login` directly (the window stays open).

### 2. IP Risk Restriction (BLOCKER)
XHS has IP-based security that can block server IPs:
- Error: `error_code=300012 IP存在风险，请切换可[^1]靠网络环境后重试`
- This means automation from this server is currently blocked
- When this happens, `browser_navigate` to creator.xiaohongshu.com shows login page even with valid cookies

**Workarounds**:
1. Complete verification in the Chrome window opened by `xhs_login` (the window has the real user session)
2. User manually publishes from their own Chrome browser
3. Run `xhs_login` on user's own machine (not this server)

### 3. xhs_login Timeout Requirements
`xhs_login.py` requires interactive QR code scan, which can take several minutes:
- 120s timeout: ❌ Too short (times out)
- 300s timeout: ❌ Too short (times out)  
- 600s timeout: ✅ Works (terminal tool, not execute_code)

**Fix**: Always use `terminal` tool with 600s timeout for `xhs_login`, not `execute_code`.

### 4. Chrome Debug Port Management
Before running `xhs_publish.py`, Chrome must be running with remote debugging:
- `lsof -i :9222` — check if port 9222 is listening
- If not running: start with `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug`
- Use `terminal` with `background=true` for the Chrome process

### 5. GitHub Token from ~/.hermes/.env
Pattern for reading GitHub credentials:
```python
env_path = os.path.expanduser("~/.hermes/.env")
with open(env_path) as f:
    for line in f:
        if line.startswith("GITHUB_TOKEN="):
            token = line.split("=",1)[1].strip()
            break
```

Then use with GitHub API:
```python
subprocess.run(["gh", "api", "repos", "-H", "Authorization: token "+token, ...])
```

### 6. Temp Files Not Persistent
`/tmp/xhs_day1/` was cleaned between sessions. Day1 content (post_data.json, covers) was lost.
**Fix**: Always regenerate content on session start, or better — read from the GitHub repo at `~/make-money-xiaohongshu_repo/` which was pushed this session.

## Day1 Content Regenerated
Re-generated Day1 content and cover at:
- `/tmp/xhs_day1/content/post_data.json`
- `/tmp/xhs_day1/covers/variant_1_final/cover.jpg`

This content is also committed to GitHub repo: `github.com/maxray88/make-money-xiaohongshu`

## Cron Jobs Created
- Day2-Day10: One-time content generation + publish jobs (job_ids: 160880a1241b through 98a736f76de8)
- 每周数据复盘: `2700d681ab03` (weekly)
- 每月策略调整: `702d223f572a` (monthly)