# 口播 skill 套装

把一条口播视频从选题做到成片、封面的 8 个 Agent Skills：总流程、选题/稿件自检、逐字稿、白板图解、网页演示、剪辑流水线、字幕动画、标题封面。

| skill | 作用 |
|---|---|
| koubo-yitiaolong | 总流程：顺序、交接文件、哪里等人确认 |
| koubo-baokuan-check | 选题 / 稿件 / 复盘自检 |
| koubo-script | 选题 → 口播逐字稿 |
| whiteboard-diagram | 手绘白板风图解动画 |
| web-page-demo | 真实网页做成演示短片 |
| koubo-edit-pipeline | 粗剪、合成、混音 |
| koubo-subtitle-fx | 字幕动画和重点标注 |
| koubo-cover | 标题和封面 |

## 安装

每个 skill 是一个文件夹，里面直接是 `SKILL.md`。复制到你的 agent 读取的目录即可：

- Claude Code：`~/.claude/skills/`
- 读 `~/.agents/skills/` 的 agent（如 VS Code Copilot agent 模式）：`~/.agents/skills/`

## 先改这个文件

`koubo-yitiaolong/references/account.md` 里的 `<尖括号>` 是占位符，换成你自己的昵称、定位、观众和配色。换账号只改这个文件。

## 检查

```
python3 koubo-yitiaolong/scripts/check_env.py                 # 检查 ffmpeg / Pillow / 字体
python3 koubo-yitiaolong/scripts/check_skills.py --root .     # 检查 skill 格式
```

更多说明见 `koubo-yitiaolong/README.md`。
