# vendor/xhs — 上游快照

这些文件**不是本项目原创**，是从
[white0dew/XiaohongshuSkills](https://github.com/white0dew/XiaohongshuSkills) 取的快照。
原 LICENSE（MIT）见 `LICENSE.upstream`。

## 快照版本

| 文件 | 行数 | 取自 commit |
|---|---|---|
| `cdp_publish.py` | 4892 | `3ede4fe` |
| `chrome_launcher.py` | 408 | `61042e7` |
| `feed_explorer.py` | 771 | `61042e7` |
| `run_lock.py` | 124 | `61042e7` |

两个 commit 都是**本地提交、从未来得及推给上游**：

- `61042e7` — 本地调试参数调整（`VIDEO_PROCESS_TIMEOUT` 120→180、
  `CDP_COMMAND_TIMEOUT` 15→60、评论页加滚动等）
- `3ede4fe` — `fix: _wait_video_processing 容忍瞬时 CDP 错误`
  （我们自己的修复：轮询循环内捕获 `CDPError` 继续轮询，
  避免一次瞬时抖动就中止整个 180s 等待并误报「视频可能太大」）

> ⚠️ 若将来 `git pull` 上游，`3ede4fe` 的改动**会冲突** ——
> 那时需要手动保留容错逻辑。冲突点在 `_wait_video_processing`。

## 为什么 vendor 而不是 submodule / symlink

cron 环境下 submodule 和 symlink 都容易在重启后失效，且让
「一个项目依赖两个仓库」这件事变得难以追溯。这里选择**把依赖
物理放进本仓库**，让本项目自包含。

`feed_explorer.py`（771 行搜索/评论爬虫）本项目**一次都没用**，
但 `cdp_publish.py:78` 顶层硬 import 它的 11 个符号 —— 缺文件会在
import 阶段炸。所以一并带上，保持与上游逐字一致。

`account_manager.py` **没有** vendor：两处引用都自带容错
（`cdp_publish.py:189` 包在 `try/except Exception`、
`chrome_launcher.py:91` 明确 `except ImportError` 且带 fallback）。
实测在缺它的情况下导入与调用均正常。

## 规则

1. **能不改就不改。** 真要改，改完在这里记一行：改了什么、为什么。
2. 改过的文件**不再是上游逐字一致**，`git diff` 对比上游时要留意。
3. 同步上游时先比对，再决定覆盖还是手工合并 —— 我们的
   `_wait_video_processing` 容错修复不能被覆盖掉。

## 不在这个目录里的东西

- **venv 不在这里。** Python 依赖（mlx / mlx-audio / playwright / websockets）
  装在 pyenv 3.11.15 全局环境（`~/.pyenv/versions/3.11.15/bin/python3`），
  不该进 Git。`bin/_xhs_common.sh` 的 `$XHS_PY` 指向它。
- `publish_pipeline.py`、`image_downloader.py`、`account_manager.py`
  本项目零引用，**未** vendor。
