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
import sys


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
        # 每次 connect 都从零开始：上一次认领的 tab id 不能带到这一次。
        # 下面三种情况都会让 created_tab_id 保持空串（而非重新认领），
        # 若不清零就会残留旧值，导致 disconnect 关错页面、并泄漏本次新建的 tab
        # （claude -p Reviewer 报告 R3，2026-10-01）：
        #   1) target_url_prefix 非空 → 守卫为假，整个认领块被跳过
        #   2) reuse_existing_tab=True → 同上
        #   3) 新建页不唯一（len(new_pages) != 1）→ 认领块执行了，但块内判定失败
        #
        # 第四种情况：connect() 自身抛异常（claude -p Reviewer 报告 R4，
        # 2026-10-02）。vendor 的 connect() 是两步的：L572 的
        # _find_or_create_tab() 先把标签页建出来，L580 才去
        # ws_client.connect() 连 WebSocket。若后者抛异常，标签页**已经存在**，
        # 但认领块在异常传播中永远跑不到 → created_tab_id 停在空串 →
        # disconnect 认为「没建过任何页面」而什么都不关 → 那一个 tab 成孤儿泄漏。
        # 所以认领必须放进 finally（见 _claim_created_tab）。
        #
        # 下面的 before 快照刻意留在 _pub.connect() **之前**：finally 里的
        # 认领依赖这份差集基准，顺序不能颠倒。
        self.created_tab_id = ""

        before = self._pub._get_targets()
        before_ids = {
            t.get("id") for t in before
            if t.get("type") == "page" and t.get("webSocketDebuggerUrl")
        }

        result = None
        try:
            result = self._pub.connect(
                target_url_prefix=target_url_prefix,
                reuse_existing_tab=reuse_existing_tab,
            )
        finally:
            # 即使 ws 连接失败，vendor 也可能已经建好 tab（L572 早于 L580），
            # 必须在异常传播前认领，否则那个 tab 会成为孤儿泄漏。
            self._claim_created_tab(before_ids, target_url_prefix, reuse_existing_tab)

        return result

    def _claim_created_tab(
        self, before_ids: set[str], target_url_prefix: str, reuse_existing_tab: bool
    ):
        """认领本次 connect 期间新建的标签页（R4 修复点）。

        由 `connect()` 的 `finally` 调用，因此**异常路径上也会执行** ——
        vendor 的 connect() 先建 tab（L572）再连 ws（L580），后者抛异常时
        tab 已经存在，认领必须在异常传播之前完成，否则它会变成永久孤儿。

        「新建」的判据与 connect() 之前取的那份 before 快照比对：只有
        「本来没有、connect 之后有了」的页面才算我们建的。

        ## 为什么吞掉所有异常

        这里跑在 `finally` 里，且可能在调用方的真实异常传播过程中执行。
        若 `_get_targets()` 自己抛错（Chrome 中途关闭、CDP 端口不通、
        json 解析失败……），异常会**替换**掉那个真实错误 —— 调用方看到的
        将是一句莫名其妙的连接错误，真正的原因被彻底埋掉。

        认领是尽力而为的清理动作：失败的后果只是这个 tab 可能不被关
        （退回 M3 之前的行为），而不该改写调用方的正常流程。故全吞。
        """
        try:
            # 只有「本来没有、connect 之后有了」才算我们新建的
            if target_url_prefix or reuse_existing_tab:
                return
            after = self._pub._get_targets()
            new_pages = [
                t for t in after
                if t.get("type") == "page"
                and t.get("webSocketDebuggerUrl")
                and t.get("id") not in before_ids
            ]
            if len(new_pages) == 1:
                self.created_tab_id = new_pages[0].get("id", "")
        except Exception as e:  # noqa: BLE001
            # 认领失败不抛：不能改写调用方正在传播的异常（见 docstring）。
            # 但必须留痕 —— 持续失败意味着 M3 泄漏在无声回归，
            # 而这类问题的表现形式恰恰是「什么都不报」。
            print(
                f"[tab_lifecycle] 认领新建标签页失败，M3 可能回归: {e!r}",
                file=sys.stderr,
            )
            return

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
