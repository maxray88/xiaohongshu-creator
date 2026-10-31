#!/usr/bin/env python3
"""CDP 依赖模块的 import 路径 —— 全项目唯一入口。

## 为什么有这层间接

2026-09-27 之前，每个脚本各自写死路径（曾经长这样）：

    sys.path.insert(0, os.path.expanduser("~/.hermes/xhs_skills/scripts"))

一共 6 处（core/ 4 个 + bin/ 1 个 + tests/ 1 个）。那种写法有两个问题：

1. 依赖放在**项目外**，项目不自包含 —— 换台机器、少个目录，
   全部脚本在 import 阶段就炸，而且是在凌晨的 cron 里炸。
2. 路径改一次要改 6 处，漏一处就是一条只在特定分支上出现的 ImportError
   （这跟 2026-09-27 那次「同一段逻辑复制三处、补两处漏一处」是同一类错误）。

现在 CDP 模块统一 vendored 到 `vendor/xhs/`，本模块是它唯一的引用点。

## 注意解释器不在这里

Python **二进制依赖**（mlx / mlx-audio —— Qwen3-TTS 推理引擎、
playwright / websockets）装在 pyenv 3.11.15 全局环境
（`~/.pyenv/versions/3.11.15/bin/python3`），没有搬进项目 ——
那是几百 MB 的可执行文件，不该进 Git。shell 侧由
`bin/_xhs_common.sh` 的 `$XHS_PY` 指向它。

注：TTS 引擎 2026-10-12 切到 Qwen3-TTS VoiceDesign（本地 MLX 推理，因原云端
服务上游返回 403），所以 venv 里要装的是 `mlx` + `mlx-audio`。

**代码**（vendor/xhs/*.py）和**依赖**（venv/）是两件事，改一个不影响另一个。
"""
from __future__ import annotations

import os
import sys

# vendor/xhs/ —— 跟 core/ 平级，所以从本文件位置 ../vendor/xhs
PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENDOR_XHS = os.path.join(PROJ_ROOT, "vendor", "xhs")
CORE_DIR = os.path.join(PROJ_ROOT, "core")

# pyenv 3.11.15 全局环境（shell 侧 $XHS_PY 用的就是这个）
VENV_PYTHON = os.path.expanduser("~/.pyenv/versions/3.11.15/bin/python3")


def add_cdp_to_path() -> str:
    """把 vendor/xhs 和 core/ 放进 sys.path。

    返回 vendor/xhs 的绝对路径，方便调用方打印或断言。

    以 (0, ...) 优先级插入：项目内的实现必须优先于任何同名模块，
    否则一次手滑的 cwd 就能让 `import cdp_publish` 拿到别处的版本。
    """
    for p in (VENDOR_XHS, CORE_DIR):
        if p not in sys.path:
            sys.path.insert(0, p)
    return VENDOR_XHS
