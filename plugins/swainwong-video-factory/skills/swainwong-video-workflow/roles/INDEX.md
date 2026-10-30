# 内部岗位方法与 Harness 索引

[返回工作流入口](../SKILL.md) · [返回总 Harness](../harness/HARNESS.md)

这里的十二个岗位是 `$swainwong-video-workflow` 的内部角色模块，不是十二个平级 Skill。目录内故意不放 `SKILL.md` 和 `agents/openai.yaml`，因此不应作为可直接 `@` / `$` 调用的入口暴露。主 Agent 根据任务依赖选择模块，并把相应 `METHOD.md` 与 `HARNESS.md` 明确附给执行该职责的子 Agent；不要求十二个岗位同时运行。

| 岗位 | 内部方法 | Harness | 主要产物 |
|---|---|---|---|
| 01 资料研究 | [01-research/METHOD.md](01-research/METHOD.md) | [R](01-research/HARNESS.md) | 研究包 |
| 02 文案与叙事 | [02-scriptwriting/METHOD.md](02-scriptwriting/METHOD.md) | [W](02-scriptwriting/HARNESS.md) | 标准稿 |
| 03 分镜与视觉设计 | [03-storyboard/METHOD.md](03-storyboard/METHOD.md) | [S](03-storyboard/HARNESS.md) | 逐镜视听合同 |
| 04 口播音频 | [04-voice/METHOD.md](04-voice/METHOD.md) | [A](04-voice/HARNESS.md) | 口播轨与时码 |
| 05 素材与图像制作 | [05-assets/METHOD.md](05-assets/METHOD.md) | [I](05-assets/HARNESS.md) | 素材包与来源台账 |
| 06 动画与动效音效 | [06-animation/METHOD.md](06-animation/METHOD.md) | [G](06-animation/HARNESS.md) | 可编辑动画与SFX |
| 07 剪辑与声音合成 | [07-editing/METHOD.md](07-editing/METHOD.md) | [E](07-editing/HARNESS.md) | 可编辑时间线与候选导出 |
| 08 技术交付与归档 | [08-delivery/METHOD.md](08-delivery/METHOD.md) | [D](08-delivery/HARNESS.md) | 交付包与审片入口 |
| 09 编导与视听审核 | [09-director-review/METHOD.md](09-director-review/METHOD.md) | [Q](09-director-review/HARNESS.md) | 独立编导审核报告 |
| 10 视觉语义与美术审核 | [10-visual-review/METHOD.md](10-visual-review/METHOD.md) | [V](10-visual-review/HARNESS.md) | 独立视觉语义报告 |
| 11 事实与引用审核 | [11-fact-review/METHOD.md](11-fact-review/METHOD.md) | [F](11-fact-review/HARNESS.md) | 独立事实审核报告 |
| 12 BGM配乐 | [12-bgm/METHOD.md](12-bgm/METHOD.md) | [B](12-bgm/HARNESS.md) | 独立BGM轨与音乐使用表 |

## 调度规则

- 任务包必须包含岗位编号、简报版本/哈希、上游产物、适用规则 ID、期望输出、放行证据和未决事项。
- 子 Agent 不重新向用户索要主 Agent 已锁定的答案；缺口、冲突和条件变化回传主 Agent。
- 岗位 `READY` 只说明该岗位交付满足，不自动使下游关口或整片通过。
- ⑥负责动画及动作组 SFX；⑫负责跨镜/段落/全片 BGM；⑦负责最终时间线混音。
- ⑨⑩⑪首次判断彼此独立，也独立于作者和制作岗；返修后复核受影响范围。
