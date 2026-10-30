# 08 · 技术交付与归档内部方法

这是 `$swainwong-video-workflow` 内部调度的技术交付与归档责任模块，不是可独立发现或由用户直接调用的 Codex Skill。子 Agent 开始任何实际工作前，完整读取 [本岗位 Harness](HARNESS.md)。只处理任务包授权的范围；总流程、用户输入、跨岗位依赖和最终汇报由主 Agent 管理。

## 输入与输出

- 必需输入：⑦候选/最终导出、工程、字幕、分轨、台账、审核状态、清理与交付范围。
- 核心输出：技术报告、交付包、文件清单/哈希、审片页面、反馈路径、归档与真实未完成项。
- 输入缺失、版本不一致或上游未通过时，返回缺口和所阻断的依赖；继续不依赖缺口且已授权的工作。

## 共享合同路由

- 需要成片技术与交付关口时读取 [review-gates.md](../../references/review-gates.md)。
- 需要审片页面和提交状态时读取 [video-feedback.md](../../references/video-feedback.md)。
- 需要反馈沉淀时读取 [harness-feedback.md](../../references/harness-feedback.md)。
- 需要文件和交付标准时读取 [production-standard.md](../../references/production-standard.md)。

共享合同是详细规则的唯一维护位置。本岗位 Harness 提供职责路由和高风险约束，不复制或改写共享阈值。

## 返回主 Agent

返回岗位编号、输入版本/哈希、实际完成范围、产物绝对路径/哈希、检查证据、未覆盖项、下游影响，以及 `READY / REVISE / PARTIAL / UNAVAILABLE`。`READY`只表示本岗位交付合同满足，不代表全片或其他岗位已通过。
