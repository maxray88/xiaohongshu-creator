# legacy/ — 旧脚本存档

本目录存放已被现行流水线取代的脚本，**仅作历史存档**。cron 与 `bin/`、`core/`
均不引用本目录中的任何文件。除非要回滚到旧实现或调试历史问题，否则不要运行它们。

> 迁移背景：2026-08-09 将散落在 `~/.hermes/scripts/` 与 `~/.hermes/data/xhs_treehole/`
> 的脚本统一迁入 `01_XHS_Daily_Post/`，过时的实现归入此处。
> 2026-08-16 再次归档一批已无引用的脚本：`core/` 的 4 个旧脚本（`_cron_draft.py`、
> `_cron_publish_video.py`、`xhs_image_draft.py`、`render_xhs_cards_v1.py`）与
> `generators/` 的 23 个历史每日生成器。归档前已全面检索 `~/.hermes/cron`、`~/.hermes/scripts`、
> `~/.hermes/xhs_skills` 与项目内相互引用，确认现行流水线（bin/ + core/ 现行脚本 +
> cron LLM prompt）对它们均为零引用。

## 文件清单与保留原因

| 文件 | 原用途 | 被谁取代 | 保留原因 |
|---|---|---|---|
| `synthesize_video.py` | 早期竖版视频合成器（Edge-TTS 逐卡配音），日期/卡文案硬编码（`D="20260719"`，day13） | `core/_cron_assemble.py` | 保留特定某天的卡文案（TTS_TEXTS_V1/V2）供历史比对 |
| `publish_xhs_video.py` | Playwright 版本视频上传（无头 Chromium + 登录 profile） | `core/xhs_video_draft.py`（CDP） | XHS 反爬已失效，仅存档；`--login` 流程可作参考 |
| `xhs_draft_video.py` | 早期 CDP 版视频存草稿（手动点击「存草稿」按钮） | `core/xhs_video_draft.py`（CDP 自动保存 + 草稿计数校验） | `_click_save_draft` 的按钮定位逻辑可复用 |
| `debug_xhs_upload.py` | Playwright 上传调试脚本（有头窗口 + 30s 观察窗口 + 截图） | 无（一次性调试工具） | 排障时可借其截图/日志逻辑 |
| `_cron_compress.py` | 把图片压缩到 <150KB（面向 opencli 图文发布，按质量递减重试） | 现行 CDP 发布流（尺寸校验在 `core/xhs_video_draft.py`、`core/xhs_image_draft.py` 同源逻辑） | 压缩参数（quality=85 起、145KB 目标）可参考 |
| `_cron_compress2.py` | 更激进压缩到总 raw <550KB（base64 体积约束，日期硬编码 `20260718`/day12） | 现行 CDP 发布流 | 记录 XHS base64 上传的体积上限经验值 |
| `_cron_draft.py` | 旧动态版「存草稿」：读 post_data.json + manifest.json 组装 publish 命令执行 | 03:00 LLM cron 直接用 `cdp_publish.py fill` 存图文草稿 | 早期接口参考；已无任何引用 |
| `_cron_publish_video.py` | 无头浏览器视频上传（Playwright 旧版视频草稿） | `core/xhs_video_draft.py`（CDP） | 历史参考 |
| `xhs_image_draft.py` | 图文笔记→草稿（CDP 版，与 xhs_video_draft.py 同一 Chrome Profile） | 03:00 LLM cron 用 `cdp_publish.py fill` 直接存图文草稿 | 历史参考 |
| `render_xhs_cards_v1.py` | 渲染 V1 图文卡片 HTML→JPG（CDP 截图）并更新 V1 manifest | 01:00 V1 生成 prompt 用 Playwright `generators/render_card.py` | 历史参考 |

## legacy/generators/ — 历史每日生成器存档

`generators/generate_day*.py`、`generators/render_day18.py`（共 23 个）是 2026-08-16 之前
逐日手动编写的生成器快照，**已全部被现行 cron 取代**：01:00/02:00 LLM cron 每天直接用
工具生成内容与卡 HTML，且 V2 生成 prompt 会每次在数据目录写出新的 `generate_day{N}_v2.py`
（运行后即完成任务，不留痕）。`generators/` 目录现存唯一活的辅助脚本是
`render_card.py`（01:00 V1 生成 prompt 引用的 Playwright 渲染器）。这批历史文件仅存档，
供日后对照 prompt 演进或复用旧排版技巧。

## 注意事项

- `synthesize_video.py`、`_cron_compress2.py` 内含**硬编码日期**，直接运行会处理错误
  或不存在的 day 目录，属预期行为（仅存档）。
- 若旧脚本需要回滚启用，先对照 `core/` 对应脚本的当前接口（`cdp_publish.py`、
  `chrome_launcher.py`）确认未破坏性变更。
