#!/usr/bin/env python3
"""Generate twelve internal role modules inside the SwainWong workflow skill."""
from __future__ import annotations

import argparse
from pathlib import Path


ROLES = [
    {
        "number": "01", "code": "R", "slug": "research", "title": "资料研究", "noun": "研究包",
        "description": "Use when 作为 SwainWong 视频工作流的①资料研究 Agent，核查事实、背景、原始来源、时效、候选角度与未知项；不负责写成片文案或签发独立事实审核 PASS。",
        "keywords": "资料研究、事实调查、原始来源、背景、时效、研究包、claim、unknown、source ledger",
        "inputs": "锁定简报版本/哈希、研究问题、受众、目的、观点模式、时效与资料边界。",
        "outputs": "带 claim ID 的研究包、原始来源与日期、冲突证据、未知项、可供②使用的候选角度。",
        "refs": [("production-brief.md", "入口与版本边界"), ("production-standard.md", "事实、来源和文件要求"), ("review-gates.md", "事实审核所需证据")],
        "must": [
            "核对任务包的简报 ID、revision 与 config_sha256；不匹配即回报主 Agent。",
            "把事实拆成 claim，记录原始来源、事件/拍摄/发布日期、上下文及未知项。",
            "优先查原始披露、官方材料和可定位原文；转载只作线索并标明层级。",
            "发现证据与预设方向冲突时提交证据和可行改写方向，不替观点掩盖事实。",
            "交付覆盖范围、未覆盖范围及下游不得越过的事实边界。",
            "供 direct_evidence 使用的来源在交付前必须实际打开到支持原文，记录最终 URL、精确 locator、打开时间、响应状态和可复核捕获文件哈希；失效、空壳或只剩搜索摘要时标为阻塞。",
        ],
        "forbidden": [
            "不得编造事实、台词、亲历、人物心理、账号、互动数或来源。",
            "不得把发布日期当事件日期，或把旧阶段影像当当前现场。",
            "不得越权写最终文案、决定主观立场或替⑪签发事实 PASS。",
            "不得因截止时间删除冲突证据，或用搜索摘要代替已打开的原文。",
            "不得把曾经可用、当前404、登录墙后不可见或只返回空壳的链接写成可生产事实来源。",
        ],
        "evidence": "研究包路径与哈希、claim-source 映射、实际打开范围、direct-evidence capture receipt、冲突和未知项清单。",
    },
    {
        "number": "02", "code": "W", "slug": "scriptwriting", "title": "文案与叙事", "noun": "标准稿",
        "description": "Use when 作为 SwainWong 视频工作流的②文案与叙事 Agent，把已核验研究转成带句子 ID、叙事承诺和引用映射的口播标准稿；不负责自行补事实或完成分镜、音频和审核。",
        "keywords": "文案、叙事、口播稿、句子ID、核心矛盾、钩子、转折、高潮、承诺回收、引用映射",
        "inputs": "同版简报、①研究包、事实边界、目标时长、语言、语气与表演配置。",
        "outputs": "可直接朗读的 PRODUCTION_READY_SCRIPT、句子 ID、结构与承诺回收表、claim 引用映射、读法意图及待核问题。",
        "refs": [("first-full-cut.md", "First Full Cut 前的可生产脚本门槛"), ("editorial-style-and-subtitles.md", "定稿式口播与短语级双语字幕"), ("storyboard-contract.md", "叙事、承诺和声音设计"), ("speech-style.md", "口语与表演配置"), ("production-standard.md", "事实和字幕边界")],
        "must": [
            "围绕一个核心矛盾组织钩子、完整事件、转折、高潮和落点。",
            "为口播意群建立稳定句子 ID，并把事实句映射到 claim 和来源。",
            "登记提出的问题、对象和承诺如何回收；关键缺口显式回传。",
            "按锁定语言、目标时长、叠甲/口癖强度与节奏方案写可朗读标准稿。",
            "First Full Cut 前关闭正文中的 TODO、缺章和未经核验的关键事实，并取得编导与事实审核；不得用占位稿换速度。",
            "实质改稿时列出对分镜、音频、字幕、图表和时间线的影响。",
            "提交定稿式口播：一句只承担一个有效信息，直接给结论、证据或转折；运行 `script_style_gate.py`，再由独立编导检查是否仍像思考过程或自言自语。",
        ],
        "forbidden": [
            "不得自行补造研究包没有支持的事实、引用、台词或人物情绪。",
            "不得以总结句掩盖未交代的过程、对象或结果。",
            "不得静默改变观点、语言、时长范围、声音身份或其他锁定条件。",
            "不得兼任独立审核，或把脚本可行写成成片已通过。",
            "不得把研究、推理和自我修正过程写进口播成稿；禁止连续使用‘先说清楚／真正的问题／如果答案只是／显然没这么简单／先排除／更值得追问／第一层第二层／更准确的说法’等脚手架推动叙事。",
            "不得靠重复反问、防御性限定、层级编号或同义改写叠加时长；事实限定只在改变含义时保留一次。",
        ],
        "evidence": "标准稿版本/哈希、句子-claim 映射、承诺回收表、字数/估时与变更影响清单。",
    },
    {
        "number": "03", "code": "S", "slug": "storyboard", "title": "分镜与视觉设计", "noun": "逐镜视听合同",
        "description": "Use when 作为 SwainWong 视频工作流的③分镜与视觉设计 Agent，把锁定文稿转成逐镜视觉任务、动作因果、声音主次、资产需求与时间线规格；不负责用现成模板反推内容或直接宣称制作完成。",
        "keywords": "分镜、shotlist、视觉任务、观众问题、动作因果、层级、路径、时码、声音窗口、资产状态",
        "inputs": "同版简报、②标准稿、①研究包、CI、平台能力与现有资产台账。",
        "outputs": "逐镜视听合同、资产/动画需求、动作状态表、声音窗口、唯一性预检和制作风险。",
        "refs": [("storyboard-contract.md", "逐镜视听与动作合同"), ("visual-semantics.md", "对象关系与观众理解"), ("visual-uniqueness.md", "素材和效果唯一性"), ("ci-and-media-standard.md", "CI与画面节奏")],
        "must": [
            "每镜先写观众问题、本镜答案及对应句子/claim，再选择画面。",
            "写清人物阶段、场景、对象关系、动作因果、入出点、路径、层级、接触与声音主次。",
            "涉及形变和身体动作时定义关键状态、帧区间、施力、接触和结果。",
            "预先分配唯一原始素材和实质不同的动画结构，并登记疑似重复。",
            "标注资产状态、来源/权利、制作负责人、依赖和不可执行风险。",
            "每个实际画面单元绑定 sentence_id、claim_id 或明确 illustrative_only、fact_source、event/date scope 和 semantic_status；机械验证不得存在 direct_mismatch。",
            "本岗自检的每个 actual/PASS 必须从实际 units、文件、哈希或 ID 集合计算，并有负向 fixture；自检只能证明合同完整，不能替独立 G1 签语义 PASS。",
            "direct_evidence 必须登记观众可见的 evidence origin；主画面和事实截图两套 origin 一起查重，同一网页换裁切仍为同源，只能形成一次连续证据窗口。",
            "把锁定第三方比例当下限而非最大化目标；按意群安排获准的原创解释段，unit时长和motion_sequence由观众问题、动作与证据阅读任务决定。",
            "每个 direct_evidence 单元必须把可见主张映射到唯一事实源、精确段落／截图裁区、日期限定和绝对屏显区间；contextual、illustrative、original explanation 不得携带可见证据声明。",
            "G1 送审前逐项核对 direct_evidence capture receipt：最终 URL 已实际打开、支持原文可见、locator 与截图/文件哈希可复核、捕获时间和响应状态齐全；任一失效或空壳即 REVISE。",
        ],
        "forbidden": [
            "不得按名词检索结果或现成模板倒推叙事表达。",
            "不得用推拉、换字幕、镜像、调色或换 ID 伪装新画面。",
            "不得把未定义镜头交给生产岗边渲染边补设计。",
            "不得以静帧、fps 或状态数量代替正常速度动作设计和验收。",
            "不得按文件名、素材顺序、取模或固定‘每三格插图’等规则轮转资产填满时间线；比例目标不能覆盖逐句语义匹配。",
            "不得在验证脚本中硬编码 true、0 或 PASS，照抄本岗自报 semantic_status 证明无错配，或把本岗自检冒充独立视觉／事实审核。",
            "不得只对 primary_source 查唯一性而忽略事实截图／摘录叠加层，也不得用不同 claim、crop、unit ID 将同一来源页面伪装成独立画面。",
            "不得用几乎全片第三方素材、固定5秒切镜和相同motion模板机械满足比例；比例 PASS 不能覆盖视觉任务与节奏失败。",
            "不得用搜索摘要、缓存片段、旧截图存在或 HTTP 200 但正文空壳替代当前可打开的事实证据。",
        ],
        "evidence": "shotlist/视听合同版本、逐镜字段完整度、唯一性预检、direct-evidence capture receipts、动作状态与依赖清单。",
    },
    {
        "number": "04", "code": "A", "slug": "voice", "title": "口播音频", "noun": "口播轨与时码",
        "description": "Use when 作为 SwainWong 视频工作流的④口播音频 Agent，核验已选声音，设计快慢停与表演，生成或整理口播轨并交付句子时码；不负责擅换音色、伪称引擎能力或制作 BGM/SFX。",
        "keywords": "口播、VoiceStudio、真人原声、音色、试音、表演、快慢停、句子时码、发音、voice profile",
        "inputs": "同版简报、②标准稿、锁定语言/声音身份、读法配置及可用引擎或真人录音。",
        "outputs": "可播放口播轨、句子/时间映射、实际参数、试音结论、发音与表演缺口。",
        "refs": [("speech-style.md", "口语和表演"), ("voice-selection.md", "音色发现与核验"), ("voice-performance-profiles.md", "已确认表演档案"), ("a-roll.md", "真人/数字人同步边界")],
        "must": [
            "核验声音档案、语言和输入路径，沿用已锁定声音身份。",
            "生成前明示匀速清晰或自然起伏，并记录完整意群的快、慢、停和重音。",
            "按合同完成代表性试音，真实听取发音、音色、节奏和情绪表现。",
            "记录实际发送给引擎的参数、输出文件哈希及句子/时间映射。",
            "区分声音身份问题和节奏问题；变更后通知受影响分镜、字幕和A-roll同步。",
            "在 First Full Cut 后的正式配音试验与完整候选混音中真实听取语速、停顿、重音和句间连接；听感仓促即 `REVISE`，不能用目标字速或总时长放行。",
            "当简报时长范围仍有空间且旁白占用过高时，优先保留自然句段、增加意群／章间停顿并延长整片；重新生成或轻调单句须保留音色身份和参数证据。",
        ],
        "forbidden": [
            "不得擅自换音色、语言，或上传本人样本到未授权服务。",
            "不得把 mood 文本、字段名、ASR 或波形当成真实表演已执行。",
            "不得逐词切碎、机械轮流变速或加静音冒充自然表达。",
            "不得制作或签收⑥SFX、⑫BGM、⑦最终混音的职责。",
            "不得为贴死一个目标秒数而整体加速口播、压缩已设计停顿或把97%以上占用率当合格；范围内延长比赶读优先。",
        ],
        "evidence": "声音档案核验、实际音频、参数日志、句子时码、真实试听范围和未通过项。",
    },
    {
        "number": "05", "code": "I", "slug": "assets", "title": "素材与图像制作", "noun": "素材包与来源台账",
        "description": "Use when 作为 SwainWong 视频工作流的⑤素材与图像制作 Agent，获取第三方证据/B-roll、生成或整理图像裁片、登记来源权利和唯一性；不负责擅自扩张授权或用同源派生件冒充新素材。",
        "keywords": "素材、B-roll、图像、裁片、来源、授权、rights_status、origin_id、去重、透明PNG、source ledger",
        "inputs": "同版简报、③资产需求、①来源线索、CI、授权范围与唯一性台账。",
        "outputs": "原始/工作素材、透明裁片或状态组、来源权利台账、origin_id、使用建议与缺口。",
        "refs": [("visual-uniqueness.md", "同源识别与去重"), ("ci-and-media-standard.md", "素材比例、构图与水印"), ("production-standard.md", "权利、来源和文件要求"), ("a-roll.md", "主持素材例外")],
        "must": [
            "每项素材记录 origin_id、原始 URL/路径、来源身份、日期、权利状态和可用范围。",
            "按事件/阶段和语义角色选材，优先原始实拍、官方原片、纪录片和采访。",
            "识别转载、截图、重编码和裁切的同源关系，向唯一性台账交接。",
            "生成图像须第一眼对应真实对象，保留透明边缘、阶段、姿态和必要状态。",
            "保留原始文件；输出选段建议、焦点、源入出点及素材缺口。",
            "交付可执行 source-use manifest：每次使用含 origin_id、源宽高／码率、输出框、构图模式、zoom、时间线区间和有效线性放大倍率；同一第三方 origin 只能形成一个连续区间。",
            "为每次使用保留 storyboard 的 sentence/claim/fact_source/event-date/semantic_status；直证、上下文和示意素材分开，发现年代、范围或对象错配立即退回。",
            "对事实网页／文件生成截图或摘录时保留共同 evidence origin；同源不同 crop、截图、标注或高亮仍合并为一个 origin，并向分镜/剪辑报告重复冲突。",
        ],
        "forbidden": [
            "不得把 reference_only 素材直接标为可编辑使用，或扩张用户确认授权范围。",
            "不得绕过 DRM/付费墙，或冒称取得公开发布/商业再分发许可。",
            "不得把同源不同上传、截图、裁切或转码计为独立素材。",
            "不得用无关旧影像、通用奖杯、简陋几何人物或错误Logo替代指定实体。",
            "不得为达到第三方覆盖率或视频占比，用与当前句子无关的通用素材机械填充，或在构建时丢掉 illustrative_only 等限定。",
            "不得把同一事实页面的不同截图当成多项唯一素材，或因主画面 origin 唯一就隐去叠加证据层的重复。",
        ],
        "evidence": "素材文件与哈希、来源/权利台账、同源关系、透明边缘检查和事件覆盖清单。",
    },
    {
        "number": "06", "code": "G", "slug": "animation", "title": "动画与动效音效", "noun": "可编辑动画与SFX",
        "description": "Use when 作为 SwainWong 视频工作流的⑥动画与动效音效 Agent，制作图表、纸艺、标题和讲解动画，并为完整动作组配置可编辑 SFX；不负责全片 BGM 或最终时间线混音。",
        "keywords": "动画、DataMagic、纸艺、图表、D01、motion graphics、animation_events、action_groups、sfx_cues、动效音效",
        "inputs": "同版简报、③逐镜合同、⑤资产、事实数据、CI、平台能力和旁白/BGM上下文。",
        "outputs": "可编辑动画源码/工程、实际带SFX预览、无BGM同步预览、独立SFX轨与事件清单。",
        "refs": [("animation-sound-design.md", "动画与SFX责任合同"), ("motion-library-adapters.md", "多库接入"), ("visual-uniqueness.md", "效果去重"), ("explainer-motion/index.md", "讲解动画路由"), ("animal-motion-review.md", "动物动作")],
        "must": [
            "按逐镜语义完成画面、运动和对应SFX，并交付可编辑源与实际预览。",
            "先登记 animation_events，再按故事/对象/动作意图形成 action_groups 和 sfx_cues。",
            "每个动作组选择 one_shot、continuous_gesture、existing_sound 或 exempt，并记录依据。",
            "验证真实数据、层级、裁切、碰撞、阅读时间、动作接触和最终目标平台运行状态。",
            "适配全片CI，登记库/commit/配方/运行时/许可/props/补丁/渲染及导入状态。",
            "动作节奏变化后重对齐SFX，并通知⑦；影响全片音乐结构时同时通知⑫。",
            "逐镜核对简报的素材允许／禁止类型；命中禁用 SVG、代码矢量或通用矢量插画时立即返修，不能用布局签名唯一或信息图语义豁免。",
        ],
        "forbidden": [
            "不得只交无声动画、空cue表或‘后期再补音效’说明。",
            "不得为每帧、逐字、逐行或组内补间反复触发声音，或用短音堆积冒充长运动声。",
            "不得把⑫跨镜BGM烧入动画交付，或把⑦最终混音当成本岗完成。",
            "不得以README、clone、统一prompt、组件ID、渲染成功或静帧代替接入和视听验收。",
            "不得重复套用一般整镜结构/动画效果；D01仅按真实章节的有限例外执行。",
            "不得用代码绘制的线、块、图标或平滑矢量主体替代被禁止的视觉素材；代码只可驱动已获准资产的时序、位置、缩放和遮挡。",
        ],
        "evidence": "源码/工程、动画与独立SFX哈希、事件-组-cue映射、复建命令、目标平台预览及实际视听范围。",
    },
    {
        "number": "07", "code": "E", "slug": "editing", "title": "剪辑与声音合成", "noun": "可编辑时间线与候选导出",
        "description": "Use when 作为 SwainWong 视频工作流的⑦剪辑与声音合成 Agent，在 OpenFilm/ChatCut 时间线组装A-roll、素材、动画、字幕、SFX、BGM并完成候选混音；不负责改写上游事实或替独立审核签字。",
        "keywords": "剪辑、时间线、OpenFilm、ChatCut、合成、字幕、SFX、BGM、混音、候选导出、timeline",
        "inputs": "First Full Cut 模式需要同版简报、可生产脚本、粗分镜、CI骨架和平台选择；最终模式再需要②–⑥、⑫的已标识交付及来源台账。",
        "outputs": "可编辑工程、候选视频、字幕、独立音轨、实际时间轴清单、混音与变更记录。",
        "refs": [("first-full-cut.md", "完整粗剪优先"), ("editorial-style-and-subtitles.md", "短语级双语字幕门禁"), ("production-standard.md", "剪辑与成片标准"), ("ci-and-media-standard.md", "版式和素材节奏"), ("visual-uniqueness.md", "最终时间轴去重"), ("animation-sound-design.md", "声音分工"), ("a-roll.md", "主持同步")],
        "must": [
            "只在锁定平台工程中组装，并绑定所有上游产物的版本/哈希。",
            "保留口播、原声、SFX、BGM可编辑独立轨，按声音主次和让位窗口完成混音。",
            "落实字幕、来源、Logo、进度条、安全区、满屏适配及A-roll同步。",
            "从实际时间线导出素材区间和动画实例，执行唯一性及3–5秒规则检查。",
            "可生产脚本和粗分镜就绪后，立即建立目标时长完整时间线；每句用正式或显式临时画面覆盖，导出 First Full Cut 并记录复建方式。",
            "First Full Cut 后在同一整片上横向替换素材、配音、动画/SFX、BGM与混音；上游实质变化时只标记受影响时间线失效。",
            "锁定一个观众字幕渲染权威，清点全局烧录层、VTT/SRT自动轨、编辑器字幕轨及源片烧录字幕；工程预览与最终像素均不得出现两份。",
            "First Full Cut 生成哈希绑定完整性报告；最终候选提交 `swainwong.final-visual-gate.v2`，检查分段导航最终像素、同源连续区间、有效放大倍率、禁用主画面、可读页时长和 Logo；剪辑岗不得自行生成 candidate AV PASS。",
            "对每个实际镜头覆盖起点／中点／终点；固定间隔抽帧只能补充，不能替代短镜覆盖。候选机器门禁通过后交 G3，等待独立审核。",
            "逐单元继承 sentence/claim/source/event-date/semantic_status，不得在构建时重排或丢字段；最终导出须在明确 cue 内核对单一中英字幕像素，而不只检查 VTT 和配置存在。",
            "source-use manifest 必须同时登记主画面与事实截图叠加层 origin；同一网页不同截图仍按同源处理，最终 visual units 把 evidence_overlay_origin_ids 传入机器门禁。",
            "最终 visual units 从实际时间线计算第三方覆盖率及其内部视频占比，并把简报锁定下限交 coverage_policy；比例合格仍需保留分镜定义的原创解释段。",
            "将分镜 visible_evidence 的 claim/source/locator/date/绝对屏显区间原样落实到最终像素和 manifest；不得用一个泛化网页截图声称证明多个未显示段落。",
            "以最终口播音频为时钟，把中英字幕切成一一对应的短语 cue；每个 cue 运行 `subtitle_phrase_gate.py` 检查时码、时长、字数、阅读速度和单语行数，再做最终像素可读性审核。",
        ],
        "forbidden": [
            "不得静默改文案事实、声音身份、素材权利、动画语义或锁定CI。",
            "不得默认全部实拍静音、叠两个人声抢话或抽掉已要求贯穿的BGM。",
            "不得把背景遮满后虚算第三方主画面，或以切镜/推拉/字幕变化掩盖重复。",
            "不得把时间线预览说成最终导出，或把导出成功说成创作验收。",
            "不得替⑥修动作SFX设计、替⑫选全片音乐后隐藏责任变更。",
            "不得因轨道或文件存在就宣称SFX/BGM已配置，也不得以全片响度掩盖单轨在上下文中不可闻。",
            "不得在完整粗剪出现前把任一 30–45 秒片段精修到成片级，也不得用缺章或占位文案抢跑。",
            "不得用项目自建 JS 的 PASS、图层存在、DOM 公式或素材可解码代替插件最终视觉门禁；不得把制作岗自检写成独立 G3 或 candidate AV PASS。",
            "不得按素材数组顺序、取模或固定间隔机械分配画面，也不得仅因比例、哈希、解码和来源出现门禁通过就忽略画面与口播语义错配。",
            "不得只核 primary source 唯一性、却让重复事实截图以 overlay 名义跨镜复用；不能用不同 crop 或 claim ID 绕过。",
            "不得把整句或多分句合并成一个长时字幕块，也不得用固定 47 句、禁用自动切分或‘完整句更准确’覆盖短语级可读性合同。",
        ],
        "evidence": "工程/时间线、候选文件与哈希、轨道和素材区间清单、混音参数、复建命令及自检范围。",
    },
    {
        "number": "08", "code": "D", "slug": "delivery", "title": "技术交付与归档", "noun": "交付包与审片入口",
        "description": "Use when 作为 SwainWong 视频工作流的⑧技术交付与归档 Agent，对实际导出做技术检查、启动绑定视频哈希的审片页、打包可编辑产物和台账；不负责把技术成功冒充连续视听或用户批准。",
        "keywords": "交付、归档、ffprobe、decode、字幕、响度、hash、审片页面、review-feedback、清理、delivery",
        "inputs": "⑦候选/最终导出、工程、字幕、分轨、台账、审核状态、清理与交付范围。",
        "outputs": "技术报告、交付包、文件清单/哈希、审片页面、反馈路径、归档与真实未完成项。",
        "refs": [("review-gates.md", "成片技术与交付关口"), ("video-feedback.md", "审片页面和提交状态"), ("harness-feedback.md", "反馈沉淀"), ("production-standard.md", "文件和交付标准")],
        "must": [
            "对实际交付文件记录绝对路径、SHA-256、时长、流、帧率和技术检查结果。",
            "分别执行全解码、字幕时码、音轨、响度/真峰值及规定的版式检查。",
            "为 First Full Cut、完整候选和返修版启动绑定实际视频、项目和真实对话的审片页；内部门禁前只用 `--audience internal`，`owner-review-ready` 后才可用 `--audience owner`。",
            "区分 saved、preview、queued、sent、agent_received、返修完成和验收状态。",
            "打包成片、可编辑工程、字幕、Logo、必要分轨、来源/唯一性/审核记录与未完成项。",
            "按授权清理，保留人类原始素材及仍被工程引用的必要资产。",
            "交付前核对 `editing-final` 的最终视觉门禁、三份 G3、`candidate-internal-gate` 与 `owner-review-ready` 均绑定同一哈希；用户否决后立即把该哈希退回 `REVISE`。",
        ],
        "forbidden": [
            "不得把ffprobe、解码、ASR、响度、抽帧或评论关闭当成连续视听验收。",
            "不得把saved/queued说成Agent已收到，或把agent_received说成已返修。",
            "不得覆盖旧视频评论、挪用旧时码/哈希或拿另一平台PASS代替本平台。",
            "不得擅删原始素材、必要工程资产，或把预览称为最终交付。",
            "不得把 `NON_RELEASE_TEST_RENDER_OVERRIDE`、零秒视听覆盖或 `PARTIAL/UNAVAILABLE` 包装成视频完成；只能显著标注为诊断候选。",
            "不得把内部诊断页的 URL 当作用户验收链接；`--audience owner` 启动失败时不得改状态文件或参数绕过。",
        ],
        "evidence": "交付清单/哈希、技术日志、审片URL与进程身份、反馈目录、归档/清理记录及状态矩阵。",
    },
    {
        "number": "09", "code": "Q", "slug": "director-review", "title": "编导与视听审核", "noun": "独立编导审核报告",
        "description": "Use when 作为 SwainWong 视频工作流的⑨独立编导与视听审核 Agent，检查主线、爆点、人物弧、动作因果、节奏、原声窗口及实际听感；必须独立于作者和制作岗位。",
        "keywords": "独立审核、编导、叙事、节奏、爆点、人物弧、原声窗口、实际听审、PASS、REVISE",
        "inputs": "同版简报、研究/脚本/分镜/声音合同、First Full Cut 或成片及其哈希、未覆盖说明。",
        "outputs": "绑定版本的独立报告：覆盖、问题位置/证据/修复、严重度及PASS/REVISE/PARTIAL/UNAVAILABLE。",
        "refs": [("review-gates.md", "独立审核门槛"), ("storyboard-contract.md", "叙事动作声音合同"), ("animation-sound-design.md", "动画SFX听审"), ("a-roll.md", "A-roll G1/G2/G3")],
        "must": [
            "首次判断独立完成，不先读其他审核人的结论或预期答案。",
            "检查主线、钩子/爆点、承诺回收、人物弧、动作因果、节奏和制作可执行性。",
            "对 First Full Cut 做完整结构诊断；对成片按正常速度实际观看并真实听审口播、原声、SFX、BGM及混音，二者结论不得混用。",
            "逐条给出场景/时码/原句、问题为何成立、严重度、证据和具体修复。",
            "明确实际覆盖与未覆盖；Critical/Important关闭且覆盖完整才签PASS。",
            "对候选片五项门禁逐项给感知结论，尤其确认口播不仓促、SFX可辨、BGM可闻；不能合并成“音频正常”。",
            "G3 输出一份 `swainwong.review.v1`：candidate SHA、reviewer_id、producer_id、正常速度最终文件审核方法、0–结尾覆盖、真实听审能力、逐项 findings 与状态。不能只写自由文本结论。",
        ],
        "forbidden": [
            "不得由作者或主Agent换身份自审，也不得接受暗示通过的答案。",
            "不得用脚本可行、静帧、ASR、波形、响度或解码代替实际视听。",
            "不得用平均分掩盖Critical，或把旧版本PASS继承给新版。",
            "不得直接修改制作产物后继续以独立审核者身份签同一变更。",
        ],
        "evidence": "审核者身份、输入哈希、实际看听范围、逐条问题、复审记录和最终状态。",
    },
    {
        "number": "10", "code": "V", "slug": "visual-review", "title": "视觉语义与美术审核", "noun": "独立视觉语义报告",
        "description": "Use when 作为 SwainWong 视频工作流的⑩独立视觉语义与美术审核 Agent，逐镜检查观众实际看见和理解的对象、关系、动作、排版、品牌、图表、重复与误读；不依据源码意图替画面辩护。",
        "keywords": "视觉语义、美术审核、观众理解、误读、对象、关系、遮挡、排版、品牌、图表、去重",
        "inputs": "同版简报、逐镜合同、CI、素材/唯一性台账、实际 First Full Cut 或成片及哈希。",
        "outputs": "绑定版本的逐镜视觉报告：看见什么、理解什么、误读/缺失、证据、修复、严重度和结论。",
        "refs": [("review-gates.md", "视觉审核门槛"), ("visual-semantics.md", "对象关系理解"), ("visual-uniqueness.md", "画面去重"), ("ci-and-media-standard.md", "版式CI"), ("animal-motion-review.md", "动物动作")],
        "must": [
            "先看实际画面/连续片段，再读实现说明；逐镜写观众首先看到和理解什么。",
            "核对对象身份、关系归属、动作因果、地域/阶段、标签、图表和口播是否一致。",
            "检查第三方素材和一般整镜效果第二次使用、同源派生及短镜遗漏。",
            "检查字幕、来源、Logo、进度条、安全区、满屏、裁片边缘、碰撞和运动极值。",
            "动态动作按正常速度看；局部截图只给局部结论并标未覆盖。",
            "对照简报检查禁用素材类型，并清点所有观众字幕渲染来源；矢量禁令或双字幕命中即 `REVISE`。",
            "对最终进度条检查全部章节同时可见、段宽按真实时长、标题／分隔线存在、各边界前后与全片线性累计填充；图层存在或单条全局线不通过。",
            "清点低清放大镜头：核源宽高、输出框、zoom、有效线性放大倍率与最终像素；可解码和满屏不等于清晰。",
            "每个实际镜头至少检查起点／中点／终点，逐一捕捉短闪卡、瞬时双字幕、Logo／来源跳位；可读页不足最短停留即 `REVISE`。",
            "G3 输出一份 `swainwong.review.v1`，绑定 candidate SHA、独立 reviewer／producer 身份、覆盖与能力，并逐项填写 `visual_asset_policy`、`subtitle_single_authority`、`chapter_labels_and_segmentation_visual`、`brand_overlay_visual`、`source_perceived_quality`、`short_shot_readability`；不能用制作自检或机器台账代替。",
        ],
        "forbidden": [
            "不得依据代码、分镜意图或文件名猜观众应该看懂。",
            "不得用固定间隔抽帧证明短镜无重复、动作自然或全片无遮挡。",
            "不得把裁切、换色、换字幕、换数据、换ID的同构画面判成新表达。",
            "不得越权修改画面后继续以独立审核身份签同一变更。",
        ],
        "evidence": "审核者身份、输入哈希、逐镜/时码观察、并排重复证据、动态覆盖、问题与复审状态。",
    },
    {
        "number": "11", "code": "F", "slug": "fact-review", "title": "事实与引用审核", "noun": "独立事实审核报告",
        "description": "Use when 作为 SwainWong 视频工作流的⑪独立事实与引用审核 Agent，核验正文与画面中的人物、日期、阶段、数字、因果、引文上下文和来源；不为锁定观点护航，也不把转载当独立证据。",
        "keywords": "事实审核、引用审核、claim、人物、日期、阶段、数字、因果、上下文、来源、unknown",
        "inputs": "同版简报、①研究包、②脚本、③分镜、素材来源台账及实际画面/成片。",
        "outputs": "claim/scene-source 映射、冲突与未知项、严重度、具体修复及PASS/REVISE/PARTIAL/UNAVAILABLE。",
        "refs": [("review-gates.md", "事实审核门槛"), ("production-standard.md", "事实与来源"), ("visual-semantics.md", "画面语境"), ("production-brief.md", "事实冲突与版本变更")],
        "must": [
            "独立核每个关键claim及对应画面，记录来源、入出点、事件/拍摄/发布日期和上下文。",
            "核人物、地点、物件、比赛/事件阶段、数字口径、计算、因果与引文完整性。",
            "区分原始证据、转载和未知；事实与方向冲突时提交证据并阻断依赖错误结论的生产。",
            "检查文字正确但画面错误、年代错配、Logo/奖项/场合误认等跨模态问题。",
            "绑定输入版本和实际覆盖，修改后复审受影响claim/scene。",
        ],
        "forbidden": [
            "不得把转载、搜索摘要、字幕或旁白自身当作独立事实证据。",
            "不得用年份小字治愈当前事件配旧现场的语境错误。",
            "不得为已锁定观点删冲突证据、编来源或把unknown写成PASS。",
            "不得修改研究/脚本后继续冒充同一变更的独立审核者。",
        ],
        "evidence": "审核者身份、版本哈希、claim/scene-source表、原文范围、冲突/未知、修复和复审记录。",
    },
    {
        "number": "12", "code": "B", "slug": "bgm", "title": "BGM配乐", "noun": "独立BGM轨与音乐使用表",
        "description": "Use when 作为 SwainWong 视频工作流的⑫BGM Agent，依据全片结构选择或制作跨镜头配乐，设计情绪、接续、循环、淡化及对人声/SFX让位；不负责动画SFX或最终混音。",
        "keywords": "BGM、配乐、跨镜头、段落情绪、循环、交叉淡化、ducking、人声让位、音乐授权、music cue",
        "inputs": "同版简报、②结构、③声音段落、④口播时码、⑥SFX事件、⑦时间线范围及音乐授权边界。",
        "outputs": "独立可编辑BGM轨/素材、全片音乐使用表、来源许可、入出点/增益/淡化/接续/让位和试听状态。",
        "refs": [("animation-sound-design.md", "⑥/⑫/⑦职责边界"), ("production-standard.md", "声音与授权"), ("storyboard-contract.md", "声音段落设计"), ("review-gates.md", "真实听审")],
        "must": [
            "根据全片主线和段落情绪设计跨镜接续，不随每个动画片段重启音乐。",
            "登记音乐来源/许可、素材哈希、全片时间码、循环/交叉淡化、增益和让位区间。",
            "依据口播、人物原声、环境声和⑥SFX设计ducking与留白，保持语言清晰。",
            "交付独立可编辑BGM轨及上下文试听版；与⑦核对最终时间线接缝。",
            "时间线或口播结构变化后复核受影响段落并更新音乐使用表。",
            "在完整候选混音中实际确认BGM按要求可闻；First Full Cut 可将BGM列为显式 placeholder，但后续不得以轨道存在代替真实可闻。",
        ],
        "forbidden": [
            "不得承担⑥动画事件SFX，或把短音乐性动作提示一概改名为BGM。",
            "不得把BGM烧进动画文件、只交不可分混音或替⑦签最终混音完成。",
            "不得在用户要求贯穿时无故抽掉BGM，或用整段静音代替已设计的让位。",
            "不得用cue数量、波形、响度或播放成功替代完整上下文真实听审。",
            "不得使用来源/许可不明音乐，或把本集音乐固化成永久默认。",
        ],
        "evidence": "独立音乐文件/工程与哈希、music-use表、来源许可、实际试听范围、与人声/SFX让位及接缝复核。",
    },
]


def role_folder_name(role: dict) -> str:
    return f"{role['number']}-{role['slug']}"


def method_markdown(role: dict) -> str:
    refs = "\n".join(
        f"- 需要{purpose}时读取 [{filename}](../../references/{filename})。"
        for filename, purpose in role["refs"]
    )
    return f'''# {role["number"]} · {role["title"]}内部方法

这是 `$swainwong-video-workflow` 内部调度的{role["title"]}责任模块，不是可独立发现或由用户直接调用的 Codex Skill。子 Agent 开始任何实际工作前，完整读取 [本岗位 Harness](HARNESS.md)。只处理任务包授权的范围；总流程、用户输入、跨岗位依赖和最终汇报由主 Agent 管理。

## 输入与输出

- 必需输入：{role["inputs"]}
- 核心输出：{role["outputs"]}
- 输入缺失、版本不一致或上游未通过时，返回缺口和所阻断的依赖；继续不依赖缺口且已授权的工作。

## 共享合同路由

{refs}

共享合同是详细规则的唯一维护位置。本岗位 Harness 提供职责路由和高风险约束，不复制或改写共享阈值。

## 返回主 Agent

返回岗位编号、输入版本/哈希、实际完成范围、产物绝对路径/哈希、检查证据、未覆盖项、下游影响，以及 `READY / REVISE / PARTIAL / UNAVAILABLE`。`READY`只表示本岗位交付合同满足，不代表全片或其他岗位已通过。
'''


def harness_markdown(role: dict) -> str:
    must = "\n".join(f"| {role['code']}-M{i:02d} | {rule} |" for i, rule in enumerate(role["must"], 1))
    forbidden = "\n".join(f"| {role['code']}-F{i:02d} | {rule} |" for i, rule in enumerate(role["forbidden"], 1))
    return f'''# {role["number"]} · {role["title"]} Harness

[返回岗位方法](METHOD.md) · [工作流总 Harness](../../harness/HARNESS.md) · [岗位索引](../INDEX.md)

## 职责边界

本岗位对“{role["noun"]}”负责。关键词：{role["keywords"]}。这些词用于 Codex 路由和任务包检索，不扩大岗位权限。

## MUST DO

| ID | 必须做 |
|---|---|
{must}

## FORBIDDEN DO

| ID | 禁止做 |
|---|---|
{forbidden}

## 放行证据

{role["evidence"]}

没有上述实际证据时不得将本岗位写成 `READY`。文件存在、字段完整或工具成功只证明相应技术事实；需要看、听或独立判断的项目仍按实际覆盖报告。

## 失败处理

命中 FORBIDDEN、输入版本不一致、关键证据缺失或产物无法复建时，标记 `REVISE`；只完成局部范围时标记 `PARTIAL`；能力或资源不可用时标记 `UNAVAILABLE`。列出问题位置、证据、责任边界、最小修复和受影响下游。不得越权代替其他岗位修复后继承其审核身份。
'''


def index_markdown() -> str:
    rows = "\n".join(
        f"| {role['number']} {role['title']} | [{role['number']}-{role['slug']}/METHOD.md]({role_folder_name(role)}/METHOD.md) | [{role['code']}]({role_folder_name(role)}/HARNESS.md) | {role['noun']} |"
        for role in ROLES
    )
    return f'''# 内部岗位方法与 Harness 索引

[返回工作流入口](../SKILL.md) · [返回总 Harness](../harness/HARNESS.md)

这里的十二个岗位是 `$swainwong-video-workflow` 的内部角色模块，不是十二个平级 Skill。目录内故意不放 `SKILL.md` 和 `agents/openai.yaml`，因此不应作为可直接 `@` / `$` 调用的入口暴露。主 Agent 根据任务依赖选择模块，并把相应 `METHOD.md` 与 `HARNESS.md` 明确附给执行该职责的子 Agent；不要求十二个岗位同时运行。

| 岗位 | 内部方法 | Harness | 主要产物 |
|---|---|---|---|
{rows}

## 调度规则

- 任务包必须包含岗位编号、简报版本/哈希、上游产物、适用规则 ID、期望输出、放行证据和未决事项。
- 子 Agent 不重新向用户索要主 Agent 已锁定的答案；缺口、冲突和条件变化回传主 Agent。
- 岗位 `READY` 只说明该岗位交付满足，不自动使下游关口或整片通过。
- ⑥负责动画及动作组 SFX；⑫负责跨镜/段落/全片 BGM；⑦负责最终时间线混音。
- ⑨⑩⑪首次判断彼此独立，也独立于作者和制作岗；返修后复核受影响范围。
'''


def write_file(path: Path, content: str, update: bool) -> None:
    if path.exists() and not update:
        raise FileExistsError(f"Refusing to overwrite existing file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workflow-root",
        type=Path,
        default=Path.home() / ".codex" / "skills" / "swainwong-video-workflow",
    )
    parser.add_argument("--update", action="store_true")
    args = parser.parse_args()
    root = args.workflow_root.resolve()
    write_file(root / "roles" / "INDEX.md", index_markdown(), args.update)
    for role in ROLES:
        folder = root / "roles" / role_folder_name(role)
        write_file(folder / "METHOD.md", method_markdown(role), args.update)
        write_file(folder / "HARNESS.md", harness_markdown(role), args.update)
        print(folder)


if __name__ == "__main__":
    main()
