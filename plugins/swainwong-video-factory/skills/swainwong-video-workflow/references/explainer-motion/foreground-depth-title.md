# D01 主体遮挡章节标题

用于口播进入新问题、关键转折或独立章节时：同源背景 → 完整大标题／可选矩形文字底板 → 同源主体抠像 → 全片导航、字幕、来源与 Logo。主体可以是人、车、建筑或其他有清晰轮廓的对象；媒介可以是图片或真实视频。它是本技能内部原创配方编号，不是第三方库或 ChatCut 的官方模板名。

用于从正文提炼爆点的整段开头时，读取 [H01 爆点预告式开头](highlight-hook-opening.md)。该模式复用本效果的层级及字体动画，按 opening_hook 登记，不把每个爆点认作正文新章节；复用边界由 H01 单独限定。

## 样式与适用场景

核心样式是横跨画面安全区的完整大标题与自然主体前后层次：字形可以粗重、斜体、带阴影或描边，但字体／字号／颜色和动作语气沿用当前项目 CI，不固定白字、建筑或某一种语言。可选矩形文字底板由项目内容层承载，置于主体后；当前字体模块不生成底板或全片包装。字体、动作及时间的实际可编辑范围见 [D01 对外接口合同](foreground-depth-title-interface.md)。

适用：新问题、因果阶段、关键转折、章节结论前的明确段落入口，素材主体可识别、轮廓可提取且能留出完整阅读时段。人、车、建筑或其他物体均可；图片与真实视频分别保留原媒介身份。

不适用：长引文／密集多行数据需要持续精读、主体遮住关键字且没有可读窗口、抠像边缘不稳定、标题与口播无章节关系（选用 H01 时改查与对应爆点的关系），或当前视觉风格不适合大字遮挡。此时选普通标题、引用卡或实拍标注；不能为了高权重强套 D01。

## 构图饱满度与标题基线

- 前景应在当前画幅中有足够体量和可辨细节，承担口播的核心对象；可用一个强主体或有因果／场景关系的多个主体组成前景。饱满不等于堆数量，也不设固定面积占比。避免小抠图被背景大字压倒，或为放大字而把已成立的前景重新缩成点缀。
- 大字须达到明显的标题层级，与主体轮廓发生自然重叠。若字在上半区、主体在下半区且互不遮挡，单有 z-index 不能形成前后关系。调整两者的尺度、位置与构图，兼顾标题突出、主体识别和短语可读；不能以主体遮满关键词冒充纵深。
- 基线可以是水平直线、拱形、浅波形或其他适合语义的连续曲线，不要求每场整行直立，也不要求每场都弯曲。统一的是项目字体、字重、材质、配色体系及描边／阴影，路径形态可随主体轮廓与标题长度变化。白色、暖金色均只是选择，不固化本次配色。
- 曲线沿基线排布完整 canonical 文本，不按主体几何逐字挖空或分成左右两组。可用保留单一完整文本节点的 SVG textPath 等实际验证过的适配实现；长句先调整路径跨度、弧度、位置或编辑措辞，不为塞进路径而压成小字。注册字体后检查路径两端、末字、标点、描边与画幅边界，DOM 中有完整字符串不代表最终像素没有裁切。
- 入场完成后回到已选定的主构图，曲线布局不需“恢复”为直线。稳定阅读在这一主态完成，不能在场景末尾突然换成顶部小字。H01 的持续状态与相邻主题出入遵循[阅读与切换合同](highlight-hook-opening.md#稳定阅读与主题切换)。

以上是创作与验收规则；现有通用 `createTitle` 仍是 DOM 排版接口，没有曲线参数。曲线适配与整场转场须登记实际实现及编辑／导出验证范围，不能把项目自定义能力写成已经发布的通用 API，详见[接口边界](foreground-depth-title-interface.md#曲线布局与整场转场的能力边界)。

## 选型与章节复用

章节开头的相对编辑选择权重建议为 **3.0**，普通候选基准 **1.0**。先满足语义贴合、主体可分割、标题可读、当前 CI，再比较候选；这只是编辑推荐，不是已有自动评分器、每片必用配额或全片默认动效。用户指定位置或数量时按本期要求执行。一个标题表达一个真实章节观点，不用通用“开篇／总结”或编号充数。

可在同片多个真实章节开头复用 D01 包装，每处使用不同原始素材与独立章节观点；根据语气选择动作，避免机械地连续重复同一入场。每个章节的背景和同源抠像是一个连续 visual_unit。此例外仅针对章节标题包装：不放宽第三方同源重复、一般整镜图表／动画模板去重，不给予纯第三方素材超过 5 秒的延时例外。详见[画面唯一性](../visual-uniqueness.md)。

## 原文、字体与自然遮挡

- `text` 保留完整原始字符串，不截断、省略、trim、normalize 或拆成左右两个词组。中、英及其他语言均用单个 canonical DOM 文本节点保留浏览器 shaping；字素显影与碎片使用整字面副本或遮罩，不能按主体位置改字。
- 暴露字体注册、`fontFamily`、`fallbackFamilies`、`fontSize`、`fontWeight`、`fontStyle`、`color`、`letterSpacing`、`wordSpacing`、`textShadow`、`textStrokeWidth/Color`、`locale`、`direction`、`lineHeight`、`autoFit`、`minFontSize`、`safeInsets`、`top`、`alignment`。加载真实字体后测量；宽度不足时缩字号或由编辑调整原文／布局。不能把超宽裁掉后称“完整”。`minFontSize` 是偏好警告阈值，不是硬下限；警告必须进入可读性审核，不能把极小字自动适配当视觉通过。
- 使用通用 DOM 直线模板时默认按画面安全边界尽量两端对齐（原生 CSS justify）；曲线适配沿已选路径排版。两者均不按主体几何分词、挖空或故意把字藏在主体背后。无可伸缩间隔的单字、单词或特定脚本允许自然排版；不拉伸字形。主体重叠处才被遮挡。
- 原文在 DOM 保全不等于观众可读。安排完整短语可辨的稳定窗口；必要时调整素材构图、主体比例、标题高度或时序，不改为逐字绕主体布局。瞬时入场隐去与稳态缺字分开判断。
- 任意语言的原文保全不代表任意字体都有相应字形。每次新脚本验证实际字体覆盖、组合字、连字、方向及最不利长句。模板不捆绑字体；调用项目登记字体来源与许可。

## 十种进入／出现动画

机器可读表：[D01 registry](foreground-depth-title-registry.json)。进入动画（drop／slide／spring／flip／depth）主要以空间变换抵达位置，出现动画（fragments／grapheme／light／ink／blur）主要改变显现方式；两类统一通过 cues.type 单项选择、可顺序切换，不宣称任意两项叠加。[接口合同](foreground-depth-title-interface.md)列出真实可调幅度／方向与尚未开放项。全部使用局部秒数及确定性随机种子；无独立墙钟、RAF 或 CSS 实时动画。入场完成后回到唯一、完整、没有入场残余形变的标题主态；主态本身可按已选基线弯曲。所有效果副本仍在主体前景下。

| type | 中文名 | 形态与适用语气 |
|---|---|---|
| heavy-drop | 沉重掉落 | 加速坠落、冲击压缩、阻尼回弹；债务、压力、后果 |
| fragments | 碎片重组 | 20 块整字面三角裁片归位；破裂后重建、结构重组 |
| spring | 弹性弹入 | 缩放过冲与轻微阻尼转动；惊讶、活跃切换 |
| grapheme-reveal | 逐字显影 | Intl.Segmenter 字素边界＋原文 Range 区域渐显；逐步提出问题 |
| light-wipe | 光幕扫入 | 方向感知的揭示边＋高光扫过；关键发现 |
| ink-reveal | 墨迹显现 | 有机墨迹区域错时扩展；历史、档案语气 |
| side-slide | 侧向滑入 | 横移、倾斜、模糊归位；切换方向或市场 |
| flip-open | 翻转展开 | X 轴透视展开；翻到下一论点 |
| depth-push | 纵深推进 | Z 轴接近、尺寸与焦点收敛；进入背景或机制 |
| blur-focus | 模糊聚焦 | 原位散焦转清晰；不确定性变得可见 |

每项配置 `at`、`until`、`enterDuration`、`exitDuration`、`seed`；`until` 默认下一 cue 或 `sceneDuration`。`heavy-drop.distance`、`fragments.scatter`、`side-slide.distance/from` 以及 `light-wipe.highlightColor/highlightShadow` 可调。留足入场后的稳定阅读时间，不能把 10 项顺序演示当作正式成片顺序。

按[动画音效合同](../animation-sound-design.md)同步登记声音：沉重掉落冲击点为 `at + 0.62 × enterDuration`；碎片聚合、逐字／墨迹／扫光各按完整动作组设计，选一个短声锚点或一次完整声体，不逐字、逐帧重触发，也不把多个短音拼成长声。⑥动画Agent负责实际SFX、对齐及核对，音效由最终混音层承载，模板不会自动生成声音；登记 cue 不等于真实听审通过。

## 可复用入口与视频帧合同

模板目录：[assets/foreground-depth-title](../../assets/foreground-depth-title/title-layout.js)。包含：

- `title-layout.js`：`await createTitle(element, sceneId, {config, configURL, fontBaseURL, sceneDuration, labelElement})`。`config` 可直接传对象，或用 `configURL` 加载；字体 src 相对 `fontBaseURL`（默认配置 URL 所在目录）。返回 `frame(t, anchor)`、`dispose()`、布局与动作 metrics；重配前 dispose，重新测字并重建动画。
- `title-animation.js`：已排版元素可直接调用 `createTitleAnimation({element, config, sceneDuration})`。原文布局先于动画初始化。
- `subject-compositor.js`：`await createSubjectCompositor({background, foreground, source, baseURL, width, height, duration, fps})`。返回异步 `frame(t)`。图片输入 `source.type=image, src, mask`；视频输入 `type=video, framePattern, maskPattern, frameCount`，`{frame}` 默认五位零补齐。灰度 mask 默认红通道转 alpha；RGBA alpha mask 设置 `maskIsAlpha=true`。`rect` 为同源媒体与 mask 的共同目标矩形；可用归一化 `polygon`／逐帧 `polygons`。本模块不自动分割或追踪主体。
- [配置示例](../../assets/foreground-depth-title/title-config.example.json)：只含可编辑示例文字与系统字体，不带业务素材或字体资产。

DOM 按顺序放置绝对定位、同尺寸的 `#background` canvas、标题（或标题底板＋标题）、`#foreground` canvas；使用同一个 stacking context。所有标题副本须位于前景下，全片 CI 层置于其上。标题需要 `position:absolute; margin:0; padding:0`；父舞台固定项目画幅，避免祖先缩放影响测字。配置色彩、阴影、矩形底板透明度时沿用项目 CI。

```js
const title = await createTitle(titleElement, 'chapter', {
  configURL: new URL('./title-config.json', location.href),
  sceneDuration: 4.7,
});
const media = await createSubjectCompositor({
  background, foreground, source: chapterSource,
  baseURL: location.href, width: 1920, height: 1080, duration: 4.7, fps: 30,
});
window.film = {
  width: 1920, height: 1080, duration: 4.7,
  async frame(t) { await media.frame(t); title.frame(t); },
};
```

视频背景与前景必须使用同一个实际已解码源帧和对应 mask 帧，裁切／缩放／时间偏移一致。附带适配器采用预解码帧序列，是连续视频的确定性导出路径，不把静图推拉冒称实拍视频。也可使用经过实际验证的浏览器解码路径；不能仅 await seek 就假定目标帧已绘制。异步 frame 必须被导出器等待，回退与随机跳帧结果应一致。用真实运动部位和边缘核同步，不把一次 seek 故障上升成所有浏览器普遍禁令。

## 交接与验收边界

以下为章节用途的交接；H01 开头用途按其交接表记录 opening_hook 与 hook_id。逐章登记 `chapter_id/sentence_id`、`packaging_role=chapter_opener`、`recipe_id=D01`、入场 type、编辑权重与选择理由、源身份／权利／派生关系、媒体时间与 mask fps/index、共同变换、完整标题配置、旁白锚点、入场／阅读／退出时间、SFX 事件、源码／配置／导出哈希及实际审核覆盖。

接口与限定集成问题先查 [D01 接口验证项](foreground-depth-title-interface.md)：预加载节点参与真实布局；含装饰框的透明 PNG 另核主体 alpha；SFX 落入实际原生轨并核最终混音。不能仅凭预加载回调、PNG 透明通道或 cue JSON 宣称已完成这些检查。

验收检查：字体与字号至少两个差异配置确实生效；最不利长文本无截断且可读；完整原文与实际 glyph 匹配；只在实际主体重叠处遮挡；图片与视频帧分开登记；视频抽查运动前中后及已知敏感边缘；所选入场正常速度可辨、末态无副本接缝；随机跳帧确定性；最终混音实际听审。字体、资产、尺寸、帧率、效果代码变更后重核受影响项。

本次准入依据为当前对话用户明确要求“测试完成后纳入动画库，并作为口播章节开头高权对象”。未声称存在审片网页提交号或自动 promote 回执；不写 Codex 记忆。基准演示为 `subject-depth-typography-demo-20261026/exports/subject-depth-typography-demo-v3.mp4`，SHA256 `01b2325073a238b62acf05a4795e834aa6be339f4a9cb3160c792f8a7e4601e8`。独立审核 `/root/mixed_typography_review` 的 `production/review-typography.md` 关闭 T01/T02/T03，字体接口、原文、多语样本、10 动作关键帧和六类主体媒体的最终抽样为 scoped PASS；整体 PARTIAL，未连续全速视听。模板接口包装与通用 compositor 属于入库适配，不能直接继承演示哈希或全平台通过；实际运行与差异证据在工作区 `docs/depth-title-library-admission-20261026/`。OpenFilm 原生演示导出成立，不宣称 ChatCut 或其他平台已接入。

3.15 接口沉淀依据：用户本轮明确表示“OK没有问题”，并要求将样式、使用场景及对外可调接口完整纳入 skill。这是本次效果认可与沉淀授权，不构造新的完整视听验收记录。3.15 的字体风格／色彩／字距／描边及光幕高光接口具有实际运行证据，记录在工作区 `docs/depth-title-interface-20261027/`；不把旧演示哈希当成新适配器哈希。
