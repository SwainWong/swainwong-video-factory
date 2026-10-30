# 02 · 文案与叙事内部方法

这是 `$swainwong-video-workflow` 内部调度的文案与叙事责任模块，不是可独立发现或由用户直接调用的 Codex Skill。子 Agent 开始任何实际工作前，完整读取 [本岗位 Harness](HARNESS.md)。只处理任务包授权的范围；总流程、用户输入、跨岗位依赖和最终汇报由主 Agent 管理。

## 输入与输出

- 必需输入：同版简报、①研究包、事实边界、目标时长、语言、语气与表演配置。
- 核心输出：可直接朗读的 PRODUCTION_READY_SCRIPT、句子 ID、结构与承诺回收表、claim 引用映射、读法意图及待核问题。
- 输入缺失、版本不一致或上游未通过时，返回缺口和所阻断的依赖；继续不依赖缺口且已授权的工作。

## 共享合同路由

- 需要First Full Cut 前的可生产脚本门槛时读取 [first-full-cut.md](../../references/first-full-cut.md)。
- 需要定稿式口播与短语级双语字幕时读取 [editorial-style-and-subtitles.md](../../references/editorial-style-and-subtitles.md)。
- 需要叙事、承诺和声音设计时读取 [storyboard-contract.md](../../references/storyboard-contract.md)。
- 需要口语与表演配置时读取 [speech-style.md](../../references/speech-style.md)。
- 需要事实和字幕边界时读取 [production-standard.md](../../references/production-standard.md)。

共享合同是详细规则的唯一维护位置。本岗位 Harness 提供职责路由和高风险约束，不复制或改写共享阈值。

## 返回主 Agent

返回岗位编号、输入版本/哈希、实际完成范围、产物绝对路径/哈希、检查证据、未覆盖项、下游影响，以及 `READY / REVISE / PARTIAL / UNAVAILABLE`。`READY`只表示本岗位交付合同满足，不代表全片或其他岗位已通过。
