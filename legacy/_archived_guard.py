#!/usr/bin/env python3
"""legacy/ 冻结守卫 —— 防止历史脚本被误执行。

背景：legacy/ 下 33 个文件（含 publish_xhs_video.py、xhs_image_draft.py、
_cron_publish_video.py、debug_xhs_upload.py）语法完好、可直接运行，
且其中 4 个会**真的向小红书上传并保存草稿**。虽然 cron 与 bin/、core/
都零引用，但一次手滑的 `python3 legacy/publish_xhs_video.py`
就会往草稿箱塞一条内容不明的笔记。

这些脚本里嵌着 2026-08 前的账号上下文与选择逻辑，行为已不可控。

处理方式：不给它们改逻辑（历史存档应保持原样以便追溯），
而是在每个文件顶部插入「打印说明 + sys.exit(2)」的守卫，
由 legacy/_archived_guard.py 批量施加。

已知副作用（可接受）：守卫插在 shebang 之前，`./legacy/foo.py` 这种
直接执行方式会变成 exec format error 而非 exit 2 —— 仍然被拦住，
只是报错形式不同。实际调用方都用 `python3 <file>`，不受影响。

用法：
    python3 legacy/_archived_guard.py --stamp   # 施加守卫
    python3 legacy/_archived_guard.py --check   # 检查是否全部已标记
"""
import os
import sys

MARKER = "# ARCHIVED: 已被现行流水线取代，禁止运行 —— 见 legacy/README.md"

GUARD = '''"""
{marker}
运行本脚本会向小红书上传并保存草稿/发布内容，且行为已不可控（内含
2026-08 前的账号上下文与选择逻辑）。如需发布，请使用 bin/ 下的现行脚本。

sys.exit 拦在所有 import 之前。
"""
import sys as _sys
_sys.stderr.write(
    "\\n❌ {name} 已归档，禁止运行。\\n"
    "   现行发布脚本：bin/publish_xhs_video.sh / bin/publish_xhs_image.sh\\n"
    "   背景见 legacy/README.md\\n\\n"
)
_sys.exit(2)

'''


def has_marker(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            head = f.read(4096)
    except OSError:
        return False
    return MARKER in head


def stamp():
    n = 0
    for root, _dirs, files in os.walk(os.path.dirname(os.path.abspath(__file__))):
        for fn in files:
            if not fn.endswith(".py") or fn == os.path.basename(__file__):
                continue
            p = os.path.join(root, fn)
            if has_marker(p):
                continue
            try:
                with open(p, encoding="utf-8") as f:
                    src = f.read()
            except (OSError, UnicodeDecodeError):
                continue
            with open(p, "w", encoding="utf-8") as f:
                f.write(GUARD.format(marker=MARKER, name=fn) + src)
            print(f"  stamped: {os.path.relpath(p)}")
            n += 1
    print(f"stamped {n} file(s)")


def check():
    missing = []
    for root, _dirs, files in os.walk(os.path.dirname(os.path.abspath(__file__))):
        for fn in files:
            if not fn.endswith(".py") or fn == os.path.basename(__file__):
                continue
            p = os.path.join(root, fn)
            if not has_marker(p):
                missing.append(os.path.relpath(p))
    if missing:
        print(f"❌ {len(missing)} 个 legacy 文件缺少 ARCHIVED 标记:")
        for m in missing:
            print(f"   {m}")
        return 1
    print("✅ 所有 legacy 文件均已标记为归档")
    return 0


if __name__ == "__main__":
    sys.exit(stamp() if "--stamp" in sys.argv else check())
