#!/usr/bin/env python3
"""Tab 生命周期管理 —— 修 M3「Tab 泄漏」。

## 问题

`vendor/xhs/cdp_publish.py` 的 `_find_or_create_tab()`（L522-568）默认
`reuse_existing_tab=False`，走 L553-562 **无条件新建标签页**；而
`connect()`（L570-581）拿到 ws_url 后**不记录自己建了哪个**，
`disconnect()`（L583-587）只关 WebSocket 连接、**不关标签页**。

后果：每跑一次 cron 就在 9222 的 Chrome 上留一个标签页，永不回收。
2026-09-30 实测堆到 11 个（全是 `creator.xiaohongshu.com/login?...401`，
即每次发布尝试失败后留下的）。它自己不报错，只是慢慢堆积 —— 直到
Chrome 被塞满标签才有人发现，而那时根因早已无从追溯。

## 为什么不在 vendor 里改

`vendor/xhs/` 是上游 `white0dew/XiaohongshuSkills` 的逐字快照（MIT）。
在那里加逻辑会让它与上游分叉，将来 `git pull` 同步时冲突（详见
`vendor/xhs/README.md`）。所以本模块用**继承 + 覆写**的方式在项目侧
包一层，vendor 保持原样。

## 为什么必须「只关自己建的」

盲目关所有 xiaohongshu 标签页会误伤用户自己打开的创作页面 —— 用户
可能正开着草稿编辑器手工调整内容。`disconnect()` 只关闭**本次
connect 期间由本库新建的**那一个，其余一律不动。
"""
from __future__ import annotations

import re


def _tab_id_from_ws_url(ws_url: str) -> str:
    """从 ws://127.0.0.1:9222/devtools/page/<ID> 提取 <ID>。

    Chrome 早期用十六进制 targetId，新版用 32 位大写 hex；两种都能
    直接当作 `/json/close/<ID>` 的路径参数用。
    """
    m = re.search(r"/devtools/page/([0-9A-Za-z]+)", ws_url or "")
    return m.group(1) if m else ""


class ManagedPublisher:
    """`XiaohongshuPublisher` 的 tab 生命周期包装。

    用法与原类完全一致，只是 `disconnect()` 之后会顺带关掉自己新建的
    标签页：

        pub = ManagedPublisher(host="127.0.0.1", port=9222)
        try:
            pub.connect()
            ...
        finally:
            pub.disconnect()      # 关连接 + 关自己开的标签页

    `created_tab_id` 为空表示复用了已有标签页（`reuse_existing_tab=True`
    或指定了 `target_url_prefix`），此时 disconnect 不会关任何页面。

    ## 已知边界：prefix 回退新建时会漏关

    vendor 的 `_find_or_create_tab`（L540-543）在给了 `target_url_prefix`
    却找不到匹配页时，会继续往下走到 L553-562 **新建**标签页。本包装在
    `target_url_prefix` 非空时跳过认领，所以那种情况下新建的 tab 不会被关。

    2026-09-30 核实：5 个生产调用点全部是 `pub.connect()` 无参调用，
    该路径当前不可达。若将来有人传 prefix，需要改成按 ws_url 反查认领。
    """

    def __init__(self, *args, **kwargs):
        # 延迟 import：调用方需先 xhs_paths.add_cdp_to_path()
        from cdp_publish import XiaohongshuPublisher

        self._pub = XiaohongshuPublisher(*args, **kwargs)
        self.created_tab_id: str = ""

    def __getattr__(self, name):
        """其余属性/方法原样转发，不做包装。

        只对 `_pub` 自身抛 AttributeError：若 `_pub` 不存在（例如
        `copy`/`deepcopy`/`pickle` 绕过 __init__ 重建对象），转发会变成
        `getattr(self._pub, ...) → __getattr__('_pub') → …` 无限递归，
        报出难以定位的 RecursionError。

        注意**不能**笼统拦所有下划线开头的名字 —— `_send` / `_evaluate` /
        `_navigate` 都要转发，它们才是生产代码真正调用的接口。
        """
        if name == "_pub":
            raise AttributeError(name)
        return getattr(self._pub, name)

    def connect(self, target_url_prefix: str = "", reuse_existing_tab: bool = False):
        before = self._pub._get_targets()
        before_ids = {
            t.get("id") for t in before
            if t.get("type") == "page" and t.get("webSocketDebuggerUrl")
        }

        result = self._pub.connect(
            target_url_prefix=target_url_prefix,
            reuse_existing_tab=reuse_existing_tab,
        )

        # 只有「本来没有、connect 之后有了」才算我们新建的
        if not target_url_prefix and not reuse_existing_tab:
            after = self._pub._get_targets()
            new_pages = [
                t for t in after
                if t.get("type") == "page"
                and t.get("webSocketDebuggerUrl")
                and t.get("id") not in before_ids
            ]
            if len(new_pages) == 1:
                self.created_tab_id = new_pages[0].get("id", "")

        return result

    def disconnect(self):
        """关连接，然后关掉自己新建的标签页（如果有）。

        关标签页失败**不影响**连接关闭，也不抛出 —— 清理是尽力而为，
        绝不能因为它把调用方的正常流程变成异常。
        """
        try:
            self._pub.disconnect()
        finally:
            self._close_created_tab()

    def _close_created_tab(self) -> bool:
        tab_id = self.created_tab_id
        if not tab_id:
            return False
        self.created_tab_id = ""  # 幂等：重复 disconnect 不会重复关
        host = getattr(self._pub, "host", "127.0.0.1")
        port = getattr(self._pub, "port", 9222)
        try:
            import requests

            # 用 GET 而非 PUT：Chrome 的 /json/close 对 GET 响应最快，
            # 且不需要构造 proxies 字典（上游 requests stub 的 proxies
            # 类型不接受 {"http": None}）。
            requests.get(
                f"http://{host}:{port}/json/close/{tab_id}",
                timeout=5,
            )
            return True
        except Exception:
            return False
