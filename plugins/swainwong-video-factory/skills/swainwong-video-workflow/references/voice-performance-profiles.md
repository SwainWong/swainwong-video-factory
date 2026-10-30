# 音色表演个性档案

用于把一个反复使用的音色，与它经过样音观察后形成的口播表演习惯分开沉淀。这里记录的是可验证的表演倾向，不是对真实人物身份、人格或固定口头禅的断言。

## 什么时候建立

满足以下任一条件时建立或更新档案：

- 用户指定一个会反复使用的音色；
- 用户说“学习这个音色的口播风格”；
- 同一音色经过两轮以上试音，需要保留有效的节奏和文案策略。

音色档案和表演档案分开。更换口癖、叠甲、停顿或局部速度，不自动更换声音；改变声音身份，也不自动带入上一音色的口头习惯。

## 档案字段

```yaml
profile_id: tim-yingshifeng
profile_name: Tim - 影视飓风
status: draft # draft | calibrated | accepted | retired
voice_source:
  provider: local-voicestudio
  voice_profile: Tim - 影视飓风
  local_profile_id: 894901d7
  checked_at: 2026-10-15
  availability: ready
  reference_samples: []
  rights_status: user_confirmed_local_use
evidence:
  observed_samples: []
  generated_ab_tests: []
  listener_feedback: []
  confidence: low
delivery:
  mode: natural
  caveat_intensity: light
  verbal_habit_intensity: light
  prosody_intensity: light
  local_rate_intensity: light
  baseline_speed: 1.0
habits:
  connectors: []
  fillers: []
  self_correction: rare
  word_restart: rare_or_off
  sentence_opening: to_validate
  sentence_ending: to_validate
tempo:
  faster_for: [known_background, short_transition]
  slower_for: [new_concept, key_number, conclusion]
  pause_for: [turn, contrast, thought_after_conclusion]
avoid:
  - automatic_expression_tags
  - constant_filler_words
  - unverified_signature_catchphrases
  - medical_or_exaggerated_stutter
  - forced_breath_or_chest_resonance_claims
notes: []
```

字段含义：

- `observed_samples` 只放真实参考片段及时间码；`generated_ab_tests` 只放本机生成结果和听审结论。
- `confidence` 低时只能作为起始假设，不能称为“已学会该人物风格”。
- `connectors`、`fillers` 和 `sentence_opening` 必须有样音证据；没有证据就留空，不为凑口癖硬编。
- `avoid` 是负向约束，优先防止过度表演；不要把表达标签当成必选能力。

## 学习和更新流程

1. 准备至少三类样音：解释事实、讲故事或举例、转折/结论。优先使用清晰且有完整意群的片段。
2. 逐段标注句子开头、连接词、停顿位置、重音、相对速度、自我修正和结尾留白；先记录事实，再写风格假设。
3. 把观察结果写入档案，并标注证据片段和置信度。一次只增加少量规则，不把整段样音概括成“真人感”。
4. 用同一段新文案做 A/B：只改变一个维度，例如口癖、叠甲或局部速度；保留相同音色、基础参数和响度。
5. 10–20 秒诊断通过后，再做 30–45 秒综合试音。听审分别记录音色、节奏/重音/停顿、文字/发音，不把生成成功当成风格学成。
6. 如果某个规则让声音变得刻意，降低强度或删除规则；不要用更多`[sigh]`、`[laughter]`、惊讶类标签补救。

## Tim - 影视飓风：初始草案

这是一个待校准的本地音色档案，不是对 Tim 本人的公开风格定论。

```yaml
profile_id: tim-yingshifeng
profile_name: Tim - 影视飓风
status: draft
local_profile_id: 894901d7
voice_engine: VoiceStudio / OmniVoice 0.5.6
delivery:
  mode: natural
  caveat_intensity: light
  verbal_habit_intensity: light
  prosody_intensity: light
  local_rate_intensity: light
habits:
  connectors: []
  fillers: []
  self_correction: to_validate
  word_restart: to_validate
tempo:
  faster_for: [已知背景, 简短过渡]
  slower_for: [新概念, 关键数字, 结论]
  pause_for: [转折, 反差, 结论后的思考]
avoid:
  - 自动加入 VoiceStudio 预设表达标签
  - 连续堆叠“嗯、啊、呃”
  - 未经样音证实的标志性口癖
  - 把单纯变速称为完整情绪表演
  - 声称已经获得胸腔共鸣或真人换气
next_evidence:
  - 一段事实解释
  - 一段带转折的口播
  - 一段结论和思考留白
```

## 使用优先级

每次生成按以下顺序合并：

1. 用户本次明确要求；
2. 当前项目的 `narration-config.json`；
3. 对应音色的本地表演档案；
4. `speech-style.md` 的轻量默认值。

实际发送给引擎的参数、分句策略、是否使用任何显式表达标记，都要记录在口播表和试音记录中。没有被实际执行或听审验证的意图，只能写成“待验证”。
