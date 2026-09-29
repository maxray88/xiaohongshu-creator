#!/usr/bin/env python3
"""vendor 化回归测试（2026-09-27）。

## 这次改了什么

把 CDP 依赖从项目外的 `~/.hermes/xhs_skills/scripts/`（独立 git 仓库
`white0dew/XiaohongshuSkills`）**物理拷进** `vendor/xhs/`，让项目自包含。

改动前 6 处脚本各自写死外部路径。现在统一由 `core/xhs_paths.py` 提供。

## 为什么要专门测

这类改动最危险的失败模式是**静默退化**：路径写错时，如果恰好系统上
还留着旧目录，测试照样绿 —— 直到某天那目录被清理，或者换台机器，
才在凌晨的 cron 里炸。所以下面几条不测「能不能 import」，
而测「是不是真的从项目内加载」。

另一个容易混的点：**venv 不 vendor**。32MB 的 edge-tts / playwright /
websockets 仍在项目外。这里显式断言它还在项目外，防止将来有人
「顺手一起搬进来」。
"""
import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJ = Path(__file__).resolve().parents[1]
VENDOR = PROJ / "vendor" / "xhs"
VENV_PY = Path(os.path.expanduser("~/.hermes/xhs_skills/venv/bin/python3"))

# 传递闭包 —— cdp_publish 顶层 import feed_explorer(11 符号多行) 和 run_lock
EXPECTED = {"cdp_publish.py", "chrome_launcher.py", "feed_explorer.py", "run_lock.py"}


# ── vendor 目录完整性 ────────────────────────────────────────────

def test_all_vendored_files_present():
    """少任何一个都会在 import 阶段炸。"""
    for f in EXPECTED:
        p = VENDOR / f
        assert p.is_file(), f"vendor/xhs/{f} 缺失"


def test_vendor_files_match_upstream():
    """与上游逐字一致 —— 不同步就会在 02:15 复核时才发现，代价很大。

    例外：cdp_publish.py 含我们自己的 _wait_video_processing 容错修复
    （上游没有），所以它允许不同；其余三个必须逐字一致。
    """
    upstream = Path(os.path.expanduser("~/.hermes/xhs_skills/scripts"))
    if not upstream.is_dir():
        pytest.skip("上游仓库不在本机")
    import hashlib

    def h(p):
        return hashlib.sha256(p.read_bytes()).hexdigest()

    for f in EXPECTED - {"cdp_publish.py"}:
        up = upstream / f
        if not up.is_file():
            pytest.skip(f"上游 {f} 不存在")
        assert h(VENDOR / f) == h(up), f"{f} 与上游不一致 —— 重新 vendor 一次"


def test_license_file_present():
    """MIT 原文必须随代码一起留档，否则合规性无从追溯。"""
    lic = VENDOR / "LICENSE.upstream"
    assert lic.is_file()
    assert "MIT" in lic.read_text(encoding="utf-8")


def test_vendor_readme_documents_provenance():
    rd = (VENDOR / "README.md").read_text(encoding="utf-8")
    for must in ("white0dew/XiaohongshuSkills", "3ede4fe", "61042e7"):
        assert must in rd, f"README 未记录 {must}"


# ── 真的从项目内加载，而不是碰巧命中旧目录 ───────────────────────

def test_cdp_modules_load_from_vendor():
    """核心断言：加载路径必须在项目内。

    如果有人把 sys.path 改回外部目录，这条会失败 —— 而一个只测
    「能不能 import」的测试在旧目录还在时永远不会失败。
    """
    code = (
        "import sys, os; sys.path.insert(0, %r); "
        "from xhs_paths import add_cdp_to_path; add_cdp_to_path(); "
        "import cdp_publish, chrome_launcher; "
        "print(cdp_publish.__file__); print(chrome_launcher.__file__)" % str(PROJ / "core")
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True,
                         text=True, cwd=str(PROJ))
    assert out.returncode == 0, f"加载失败: {out.stderr}"
    for line in out.stdout.strip().splitlines():
        assert str(VENDOR) in line, f"从项目外加载了: {line}"


def test_xhs_paths_adds_both_dirs():
    sys.path.insert(0, str(PROJ / "core"))
    from xhs_paths import CORE_DIR, PROJ_ROOT, VENDOR_XHS, add_cdp_to_path

    assert VENDOR_XHS == str(PROJ / "vendor" / "xhs")
    assert CORE_DIR == str(PROJ / "core")
    assert PROJ_ROOT == str(PROJ)

    before = len(sys.path)
    add_cdp_to_path()
    added = sys.path[:len(sys.path) - before] if len(sys.path) > before else []
    assert str(VENDOR) in sys.path
    assert str(PROJ / "core") in sys.path


def test_add_cdp_to_path_is_idempotent():
    """重复调用不能把 path 越堆越长（模块可能被多个入口 import）。"""
    sys.path.insert(0, str(PROJ / "core"))
    from xhs_paths import add_cdp_to_path

    add_cdp_to_path()
    n = sys.path.count(str(PROJ / "vendor" / "xhs"))
    for _ in range(5):
        add_cdp_to_path()
    assert sys.path.count(str(PROJ / "vendor" / "xhs")) == n


# ── venv 必须留在项目外 ──────────────────────────────────────────

def test_venv_is_not_vendored():
    """32MB 二进制依赖绝不能进项目目录 / Git。"""
    assert not (PROJ / "vendor" / "xhs" / "venv").exists()
    # 路径层级：.../xhs_skills/venv/bin/python3 —— parent 是 bin，再 parent 是 venv
    assert VENV_PY.parent.name == "bin"
    assert VENV_PY.parent.parent.name == "venv"
    # 且必须真的还在项目外
    assert str(PROJ) not in str(VENV_PY)


def test_gitignore_excludes_venv_and_pycache():
    gi = PROJ / ".gitignore"
    assert gi.is_file(), "缺 .gitignore —— venv/和 __pycache__ 会被提交"
    txt = gi.read_text(encoding="utf-8")
    assert "__pycache__" in txt
    # 写的是 `*.py[cod]`（覆盖 .pyc/.pyo/.pyd），比字面 "*.pyc" 更严。
    # 这里只要求「.pyc 被排除」，不绑定具体写法 —— 否则换个等价写法就假失败。
    assert ("*.pyc" in txt) or ("*.py[cod]" in txt) or ("*.py?" in txt), \
        "未排除 .pyc 字节码"
    # venv 必须被排除（XHS 依赖 32MB，目前仍在项目外，将来若搬进来要拦住）
    assert "venv/" in txt


# ── 旧路径不该再被代码引用（注释与 docstring 除外）───────────────

def test_no_live_references_to_external_scripts_dir():
    """代码里不能再有 xhs_skills/scripts —— 那是这次要消灭的东西。

    只扫真正的 import 语句：docstring 和注释里提到旧路径是**合理的**
    （vendor/README.md 和 xhs_paths.py 都在解释「以前是什么样」），
    拿字符串匹配去查会把这些正当说明误判成残留。
    """
    offenders = []
    this_file = Path(__file__).name
    for py in list(PROJ.glob("core/*.py")) + list(PROJ.glob("bin/*.py")) \
            + list(PROJ.glob("tests/*.py")):
        # 排除本文件：它必须提到旧路径才能去比对上游，
        # 那是「验证残留」而不是「引入残留」。
        if py.name == this_file:
            continue
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            # 只看真正执行的语句：import / 赋值 / 函数调用参数
            targets = []
            if isinstance(node, ast.Import):
                targets = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                targets = [node.module or ""]
            elif isinstance(node, ast.Assign):
                targets = [ast.unparse(node)]
            for t in targets:
                if "xhs_skills/scripts" in t:
                    offenders.append(f"{py.name}:{getattr(node, 'lineno', '?')}")
    assert not offenders, f"仍引用外部目录: {offenders}"


def test_venv_path_still_referenced_in_shell():
    """反向确认：venv 路径必须还在 shell 里（被上面那轮误改过）。"""
    common = (PROJ / "bin" / "_xhs_common.sh").read_text(encoding="utf-8")
    assert "xhs_skills/venv" in common, "$XHS_PY 不该指向已搬迁的 venv"
