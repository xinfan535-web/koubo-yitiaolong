# 口播 skill 套装：安装与检查（给人看的，agent 不会自动读）

## 这套 skill 有哪些

koubo-yitiaolong（总流程）、koubo-baokuan-check（自检）、koubo-script（逐字稿）、whiteboard-diagram（图解）、web-page-demo（网页演示）、koubo-edit-pipeline（剪辑）、koubo-subtitle-fx（字幕动画）、koubo-cover（标题封面）。

## 装在哪

放进 `~/.agents/skills/`（每个 skill 一个文件夹，文件夹里直接是 SKILL.md）。VS Code 的 Copilot agent 模式会读这个目录；Claude Code 读 `~/.claude/skills/`，Copilot 的专用目录是 `~/.copilot/skills/`。同一份文件夹复制过去就行，不用改内容。

## 省额度的设计

- VS Code 启动时只读每个 skill 的 name 和 description；匹配上才读 SKILL.md 正文；正文里点名的文件才会再读。所以：
  - 描述写短（每个约 60–90 token），8 个合计 600 token 左右；
  - 正文只放“判断和步骤”，规格表、样式表、输出模板放 `references/`，用到才读；
  - 代码全部放 `scripts/`，正文里只写怎么调用，不贴代码。
- 固定步骤交给脚本（渲染字幕、画图解、检查环境），模型只负责判断和填参数，DeepSeek 这类模型也不容易写错。

## 检查

```
python3 ~/.agents/skills/koubo-yitiaolong/scripts/check_skills.py          # 检查这套 8 个
python3 ~/.agents/skills/koubo-yitiaolong/scripts/check_skills.py --all    # 只报硬错误，扫目录里全部 skill
python3 ~/.agents/skills/koubo-yitiaolong/scripts/check_env.py             # 检查 ffmpeg / Pillow / 字体
```

脚本能检查的是文档里写明的规则（name 格式、description 长度、文件是否存在等）。**它不能替你确认 VS Code 真的加载了**，装好后手动确认一次：

1. VS Code 命令面板（Cmd+Shift+P）运行 `Chat: Open Customizations`，选 Skills，看 koubo-* 在不在列表里；
2. 新开一个聊天，输入 `/`，菜单里应该有这 8 个；
3. 用一个小任务试一下，例如：`自检一下这个选题：为什么 AI 越用越累`，看它有没有按 koubo-baokuan-check 的格式输出。

## 用的不是 Copilot 的 agent 怎么办

接 DeepSeek 的 VS Code 插件（Cline、Roo、Continue、Kilo 等）读哪个目录各不相同，我没有逐个验证。没识别到 skill 时的兜底做法：在对话里直接说“先读 `~/.agents/skills/koubo-yitiaolong/SKILL.md`，按它做”，这些 skill 都是普通 markdown，任何能读文件的 agent 都能照着执行。
