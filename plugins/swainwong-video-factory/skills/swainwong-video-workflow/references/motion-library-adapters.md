# 多动效库的统一风格与接入合同

适用于从 DataMagic 或第三方 GitHub 动效库选配方、改编或跨库组合。一个成片只有一套已确认的视觉系统；多个库提供表达方法和实现来源，不各自带入一套字体、人物、版式和运动语言。本文定义生产合同，不声明存在统一 API、已安装适配器或已完成平台接入。各库只是配方/方法来源，不直接启用它们的总控工作流替代本流程岗位分工（①–⑪及独立⑫BGM）。

## 输入、责任与产物

先遵循[初始简报](production-brief.md)。人类已定的受众、核心方向、画幅、时长区间、语言/音色、字幕、Logo、风格和平台优先于库的 demo；不因某库省事而静默改条件。主 Agent 只派单、转交同版本输入和汇总缺口，不选择未经专业岗审核的替代方案，也不代签 PASS。

| 岗位 | 此合同中的职责与交接 |
|---|---|
| ③分镜与视觉设计 | 从句意、事实和观众需要出发，定义对象/关系/状态/结论；锁定全片视觉规范、角色状态与逐镜布局，提出配方用途和可替代方案 |
| ⑤素材与图像 | 制作并维护共用资产、角色状态、字体与许可台账；交付可辨识、带锚点和版本的资产，而非让每个库重新生成人物 |
| ⑥图表与动画及动效音效 | 核查选定版本实际源码/schema，逐字段映射、适配配方、记录补丁，按实测口播时码制作画面、运动及同步SFX；交付可编辑源码、props、内容层、SFX轨/事件映射和接入说明；无声库的配声仍由⑥负责落地 |
| ⑦剪辑合成 | 将内容层/A-roll放入选定平台，处理全片时间和混音；统一渲染字幕、来源、Logo、章节进度与转场包装 |
| ⑧技术交付 | 核运行时、依赖、素材引用、时间基准、导出和可重建性；保留许可、复现命令及适配记录 |
| ⑨⑩⑪独立审核 | ⑨审解释节奏、语义推进与实际视听；⑩审跨库一致性、主体/排版/动态；⑪审数据、引用语境和来源。失败由主 Agent 派回责任岗，作者自检不替代独立审核 |

⑫BGM独立交付跨镜头音乐轨与接续/让位计划；⑥不将BGM烧入动画片段，⑦按[动画音效分工](animation-sound-design.md)汇总混音。

②标准稿和④最终口播/句子时间映射是制作依赖；①/⑪核实的数据是图表依赖。③可先定视觉结构，不能按估计口播长度签发最终同步通过。

## 口播到视觉匹配，再到选库

③为每个视觉意群交付匹配单：`sentence_id / claim_id`、观众问题、必须看到的对象与关系、数据shape/口径与证据、禁用替代、实测音频起止与揭示时点、候选配方及选择/拒绝理由。先确认配方是否真实表达该句，再做视觉适配；不得为了集齐五个库而选效果，不把缺证据的对象改成无关图表。没有适合配方时可保留实拍或设计新表达，不能让库的输入格式反过来改事实。

## 全片视觉系统不是一段通用 prompt

③交付本期 `visual-system` 与 `ci.json`，至少包含下表；具体数值取本期简报与品牌文件实际版本，不把某次 demo 作为永久值。

| 维度 | 必须明确的约束 |
|---|---|
| 色彩与材质 | 背景、文字、强调、比较色的语义；纸张/印刷/照片的使用方式；纹理比例、透明边缘、纸厚、阴影和光照 |
| 字体与排版 | 实际字体文件/许可、标题/正文/数字/代码字族、字号字重、行距、文本包裹、对齐、留白、长文与数字溢出处理 |
| 布局与边框 | 按画幅定义的网格、内外间距、内容容器、圆角、描边、图表标签及图例；A-roll/字幕/Logo/来源/导航安全区 |
| 对象与角色 | 共用资产ID、身份与状态、参考图、缩放基准、裁切焦点、脚底/手部/物件接触锚点、视线与层级 |
| 运动与镜头 | 进入/强调/离开的时长范围、缓动或弹性约束、运动幅度、相机/视差/切换方法、遮挡次序；非必要不移动 |
| 时间与声音 | 最终fps、分辨率、全片与局部时间映射、句子/音频版本、揭示时点与阅读停留；内容结束后不靠循环填满 |

“暖纸色、剪纸风、自然运动”等统一 prompt 可帮助生成草案，不能代替这些可执行输入，更不能把描述词当成各库都有的参数。真实Logo使用核实资产，不用生成图重画；图表可使用几何，但不得用临时矢量拼人、门店、食品等实体。

## 共用资产合同

⑤维护每个 `asset_id` 的版本/哈希、原始来源与许可、角色/对象身份、`state_id`、像素尺寸与透明范围、缩放基准、锚点、裁切焦点和派生关系。主体在不同库之间沿用相同资产或同一已审核状态库；不能仅因为 prompt 中都写“同一位主持人”就声称身份一致。

⑥明确适配器如何读取资产：URL、本地文件、图像props、视频槽或纹理，以及支持的格式/透明度/尺寸。若原配方只有内置SVG人物，需换为共用裁片或选择另一表达；没有资产入口就记录源码补丁或不支持，不能默默重画近似角色。纸艺状态配准遵循[动作合同](storyboard-contract.md)；A-roll真实视频、原声与口型另遵循[A-roll合同](a-roll.md)。

## 逐配方能力映射

以 `owner/repo@commit:recipe/path` 建立命名空间；本skill的 C01/R01 等内部别名不替代来源身份。不同库的同名配方和不同ID的同构画面分别登记，不能混为一个接口或躲过[唯一性审核](visual-uniqueness.md)。

每条适配记录列出“本期要求 → 原生字段或代码位置 → 映射方式 → 实际值 → 证据/限制”。方式只有以下四类，不把 unsupported 写成“应该支持”：

| 标记 | 定义 | 证据与处置 |
|---|---|---|
| `native` | 原配方公开且实际使用的参数支持目标要求 | 指向该版本schema、props和读取位置；检查参数不是仅声明未使用 |
| `override` | 可通过已经支持的主题/样式/资产注入点覆盖，无须改原实现 | 记录注入范围、优先级及继承边界；验证局部样式未覆盖注入值 |
| `patch` | 需修改源码或加项目适配层 | 保存基准commit、改动文件/补丁、输入输出合同与视觉回归证据；不能冒充原库能力 |
| `unsupported` | 当前版本或当前路径不能实现，或证据不足 | 列具体缺口；改用已支持实现、交⑦合成，或提出需人类决定的条件变化，不静默降级 |

分别核查字体、全部色彩、材质、边框、布局、安全区、资产入口、运动与时间；一个模板有 `color` 不等于整库可换主题。替换背景色后仍须查文字/边框/图例/阴影、单位及数据含义。全片风格需要源码适配时，保留数据/关系正确性，不为统一外观扭曲图表比例或删掉必要说明。

## 原生运行时、确定性时间与目标剪辑平台

在单条配方层记录原生运行时（例如React/Remotion、HTML/Canvas或其他）、依赖版本、入口和实际渲染方式。统一规范是编排合同，不是把所有库装进同一个API；不得假设Remotion组件能直接导入OpenFilm或ChatCut。

⑥选定并证明一种交接：目标编辑器支持的可编辑组件/页面，或按约定编码/透明格式渲染的内容片段，连同可编辑源码、数据和复现命令。需透明叠加时验证真实alpha；普通MP4不冒充透明视频。依赖浏览器事件、滚动、实时音频或CSS循环的动画，要改成可寻址的时间函数，或先在已验证运行时预渲染；不能用屏幕预览可动代替固定fps导出可复现。

全片锁定一个fps，明确秒/帧转换、镜头起点和局部时间；不同库的默认帧率、固定demo时长和随机状态不得直接混入。记录确定性随机种子（如有）、字体/图片加载完成条件、音频哈希、句子时间、揭示/停留/退场点。时间变化影响所有依赖它的字幕、图表、人物动作和剪辑，不能只拉伸视频掩盖不同步。

⑦实际导入并检查原速、拖动/回退、镜头边界、透明度、音轨和最终导出。OpenFilm/CSS、DataMagic配方或其他平台能力，以当前技能、源码和实际样段为准；本文没有新增这些运行时的功能。

## 总包装只渲染一次

⑥输出内容层时关闭模板自带的全局Logo、字幕、页码、章节导航和重复装饰；⑦在总时间线上统一渲染用户确认的Logo、字幕、来源槽、章节进度和必要包装。可共享同一个包装组件，但同一帧只有一个实际渲染责任层，不将包装烧入各片段后再叠一次。章节进度使用全片时间，不能随配方重新开始。

配方里的真实公司Logo、图表标签、数字单位、引文署名是内容，不能误删。代码许可证、字体许可、第三方素材署名/平台披露分别登记，并在其要求的文件/片尾/可见位置保留；视觉统一不构成去除许可声明的理由。移除demo装饰水印与移除法律要求的署名不是同一操作，不能混用授权。

## 接入状态与放行证据

每条“库版本＋配方＋本期数据/资产＋目标平台”独立记录状态，不能给整个库笼统打“可用”：

1. `candidate`：认可作为候选；有地址/目标用途，不等于可执行。
2. `source_checked`：已读指定commit的相关源码、schema、样例和许可，已有能力映射。
3. `adapted`：本期源码/props/资产映射已形成；仍可能未运行。
4. `rendered`：实际渲染成功，保存命令、产物哈希和开头/揭示/末尾证据；不等于观感通过。
5. `editor_import_verified`：在所选平台实际导入、播放与导出检查，保存工程及对应输出。
6. `av_review_passed`：⑨⑩⑪完成本次实际内容、视觉与视听检查，范围/版本明确。高风险技术小样只证明被测能力，First Full Cut 只证明整片结构存在，均不等于最终完整候选通过。

分别保留通过/失败/未执行/能力不可用及原因。G1前核输入、语义、CI和适配可行性；G2用真实字体、资产、数据与音轨检查跨库相邻镜头及最不利长文本；G3看最终导出连续播放。抽帧、props检查、成功日志或哈希都不能单独升级为实际视听验收。换commit、patch、字体、资产、数据、fps或声音时复核相关依赖；不继承不适用的旧PASS。

最小交接包：`brief_revision/hash`、`ci_version/hash`、库URL/commit/许可、命名空间配方ID、基准源码与补丁、原生运行时/依赖、能力映射、props/数据及来源、共用资产清单、分辨率/fps/实测时间表、渲染命令与内容层、目标编辑器工程/接入记录、独立审核报告。此为产物字段合同，不宣称已有同名校验器。

## 现有规则的范围

统一风格允许共用CI、字体、基础代码、角色状态与包装，不允许在同片反复套一般整镜模板。[D01 主体遮挡章节标题](explainer-motion/foreground-depth-title.md)可按限定范围作为章节包装复用；原始素材、观点与阅读设计逐章独立，一般内容模板去重不变。D01 为本地原创 DOM/Canvas 配方，已测的 OpenFilm 演示不代表 ChatCut 或其他库的原生接口；跨平台仍逐适配器验证。换库、换ID、换数据、调色或换人名不能让同构画面变成新表达；按[画面唯一性合同](visual-uniqueness.md)复核。A-roll同源不同有效句段及人物槽例外保持原范围，不能扩大到其下B-roll和图表。

现行“纯第三方素材3–5秒、实质DataMagic叠加可延长至讲解完成”的例外不自动授予其他库。新库可作为讲解内容来源，但不能仅因接入统一合同就延长第三方素材；需要更改该规则时明确提出由用户决定。许可/版权和素材比例也不因技术接入而变更。

## 已核源码事实矩阵

以下仅记录具体版本的源码证据；未执行项保持未执行。GitHub可访问、README声称、候选认可和本地目录存在均不能证明渲染或导入完成。

核查日期：2026-10-23。下列均只到 `source_checked`；我方适配是方案，未据此安装依赖、渲染或测试目标编辑器。版本变化后重新核查选中配方。代码许可与demo中的字体/人像/视频等素材许可分开处理。

| 来源与固定版本 | 已核原生事实 | 我方适配方案与限制（尚未实现） |
|---|---|---|
| DataMagic `3a66365b6dcab798efc76baf54a3039d0b273f2c` | 本地已跟踪且未改动的 [RankedReveal.tsx](https://github.com/HKUSTDial/DataMagic/blob/3a66365b6dcab798efc76baf54a3039d0b273f2c/cards/templates/ranked-reveal/RankedReveal.tsx) 读取 `fontFamily`、行 `iconSrc/color`；底色 `#fbfbfc`、边框 `#d8d9df` 等仍硬编码；[entityVisuals.tsx](https://github.com/HKUSTDial/DataMagic/blob/3a66365b6dcab798efc76baf54a3039d0b273f2c/cards/src/entityVisuals.tsx) 是相关实体展示实现。 | 字体/行图像/行色可按该配方native字段映射，其他主题项需逐处patch；不推广为全库通用主题API。运行时、许可和可导入方式按实际选中配方另核。 |
| video-talkcraft `a7c29edfb2404612dde6a5a1c8aa94232e85625b` | Remotion TSX配方、主题模块与工作台；[theme.ts](https://github.com/Vincentwei1021/video-talkcraft/blob/a7c29edfb2404612dde6a5a1c8aa94232e85625b/template/motion-systems/theme.ts) 的 `C/FONT/bg`、[ThemeFrame](https://github.com/Vincentwei1021/video-talkcraft/blob/a7c29edfb2404612dde6a5a1c8aa94232e85625b/template/components/theme-frame.tsx) 的 `kind/ink/stageBg` 存在，但逐卡不必导入主题。 | 映射已暴露模块/props并patch各卡硬编码与局部CONFIG；外层主题不能保证所有内部样式统一。原生Remotion运行与目标编辑器交接分别验证。[LICENSE](https://github.com/Vincentwei1021/video-talkcraft/blob/a7c29edfb2404612dde6a5a1c8aa94232e85625b/LICENSE) 为PolyForm Noncommercial，商业使用需匹配授权，不能当MIT或以用户视觉认可替代商用许可。 |
| mg-styles-15 `49052d80bfaf9fa8412cc9710530e5e95a3b8d8c` | 独立HTML/Canvas等风格示例。[render.mjs](https://github.com/Vincentwei1021/mg-styles-15/blob/49052d80bfaf9fa8412cc9710530e5e95a3b8d8c/harness/render.mjs) 使用 `DEMO`、`__ready`、`renderAt(t)`；这是时间协议。[Collage](https://github.com/Vincentwei1021/mg-styles-15/blob/49052d80bfaf9fa8412cc9710530e5e95a3b8d8c/demos/06-collage/index.html) 将人物切片、布局和样式绑定具体资产。 | 对选中示例抽取本期视觉参数并patch源码，按共用资产重新配准角色锚点；URL query透传不等于页面支持任意theme参数。代码/提示词/作品在[README](https://github.com/Vincentwei1021/mg-styles-15/blob/49052d80bfaf9fa8412cc9710530e5e95a3b8d8c/README.md)声明MIT，第三方资产另查许可。 |
| lemo-opuscar `3961ddb3d24d8876e0e2754f7790d66908acee51` | 风格prompt、独立demo与共享渲染工具；[paper.js](https://github.com/lemomo-ai/lemo-opuscar/blob/3961ddb3d24d8876e0e2754f7790d66908acee51/styles/paper-popup/demo/paper.js) 有局部 `paperFill/finishCut` 色彩/纸边参数；[TECHNIQUE.md](https://github.com/lemomo-ai/lemo-opuscar/blob/3961ddb3d24d8876e0e2754f7790d66908acee51/TECHNIQUE.md) 规定 `DUR/READY/render(t)`。 | 局部字段可native映射，字体/固定颜色/角色锚点等逐demo patch；STYLE.md是提示词，style.json是目录元数据，均非统一主题API。公共渲染JPEG帧→视频不提供alpha。[许可](https://github.com/lemomo-ai/lemo-opuscar/blob/3961ddb3d24d8876e0e2754f7790d66908acee51/README.md#licence)：代码/文档MIT，demo成片/stills为CC BY 4.0，部分音轨排除，第三方资产另计。 |
| motion-anything `b016900d9ee92fc2d3e4dc520359cc8999d2ed4e` | [DESIGN.md关联机制](https://github.com/nexu-io/motion-anything/blob/b016900d9ee92fc2d3e4dc520359cc8999d2ed4e/app/data/design-systems.js)是prompt注入；[engine.js](https://github.com/nexu-io/motion-anything/blob/b016900d9ee92fc2d3e4dc520359cc8999d2ed4e/app/video/engine.js) 的 `VideoComp` 实际读取layers的font/color/size/src/tracks等。 | 把视觉合同映射到真实layer JSON或所选配方CSS；非所有配方都走VideoComp。radius仅已核矩形分支消费，image/video直接drawImage，人物圆形遮罩须patch或交⑦；[export.js](https://github.com/nexu-io/motion-anything/blob/b016900d9ee92fc2d3e4dc520359cc8999d2ed4e/app/video/export.js)仅video流、alpha:false/H.264，⑦另做口播混音，不当透明素材。[许可及上游](https://github.com/nexu-io/motion-anything/blob/b016900d9ee92fc2d3e4dc520359cc8999d2ed4e/ATTRIBUTION.md)：主库Apache-2.0，vendor/port/reference逐文件核实，卡片存在不证明包含可用源码。 |

Talkcraft的[host-card-glass-board.tsx](https://github.com/Vincentwei1021/video-talkcraft/blob/a7c29edfb2404612dde6a5a1c8aa94232e85625b/template/cards/host-card-glass-board.tsx)虽有 `hostSrc`，其Host示例使用13秒Loop且视频muted；用于A-roll须按take源时间和最终主轨改编，禁止循环口型凑时。工作台主题桥可能回退stub；无报错不等于全片已采用本期CI。MG抽查结果不是对所有示例函数的完整能力证明。


Talkcraft的[时间桥](https://github.com/Vincentwei1021/video-talkcraft/blob/a7c29edfb2404612dde6a5a1c8aa94232e85625b/template/motion-systems/time.ts)区分绝对、shot-local和Sequence-local时间，`useAbs=(frame-lead)/fps+startSec`；我方必须映射时基，不能直接套全片秒数。Opuscar的角色pose绑定其demo绘制资产，不是通用角色ID系统。Motion Anything视频默认loop，A-roll须显式取消循环；加载/seek超时也可能resolve，Promise结束不等于媒体已正确呈现。上述代码能力仍须用本期实材完成样段与目标平台验证。
