# 04 · 口播音频内部方法

这是 `$swainwong-video-workflow` 内部调度的口播音频责任模块，不是可独立发现或由用户直接调用的 Codex Skill。子 Agent 开始任何实际工作前，完整读取 [本岗位 Harness](HARNESS.md)。只处理任务包授权的范围；总流程、用户输入、跨岗位依赖和最终汇报由主 Agent 管理。

## 输入与输出

- 必需输入：同版简报、②标准稿、锁定语言/声音身份、读法配置及可用引擎或真人录音。
- 核心输出：可播放口播轨、句子/时间映射、实际参数、试音结论、发音与表演缺口。
- 输入缺失、版本不一致或上游未通过时，返回缺口和所阻断的依赖；继续不依赖缺口且已授权的工作。

## 共享合同路由

- 需要口语和表演时读取 [speech-style.md](../../references/speech-style.md)。
- 需要音色发现与核验时读取 [voice-selection.md](../../references/voice-selection.md)。
- 需要已确认表演档案时读取 [voice-performance-profiles.md](../../references/voice-performance-profiles.md)。
- 需要真人/数字人同步边界时读取 [a-roll.md](../../references/a-roll.md)。

共享合同是详细规则的唯一维护位置。本岗位 Harness 提供职责路由和高风险约束，不复制或改写共享阈值。

## 返回主 Agent

返回岗位编号、输入版本/哈希、实际完成范围、产物绝对路径/哈希、检查证据、未覆盖项、下游影响，以及 `READY / REVISE / PARTIAL / UNAVAILABLE`。`READY`只表示本岗位交付合同满足，不代表全片或其他岗位已通过。
