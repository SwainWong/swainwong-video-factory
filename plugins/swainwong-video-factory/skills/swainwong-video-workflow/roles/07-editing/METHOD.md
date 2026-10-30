# 07 · 剪辑与声音合成内部方法

这是 `$swainwong-video-workflow` 内部调度的剪辑与声音合成责任模块，不是可独立发现或由用户直接调用的 Codex Skill。子 Agent 开始任何实际工作前，完整读取 [本岗位 Harness](HARNESS.md)。只处理任务包授权的范围；总流程、用户输入、跨岗位依赖和最终汇报由主 Agent 管理。

## 输入与输出

- 必需输入：First Full Cut 模式需要同版简报、可生产脚本、粗分镜、CI骨架和平台选择；最终模式再需要②–⑥、⑫的已标识交付及来源台账。
- 核心输出：可编辑工程、候选视频、字幕、独立音轨、实际时间轴清单、混音与变更记录。
- 输入缺失、版本不一致或上游未通过时，返回缺口和所阻断的依赖；继续不依赖缺口且已授权的工作。

## 共享合同路由

- 需要完整粗剪优先时读取 [first-full-cut.md](../../references/first-full-cut.md)。
- 需要短语级双语字幕门禁时读取 [editorial-style-and-subtitles.md](../../references/editorial-style-and-subtitles.md)。
- 需要剪辑与成片标准时读取 [production-standard.md](../../references/production-standard.md)。
- 需要版式和素材节奏时读取 [ci-and-media-standard.md](../../references/ci-and-media-standard.md)。
- 需要最终时间轴去重时读取 [visual-uniqueness.md](../../references/visual-uniqueness.md)。
- 需要声音分工时读取 [animation-sound-design.md](../../references/animation-sound-design.md)。
- 需要主持同步时读取 [a-roll.md](../../references/a-roll.md)。

共享合同是详细规则的唯一维护位置。本岗位 Harness 提供职责路由和高风险约束，不复制或改写共享阈值。

## 返回主 Agent

返回岗位编号、输入版本/哈希、实际完成范围、产物绝对路径/哈希、检查证据、未覆盖项、下游影响，以及 `READY / REVISE / PARTIAL / UNAVAILABLE`。`READY`只表示本岗位交付合同满足，不代表全片或其他岗位已通过。
