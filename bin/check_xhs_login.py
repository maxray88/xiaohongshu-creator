#!/usr/bin/env python3
"""XHS 情绪树洞 02:45 登录健康探针。

在 03:00 图文存草稿之前确认小红书创作平台登录态有效：登录过期是整条
流水线最安静的单点故障（CDP 脚本只在登录检查处失败，当天两份草稿全缺）。
提前 15 分钟告警，把一次「起床发现昨天没发」变成一次 5 分钟扫码。

只做轻量探针（连接 → 导航发布页 → 确认未跳登录），不上传任何内容，
结束后关闭自己拉起的 Chrome，不影响后续任务按需拉起。

配合 hermes no_agent cron：
  - 登录有效 → 无 stdout、exit 0 → 静默
  - 失效或探针异常 → 输出 ❌ 报告、exit 1 → feishu 告警
"""

import io
import os
import sys
import time
from contextlib import redirect_stdout
from urllib.parse import urlsplit

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "core"))
from xhs_paths import add_cdp_to_path  # noqa: E402

# CDP 模块已 vendored 到项目内 vendor/xhs/（2026-09-27，原 ~/.hermes/xhs_skills/scripts）
add_cdp_to_path()

from xhs_config import PUBLISH_URL  # noqa: E402


def main() -> int:
    os.environ["XHS_CHROME_HEADLESS"] = "1"
    try:
        from chrome_launcher import ensure_chrome, kill_chrome
        from cdp_publish import CDPError  # noqa: F401
    except Exception as e:
        print("❌ XHS 登录探针：无法加载 CDP 技能库")
        print("=" * 46)
        print(f"• [探针] import 失败：{e}")
        return 1

    from tab_lifecycle import ManagedPublisher

    started_here = False
    try:
        from chrome_launcher import is_port_open
        if not is_port_open(9222):
            started_here = True
        if not ensure_chrome(port=9222, headless=True):
            print("❌ XHS 登录探针：Chrome 启动失败")
            print("=" * 46)
            print("• [探针] Chrome CDP 9222 不可用——请检查 Chrome 安装与 profile")
            return 1

        pub = ManagedPublisher(host="127.0.0.1", port=9222, timing_jitter=0.25)
        # CDP 库自带连接日志；探针通过时必须保持无 stdout（静默约定），
        # 因此缓冲其输出，只在失败时输出我们自己的报告。
        buf = io.StringIO()
        href, failure = "", None
        with redirect_stdout(buf):
            try:
                pub.connect()
            except Exception as e:
                failure = ("❌ XHS 登录探针：CDP 连接失败", f"• [探针] {e}")
            if failure is None:
                try:
                    pub._navigate(PUBLISH_URL)
                    href, ready = "", ""
                    for _ in range(12):
                        try:
                            href = pub._evaluate("window.location.href") or ""
                            ready = pub._evaluate("document.readyState") or ""
                        except CDPError as e:
                            failure = ("❌ XHS 登录探针：发布页导航失败", f"• [探针] {e}")
                            break
                        if href and ready == "complete":
                            # late JS redirects (challenge pages) land a beat after load —
                            # require one more identical reading before trusting the URL
                            try:
                                href2 = pub._evaluate("window.location.href") or ""
                            except CDPError as e:
                                failure = ("❌ XHS 登录探针：发布页导航失败", f"• [探针] {e}")
                                break
                            if href2 == href:
                                break
                            href = href2
                        time.sleep(1)
                except CDPError as e:
                    failure = ("❌ XHS 登录探针：发布页导航失败", f"• [探针] {e}")
                finally:
                    try:
                        pub.disconnect()
                    except Exception:
                        pass
        if failure is not None:
            print(failure[0])
            print("=" * 46)
            print(failure[1])
            return 1

        low = (href or "").lower()
        BLOCK_MARKERS = ("login", "passport", "auth", "captcha", "sso", "verify")
        expected = urlsplit(PUBLISH_URL)
        actual = urlsplit(href or "")
        try:
            jar = pub._send("Network.getAllCookies", {})
            cookie_count = len(jar.get("cookies", []))
        except Exception:
            cookie_count = None
        cookie_line = (
            f"• [会话] Cookie 数量：{cookie_count}"
            if cookie_count is not None
            else "• [会话] Cookie jar 不可读"
        )
        if any(m in low for m in BLOCK_MARKERS):
            print("❌ XHS 登录探针：登录已过期（被重定向到登录页）")
            print("=" * 46)
            print("• [登录] 03:00 图文与 05:00 视频草稿将因未登录而失败")
            print("备注：")
            print("  · 请用有头 Chrome 打开创作平台手动扫码登录后重跑当日发布任务")
            print(cookie_line)
            return 1
        elif actual.netloc != expected.netloc or "publish" not in actual.path:
            print("❌ XHS 登录探针：登录状态异常（发布页未如预期加载，可能被鉴权重定向）")
            print("=" * 46)
            print(f"• [当前] {href}")
            print(cookie_line)
            print("备注：")
            print("  · 请用有头 Chrome 打开创作平台手动扫码登录后重跑当日发布任务")
            return 1
        return 0
    finally:
        if started_here:
            try:
                kill_chrome(port=9222)
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
