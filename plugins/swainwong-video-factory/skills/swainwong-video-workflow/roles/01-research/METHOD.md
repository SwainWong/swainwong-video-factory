# 01 · 资料研究内部方法

这是 `$swainwong-video-workflow` 内部调度的资料研究责任模块，不是可独立发现或由用户直接调用的 Codex Skill。子 Agent 开始任何实际工作前，完整读取 [本岗位 Harness](HARNESS.md)。只处理任务包授权的范围；总流程、用户输入、跨岗位依赖和最终汇报由主 Agent 管理。

## 输入与输出

- 必需输入：锁定简报版本/哈希、研究问题、受众、目的、观点模式、时效与资料边界。
- 核心输出：带 claim ID 的研究包、原始来源与日期、冲突证据、未知项、可供②使用的候选角度。
- 输入缺失、版本不一致或上游未通过时，返回缺口和所阻断的依赖；继续不依赖缺口且已授权的工作。

## 共享合同路由

- 需要入口与版本边界时读取 [production-brief.md](../../references/production-brief.md)。
- 需要事实、来源和文件要求时读取 [production-standard.md](../../references/production-standard.md)。
- 需要事实审核所需证据时读取 [review-gates.md](../../references/review-gates.md)。

共享合同是详细规则的唯一维护位置。本岗位 Harness 提供职责路由和高风险约束，不复制或改写共享阈值。

## 返回主 Agent

返回岗位编号、输入版本/哈希、实际完成范围、产物绝对路径/哈希、检查证据、未覆盖项、下游影响，以及 `READY / REVISE / PARTIAL / UNAVAILABLE`。`READY`只表示本岗位交付合同满足，不代表全片或其他岗位已通过。
