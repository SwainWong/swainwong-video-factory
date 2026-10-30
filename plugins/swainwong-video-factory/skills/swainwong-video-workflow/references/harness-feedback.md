# 审片反馈 → Harness 持续沉淀合同

[Harness 主入口](../harness/HARNESS.md) · [审片与提交合同](video-feedback.md)

## 插件服务入口

安装 `swainwong-video-factory` 插件后，优先使用本地 MCP 的 `feedback_capture_evidence`、`feedback_record_analysis`、`feedback_get_progress` 和 `feedback_promote_candidate`。这些工具调用当前文件同一套证据与晋升函数，不创建第二份规则状态；MCP 成功只证明对应持久化操作完成，不代表返修、独立审核或用户验收完成。CLI 继续作为可检查、可恢复的后备入口。

## 自动完成与 Agent 职责

页面保存评论时记录 `harness_target=auto/must/should/must_not/verification/project_only`，默认 auto。类别是用户意向，尚不是规则结论。旧评论无此字段时按 auto 读取。原有本期／长期候选范围保留，用户只需填写具体观察。

预览本轮消息时，服务从绑定视频截取 JPEG；区间评论另生成保留可用音轨的 MP4。每条片段最多 30 秒、每轮累计 60 秒，最多自动取证 50 条，防止每轮无限复制媒体；原选区与实际提取区间分别登记。EOF 截图定位到最后可解码帧，浏览器时间及视频平均帧率不等于精确帧号。失败或预算外项保留原评论并标缺口，不能把缺证据当作问题不存在。截图来自视频渲染结果，**不是整个浏览器界面的截图**；页面布局问题可由 Agent 另行检查实际页面并附证据，不冒称服务已截图页面 UI。

每个提交目录保存：

- `snapshot.json`、`message.md`、`state.json`：原有不可变提交与发送状态。
- `harness-intake.json`、`evidence/`：待解析项、原视频哈希、时码、媒体文件及各自哈希。
- `harness-analysis/<revision>.json`：Agent 分析历史。
- `harness-progress.json`：页面显示的最新解析／候选／确认结果，与送达和返修状态分开。

预览只创建证据和待解析项，不改 skill 规则。目标 Agent 实际收到后按原合同确认接收，随后完成以下步骤；不能因为接口返回成功就自动声称理解过画面。

## 每条评论的处理

1. 核对提交号、目标线程、视频身份及快照；查看截图，动态反馈还要按实际速度查看对应片段，音频反馈实际听。自动取证不足时补核原选区，原视频不可用则保持证据不足。
2. 保留用户原话，将观察、理解、具体返修、可复用规则分开。检查现有四类清单和详细合同。
3. 每条选一种结果：`existing_rule`（已有规则执行失败，引用 ID）、`project_only`（只修改本期）、`candidate`（新增或修订规则候选）、`needs_evidence`（证据不足）。不能为了沉淀而每条新建规则；多个反馈支持同一规则时在分析中关联。
4. 新候选归入四类之一，并写明适用条件、例外、检查证据、失败处理及冲突检查。页面指定类别需要调整时说明理由。scope 为 project 的反馈允许形成待审候选；`harness_target=project_only` 明确禁止创建候选。
5. 派返修与独立核对。主 Agent 负责协调，不冒充制作或独立审核；记录实际参与者，能力缺失如实保留。
6. 用下述命令写回分析。没有调用成功或没有产物，不能声称“已沉淀”。本轮解析不等于返修完成，候选不等于长期规则确认。

## 分析写回格式

分析 JSON 需提供 `submission_id`、`video_sha256`、实际 `agent_id` 和 `decisions`。每条评论恰好一项 decision：

| 字段 | 要求 |
|---|---|
| comment_id | 快照内原始评论 ID |
| disposition | existing_rule / project_only / candidate / needs_evidence |
| interpretation / reason | 理解以及这样处理的依据 |
| coverage | 实际看／听范围及未覆盖项，不用“检查通过”代替 |
| repair_action | 本期具体返修，或写明无需返修的理由 |
| existing_rule_ids | 关联现有规则 ID 列表；existing_rule 必须非空 |
| group | candidate 必填 must / should / must_not / verification |
| rule / applies_when / exceptions | candidate 必填可执行条款、适用条件、明确例外（无则说明） |
| check_evidence / failure_action / conflict_check | candidate 必填验收证据、失败处理、既有规则与候选的冲突核对 |

```bash
python3 /absolute/path/to/swainwong-video-workflow/scripts/harness_feedback.py record --snapshot /absolute/submissions/SUBMISSION_ID/snapshot.json --analysis /absolute/analysis.json
```

快照、视频哈希或评论集合不一致会拒绝写回。完全相同的分析重复提交返回已有结果；修改分析建立新修订，保留旧记录。候选写到对应分类的 `candidates/<submission-id>-<comment-id>/<revision>.json` 和 `.md`；候选文件明确标注未生效。项目原始评论不会被改写，页面只读处理状态。

对取证失败项先使用 needs_evidence。原视频恢复后运行 `harness_feedback.py capture --snapshot /absolute/snapshot.json`，工具重新核对原视频哈希并生成独立补充取证清单，保留原快照不变；在新分析中附返回的 `evidence_manifest` 与 `evidence_manifest_sha256` 再 record。不能拿新版补旧版，也不需要重发用户消息。

## 从候选纳入正式规则

新规则不能仅凭一次喜欢、提交、自动分类或 author 自检生效。独立核对：是否忠实原话，是否真能复用，推荐是否被错升为硬性要求，例外是否保留，是否已被已有规则覆盖或与之冲突。用户明确接受具体条款和范围后，保存审核与确认依据 JSON：

- `candidate_sha256`：实际候选 JSON 的 SHA-256。
- `reviewer_id`：实际独立审核者，与提炼者不同。
- `review_status=PASS`、`review_evidence`：真实审核结论和报告位置／依据。
- `confirmation_basis`：真实用户确认的消息／记录及明确内容；不能由 Agent 捏造。
- `confirmed_scope`：与候选 `applies_when` 一致；范围有变化先修候选。
- `conflicts_resolved=true`：已核对并解决冲突的实际结论。

```bash
python3 /absolute/path/to/swainwong-video-workflow/scripts/harness_feedback.py promote --candidate /absolute/candidate.json --approval /absolute/approval.json
```

工具核对版本绑定、独立身份字段和确认范围，写到同分类 `confirmed/` 并链接索引，记录确认历史。它验证记录完整性，**不能独立判断填写的用户确认或审核是否真实**；Agent 必须核对实际对话与报告。页面没有直接晋升规则接口。旧分析已被替换则不能晋升；同一评论已经生效的规则若要修订，须明确更新／替代旧条款并保留历史，不能并排叠加矛盾禁令。

正式条款若同时影响原 references 合同，维护岗位必须同步核对原合同，避免与原规则形成双版本；工具追加索引不代表冲突已自动消除。Codex 记忆不在此链路中自动修改。

## 可见状态与运行边界

页面分别展示消息是否排队／收到，以及反馈是否已解析、候选数、已确认数和媒体证据入口。刷新后恢复，不能用“已解析”代替“返修完成”。现有原生 MCP 页面仍为实验备选；普通网页是本次新增交互的目标入口，后台快照兼容旧客户端的默认 auto。

已运行的 Python 服务需要重启才能加载后端修改；不能仅刷新 HTML 就声称新后台已生效。服务升级须保留绑定视频、项目、线程与端口，并检查正在发送的提交；禁止为了升级重发 queued／unknown 消息。
