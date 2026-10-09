#!/usr/bin/env python3
"""检查器共享原语 —— emoji 判定 + 容错 JSON 读。

从三个检查器（bin/check_xhs_pipeline.py、bin/check_content_quality.py、
core/content_regression.py）抽出重复实现（S3）。

注意：调用方的输出形态不同（pipeline 用 problems 硬门，quality 用评分表），
本模块只提供原语，不决定输出形态。
"""
import json
import unicodedata


def has_emoji(s: str) -> bool:
    """So = 符号，Sk = 肤色修饰符。

    只查 So 会漏掉 👍🏽（So + Sk）这类带肤色的 emoji。
    """
    return any(unicodedata.category(c) in ("So", "Sk") for c in s)


def load_json_tolerant(path, default=None, on_error=None):
    """容错读 JSON。

    path 不存在 → 返回 default，不调 on_error。
    其他异常 → 调 on_error(path, exc)（若给了），仍返回 default。

    default 由调用方决定：pipeline/regression 传 {} 并记 problems，
    quality 传 None 静默 —— 三种语义由调用方保留，本函数不做取舍。
    """
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except Exception as e:
        if on_error is not None:
            on_error(path, e)
        return default
