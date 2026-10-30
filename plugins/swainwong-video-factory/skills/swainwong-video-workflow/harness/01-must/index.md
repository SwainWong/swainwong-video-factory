# 一定要做 MUST

[返回主入口](../HARNESS.md) · [失败处理与证据格式](../04-verification/index.md)

以下是已有规范的关键执行项。适用规则缺证据不能自动勾选通过；例外必须记录适用依据。条件性的制作细节仍需读取链接原文。

| ID | 何时适用 | 一定要做 | 检查证据／不满足的处理 | 原文依据 |
|---|---|---|---|---|
| M01 | 新片或成片重编 | 展示完整有效简报，沿用已知答案，锁定素材允许／禁止类型与唯一字幕渲染权威，取得当前版本真实确认并完成入口核验 | 确认依据、配置哈希、入口校验记录；缺失只做入口准备 | [制作简报](../../references/production-brief.md) |
| M02 | 任意派单、条件变更 | 所有任务绑定同一有效简报；条件变更确认新版本并使受影响下游失效 | 任务输入版本、变更差异、依赖清单；旧输入任务退回 | [制作简报](../../references/production-brief.md) |
| M03 | 脚本与事实研究 | 维护事实来源和叙事承诺，核对人物、阶段、数字、事件、引用上下文；First Full Cut 前完成可直接朗读、结构完整、事实有界的 `PRODUCTION_READY_SCRIPT` | claim 与来源、句子 ID、承诺回收表、目标时长估算及编导／事实审核；关键证据或正文缺口未关闭时不进入整片粗剪 | [First Full Cut](../../references/first-full-cut.md)、[叙事合同](../../references/storyboard-contract.md) |
| M04 | 选画面、动画与全片设计 | 先写本镜观众问题和答案，再设计对象、关系、动作因果、状态、层级、时点、声音和字幕 | 完整逐镜视听脚本与动作／声音表；未定义镜头退回设计 | [叙事合同](../../references/storyboard-contract.md) |
| M05 | 制作与跨库接入 | 锁定全片一套可编辑 CI，并映射每个库实际能力与交接方式 | CI token、适配记录、实际渲染及目标平台证据；不支持项保留缺口 | [CI](../../references/ci-and-media-standard.md)、[接入合同](../../references/motion-library-adapters.md) |
| M06 | 第三方素材、讲解图表 | 建唯一性台账，分镜、时间轴、最终画面分别查重，核对口播对应 | 原始身份、派生关系、整镜结构、使用区间及实际画面；重复或待判定不放行 | [去重合同](../../references/visual-uniqueness.md) |
| M07 | 第三方素材与比例检查 | 保留来源和使用依据，按真实主画面时长统计第三方覆盖率、其内部视频占比、混合镜头及独立素材数；执行纯素材 3–5 秒及有限例外。`至少`比例是下限，不是自动追求100%的目标；仍须为机制解释和结尾保留获准的原创表达层 | 来源／权利台账、实际 visual units、时间轴区间、统计分母及 `third_party_coverage`；不足、误计或为凑比例形成固定轮转素材墙均退回分镜／剪辑 | [CI](../../references/ci-and-media-standard.md)、[主规范](../../SKILL.md) |
| M08 | 口播生成及节奏调整 | 明示匀速清晰／自然起伏和快慢停位置；保留已选音色，按要求做表演试音并记录真实发送参数。简报范围有空间且旁白占用过高时，优先保留自然句段、增加意群／章间停顿并延长整片 | 实际音频、参数、占用率、试听范围和结论；声音身份未核验与表演未验收分别记录 | [口语配置](../../references/speech-style.md)、[音色选择](../../references/voice-selection.md) |
| M09 | 动画声音设计、混音及含现场声的视频 | ⑥对动画画面、运动和实际SFX完整负责；⑫独立交BGM，⑦汇总混音；按声音角色分类选材、保留独立轨并核实际带声交接；新旧音轨一起检查同组重复及无可见动作的残留提示。设计旁白、人物原声、环境声主导区间；BGM 按约定贯穿并主动让位；登记前景事件并按故事/对象/动作分组，一个短提示或一个完整声体，组内多帧/补间不重触发，禁短音堆长音；事件→组→cue映射，变更节奏后重核组和锚点 | 全事件覆盖台账、实际资产与包络、可编辑分轨、含声预览及真实听审；保护豁免定位具体区间，独立组无理由漏配、组内反复触发、短音拼长音、不可辨、错位、抢话或丢音轨返修；组内不重触发及单锚点允许 | [制作规范](../../references/production-standard.md)、[动画音效合同](../../references/animation-sound-design.md) |
| M10 | 字幕、Logo、进度条及素材构图 | 执行当前锁定布局；核最终导出的槽位、安全区、满屏、章节语义与真实时长边界；逐镜覆盖起点／中点／终点，短可读页不得闪现；字幕至少在片头／中段／片尾 cue 对比同帧干净参考，证明最终像素存在，双语须检测到对应多行 | `swainwong.final-visual-gate.v2`、字幕 pixel proofs、最终像素边界样本及逐镜证据；错位、缺失、重复、遮挡、章名占位、禁用主画面、低清放大或不可读闪卡返修 | [CI](../../references/ci-and-media-standard.md)、[主规范](../../SKILL.md) |
| M11 | 主持 A-roll | 核来源、人物、声音／输入路径，按句子 ID、take 和源／时间轴时码交接；按实测音频同步 | 档案核验、take manifest、声画同步与裁切检查；依赖未到位的步骤等待 | [A-roll](../../references/a-roll.md) |
| M12 | 纸艺过程、身体动作、动物动作 | 设计连续可辨状态、施力接触及结果，并正常速度检查完整动作 | 状态图、帧区间和实际播放审查；静帧只能支持局部判断 | [叙事合同](../../references/storyboard-contract.md)、[动物审查](../../references/animal-motion-review.md) |
| M13 | G1、G2、G3 | 专业编导、观众画面语义、事实检查独立审查同一版本；作者自检单列 | 三角色报告、输入身份、覆盖和具体问题；Critical／Important 未关闭不通过 | [审核合同](../../references/review-gates.md) |
| M14 | 可生产脚本与粗分镜就绪后 | 在最低完整播放条件成立时立即导出目标时长 First Full Cut；每个句子都有正式或显式临时画面，并登记所有待替换素材、动画、SFX、BGM与混音缺口 | 整片视频、脚本哈希、`swainwong.first-full-cut.v1`、placeholder manifest 与 G2 整片问题清单；不得等待局部成片级精修 | [First Full Cut](../../references/first-full-cut.md)、[审核合同](../../references/review-gates.md) |
| M15 | 最终导出与返修验收 | 候选先过最终视觉机器门禁；三份 G3 结构化独立审核再绑定同一哈希；技术检查、连续正常速度视觉审片、真实听审分别完成后汇总 candidate AV gate | `editing-final → G3 → candidate-internal-gate → owner-review-ready` 的哈希链；不可用项保持 PARTIAL／UNAVAILABLE | [候选片门禁](../../references/candidate-av-gate.md)、[审核合同](../../references/review-gates.md) |
| M16 | 每次 First Full Cut、完整候选、返修版渲染后 | 提供加载实际视频的本地审片页面和文件；未到 `owner-review-ready` 只能启动 `--audience internal`，通过后才可启动 `--audience owner`；评论绑定视频哈希及不可变快照 | 页面模式、视频路径、门禁状态、评论提交／队列／实际接收证据；状态不能跨级 | [反馈合同](../../references/video-feedback.md) |
| M17 | 交付、双平台制作 | 交付成片、可编辑工程、字幕、Logo、必要分轨、台账、审核及未完成项；双平台各自验收 | 交付清单和可打开文件；缺项明确报告，不写全部完成 | [审核合同](../../references/review-gates.md) |
| M18 | 复盘与偏好沉淀 | 把反馈写成适用场景、规则和证据；区分本期修改、长期候选、已确认长期规则 | 反馈来源、范围、冲突处理与确认依据；未确认不升格 | [反馈合同](../../references/video-feedback.md) |
| M19 | 编写或运行任何自动门禁 | 每个 PASS 必须由实际输入计算，报告 `actual` 必须等于实测值；用负向 fixture 证明错误输入会失败。程序只验证可机械判断的字段、文件、哈希与像素，语义 PASS 仍由独立审核者签发 | 校验器源码、正常与负向测试、实际产物重算报告；发现常量 PASS、信任自报或作者自签语义结论时整份门禁失效 | [工作流状态合同](../../references/workflow-state-contract.md)、[审核合同](../../references/review-gates.md) |
| M20 | 用户指定独立 Codex 制作对话 | 主对话只做 Owner：维护简报与状态、派任务包、核产物和门禁、汇报；绑定一个持久制作 thread 执行脚本、字幕、工程和渲染写入 | production thread ID、实际接收回执、任务包和产物哈希；主对话越权写片则停止并把受影响生产交回独立对话 | [主流程](../../SKILL.md) |
| M21 | 口播成稿和中英字幕 | 口播使用定稿式直接表达，先过 `swainwong.script-style-gate.v1` 再独立编导通读；最终音频锁定后按短语制作一一对应中英 cue，并通过 `swainwong.subtitle-phrase-gate.v1` 与最终像素审核 | 两份机器报告、脚本／音频／字幕哈希、编导结论和字幕像素样本；任一长段、思考过程或配对错误退回②／⑦ | [定稿与字幕](../../references/editorial-style-and-subtitles.md) |

范围提醒：默认 8:2 与尽量 3:7 不等价。前者是需在简报中明确的项目默认目标，后者是推荐倾向；当前明确选择可覆盖默认。授权主持 A-roll 单列比例与覆盖，不能塞进第三方 B-roll 分母强行套规则。
