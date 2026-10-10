#!/usr/bin/env python3
"""S4 配置与 IO 集中回归测试（core/xhs_config.py + core/io_utils.py）。

锁住三件事：
1. 共享常量的值（CDP 9222 是本项目唯一正确的调试端口，9224 是其他平台环境）；
2. atomic_write_json 的 roundtrip + 失败原子性（写坏不破坏原文件、不留 .tmp）；
3. 防分叉：标题阈值不再有裸 18 字面量比较，_atomic_write_json 只剩一处定义。

运行：python3 -m pytest tests/test_config_and_io.py -v（项目根目录）
"""
import json
import re
import sys
from pathlib import Path

import pytest

PROJ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJ / "core"))


def test_config_values():
    from xhs_config import CDP_HOST, CDP_PORT, PUBLISH_URL, TITLE_MAX, CONTENT_MIN, CONTENT_MAX
    assert CDP_HOST == "127.0.0.1"
    assert CDP_PORT == 9222              # 9224 是其他平台环境
    assert PUBLISH_URL.startswith("https://creator.xiaohongshu.com/publish/publish")
    assert TITLE_MAX == 18
    assert CONTENT_MIN == 400
    assert CONTENT_MAX == 900


def test_publish_guard_reexports_config():
    """from publish_guard import TITLE_MAX 仍可用（旧调用方不断）。"""
    import xhs_config as c
    from publish_guard import CONTENT_MAX, CONTENT_MIN, TITLE_MAX
    assert (TITLE_MAX, CONTENT_MIN, CONTENT_MAX) == (c.TITLE_MAX, c.CONTENT_MIN, c.CONTENT_MAX)


def test_atomic_write_json_roundtrip(tmp_path):
    from io_utils import atomic_write_json
    p = tmp_path / "x.json"
    atomic_write_json(str(p), {"t": "情绪树洞"})
    assert json.loads(p.read_text(encoding="utf-8"))["t"] == "情绪树洞"
    assert list(tmp_path.iterdir()) == [p]   # 无残留 .tmp 文件


def test_atomic_write_json_is_atomic_on_failure(tmp_path):
    """写坏对象时不应破坏已有文件，且不留 .tmp 残渣。"""
    from io_utils import atomic_write_json
    p = tmp_path / "x.json"
    atomic_write_json(str(p), {"good": 1})
    with pytest.raises(TypeError):
        atomic_write_json(str(p), {"bad": object()})   # 不可序列化
    assert json.loads(p.read_text(encoding="utf-8")) == {"good": 1}   # 原文件完好


def test_no_hardcoded_18_left():
    """标题阈值只剩 xhs_config 的常量定义，不该再有裸 18 比较。"""
    pat = re.compile(r"len\(\w+\)\s*(>|>=|<|<=|==|!=)\s*18\b")
    offenders = []
    for d in ("core", "bin"):
        for p in sorted((PROJ / d).glob("*.py")):
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                if pat.search(line):
                    offenders.append(f"{p.name}:{i}:{line.strip()}")
    assert offenders == []


def test_single_atomic_write_definition():
    """atomic 写只剩 io_utils 一处定义（旧 _atomic_write_json 已全部迁移）。"""
    defs = []
    pat = re.compile(r"def\s+_?atomic_write_json\s*\(")
    for d in ("core", "bin"):
        for p in sorted((PROJ / d).glob("*.py")):
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                if pat.search(line):
                    defs.append(f"{p.relative_to(PROJ)}:{i}")
    assert len(defs) == 1 and defs[0].startswith("core/io_utils.py:"), defs
