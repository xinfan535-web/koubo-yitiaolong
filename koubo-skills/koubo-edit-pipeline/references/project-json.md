# project.json 字段

```json
{
  "orient": "portrait",
  "source": "粗剪/xxx.mov",
  "srt": "粗剪/xxx.srt",
  "keep": [{"srt": 3, "in": 12.40, "out": 15.82}],
  "inserts": [{"file": "图解/图解1.mp4", "at_srt": 14, "until_srt": 17}],
  "chapters": [{"label": "开场", "start_srt": 1}],
  "music": {"file": "…", "gain_db": -22},
  "sfx": [{"file": "…", "at_srt": 14}],
  "short": {"hook": "补录开头.mov", "keep_srt": [20, 21, 22]}
}
```

- `orient`：`"portrait"`（默认，可省）或 `"landscape"`。
- `keep`：保留的句子，`srt` 是字幕序号，`in/out` 是静音点微调后的秒数（原始视频时间）。
- `inserts`：图解/网页素材全屏切入的范围，用字幕序号表示；这几句里人物缩进圆窗。
- `chapters`：章节名（2–4 个字或一个英文词），切点用每部分真正开讲的那一句。字幕章节条读它。
- `music.gain_db`：背景音乐基础增益；说话时自动压低由混音步骤做。
- `sfx`：音效和触发的字幕序号，全片约 5 个。
- `short`：短版的补录钩子和要用的正片字幕序号。
