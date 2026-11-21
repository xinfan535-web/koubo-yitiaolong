---
name: whiteboard-diagram
description: 给口播视频做手绘白板风图解动画（纸纹底、黑色手写笔触、黄橙强调），支持竖屏 1080×1920 和横屏 1920×1080。逐字稿里有【图解N】标注，或用户说“做个图解”“画个白板动画”“把这个概念画出来”时使用。
---

# 白板图解动画

口播一条龙的第 2A 步：把逐字稿里的【图解N】做成一段段独立的 mp4，剪辑时全屏切入，人缩到下角的人物角标。
引擎和纸纹底都在本 skill 里（`scripts/`、`assets/`），不要从零重写。数值规格（画布、安全区、字号、颜色）读 [references/spec.md](references/spec.md)。

## 开工

1. 先问或确认画幅：竖屏用 `scripts/scenes.py`，横屏用 `scripts/scenes_landscape.py`（里面已设好横屏）。没说就竖屏。
2. 环境：Python3 + Pillow + numpy + ffmpeg；字体霞鹜文楷在 `~/fonts`。缺什么运行 `python3 ../koubo-yitiaolong/scripts/check_env.py`，缺字体运行 `bash ../koubo-yitiaolong/scripts/get_fonts.sh`。
3. 在本期文件夹建 `脚本/`，把 `scripts/` 里的 `wb.py`、`fontkit.py`、`scenes.py`（横屏用 `scenes_landscape.py`）和 `assets/paper.png`（竖屏）、`assets/paper_横屏.png`（横屏）都复制进去（和 `wb.py` 放同一目录，引擎会自动找到）。在副本里写本期场景，**不改 skill 目录里的原件**。

## 写一个场景

1. 读逐字稿里【图解N】前后的句子，用一句话写出“这张图要让人看懂什么关系”。一段图解只讲一个关系：对比、组成、流程、选择题、层级，选一种；元素不超过 7 个。
2. 先定布局：哪些元素、坐标、出现顺序（对应博主说话的顺序）。
3. 在场景文件里写 `def sceneN(t, c, d)`，用现成工具：`write`（手写字）、`stroke`、`box`、`arrow`、`curve_arrow`、`highlight`（荧光笔）、`check`、`cross`、`flag`、`dot_along`（沿路径跑的点）、`scribble`；在 `SCENES` 字典里登记 `{编号: (函数, 秒数)}`。横屏场景要用这些工具时 `from scenes import arrow, box, ...`（先设好 `WB_ORIENT`，`scenes_landscape.py` 开头已设）。
4. 抽 3 帧检查（2 秒、6 秒、最后 1 秒）：字有没有出界、有没有进字幕和角标区域、元素有没有重叠。再用 `--mock` 看整体排版。
5. 渲染 `图解/图解N.mp4`，编号和逐字稿一致。把检查帧拼成一张图给用户看，通过再做下一段。

命令（在放脚本的目录里运行）：

```bash
python3 scenes.py still <场景号> <秒> 检查.png [--mock]   # 单帧；--mock 叠上字幕位和人物角标占位
python3 scenes.py render <场景号> 图解N.mp4               # 出片（横屏把 scenes.py 换成 scenes_landscape.py）
```

## 动画规则

- 所有元素都是“画出来”的：线按进度逐段出现，字从左往右擦出，荧光笔一扫而过。**不用淡入、弹跳、缩放。**
- 缓动统一用 ease-out 三次方（`prog(t, 开始秒, 时长)`）。一个元素 0.2–0.5 秒画完，元素之间错开 0.3–0.6 秒，跟着博主讲到哪画到哪。
- 单段 10–12 秒，前 8 秒左右画完，后面留一个循环小动作（沿路线跑的点、轮流高亮的节点），口播比预计长时画面不会僵住。
- 线条过 `wobble` 加轻微抖动，矩形收笔多画一点，圈越画越大一点，要像人画的。保持干净的手绘感，不加表情、贴纸、卡通元素。

## 交付

- `<本期文件夹>/图解/图解N.mp4`
- `<本期文件夹>/脚本/`：本期的场景文件、`wb.py`、纸纹底和一份 `说明.md`（每段的渲染命令）。
- 以后还会用的新通用小工具（新图形、新动画手法），告诉用户，同意后补进本 skill 的 `scripts/`。

## 注意

颜色有疑问时问清是哪个元素的颜色：图解用荧光黄 `#FFD640`，和封面标题的奶油黄 `#F5F2C4` 不是同一个。
