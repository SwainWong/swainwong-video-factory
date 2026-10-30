# D01 对外可编辑接口（3.15）

[样式与适用场景](foreground-depth-title.md) · [10 项 registry](foreground-depth-title-registry.json) · [完整 JSON 示例](../../assets/foreground-depth-title/title-config.example.json)

本合同对应实际 DOM/Canvas 模板，不是统一 prompt。调用者把可编辑值写入配置，再 `await createTitle(element, sceneId, options)`。更改字体、字号、间距、原文或动画配置后，先对旧对象 `dispose()`，再加载、测字、重建；没有实时 `setConfig` API。

## 入口、覆盖与默认

`options.config`（对象）优先于 `options.configURL`（URL／字符串）；都不提供时读取模板同目录的 `title-config.example.json`。合并顺序为内置默认 → `config.global` → `config.scenes[String(sceneId)]`；仅 `safeInsets` 逐边合并，其他对象／数组（含 `animation`、`fallbackFamilies`）整项替换。`fonts` 与 `canvas` 属于配置根，不随 scene 覆盖。需要恢复样式时显式填写目标值，不依赖 null 的隐式回退。

| 入口字段 | 默认／支持范围 |
|---|---|
| config / configURL | 完整配置对象／URL；相对 configURL 以模块 URL 解析，建议调用方显式 `new URL(..., location.href)` |
| fontBaseURL | 配置 URL 所在目录；fonts[].src 相对它解析，可传绝对 URL |
| sceneDuration | 5 秒；正数，最终硬停止，不是固定演示时长 |
| labelElement | null；可选标签 DOM，仅显示当前效果名，正式片无需显示 |
| canvas.width / height | 1920 / 1080；与真实舞台、媒体、导出尺寸一致，单位 px |
| fonts[] | []；每项 `family, src, weight, style`；weight/style 省略为 normal，注册并 await FontFace 后再测字 |

返回 `frame(t, anchor=0)`、`dispose()`、`metrics`、`animationMetrics`。t 是当前章节的局部秒数。所有原文、字体、风格先完成加载与布局，再创建动作副本／字素区域；异步初始化是实际 ready 依赖，不可只发起而不等待。

## 标题字段

| 字段 | 默认 | 支持与计量 |
|---|---|---|
| text | 必填字符串 | 原文不删、trim、normalize 或左右拆组；单 canonical 文本节点 |
| fontFamily | sans-serif | 一个 family 名称；不把逗号拼接串当多个字体 |
| fallbackFamilies | Arial, PingFang SC, sans-serif | 按顺序回退的数组；项目提供所需脚本字体与许可 |
| fontSize / fontWeight | 260px / 900 | fontSize 正数 px；weight 为 CSS 字重。真实加载后测量 |
| fontStyle | 当前宿主 CSS，通常 normal | normal / italic / oblique（支持浏览器接受的斜角语法）；参与 fonts.load 与测字。未提供对应斜体 face 时浏览器可能合成，不冒称原生斜体字形 |
| color | 当前宿主 CSS | 有效 CSS color；例 `#ffffff`，RGBA 亦可 |
| letterSpacing / wordSpacing | normal / normal | 数值按 px；或有效 CSS length／normal。测量前应用；justify 可能再分配词间／字间空间 |
| lineHeight | 1.2 | 无单位倍数或有效 CSS line-height；影响垂直计量与安全区 |
| textShadow | 当前宿主 CSS，通常 none | 有效 CSS text-shadow；支持多重阴影 |
| textStrokeWidth / textStrokeColor | 当前宿主 CSS，通常 0px／当前色 | 数值宽度按 px，或有效 CSS length；使用浏览器 -webkit-text-stroke；颜色为 CSS color |
| locale / direction | zh-CN / auto | locale 对应 lang 与字素分割；direction 为 auto/ltr/rtl。原文原生双向排版 |
| alignment | justify | justify/start/end/left/right/center；整画面安全区排版，禁止按主体几何改字 |
| safeInsets | left88/right88/top130/bottom200 | px；每边可单独覆盖，不能把安全区压至零 |
| top | 205px | 实际取 max(top,safeInsets.top)；不由主体位置反推 |
| autoFit / minFontSize | true / 96px | 真实字体与间距超宽／超高时缩字号；minFontSize 是警告阈值。autoFit=false 时溢出报错，不裁掉原文 |
| animation | 默认 spring 单 cue | 下表；支持 `{cues:[...]}`，保留旧 `{type,...}` 单 cue 形式 |

省略颜色／阴影／描边／fontStyle 时保留当前元素／宿主 CSS，兼容原工程；同一个元素复用后若需重置，显式填写 normal、none、0、目标颜色等值，不能假定 dispose 会撤销作者样式。CSS `!important` 仍遵循浏览器层叠规则。新字段在复制 fragments／sheen 前应用；光幕的高光色单独控制。

DOM 宽高测量包含字体样式与间距，但 CSS 阴影、描边、斜体外沿属于绘制范围，不能仅以元素盒不溢出就宣称没有视觉裁切。按当前效果检查最左／最右字形、阴影及描边的实际截图，留足画幅安全边距；稳定阅读阶段不可缺字。

## 动作选择与时序

**进入动画**用空间变换到达最终位置：heavy-drop、side-slide、spring、flip-open、depth-push。**出现动画**主要改变可见区域、组合或清晰度：fragments、grapheme-reveal、light-wipe、ink-reveal、blur-focus。分类描述主导视觉机制；碎片仍有位移，不把分类当互斥底层算法。

两类都通过同一 `animation.cues[].type` 选择。每个 cue 只运行一个 type，允许顺序切换；不支持任意“进入＋出现”两效果同时叠加。多个 cue 到时后最新开始项接管，不混合前一项。推荐每个正式章节选一个主效果；需要连续 cue 时逐项设置严格递增的 at。

| cue 字段 | 默认／含义 |
|---|---|
| type / label | spring／registry 中文名；type 仅10项，label只用于可选标签 |
| at | 省略时取 frame(t,anchor) 的 anchor，anchor 默认0；单位秒 |
| until | 下一 cue 的 at 或 sceneDuration；到时隐藏；sceneDuration 始终硬停止 |
| enterDuration | 0.85秒，必须大于0；旧 duration 是其别名，enterDuration 优先 |
| exitDuration | 0.16秒，结束前的不透明度淡出；0为直接隐藏，不支持独立退出类型 |
| seed | 1997 + cue索引×101；只影响 fragments/ink-reveal。当前随机函数把0视作1997；同种子可重复，不提供随机自动换种子模式 |

稳定窗口约为 `min(until, sceneDuration) - at - enterDuration - exitDuration`，应给当前标题足够阅读时间。until 超过场景硬边界时淡出可能尚未完成就被场景截断；正式配置应让 until 不超过 sceneDuration。字幕、旁白、SFX 都对齐当前局部时间与全片起点。

| type | 实际额外可调字段（未列出的动力学尚未开放） |
|---|---|
| heavy-drop | distance，默认440px，下落起始高度；方向固定从上方 |
| fragments | scatter，默认630px，控制横向径向散布系数；20片、纵向散布和旋转内置 |
| spring | 无；弹性系数与转动内置 |
| grapheme-reveal | 无；Intl.Segmenter 原文字素顺序，区域在已排版文本上计量 |
| light-wipe | highlightColor=`#fff5c3`、highlightShadow=`0 0 22px #ffe9a8,0 0 42px #fff9`；扫描方向跟随标题实际 ltr/rtl，不是独立 cue.direction |
| ink-reveal | 无；形状网格内置，seed控制错时／位置 |
| side-slide | distance 默认排版宽×0.58px；from=left/right，默认left；倾斜与模糊内置 |
| flip-open | 无；X轴角度与透视内置 |
| depth-push | 无；Z深度、Y角度与模糊内置 |
| blur-focus | 无；散焦强度内置 |

旧名称仍接受：shard-rebuild→fragments、elastic-pop→spring、letter-reveal→grapheme-reveal、slide-in→side-slide。不把不认识的字段写进示例并声称有效。

## 曲线布局与整场转场的能力边界

本表对应的通用 `createTitle`／`createTitleAnimation` 仍是 DOM 直线排版及十种入场，不接受 `path`、`readPath`、`readAt`、曲率或场景转场参数。不能将未知字段塞进配置后声称已经生效。D01 的[曲线构图规则](foreground-depth-title.md#构图饱满度与标题基线)是可选创作能力；选用时另建或复用实际验证过的曲线适配，并登记其真实入口。

本次 H01 项目使用完整单文本 SVG textPath 与共同场景容器，可作为重建参考；尚未将该项目实现发布为跨语言、十种入场或跨平台均已验证的通用库。适配至少交接 canonical 文本、真实字体、路径、样式、关键词入场、稳定主态、场景组退出及确定性 frame(t)，并核末字／标点、自然遮挡、实际字体 shaping、跳帧重绘和最终导出。不能借本次英文样本宣称其他脚本都支持。

由外层容器负责整场退出时，标题应随组保留到退出完成：通用接口可设 `exitDuration=0`，同时保证 cue 的 `until`、`sceneDuration` 及宿主生命周期覆盖这段可见退出区间。仅关掉 fade 但在转场开始时销毁节点，仍会闪退。新主题的标题首次揭示可按语义延后。其他项目若明确选择独立标题退出，仍按该动作设计和检查，不全局废除 `exitDuration`。

## 可直接复制的最小完整调用

复制模板的两个 JS 模块到本期同一目录，再使用下面完整页面。它不依赖业务媒体，用于接口验证；真实工程加入已分割主体，并按[同帧合成合同](foreground-depth-title.md)添加媒体。所有风格值都在配置中可改，不用修改动作源码。

```html
<!doctype html><meta charset="utf-8">
<style>html,body{margin:0;background:#18232b;color:white}#stage{position:relative;width:1920px;height:1080px;overflow:hidden}#title{position:absolute;margin:0;padding:0}#foreground{position:absolute;inset:0;pointer-events:none}</style>
<main id="stage"><div id="title"></div><canvas id="foreground" width="1920" height="1080"></canvas></main>
<script type="module">
import {createTitle} from './title-layout.js';
const config = {
  canvas:{width:1920,height:1080}, fonts:[],
  global:{fontFamily:'Arial',fallbackFamilies:['sans-serif'],fontSize:230,
    fontWeight:900,fontStyle:'italic',color:'#fff0c2',letterSpacing:2,wordSpacing:4,
    lineHeight:1.2,textShadow:'0 12px 20px #0008',textStrokeWidth:2,
    textStrokeColor:'#18232b',minFontSize:96,autoFit:true,
    locale:'en',direction:'ltr',alignment:'justify',
    safeInsets:{left:100,right:100,top:130,bottom:200},top:205},
  scenes:{chapter:{text:'A NEW CHAPTER',animation:{cues:[
    {type:'light-wipe',at:0.3,until:4.7,enterDuration:0.8,exitDuration:0.2,
     seed:2026,highlightColor:'#ffffff',highlightShadow:'0 0 24px #ffcc66'}
  ]}}}
};
const ready=createTitle(document.querySelector('#title'),'chapter',{config,sceneDuration:4.7});
window.film={width:1920,height:1080,duration:4.7,ready,
  async frame(t){(await ready).frame(t);}};
(await ready).frame(1.5);
</script>
```

## 限定范围验证项

- **入口预加载**：使用本 DOM 测字模板时，元素须附着且参与布局。可用 visibility:hidden 或 opacity:0 预加载；display:none 会拒绝测量。若使用另一种已验证的离屏排版实现可以采用，但必须证明字体／字素计量与实际页面一致，不能把此次问题推广成所有预加载方式禁令。
- **透明 PNG 主体**：当 PNG 含相框、装饰边、文字或底板时，整图 alpha 不等于主体 alpha。按真实主体另做遮罩，排除框饰；透明背景本身不能作为抠像验收。纯主体 PNG 可直接用已核实 alpha，不强制重复分割。
- **声音落地**：本模板只提供视觉时序，不产 SFX。OpenFilm／目标编辑器须有可追溯的实际原生音轨／SFX clip，并核最终导出混音是否可闻且对齐。JSON cue 表或单独的音效文件不替代轨道插入与混音；其他已验证的音频管线按其真实交付证据验收。

每次新配置验证字体风格／字号、颜色／描边、间距在实际画面生效，原文完整、自然遮挡、最不利字形无裁切；验证所选 type、at/enter/until/exit 的实际中间态和回退结果。技术或抽样通过与完整正常速度视觉／听审分别报告。本轮用户“OK没有问题”记录为效果认可及沉淀授权，不据此杜撰额外连续视听审核记录。
