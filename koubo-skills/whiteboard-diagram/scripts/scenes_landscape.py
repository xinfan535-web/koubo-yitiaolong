#!/usr/bin/env python3
"""横屏（1920×1080）白板图解：排版安全区 + 一个示例场景
python3 scenes_landscape.py still <n> <t> out.png [--mock]   --mock 叠上字幕/人物圆窗占位，只用于看排版
python3 scenes_landscape.py render <n> out.mp4
写新场景：照 scene1 的写法加 sceneN，并在 SCENES 里登记。
"""
import os, sys, subprocess
os.environ.setdefault("WB_ORIENT", "landscape")          # 必须在 import wb 之前
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wb
from wb import S, W, H, FPS, INK, CORAL as YEL, CORAL_D as ORG, paper, stroke, wobble, ellipse_pts, write, highlight, prog
from scenes import line, arrow, curve_arrow, box, check, cross, dot_along, GRAY
from PIL import Image, ImageDraw, ImageFilter

# ---------- 横屏安全区（按对标视频校准） ----------
AREA = (110, 110, 1810, 920)       # 作图区 x0,y0,x1,y1
PIP = (1700, 860, 150)             # 人物圆窗（和竖屏一样是圆形）：圆心 x,y 和半径，白边 + 阴影。右下角 x 1530–1870、y 690–1030 不要画东西
SUB_Y = 1010                       # 字幕中心高度（黑色圆角条，高约 95）。字幕条会压在作图区下沿，重要内容放在 y 920 以上
# 字号：横屏在手机上是按宽度缩小显示的，同样的字要比竖屏大约 1.6 倍
T_TITLE, T_BOX, T_NOTE = 110, 80, 60

def scene1(t, c, d):
    """示例：一个选择题，两条路"""
    cx, cy = 960, 235
    write(c, "你想要？", cx, cy, T_TITLE, prog(t, 0.15, 0.4))
    stroke(d, wobble(ellipse_pts(cx, cy + 4, 250, 82, seed=1), 1.2, 2), prog(t, 0.4, 0.45), 6)
    L, R, by = 480, 1330, 640
    curve_arrow(d, (cx - 230, cy + 60), (560, 330), (L, by - 100), t, 1.0, 0.5, INK, 6, 10)
    curve_arrow(d, (cx + 230, cy + 60), (1260, 330), (R, by - 100), t, 1.3, 0.5, INK, 6, 20)
    write(c, "按你的流程干活", 300, 400, 56, prog(t, 1.5, 0.4), GRAY)
    write(c, "派出去独立干完", 1620, 400, 56, prog(t, 1.9, 0.4), GRAY)
    if t > 4.2:
        highlight(c, L - 170, L + 170, by, 96, prog(t, 4.2, 0.35), YEL, 170, 5)
    box(d, L - 220, by - 85, L + 220, by + 85, t, 2.4, 0.4, 30)
    write(c, "写 skill", L, by - 4, T_BOX, prog(t, 2.6, 0.3))
    box(d, R - 220, by - 85, R + 220, by + 85, t, 3.0, 0.4, 40)
    write(c, "造 agent", R, by - 4, T_BOX, prog(t, 3.2, 0.3))
    write(c, "= 把 SOP 写下来", L, by + 140, T_NOTE, prog(t, 3.7, 0.35), ORG)
    write(c, "= 比如调研 100 家", R - 60, by + 140, T_NOTE, prog(t, 4.6, 0.35), ORG)

SCENES = {1: (scene1, 10.0)}

def mock_overlay(c):
    d = ImageDraw.Draw(c)
    fs = wb.font(wb.HAND, 50); sub = "字幕位置 一行最多二十个字"
    tw = fs.getlength(sub) / S + 72
    d.rounded_rectangle([(960 - tw / 2) * S, (SUB_Y - 47) * S, (960 + tw / 2) * S, (SUB_Y + 47) * S], 24 * S, fill=(0, 0, 0, 240))
    d.text((960 * S, SUB_Y * S), sub, font=fs, fill=(255, 255, 255, 255), anchor="mm")
    x, y, r = PIP
    sh = Image.new("RGBA", c.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse([(x - r + 4) * S, (y - r + 10) * S, (x + r + 4) * S, (y + r + 10) * S], fill=(0, 0, 0, 90))
    c.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14 * S)))
    d = ImageDraw.Draw(c)
    d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=(150, 140, 135, 255), outline=(255, 255, 255, 255), width=6 * S)
    d.text((x * S, y * S), "人物", font=fs, fill=(255, 255, 255, 255), anchor="mm")
    a = AREA
    d.rectangle([a[0] * S, a[1] * S, a[2] * S, a[3] * S], outline=(226, 122, 28, 120), width=2 * S)

def frame(n, t, mock=False):
    c = paper()
    d = ImageDraw.Draw(c)
    SCENES[n][0](t, c, d)
    if mock: mock_overlay(c)
    return c.resize((W, H), Image.LANCZOS).convert("RGB")

if __name__ == "__main__":
    mock = "--mock" in sys.argv
    if sys.argv[1] == "still":
        frame(int(sys.argv[2]), float(sys.argv[3]), mock).save(sys.argv[4])
    else:
        n = int(sys.argv[2]); out = sys.argv[3]; tmp = out[:-4] + ".part.mp4"
        p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                              "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
                              "-pix_fmt", "yuv420p", "-movflags", "+faststart", tmp], stdin=subprocess.PIPE)
        for i in range(int(FPS * SCENES[n][1])):
            p.stdin.write(frame(n, i / FPS, mock).tobytes())
        p.stdin.close()
        if p.wait() == 0:
            os.replace(tmp, out); print("ok", out)
        else:
            sys.exit("ffmpeg failed")
