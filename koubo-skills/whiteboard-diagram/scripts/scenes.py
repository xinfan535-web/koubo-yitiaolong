#!/usr/bin/env python3
"""白板图解 1/3/4/5（和图解2 同一套笔触、纸纹、黑白黄配色）
python3 scenes.py still <n> <t> out.png
python3 scenes.py render <n> out.mp4
画面区：y 200–1130（上面留白，下面留给字幕和人物小窗）
"""
import sys, os, math, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wb
from wb import (S, W, H, FPS, INK, CORAL as YEL, CORAL_D as ORG, paper, stroke, wobble, resample, rrect_pts,
                arc_pts, arrow_head, ellipse_pts, write, highlight, prog, clamp, eo)
from PIL import Image, ImageDraw

GRAY = (120, 118, 122)

# ---------- 小工具 ----------
def line(d, p0, p1, p, color=INK, width=6, seed=0, amp=1.4):
    stroke(d, wobble(resample([p0, p1], 4), amp, seed), p, width, color)

def arrow(d, p0, p1, t, t0, dur=0.35, color=INK, width=6, seed=0, head=24):
    p = prog(t, t0, dur)
    pts = wobble(resample([p0, p1], 4), 1.2, seed)
    stroke(d, pts, p, width, color)
    if p > 0.97:
        a = math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
        arrow_head(d, pts[-1], a, prog(t, t0 + dur, 0.12), color, head, width, seed + 1)

def bez(p0, c, p1, n=60):
    return [((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * c[0] + u * u * p1[0],
             (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * c[1] + u * u * p1[1]) for u in [i / n for i in range(n + 1)]]

def curve_arrow(d, p0, c, p1, t, t0, dur=0.5, color=INK, width=6, seed=0, dashed=False):
    pts = wobble(resample(bez(p0, c, p1), 4), 1.2, seed)
    p = prog(t, t0, dur)
    if dashed:
        k = int(len(pts) * p)
        for i in range(0, k - 3, 7):
            stroke(d, pts[i:i + 4], 1, width, color)
    else:
        stroke(d, pts, p, width, color)
    if p > 0.97:
        a = math.degrees(math.atan2(pts[-1][1] - pts[-4][1], pts[-1][0] - pts[-4][0]))
        arrow_head(d, pts[-1], a, prog(t, t0 + dur, 0.12), color, 24, width, seed + 1)
    return pts

def box(d, x0, y0, x1, y1, t, t0, dur=0.4, seed=0, width=6, color=INK, r=24):
    stroke(d, wobble(rrect_pts(x0, y0, x1, y1, r), 1.6, seed), prog(t, t0, dur), width, color)

def scribble(d, x0, x1, y, t, t0, dur=0.35, seed=0, color=GRAY):
    """一行"字"：波浪线代表正文"""
    n = int((x1 - x0) / 6)
    pts = [(x0 + i * 6, y + 5 * math.sin(i * 0.9 + seed)) for i in range(n)]
    stroke(d, pts, prog(t, t0, dur), 4, color)

def cross(d, x, y, t, t0, color=ORG, s=22, seed=0):
    line(d, (x - s, y - s), (x + s, y + s), prog(t, t0, 0.15), color, 6, seed)
    line(d, (x + s, y - s), (x - s, y + s), prog(t, t0 + 0.12, 0.15), color, 6, seed + 1)

def check(d, x, y, t, t0, color=ORG, s=26, seed=0):
    pts = resample([(x - s, y), (x - s * 0.3, y + s * 0.7), (x + s * 1.1, y - s * 0.9)], 3)
    stroke(d, wobble(pts, 0.8, seed), prog(t, t0, 0.3), 7, color)

def dot_along(d, pts, u, color=ORG, r=12):
    if u is None: return
    x, y = pts[min(len(pts) - 1, int(u * (len(pts) - 1)))]
    d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=color + (255,))

def flag(d, x, y, t, t0, seed=0):
    line(d, (x, y + 40), (x, y - 50), prog(t, t0, 0.2), INK, 6, seed)
    p = prog(t, t0 + 0.2, 0.25)
    if p > 0:
        pts = wobble(resample([(x, y - 50), (x + 52, y - 36), (x, y - 20)], 3), 0.8, seed + 2)
        stroke(d, pts, p, 6, ORG)

# ---------- 图解1：workflow vs agent ----------
def scene1(t, c, d):
    # 上：workflow，路线写死
    write(c, "workflow", 90, 268, 66, prog(t, 0.1, 0.4), INK, "lm")
    write(c, "路线提前写死", 420, 272, 42, prog(t, 0.45, 0.4), ORG, "lm")
    xs = [150, 400, 650, 900]
    labels = ["第1步", "第2步", "第3步", "第4步"]
    for i, x in enumerate(xs):
        t0 = 0.9 + i * 0.55
        box(d, x - 95, 360, x + 95, 470, t, t0, 0.3, 10 + i, 5)
        write(c, labels[i], x, 413, 44, prog(t, t0 + 0.15, 0.25))
        if i < 3:
            arrow(d, (x + 100, 415), (xs[i + 1] - 102, 415), t, t0 + 0.32, 0.2, INK, 5, 20 + i, 18)
    # 走一遍：小点按固定路线跑
    if t > 3.3:
        u = ((t - 3.3) / 1.6) % 1
        x = xs[0] + (xs[-1] - xs[0]) * u
        d.ellipse([(x - 11) * S, (500 - 11) * S, (x + 11) * S, (500 + 11) * S], fill=GRAY + (255,))
    line(d, (60, 590), (1020, 590), prog(t, 3.8, 0.4), (190, 188, 190), 3, 99, 2)

    # 下：agent，自己决定路线
    write(c, "agent", 90, 668, 66, prog(t, 4.2, 0.35), INK, "lm")
    write(c, "AI自己决定下一步", 330, 672, 42, prog(t, 4.5, 0.4), ORG, "lm")
    start, fork, goal = (130, 900), (420, 900), (930, 960)
    r0 = 14 * prog(t, 4.9, 0.2)
    if r0 > 0.5:
        d.ellipse([(start[0] - r0) * S, (start[1] - r0) * S, (start[0] + r0) * S, (start[1] + r0) * S], fill=INK + (255,))
    write(c, "起点", start[0], start[1] + 58, 38, prog(t, 4.9, 0.25), GRAY)
    flag(d, goal[0], goal[1], t, 5.0, 40)
    write(c, "目标", goal[0] + 10, goal[1] + 82, 38, prog(t, 5.1, 0.25), GRAY)
    p1 = curve_arrow(d, start, (280, 860), fork, t, 5.4, 0.45, INK, 6, 50)
    write(c, "?", fork[0] + 6, fork[1] - 70, 56, prog(t, 5.9, 0.2), ORG)
    # 试一条：走不通
    p2 = curve_arrow(d, fork, (520, 760), (640, 770), t, 6.2, 0.45, INK, 6, 60)
    cross(d, 668, 770, t, 6.75, ORG, 22, 70)
    # 退回来，换一条
    curve_arrow(d, (630, 800), (560, 860), (468, 880), t, 7.1, 0.4, GRAY, 4, 80, dashed=True)
    p3 = curve_arrow(d, fork, (620, 1040), (goal[0] - 30, goal[1] + 20), t, 7.6, 0.6, INK, 6, 90)
    write(c, "看结果，再换路", 650, 1095, 40, prog(t, 8.2, 0.4), ORG)
    if t > 8.4:
        route = p1 + p3
        dot_along(d, route, ((t - 8.4) / 1.5) % 1)

# ---------- 图解3：渐进式披露 ----------
def scene3(t, c, d):
    write(c, "渐进式披露", 540, 262, 70, prog(t, 0.1, 0.45))
    line(d, (360, 312), (720, 306), prog(t, 0.5, 0.3), ORG, 5, 1)
    # ① 目录
    box(d, 70, 350, 840, 610, t, 0.8, 0.45, 2)
    write(c, "① 目录：只记名字和一句描述", 100, 392, 40, prog(t, 1.1, 0.4), INK, "lm")
    rows = [("封面规范", "做封面时用"), ("选题模板", "找选题时用"), ("字幕动画", "剪口播时用"), ("剪辑SOP", "粗剪时用")]
    for i, (n, desc) in enumerate(rows):
        y = 450 + i * 40
        if i == 2 and t > 2.7:
            highlight(c, 110, 270, y, 36, prog(t, 2.7, 0.3), alpha=190, seed=5)
        write(c, n, 110, y, 34, prog(t, 1.5 + i * 0.2, 0.25), INK, "lm")
        write(c, "· " + desc, 280, y, 30, prog(t, 1.6 + i * 0.2, 0.25), GRAY, "lm")
    # ② 章节
    arrow(d, (190, 620), (190, 680), t, 3.1, 0.2, ORG, 5, 10, 18)
    write(c, "相关了才翻开", 215, 652, 32, prog(t, 3.1, 0.3), ORG, "lm")
    box(d, 70, 700, 840, 900, t, 3.4, 0.45, 3)
    write(c, "② 章节：字幕动画 / SKILL.md 全文", 100, 742, 40, prog(t, 3.7, 0.4), INK, "lm")
    for i in range(4):
        scribble(d, 110, 760 - i * 70, 795 + i * 28, t, 4.1 + i * 0.18, 0.3, i)
    # ③ 附录
    arrow(d, (190, 910), (190, 965), t, 5.0, 0.2, ORG, 5, 11, 18)
    write(c, "用到才查", 215, 940, 32, prog(t, 5.0, 0.3), ORG, "lm")
    box(d, 70, 985, 840, 1110, t, 5.3, 0.4, 4)
    write(c, "③ 附录：脚本 · 字体 · 示例", 100, 1047, 40, prog(t, 5.6, 0.4), INK, "lm")
    # 右侧：脑容量计
    gx0, gx1, gy0, gy1 = 900, 980, 380, 1080
    box(d, gx0, gy0, gx1, gy1, t, 0.9, 0.4, 7, 5, INK, 18)
    write(c, "脑容量", (gx0 + gx1) / 2, gy0 - 34, 32, prog(t, 1.0, 0.3))
    level = 0.08 * prog(t, 1.6, 0.6) + 0.22 * prog(t, 4.0, 0.6) + 0.12 * prog(t, 5.7, 0.5)
    if level > 0:
        top = gy1 - 12 - (gy1 - gy0 - 24) * level
        lay = Image.new("RGBA", c.size, (0, 0, 0, 0))
        ImageDraw.Draw(lay).rounded_rectangle([(gx0 + 12) * S, top * S, (gx1 - 12) * S, (gy1 - 12) * S], 10 * S,
                                              fill=YEL + (210,))
        c.alpha_composite(lay)
    write(c, "还空着", (gx0 + gx1) / 2, gy0 + 120, 32, prog(t, 7.0, 0.4), ORG)

# ---------- 图解4：两条岔路 ----------
def scene4(t, c, d):
    write(c, "你想要？", 540, 270, 64, prog(t, 0.1, 0.4))
    ellipse = wobble(ellipse_pts(540, 270, 150, 58, seed=3), 1.0, 3)
    stroke(d, ellipse, prog(t, 0.4, 0.4), 5)
    # 左：流程 → skill
    curve_arrow(d, (450, 330), (300, 400), (270, 560), t, 1.0, 0.5, INK, 6, 10)
    write(c, "所有人都按", 210, 430, 38, prog(t, 1.3, 0.3), GRAY)
    write(c, "你的流程干活", 210, 476, 38, prog(t, 1.45, 0.3), GRAY)
    if t > 2.5: highlight(c, 170, 370, 640, 70, prog(t, 2.5, 0.3), alpha=200, seed=4)
    box(d, 140, 585, 400, 700, t, 1.9, 0.4, 20)
    write(c, "写 skill", 270, 640, 58, prog(t, 2.2, 0.35))
    write(c, "= 把 SOP 写下来", 270, 742, 36, prog(t, 2.8, 0.35), ORG)
    # 右：派出去 → agent
    curve_arrow(d, (630, 330), (780, 400), (810, 560), t, 3.4, 0.5, INK, 6, 30)
    write(c, "派一个人出去", 880, 430, 38, prog(t, 3.7, 0.3), GRAY)
    write(c, "独立干完再交差", 870, 476, 38, prog(t, 3.85, 0.3), GRAY)
    box(d, 680, 585, 940, 700, t, 4.3, 0.4, 40)
    write(c, "造 agent", 810, 640, 58, prog(t, 4.6, 0.35))
    write(c, "= 比如调研100个账号", 810, 742, 36, prog(t, 5.2, 0.35), ORG)
    # 汇合：派出去的人也带着 skill
    curve_arrow(d, (290, 800), (540, 990), (790, 800), t, 6.1, 0.7, ORG, 6, 50)
    write(c, "派出去的人，也带着 skill 干活", 540, 960, 40, prog(t, 6.8, 0.5), ORG)
    if t > 8.2: highlight(c, 370, 710, 1062, 52, prog(t, 8.2, 0.35), alpha=170, seed=8)
    write(c, "两个经常一起用", 540, 1060, 56, prog(t, 7.7, 0.45))

# ---------- 图解5：Agent = Model + Harness ----------
def scene5(t, c, d):
    write(c, "Agent = Model + Harness", 540, 262, 64, prog(t, 0.1, 0.7))
    line(d, (500, 312), (1000, 306), prog(t, 0.8, 0.35), ORG, 5, 1)
    cx, cy, R = 470, 640, 225
    # 模型 = 马
    stroke(d, wobble(ellipse_pts(cx, cy, 110, 82, seed=2), 1.0, 2), prog(t, 1.1, 0.4), 6)
    write(c, "模型", cx, cy - 12, 64, prog(t, 1.3, 0.3))
    write(c, "= 马", cx, cy + 46, 40, prog(t, 1.6, 0.3), ORG)
    # harness 外壳
    ring = wobble(arc_pts(cx, cy, R, -100, 262), 2.0, 5)
    stroke(d, ring, prog(t, 2.2, 0.8), 6, ORG)
    write(c, "harness = 挽具", cx, cy - R - 42, 40, prog(t, 2.6, 0.4), ORG)
    parts = [(-150, "循环"), (-30, "工具"), (30, "记忆"), (90, "检查"), (150, "权限")]
    for i, (a, w) in enumerate(parts):
        x = cx + R * math.cos(math.radians(a)); y = cy + R * math.sin(math.radians(a))
        t0 = 3.1 + i * 0.35
        lay_w = 40 + 46 * len(w)
        if t > t0:
            pad = Image.new("RGBA", c.size, (0, 0, 0, 0))
            ImageDraw.Draw(pad).rounded_rectangle([(x - lay_w / 2) * S, (y - 30) * S, (x + lay_w / 2) * S, (y + 30) * S],
                                                  26 * S, fill=(244, 243, 241, int(255 * prog(t, t0, 0.15))))
            c.alpha_composite(pad)
        write(c, w, x, y, 42, prog(t, t0, 0.25))
    arrow(d, (cx + R + 20, cy), (cx + R + 150, cy), t, 4.9, 0.3, INK, 6, 60)
    write(c, "能拉车", cx + R + 230, cy - 22, 48, prog(t, 5.2, 0.3))
    write(c, "= agent", cx + R + 230, cy + 32, 40, prog(t, 5.4, 0.3), ORG)
    # 下：自己造 vs 写 skill
    line(d, (60, 930), (1020, 930), prog(t, 6.6, 0.4), (190, 188, 190), 3, 99, 2)
    write(c, "自己造 agent：自己挑马、自己做挽具（写代码）", 80, 990, 38, prog(t, 7.0, 0.7), GRAY, "lm")
    if t > 9.2: highlight(c, 98, 200, 1070, 50, prog(t, 9.2, 0.3), alpha=190, seed=9)
    write(c, "写 skill：马和挽具都配好，你只管指路", 80, 1070, 38, prog(t, 8.3, 0.7), INK, "lm")
    check(d, 900, 1066, t, 9.6, ORG, 26, 70)

SCENES = {1: (scene1, 10.0), 3: (scene3, 10.0), 4: (scene4, 10.0), 5: (scene5, 12.0)}

def frame(n, t):
    c = paper()
    d = ImageDraw.Draw(c)
    SCENES[n][0](t, c, d)
    return c.resize((W, H), Image.LANCZOS).convert("RGB")

if __name__ == "__main__":
    if sys.argv[1] == "still":
        frame(int(sys.argv[2]), float(sys.argv[3])).save(sys.argv[4])
    else:
        n = int(sys.argv[2]); out = sys.argv[3]; tmp = out[:-4] + ".part.mp4"
        p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                              "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
                              "-pix_fmt", "yuv420p", "-movflags", "+faststart", tmp], stdin=subprocess.PIPE)
        for i in range(int(FPS * SCENES[n][1])):
            p.stdin.write(frame(n, i / FPS).tobytes())
        p.stdin.close()
        if p.wait() == 0:
            os.replace(tmp, out); print("ok", out)
        else:
            sys.exit("ffmpeg failed")
