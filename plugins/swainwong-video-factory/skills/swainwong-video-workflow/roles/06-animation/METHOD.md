# 06 · 动画与动效音效内部方法

这是 `$swainwong-video-workflow` 内部调度的动画与动效音效责任模块，不是可独立发现或由用户直接调用的 Codex Skill。子 Agent 开始任何实际工作前，完整读取 [本岗位 Harness](HARNESS.md)。只处理任务包授权的范围；总流程、用户输入、跨岗位依赖和最终汇报由主 Agent 管理。

## 输入与输出

- 必需输入：同版简报、③逐镜合同、⑤资产、事实数据、CI、平台能力和旁白/BGM上下文。
- 核心输出：可编辑动画源码/工程、实际带SFX预览、无BGM同步预览、独立SFX轨与事件清单。
- 输入缺失、版本不一致或上游未通过时，返回缺口和所阻断的依赖；继续不依赖缺口且已授权的工作。

## 共享合同路由

- 需要动画与SFX责任合同时读取 [animation-sound-design.md](../../references/animation-sound-design.md)。
- 需要多库接入时读取 [motion-library-adapters.md](../../references/motion-library-adapters.md)。
- 需要效果去重时读取 [visual-uniqueness.md](../../references/visual-uniqueness.md)。
- 需要讲解动画路由时读取 [explainer-motion/index.md](../../references/explainer-motion/index.md)。
- 需要动物动作时读取 [animal-motion-review.md](../../references/animal-motion-review.md)。

共享合同是详细规则的唯一维护位置。本岗位 Harness 提供职责路由和高风险约束，不复制或改写共享阈值。

## 返回主 Agent

返回岗位编号、输入版本/哈希、实际完成范围、产物绝对路径/哈希、检查证据、未覆盖项、下游影响，以及 `READY / REVISE / PARTIAL / UNAVAILABLE`。`READY`只表示本岗位交付合同满足，不代表全片或其他岗位已通过。
