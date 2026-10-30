# Runtime requirements

在初始化项目和提交 `editing-final` 前运行：

```bash
python3 scripts/preflight.py
```

硬门禁依赖 `ffmpeg`、`ffprobe`、Python `opencv-python`（导入名 `cv2`）和 `numpy`。它们用于探测真实媒体、读取最终像素、比较候选画面与声明的第三方来源。缺少任一项必须 `FAIL`，不得退化成只信 manifest 的软检查。

`swainwong.final-visual-gate.v2` 能机械证明媒体身份、分段进度像素、来源技术质量、时间线映射和来源画面是否实际出现；它不能替代对审美、语义、清晰感、字幕可读性及真实 Logo 视觉质量的连续人工／独立 Agent 审片。后三类证据继续由 G3 和 candidate AV gate 承担。
