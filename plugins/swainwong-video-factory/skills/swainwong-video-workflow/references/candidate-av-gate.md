# 候选片视听准入门禁

适用于完整成片候选的 `candidate-internal-gate`。`editing-final` 先生成候选并通过 `swainwong.final-visual-gate.v2`；G3 三审再绑定该候选哈希；本门禁最后汇总真实视听与三审报告，阻止“文件、轨道、台账都存在，但人实际观看或听取时仍然失败”的候选片进入用户审核或交付。First Full Cut 使用独立完整性合同，允许显式临时项，不能被本门禁误当成成片质量验收。

## 五项不可缺少的判定

同一候选文件必须在正常速度、完整时长下完成实际观看与真实听审，并对以下五项分别给出 `PASS`：

1. `visual_asset_policy`：最终画面遵守简报锁定的允许／禁止素材类型。用户禁止 SVG、代码矢量或通用矢量插画时，布局签名唯一、代码不同或运动不同都不能豁免。
2. `subtitle_single_authority`：同一时刻只有一个观众字幕渲染权威。OpenFilm 全局烧录字幕、同名 VTT／SRT 自动字幕、编辑器字幕轨和源片烧录字幕都计入；保留其中一个，其他关闭、换干净源或安全清理，不能叠成两份。该权威还必须绑定通过的 `swainwong.subtitle-phrase-gate.v1`，最终连续观看确认每个中英块是可读的短语而非整句长段；机器报告不能代替最终像素判断。
3. `voice_pacing`：实际听取口播，确认语速、停顿、重音和句间连接不仓促。参数、字数／分钟、ASR 和总时长不能代替。
4. `animation_sfx_audible`：动作组 SFX 在完整混音中确实可辨、同步且不抢旁白。文件存在、cue 数量、波形或峰值不能代替。
5. `bgm_audible`：BGM 在要求覆盖的区间确实可闻、接续自然并正确让位。轨道存在或全片响度合格不能代替。

另外三项机器门禁必须为 `PASS`：`chapter_navigation`、`source_quality`、`third_party_origin_uniqueness`。它们来自同一候选的 `swainwong.final-visual-gate.v2`，不能由审核者手填字符串替代。机器还要求每个观众画面单元保留 sentence／claim／fact source／event-date／semantic status 合同，并用片头／中段／片尾 cue 对比同帧干净参考，证明最终视频中确有预期行数的字幕像素；它不能理解语义，也不能判断字幕是否重复、内容是否正确。禁用素材是否真的未出现、是否只有一份观众字幕、章节文字是否正确、Logo 是否真实可见、素材观感是否清晰、短镜是否可读，必须由 G3 视觉审片分别填写 `visual_asset_policy`、`subtitle_single_authority`、`chapter_labels_and_segmentation_visual`、`brand_overlay_visual`、`source_perceived_quality`、`short_shot_readability`；G3 事实审核还必须分别填写 `source_semantic_fit`、`event_date_scope`、`claim_visual_alignment`。candidate AV gate 原样绑定这些结论。

任一项为 `FAIL / PARTIAL / UNAVAILABLE`，候选片只能标 `REVISE / PARTIAL / UNAVAILABLE`，不得进入 `owner-review-ready` 或完成态交付。

## 机器可检查的记录

`scripts/workflow_state.py record --status READY` 在 `candidate-internal-gate` 阶段要求产物中恰有一份 `swainwong.candidate-av-gate.v1` JSON，并校验：候选 SHA-256 绑定、视听覆盖完整、方法为正常速度最终文件审核、审核者与制作人分离、三份 G3 报告哈希一致、全部十五项均为 `PASS`、未解决问题为空。

```json
{
  "schema": "swainwong.candidate-av-gate.v1",
  "stage": "candidate-internal-gate",
  "candidate": {"sha256": "...", "duration_seconds": 360.0},
  "producer_id": "07-editing-producer",
  "review_reports": {"g3-director-review": "...", "g3-visual-review": "...", "g3-fact-review": "..."},
  "review": {
    "visual": {"status": "PASS", "coverage_seconds": 360.0, "reviewer": "independent-visual-reviewer", "method": "continuous-normal-speed-final-file-review"},
    "audio": {"status": "PASS", "coverage_seconds": 360.0, "reviewer": "independent-audio-capable-reviewer", "method": "continuous-normal-speed-final-file-review"}
  },
  "checks": {
    "visual_asset_policy": "PASS",
    "subtitle_single_authority": "PASS",
    "voice_pacing": "PASS",
    "animation_sfx_audible": "PASS",
    "bgm_audible": "PASS",
    "chapter_navigation": "PASS",
    "source_quality": "PASS",
    "third_party_origin_uniqueness": "PASS",
    "chapter_labels_and_segmentation_visual": "PASS",
    "brand_overlay_visual": "PASS",
    "source_perceived_quality": "PASS",
    "short_shot_readability": "PASS",
    "source_semantic_fit": "PASS",
    "event_date_scope": "PASS",
    "claim_visual_alignment": "PASS"
  },
  "findings": []
}
```

这份 JSON 只固定记录结构，不能证明审核者真的看听过。伪造覆盖或把播放命令、抽帧、ASR、响度写成感知审核，仍是合同违规。

## 测试渲染与用户否决

`NON_RELEASE_TEST_RENDER_OVERRIDE` 只允许生成内部诊断候选，不得把它称为“视频完成”“最终交付”或当前可验收成果，也不得绕过本门禁进入 `delivery`。向用户展示时必须显著标为“未通过视听门禁的诊断候选”，并列出未完成项。

用户对实际画面或声音明确否决后，该哈希立即视为 `REVISE`；旧的静态检查、技术 PASS、零问题报告和测试 override 不能继续作为有效放行依据。返修版使用新哈希重新完成本门禁。
