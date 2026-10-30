# 可执行工作流状态合同

本合同区分“由代码强制的事实”和“由 Agent／人类判断的创作质量”。状态机只放行已经具备版本身份、真实文件和必要依赖的产物；它不判断故事、画面、表演或声音是否优秀。

## 使用入口

```sh
python3 scripts/workflow_state.py init --project PROJECT --brief BRIEF.json
python3 scripts/workflow_state.py status --project PROJECT
python3 scripts/workflow_state.py task-packet --project PROJECT --role 01-research
python3 scripts/workflow_state.py record --project PROJECT --stage research --status READY --artifact FILE --evidence TEXT
```

项目状态写在 `PROJECT/.video-workflow/`：

- `brief.json`：规范化锁定简报；其文件 SHA-256 是本轮配置身份。
- `state.json`：当前阶段状态和产物哈希。
- `events.jsonl`：只追加的状态事件历史。

## 硬门槛

- `brief_confirmed` 必须来自真实人类确认；脚本只校验字段和值，不替人类产生确认。
- `READY` 之前，所有直接依赖必须已经 `READY`。
- `READY` 必须提交项目目录内的真实普通文件，状态记录其绝对路径、字节数和 SHA-256。
- G1/G2/G3 审核必须绑定当前依赖产物的 SHA-256。
- 已经放行的上游产物发生变化时，所有已有下游结果标为 `STALE`；旧 PASS 不继承。
- 已记录产物若被原地修改，普通状态读取必须 fail-closed。合法新版本只能用 `record` 显式重记同一阶段，重新计算文件身份并使受影响下游过期。记录某上游阶段时，只可临时容忍该阶段及其递归后代的哈希漂移，因为成功记录会把已启动后代统一重绑为 `STALE`；依赖、兄弟或其他无关阶段仍不得借机忽略漂移，也不得手改 `state.json` 解锁。
- `REVISE / PARTIAL / UNAVAILABLE / BLOCKED` 必须保留证据说明，但不伪装成放行。

## 创作判断边界

状态机不能把字段完整、文件存在、渲染成功、解码成功、抽帧、ASR、响度或 MCP 调用成功解释成连续视觉审核、真实听审、独立审核或用户批准。相应岗位仍须按照自己的 `METHOD.md`、`HARNESS.md` 和共享合同完成判断。

`storyboard` 记录 `READY` 时必须提交且只能提交一份含 canonical `audience_visual_units` 的 `swainwong.storyboard.*` JSON。插件从该文件和项目内 capture 文件重算 `swainwong.storyboard-gate.v1`：验证工作流 4.9、角色 READY、从 0 连续到正文结尾并接满 credits 的时间线、逐 unit 必填语义字段、direct evidence 的 claim／fact source／origin／可见证据与内嵌 capture receipt、2xx/3xx 状态和实测 SHA-256、非 direct 不得携带可见事实证据、同一 evidence origin 不得跨不连续 unit 复用、锁定的第三方覆盖率及内部视频占比、禁用 vector 主画面、固定 5 秒墙，以及每个真实章节边界前／时／后的全局不重置进度探针。项目自定义 validator 或自报 `PASS` 不参与放行；已存的 storyboard READY 在普通状态读取时也会重新计算。该门禁只判断机械合同，不判断创意质量，也不能替代独立 `g1-visual-review`。

`editing-first-full-cut` 记录 `READY` 前必须读取 [First Full Cut 合同](first-full-cut.md)，把哈希绑定的 `swainwong.first-full-cut.v1` JSON 与整片粗剪一同提交；脚本机械检查目标时长、脚本身份、时间线覆盖、渲染解码、声画时钟及显式 placeholder 列表。它不要求最终素材或最终视听质量。

`editing-final` 记录 `READY` 前必须把候选视频、`swainwong.final-visual-gate-input.v2` 与 `swainwong.final-visual-gate.v2` 一同提交；v1 证据不得沿用。该门禁机械检查分段导航结构与最终像素进度、第三方覆盖率及其内部视频占比、第三方同源连续区间、缩放后有效清晰度、禁用主画面、可读页最短时长、逐单元语义字段、事实证据叠加层 origin 唯一性、Logo 归位，以及片头／中段／片尾字幕 cue 相对同帧干净参考的最终像素差异。同一网页不同截图／裁切不能登记成不同证据 origin；双语字幕须检测到相应的多行字幕带。这些只能证明合同与像素存在，字幕内容、单双份权威、事实语义和可读性仍由 G3 连续审片判断。机器 PASS 不等于创作验收。

之后 `g3-director-review / g3-visual-review / g3-fact-review` 各提交一份绑定候选哈希的 `swainwong.review.v1`；制作人与审核者必须分离。三审通过后，`candidate-internal-gate` 才接受引用三份报告哈希的 `swainwong.candidate-av-gate.v1`。最后 `owner-review-ready` 绑定该内部门禁与候选哈希；未到此状态只能启动内部诊断页，不能向用户提交为待验收版本。
