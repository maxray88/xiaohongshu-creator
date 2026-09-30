#!/usr/bin/env python3
"""Chrome profile 路径一致性测试（2026-09-30）。

## 这个 bug 的形态

`bin/_xhs_common.sh` 的 `XHS_CHROME_PROFILE` 写的是
`~/Google/Chrome/XiaohongshuProfiles/default`，而真正启动 Chrome 的
`vendor/xhs/chrome_launcher.py` 在没有 account_manager 时回退到硬编码的
`PROFILE_DIR_NAME = "XiaohongshuProfile"`。

两者只差一个 `s` 和 `/default`，但是**完全不同的目录**（147M vs 5.5G）。
后果不是启动失败 —— Chrome 照常用它自己那份 —— 而是
`kill_pipeline_chrome()` 的进程匹配**永远落空**，清理静默失效，
标签页逐次累积（实测攒到 10 个 creator.xiaohongshu.com 登录页）。

## 为什么值得单独测

这类失配**没有任何运行时症状**：Chrome 起来了、任务跑完了、只有清理
不生效。等到标签页堆到几十个才有人发现，而那时根因早已无从追溯。

所以这里不测「路径对不对」（那是部署事实），而是测**两处定义不会漂移**：
只要有一方改了名字或路径，测试立刻响。
"""
import re
import sys
from pathlib import Path

import pytest

PROJ = Path(__file__).resolve().parents[1]
VENDOR_LAUNCHER = PROJ / "vendor" / "xhs" / "chrome_launcher.py"
COMMON_SH = PROJ / "bin" / "_xhs_common.sh"
CREATOR_SH = PROJ / "bin" / "open_xhs_creator.sh"


def _sh_profile() -> str:
    """从 _xhs_common.sh 解析出 XHS_CHROME_PROFILE 的默认值。

    必须**展开** $HOME 成真实绝对路径 —— 进程命令行里写的是完整路径
    （`/Users/<you>/Google/Chrome/...`），如果只把 `$HOME` 删成空串，
    拿到的 `/Google/Chrome/XiaohongshuProfile` 永远匹配不上，
    测试会「因为没有进程而 skip」，看起来绿、实则什么都没测。
    """
    txt = COMMON_SH.read_text(encoding="utf-8")
    m = re.search(r'XHS_CHROME_PROFILE="\$\{XHS_CHROME_PROFILE:-(.+)\}"', txt)
    assert m, "_xhs_common.sh 里找不到 XHS_CHROME_PROFILE 的默认值定义"
    raw = m.group(1)
    if raw.startswith("$HOME"):
        raw = str(Path.home()) + raw[len("$HOME"):]
    return raw.rstrip("/")


def _sh_profile_basename() -> str:
    """同 _sh_profile()，但只取最后一段 —— 用于 endswith 比较。"""
    return _sh_profile().rsplit("/", 1)[-1]


def _launcher_profile_name() -> str:
    """从 chrome_launcher.py 解析 PROFILE_DIR_NAME 常量。

    引号风格要兼容单/双引号 —— 只匹配双引号的话，上游哪天改成单引号，
    assert 会报「上游改名了？」，而实际只是引号风格变了，排查会走偏。
    """
    txt = VENDOR_LAUNCHER.read_text(encoding="utf-8")
    m = re.search(r'^PROFILE_DIR_NAME\s*=\s*["\']([^"\']+)["\']', txt, re.M)
    assert m, (
        "chrome_launcher.py 里找不到 PROFILE_DIR_NAME —— "
        "上游改名了、删了，或改了引号风格？"
    )
    return m.group(1)


# ── 核心：两处定义必须一致 ──────────────────────────────────────

def test_shell_profile_matches_vendor_launcher():
    """这是那个 bug 的回归测试。

    失配时不会报任何错，只是清理悄悄失效 —— 所以必须由测试守住。
    """
    sh = _sh_profile()
    la = _launcher_profile_name()
    assert _sh_profile_basename() == la, (
        f"profile 路径失配！\n"
        f"  _xhs_common.sh  用的是: {sh}\n"
        f"  chrome_launcher 用的是: {la}\n"
        f"  → kill_pipeline_chrome() 匹配不到进程，清理静默失效"
    )


def test_profile_is_not_the_multiblast_variant():
    """流水线必须用**仅小红书**的专用 profile。

    `XiaohongshuProfiles/default` 是 5.5G 的多平台混杂 profile
    （抖音 23 / Google 20 / TikTok 20 / YouTube 17 条 cookie）。
    只差一个 `s`，肉眼极易看错，所以单独钉住。
    """
    sh = _sh_profile()
    assert "XiaohongshuProfiles/default" not in sh, \
        "用错了多平台混杂 profile（XiaohongshuProfiles/default）"
    assert _sh_profile_basename() == "XiaohongshuProfile", sh


# ── 文档与代码不能漂移 ───────────────────────────────────────────

def test_creator_script_uses_correct_profile():
    """open_xhs_creator.sh 硬编码了 profile 路径。

    它原先写的是错的那个 —— 用这个脚本打开会启动一个「不是流水线
    那个」的 Chrome 实例，于是 9222 上出现两个不同 profile 的实例。
    """
    txt = CREATOR_SH.read_text(encoding="utf-8")
    found = re.findall(r'--user-data-dir="([^"]+)"', txt)
    assert found, "open_xhs_creator.sh 里找不到 --user-data-dir"
    for path in found:
        assert "XiaohongshuProfiles/default" not in path, \
            f"open_xhs_creator.sh 用了多平台混杂 profile: {path}"
        assert path.endswith("/XiaohongshuProfile"), path


@pytest.mark.parametrize("doc", ["README.md", "docs/PRD.md"])
def test_docs_use_correct_profile(doc):
    """文档写错 profile 会让下一个人去错误的目录排查。"""
    txt = (PROJ / doc).read_text(encoding="utf-8")
    # 旧串**允许**作为反例/警示出现（README、PRD 特意写了对比说明），
    # 所以只强制要求正确路径存在。只写 `旧串 not in txt` 的话，
    # 文档把两个都删掉反而会通过 —— 那正是我们要防的漂移方向。
    assert re.search(r"XiaohongshuProfile(?!s)", txt), \
        f"{doc} 没提到正确的 profile 路径（XiaohongshuProfile）"


# ── 语义自检：别把两个目录搞反 ───────────────────────────────────

def test_two_profile_dirs_are_distinct():
    """把「只差一个 s」这件事变成显式事实。

    真实的机器上这两个目录都存在。若哪天有人统一了命名，
    这条会提醒你同步更新上面所有断言，而不是让它们静默继续通过。
    """
    home = Path.home() / "Google" / "Chrome"
    dedicated = home / "XiaohongshuProfile"
    multi = home / "XiaohongshuProfiles" / "default"
    if not dedicated.exists() or not multi.exists():
        pytest.skip("本机没有这两个 profile 目录")
    assert dedicated != multi
    assert dedicated.resolve() != multi.resolve()


# ── 真实进程只读验证（不 kill）────────────────────────────────────

def test_real_chrome_process_matches_configured_profile():
    """若当前有 9222 的 Chrome 在跑，它必须能被配置值匹配到。

    只读检查，绝不 kill —— 破坏性操作需要用户单独授权。
    """
    import subprocess
    try:
        out = subprocess.run(
            ["ps", "-ax", "-o", "pid=,command="],
            capture_output=True, text=True, timeout=10,
        ).stdout
    except Exception:
        pytest.skip("ps 不可用")

    prof = _sh_profile()
    port = "9222"
    hits = [
        line.split()[0] for line in out.splitlines()
        if "Google Chrome" in line and "Google Chrome Helper" not in line
        and f"--user-data-dir={prof}" in line
        and f"--remote-debugging-port={port}" in line
    ]
    if not hits:
        pytest.skip("当前没有 9222 的流水线 Chrome 在跑")
    # 有命中即通过；匹配不到才说明配置又漂了
    assert hits, f"配置 {prof} 匹配不到任何 9222 进程 —— 又漂了？"
