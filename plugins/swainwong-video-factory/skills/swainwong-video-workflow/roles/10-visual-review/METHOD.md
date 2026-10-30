# 10 · 视觉语义与美术审核内部方法

这是 `$swainwong-video-workflow` 内部调度的视觉语义与美术审核责任模块，不是可独立发现或由用户直接调用的 Codex Skill。子 Agent 开始任何实际工作前，完整读取 [本岗位 Harness](HARNESS.md)。只处理任务包授权的范围；总流程、用户输入、跨岗位依赖和最终汇报由主 Agent 管理。

## 输入与输出

- 必需输入：同版简报、逐镜合同、CI、素材/唯一性台账、实际 First Full Cut 或成片及哈希。
- 核心输出：绑定版本的逐镜视觉报告：看见什么、理解什么、误读/缺失、证据、修复、严重度和结论。
- 输入缺失、版本不一致或上游未通过时，返回缺口和所阻断的依赖；继续不依赖缺口且已授权的工作。

## 共享合同路由

- 需要视觉审核门槛时读取 [review-gates.md](../../references/review-gates.md)。
- 需要对象关系理解时读取 [visual-semantics.md](../../references/visual-semantics.md)。
- 需要画面去重时读取 [visual-uniqueness.md](../../references/visual-uniqueness.md)。
- 需要版式CI时读取 [ci-and-media-standard.md](../../references/ci-and-media-standard.md)。
- 需要动物动作时读取 [animal-motion-review.md](../../references/animal-motion-review.md)。

共享合同是详细规则的唯一维护位置。本岗位 Harness 提供职责路由和高风险约束，不复制或改写共享阈值。

## 返回主 Agent

返回岗位编号、输入版本/哈希、实际完成范围、产物绝对路径/哈希、检查证据、未覆盖项、下游影响，以及 `READY / REVISE / PARTIAL / UNAVAILABLE`。`READY`只表示本岗位交付合同满足，不代表全片或其他岗位已通过。
