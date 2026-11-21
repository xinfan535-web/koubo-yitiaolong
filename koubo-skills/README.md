# 口播一条龙 skill 套装

一套给 AI agent（Claude、VS Code 里的 agent 等）用的 skill，把一期口播视频从**选题**做到**成片 + 封面**。

博主只做 4 件事：**确认稿子 → 录口播 → 看预览 → 定标题**。写稿、做图解、做网页演示、剪辑、加字幕、做封面，全部交给 agent。

---

## 一、怎么开始用（最常用的一句话）

装好之后，直接对 agent 说：

> **做一期口播，选题是：xxx**

agent 会按总流程 `koubo-yitiaolong` 一步步往下走，每到需要你做决定的地方会停下来问你。

中途想知道走到哪了，问一句：

> **下一步做什么？**

也可以只用其中某一步，比如：

| 你想做的 | 直接说 |
|---|---|
| 只想看看选题行不行 | 自检一下这个选题：xxx |
| 只写稿 | 把这个选题写成口播逐字稿 |
| 只做图解 | 把这个概念做成白板图解 |
| 只做网页演示 | 把这个网页做成演示素材 |
| 已经录好了，要剪 | 帮我剪（附上视频和 SRT） |
| 只加字幕 | 给这条视频加字幕动画 |
| 只做封面 | 帮我起标题、做封面 |
| 发完复盘 | 复盘这条数据 |

---

## 二、一期口播的完整流程

✋ = 停下来等博主

| 步 | 做什么 | 用哪个 skill | 谁动手 |
|---|---|---|---|
| 0 | 选题自检：值不值得做 | koubo-baokuan-check | agent |
| 1 | 写口播逐字稿（标好哪里放图解、哪里放网页） | koubo-script | agent |
| 1.5 | 稿子自检，必须改的改完 | koubo-baokuan-check | agent |
| ✋ | **确认稿子** | — | 博主 |
| 2A | 做白板图解动画 | whiteboard-diagram | agent（和录制同时进行） |
| 2B | 做真实网页演示短片 | web-page-demo | agent（和录制同时进行） |
| ✋ | **录口播，导出视频和 SRT 字幕** | — | 博主 |
| 3 | 粗剪 → 合成 → 字幕 → 声音 → 进度条 | koubo-edit-pipeline（字幕调用 koubo-subtitle-fx） | agent |
| ✋ | **看预览，提修改意见** | — | 博主 |
| 4 | 起标题、做封面 | koubo-cover | agent 出，博主定 |
| 5 | 交付到本期文件夹 | — | agent |
| 6 | 发布 3 天后复盘 | koubo-baokuan-check | 博主给数据，agent 写 |

---

## 三、每期开剪前要选的几项

剪辑开始时 agent 会问你，每期选一次就行：

**1. 画幅**
- 竖屏（默认）：小红书 / 视频号 / 抖音
- 横屏：B 站等

**2. 录屏 / 素材怎么呈现**
- **上下分屏**：人物固定在上半屏，录屏在下半屏，全程同时出现。适合边讲边演示电脑操作的教程。
- **交互式**（默认）：平时人物全屏，讲到图解、网页、录屏时素材全屏，人物缩到角落的小窗里。

**3. 选了「交互式」的话，再选两项**
- 人物小窗位置：**左下角**（默认）或**右下角**
- 素材切入方式：
  - **常规**（默认）：直接切过去
  - **网感剪辑**（测试中）：切入时人物带推镜缩小的动画，配转场音效，更有节奏感

---

## 四、8 个 skill 分别是什么

| skill | 作用 |
|---|---|
| **koubo-yitiaolong** | 总流程。管顺序和交接，告诉 agent 每一步该用哪个 skill |
| koubo-baokuan-check | 爆款自检。选题、稿子、发布后数据都能查 |
| koubo-script | 选题写成可以直接录的逐字稿，含短版 |
| whiteboard-diagram | 手绘白板风的图解动画 |
| web-page-demo | 把真实网页做成「指着屏幕讲」的演示短片，不用自己录屏 |
| koubo-edit-pipeline | 把录好的素材剪成成片：预览、长版、短版 |
| koubo-subtitle-fx | 字幕动画和重点标注（金句、分点、清单等） |
| koubo-cover | 起标题、做封面 |

一般只需要记住总流程 `koubo-yitiaolong`，其他 7 个它会自己调用。

---

## 五、文件夹说明

```
koubo-skills/
├── README.md              ← 就是这份
├── koubo-yitiaolong/      ← 每个 skill 一个文件夹
│   ├── SKILL.md           ← 主说明书，agent 每次调用都读
│   ├── references/        ← 详细参数表，用到才读
│   └── scripts/           ← 检查环境、检查 skill 的脚本
├── koubo-edit-pipeline/
├── whiteboard-diagram/
│   ├── SKILL.md
│   ├── references/
│   ├── scripts/           ← 渲染图解的代码
│   └── assets/            ← 纸纹底图等素材
└── ……
```

为什么分这么多文件夹：agent 认 skill 的规则就是「一个文件夹 + 里面一个 SKILL.md」。分开放，用到哪个只读哪个，省额度，改一个也不会影响别的。

---

## 六、安装

把 `koubo-skills/` 下面的 8 个 skill 文件夹整体复制到对应目录（不用改内容）：

| 在哪用 | 放到 |
|---|---|
| Claude Code | `~/.claude/skills/` |
| VS Code agent | `~/.agents/skills/` |
| Claude 网页 / 桌面 App | 在 Claude 的 skill 设置里逐个上传 |

装好后可以跑一下检查（需要 Python 3）：

```bash
python3 ~/.agents/skills/koubo-yitiaolong/scripts/check_env.py      # 检查 ffmpeg、Pillow、字体
python3 ~/.agents/skills/koubo-yitiaolong/scripts/check_skills.py   # 检查 8 个 skill 格式
```

识别不到 skill 时的兜底：直接对 agent 说「先读 koubo-yitiaolong/SKILL.md，按它做」。

---

## 七、注意事项

- 每期项目放 `~/projects/口播/<日期 选题>/`，**不要放桌面或「文稿」**，这两个位置会同步 iCloud，大视频会一直上传。
- 先出**预览**，你看过没问题才出长版；短版在长版之后。
- 改过任何 skill 后跑一次 `check_skills.py`，有 ❌ 的要修。
