# SwainWong Video Factory

A Codex plugin for editable video production, motion design, evidence-bound review, and reusable filmmaking workflows.

面向 SwainWong / SwainTalk 的视频制作工作流：从主题与脚本，到分镜、素材、声音、剪辑、独立审核和反馈沉淀。插件提供一个公开 Skill：`swainwong-video-workflow`；内部专业岗位、Python 检查工具和本地 MCP 服务共同支持制作。

## 能力与边界

- **完整制作流程**：锁定制作简报，生成可生产脚本，尽快形成整片 First Full Cut，再逐步完善画面与声音。
- **可编辑交付**：按项目选择 OpenFilm、ChatCut 或双平台；外部编辑器与配音工具需另行安装或连接。
- **H01 爆点预告式开头**：从正文提炼爆点，用大字与前景主体构成可选开头模式。
- **D01 主体遮挡标题**：完整文字、真实主体遮挡、统一字体风格与可配置入场。曲线排版是可选适配方法，尚非通用 DOM 模块的内置 API。
- **声音分工**：动画与 SFX 配套设计，BGM 独立制作，最终在剪辑层混音。
- **可追溯审核**：版本与文件哈希绑定，分镜／最终像素检查，独立视听审核，审片反馈与规则沉淀。

代码可以验证依赖、文件、哈希、时序与部分像素条件；渲染成功、抽帧或测试通过不代表视频已完成连续观看、真实听审或用户验收。

## 安装

先克隆本仓库，再通过支持插件的 Codex CLI 添加本地 marketplace：

```bash
git clone git@github.com:SwainWong/swainwong-video-factory.git
cd swainwong-video-factory
codex plugin marketplace add .
codex plugin add swainwong-video-factory@swainwong-video-local
```

安装后在新会话中调用 `$swainwong-video-workflow`，说明主题、目标观众、平台和期望时长。具体 CLI 参数以本机 `codex plugin marketplace add --help` 为准。

本地 MCP 服务使用 Python 3。最终媒体检查还需要 FFmpeg（含 ffprobe）、NumPy 和 OpenCV；实际制作需要对应编辑器、素材与声音服务，仓库不捆绑它们。

## 仓库结构

```text
.agents/plugins/marketplace.json       # 插件发现入口
.github/workflows/tests.yml            # 自动测试
plugins/swainwong-video-factory/
  plugin.json                         # 插件元数据
  mcp.json                            # 本地 MCP 服务入口
  server/                             # MCP 工具
  scripts/                            # 架构冒烟检查
  skills/swainwong-video-workflow/
    SKILL.md                          # 唯一公开 Skill
    references/                       # 制作规范与效果配方
    roles/                            # 内部岗位方法和 Harness
    scripts/                          # 工作流、审核与反馈工具
    assets/                           # 插件自身模板与参考资产
  tests/
docs/                                 # 架构说明与选定的方法沉淀
```

当前插件版本 **0.3.10**，内部机械工作流合同 **4.9**。0.3.10 整理独立 Git 交付与可移植测试，包含 0.3.9 的 H01／D01 经验。两种版本号属于不同层级。源码只在 `plugins/swainwong-video-factory/` 维护；兼容 skill 路径可指向它，安装缓存是版本副本。

## 开发与验证

```bash
python3 -m pip install numpy opencv-python
python3 -m unittest discover -s plugins/swainwong-video-factory/tests -v
python3 plugins/swainwong-video-factory/skills/swainwong-video-workflow/scripts/test_animal_motion_review_gate.py
```

FFmpeg 需通过系统包管理器另行安装。测试使用临时项目与合成夹具，不需要作者电脑的 Codex 配置或已安装的兼容 Skill。测试夹具中的确认和审核字段只用于测试，不得用于生产项目。

## 不进入 Git 的内容

仓库根目录采用 `.gitignore` 白名单：只收录插件、marketplace、CI 和列出的项目说明。视频工程、下载素材、原始参考片、导出成片、配音样本、运行日志、缓存、凭据与本机配置均不收录。文档中的历史本地证据路径不代表对应文件已随仓库分发。

插件自有模板与 CI 参考资产保留在 `assets/`；第三方字体只登记来源和原有许可，不将用户项目里的字体或媒体复制进仓库。此仓库尚未指定开源许可证；第三方内容遵循各自许可，SwainTalk 品牌资产不因此授权再分发。

[制作工作流](plugins/swainwong-video-factory/skills/swainwong-video-workflow/SKILL.md) · [插件架构](docs/swainwong-video-plugin-architecture.md) · [H01／D01 本轮经验](docs/h01-depth-title-lessons-20261030.md)
