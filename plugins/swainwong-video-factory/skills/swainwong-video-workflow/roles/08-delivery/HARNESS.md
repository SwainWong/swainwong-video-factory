# 08 · 技术交付与归档 Harness

[返回岗位方法](METHOD.md) · [工作流总 Harness](../../harness/HARNESS.md) · [岗位索引](../INDEX.md)

## 职责边界

本岗位对“交付包与审片入口”负责。关键词：交付、归档、ffprobe、decode、字幕、响度、hash、审片页面、review-feedback、清理、delivery。这些词用于 Codex 路由和任务包检索，不扩大岗位权限。

## MUST DO

| ID | 必须做 |
|---|---|
| D-M01 | 对实际交付文件记录绝对路径、SHA-256、时长、流、帧率和技术检查结果。 |
| D-M02 | 分别执行全解码、字幕时码、音轨、响度/真峰值及规定的版式检查。 |
| D-M03 | 为 First Full Cut、完整候选和返修版启动绑定实际视频、项目和真实对话的审片页；内部门禁前只用 `--audience internal`，`owner-review-ready` 后才可用 `--audience owner`。 |
| D-M04 | 区分 saved、preview、queued、sent、agent_received、返修完成和验收状态。 |
| D-M05 | 打包成片、可编辑工程、字幕、Logo、必要分轨、来源/唯一性/审核记录与未完成项。 |
| D-M06 | 按授权清理，保留人类原始素材及仍被工程引用的必要资产。 |
| D-M07 | 交付前核对 `editing-final` 的最终视觉门禁、三份 G3、`candidate-internal-gate` 与 `owner-review-ready` 均绑定同一哈希；用户否决后立即把该哈希退回 `REVISE`。 |

## FORBIDDEN DO

| ID | 禁止做 |
|---|---|
| D-F01 | 不得把ffprobe、解码、ASR、响度、抽帧或评论关闭当成连续视听验收。 |
| D-F02 | 不得把saved/queued说成Agent已收到，或把agent_received说成已返修。 |
| D-F03 | 不得覆盖旧视频评论、挪用旧时码/哈希或拿另一平台PASS代替本平台。 |
| D-F04 | 不得擅删原始素材、必要工程资产，或把预览称为最终交付。 |
| D-F05 | 不得把 `NON_RELEASE_TEST_RENDER_OVERRIDE`、零秒视听覆盖或 `PARTIAL/UNAVAILABLE` 包装成视频完成；只能显著标注为诊断候选。 |
| D-F06 | 不得把内部诊断页的 URL 当作用户验收链接；`--audience owner` 启动失败时不得改状态文件或参数绕过。 |

## 放行证据

交付清单/哈希、技术日志、审片URL与进程身份、反馈目录、归档/清理记录及状态矩阵。

没有上述实际证据时不得将本岗位写成 `READY`。文件存在、字段完整或工具成功只证明相应技术事实；需要看、听或独立判断的项目仍按实际覆盖报告。

## 失败处理

命中 FORBIDDEN、输入版本不一致、关键证据缺失或产物无法复建时，标记 `REVISE`；只完成局部范围时标记 `PARTIAL`；能力或资源不可用时标记 `UNAVAILABLE`。列出问题位置、证据、责任边界、最小修复和受影响下游。不得越权代替其他岗位修复后继承其审核身份。
