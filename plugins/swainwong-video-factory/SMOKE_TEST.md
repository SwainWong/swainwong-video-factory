# SwainWong Video Factory 冒烟测试

这个入口验证插件结构、brief 锁定、持久化状态和 research 任务包。它不会生成研究、脚本、素材或视频，也不会伪造任何独立审核、视听验收或用户接受结论。

## 自动架构测试

仓库内的 `tests/fixtures/smoke-brief.json` 只用于自动测试。它的 `brief_confirmed=true` 仅代表测试夹具满足字段合同，不是任何真实视频的用户授权，禁止复制到生产项目。

```bash
python3 -m unittest plugins/swainwong-video-factory/tests/test_smoke_runner.py -v
```

成功只表示：

- 插件仍只有一个公开 Skill；
- brief 被写入项目并绑定 SHA-256；
- research 任务包可派发；
- 后续阶段仍保持 `NOT_STARTED`。

## 收到真实主题后的第一次运行

1. 主 Agent 根据用户主题补齐 `production-brief.md` 要求的全部条件。
2. 将完整 brief 展示给用户并取得明确确认；把真实确认依据写入 `confirmation_basis`，不得复用测试夹具。
3. 保存为新的 JSON，并使用全新的项目目录：

```bash
python3 plugins/swainwong-video-factory/scripts/run_smoke_test.py \
  --project /absolute/path/to/topic-smoke-project \
  --brief /absolute/path/to/confirmed-brief.json
```

4. 检查 `.video-workflow/smoke-report.json` 和 `research-task-packet.json` 后，才开始真实 research 阶段。
5. 每个阶段只可由真实产物和证据推进；渲染成功不等于连续正常速度观看、真实听音、独立审核或用户验收完成。

若目录已存在工作流状态，命令会拒绝覆盖。需要重跑时使用新的项目目录，以保留旧测试的证据链。
