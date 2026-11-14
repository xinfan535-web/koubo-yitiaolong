#!/usr/bin/env python3
"""白板风格图解：纸纹底 + 黑色手写笔触 + 珊瑚色强调
python3 wb.py paper out.png
python3 wb.py still <t> out.png [--mock]
python3 wb.py render out.mp4 [--mock]     --mock 叠上字幕位/人物小窗占位，只用于看排版
字体自动在 ~/fonts 和系统目录里找（fontkit.py）；纸纹底在 ../assets/，没有会自动生成。
"""
import sys, math, os, random, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

S = 2
# 画幅：默认竖屏 1080×1920；环境变量 WB_ORIENT=landscape 时横屏 1920×1080
LAND = os.environ.get("WB_ORIENT", "portrait").lower() in ("landscape", "h", "横屏")
W, H = (1920, 1080) if LAND else (1080, 1920)
FPS, DUR = 30, 10.0
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fontkit
ASSETS = os.path.join(os.path.dirname(HERE), "assets")      # 纸纹底放这里
HAND = "hand"             # 霞鹜文楷（手写字）
BLK = "sans_black"        # 思源黑体 Black（字幕占位用）
INK = (34, 34, 38)
CORAL = (255, 214, 64)      # 荧光笔黄（和字幕金句同一个黄）
CORAL_D = (226, 122, 28)    # 橙：箭头、注释、强调线

_fc = {}
def font(key, size):
    k = (key, size)
    if k not in _fc:
        try:
            _fc[k] = fontkit.truetype(key, size * S)
        except fontkit.FontMissing as e:
            sys.exit(f"❌ {e}")
    return _fc[k]

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def eo(p): p = clamp(p); return 1 - (1 - p) ** 3
def prog(t, t0, dur): return eo((t - t0) / dur)

# ---------------- 纸纹底 ----------------
def make_paper(path):
    rng = np.random.default_rng(7)
    h, w = H, W
    def octave(scale):
        sh, sw = max(2, h // scale), max(2, w // scale)
        n = rng.random((sh, sw)).astype(np.float32)
        return np.asarray(Image.fromarray((n * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 255
    base = 0.55 * octave(420) + 0.3 * octave(160) + 0.15 * octave(60)
    gy, gx = np.gradient(base)
    shade = np.clip(0.5 + (gx * 0.7 - gy * 0.7) * 260, 0, 1)          # 斜光照出大块起伏
    fib = np.asarray(Image.fromarray((rng.random((h // 3, w // 3)) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 255
    grain = rng.normal(0, 1, (h, w)).astype(np.float32)
    v = 233 + (shade - 0.5) * 17 + (base - 0.5) * 10 + (fib - 0.5) * 5 + grain * 1.6
    rgb = np.stack([v - 1, v, v + 3], -1)
    Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6)).save(path)

_paper = None
def paper():
    global _paper
    if _paper is None:
        name = "paper_横屏.png" if LAND else "paper.png"
        p = next((q for q in (os.path.join(ASSETS, name), os.path.join(HERE, name)) if os.path.exists(q)), None)
        if p is None:
            os.makedirs(ASSETS, exist_ok=True); p = os.path.join(ASSETS, name); make_paper(p)
        _paper = Image.open(p).convert("RGBA").resize((W * S, H * S), Image.BICUBIC)
    return _paper.copy()

# ---------------- 手绘笔触 ----------------
def resample(pts, step=5):
    out = [pts[0]]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        d = math.hypot(x1 - x0, y1 - y0); n = max(1, int(d / step))
        out += [(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n) for i in range(1, n + 1)]
    return out

def wobble(pts, amp=2.2, seed=0):
    rnd = random.Random(seed)
    ph = [rnd.random() * 6.28 for _ in range(4)]
    out = []
    for i, (x, y) in enumerate(pts):
        a = i / 18.0
        dx = amp * (math.sin(a + ph[0]) + 0.5 * math.sin(2.3 * a + ph[1]))
        dy = amp * (math.sin(1.1 * a + ph[2]) + 0.5 * math.sin(2.7 * a + ph[3]))
        out.append((x + dx, y + dy))
    return out

def stroke(d, pts, p, width=6, color=INK, alpha=255):
    if p <= 0 or len(pts) < 2: return
    k = max(2, int(len(pts) * clamp(p)))
    seg = [(x * S, y * S) for x, y in pts[:k]]
    c = color + (alpha,)
    d.line(seg, fill=c, width=int(width * S), joint="curve")
    r = width * S / 2
    for x, y in (seg[0], seg[-1]):
        d.ellipse([x - r, y - r, x + r, y + r], fill=c)

def rrect_pts(x0, y0, x1, y1, r=26, overshoot=18):
    pts = []
    def arc(cx, cy, a0, a1):
        for i in range(9):
            a = math.radians(a0 + (a1 - a0) * i / 8)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    pts.append((x0 + r - 4, y0 + 2))
    pts.append((x1 - r, y0)); arc(x1 - r, y0 + r, 270, 360)
    pts.append((x1, y1 - r)); arc(x1 - r, y1 - r, 0, 90)
    pts.append((x0 + r, y1)); arc(x0 + r, y1 - r, 90, 180)
    pts.append((x0, y0 + r)); arc(x0 + r, y0 + r, 180, 270)
    pts.append((x0 + r + overshoot, y0 - 3))           # 收笔多画一点，不严丝合缝
    return resample(pts)

def arc_pts(cx, cy, R, a0, a1, jit=0):
    n = max(8, int(abs(a1 - a0) / 2))
    return [(cx + (R + jit * math.sin(i * 0.5)) * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + (R + jit * math.sin(i * 0.5)) * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]

def arrow_head(d, tip, ang_deg, p, color=INK, size=26, width=6, seed=0):
    """ang = 箭头前进方向"""
    if p <= 0: return
    a = math.radians(ang_deg)
    for s, sd in ((150, seed), (-150, seed + 1)):
        b = a + math.radians(s)
        end = (tip[0] + size * math.cos(b), tip[1] + size * math.sin(b))
        stroke(d, wobble(resample([tip, end], 3), 0.8, sd), p, width, color)

def ellipse_pts(cx, cy, rx, ry, a0=-100, sweep=385, seed=0):
    rnd = random.Random(seed); tilt = rnd.uniform(-4, 4)
    pts = []
    for i in range(int(sweep / 3) + 1):
        a = math.radians(a0 + i * 3)
        grow = 1 + 0.06 * i / (sweep / 3)        # 手画圈：越画越大一点
        x, y = rx * grow * math.cos(a), ry * grow * math.sin(a)
        ta = math.radians(tilt)
        pts.append((cx + x * math.cos(ta) - y * math.sin(ta), cy + x * math.sin(ta) + y * math.cos(ta)))
    return pts

# ---------------- 手写字：从左往右擦出 ----------------
_tl = {}
def text_layer(txt, size, color, path=HAND, bold=1.2):
    k = (txt, size, color, path)
    if k not in _tl:
        f = font(path, size)
        sw = int(bold * S)
        l, t, r, b = f.getbbox(txt, stroke_width=sw)
        im = Image.new("RGBA", (r - l + 6 * S, b - t + 6 * S), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((3 * S - l, 3 * S - t), txt, font=f, fill=color + (255,), stroke_width=sw,
                                stroke_fill=color + (255,))
        _tl[k] = im
    return _tl[k]

def write(c, txt, cx, cy, size, p, color=INK, anchor="mm", path=HAND):
    if p <= 0: return
    lay = text_layer(txt, size, color, path)
    w, h = lay.size
    if p < 1:
        edge = int(w * p)
        m = Image.new("L", (w, h), 0)
        md = ImageDraw.Draw(m)
        md.rectangle([0, 0, edge, h], fill=255)
        soft = int(18 * S)
        for i in range(soft):
            md.line([(edge + i, 0), (edge + i, h)], fill=int(255 * (1 - i / soft)))
        lay = lay.copy(); lay.putalpha(Image.composite(lay.getchannel("A"), Image.new("L", (w, h), 0), m))
    x = cx * S - (w / 2 if anchor[0] == "m" else 0)
    y = cy * S - h / 2
    c.alpha_composite(lay, (int(x), int(y)))

def highlight(c, x0, x1, cy, h, p, color=CORAL, alpha=165, seed=0):
    """荧光笔一扫"""
    if p <= 0: return
    lay = Image.new("RGBA", c.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    pts = wobble(resample([(x0, cy + 4), (x1, cy - 3)], 4), 1.5, seed)
    stroke(d, pts, p, h, color, 255)
    a = lay.getchannel("A").point(lambda v: v * alpha // 255)
    lay.putalpha(a)
    c.alpha_composite(lay)

# ---------------- 图解2：agent = 大脑 + 手 + 循环 ----------------
BOX_Y, BOX_H, BOX_W = 495, 165, 250
BOXES = [  # cx, 字, 注释, 画框时间, 注释时间
    (180, "大脑", "模型", 0.70, 2.8),
    (540, "手", "工具", 1.35, 3.6),
    (900, "循环", "会自己转", 2.00, 4.5),
]
LC = (540, 958); R = 172
NODES = [(270, "判断", 5.1), (30, "动手", 5.9), (150, "看结果", 6.7)]
GAP = 34
ARCS = [(270 + GAP, 390 - GAP, 5.35, INK), (30 + GAP, 150 - GAP, 6.15, INK), (150 + GAP, 270 - GAP, 6.95, CORAL_D)]
DOT_T0, DOT_PERIOD = 7.8, 2.4

def pt(a, r=R): return LC[0] + r * math.cos(math.radians(a)), LC[1] + r * math.sin(math.radians(a))

def frame(t, mock=False, overlay=None):
    c = paper()
    d = ImageDraw.Draw(c)

    write(c, "agent =", 540, 312, 128, prog(t, 0.15, 0.55))
    # 下划线
    stroke(d, wobble(resample([(330, 382), (760, 375)]), 1.5, 3), prog(t, 0.55, 0.3), 5, CORAL_D)

    for i, (cx, word, note, t0, tn) in enumerate(BOXES):
        x0, x1 = cx - BOX_W / 2, cx + BOX_W / 2
        y0, y1 = BOX_Y - BOX_H / 2, BOX_Y + BOX_H / 2
        if word == "循环" and t > 4.9:   # 被点名：荧光笔把整个框涂一下
            highlight(c, x0 + 72, x1 - 72, BOX_Y, BOX_H - 50, prog(t, 4.9, 0.35), alpha=150, seed=9)
        stroke(d, wobble(rrect_pts(x0, y0, x1, y1), 1.8, 10 + i), prog(t, t0, 0.42), 6)
        write(c, word, cx, BOX_Y - 4, 84, prog(t, t0 + 0.25, 0.3))
        # 注释：小箭头 + 珊瑚色手写
        ap = prog(t, tn, 0.25)
        stroke(d, wobble(resample([(cx, y1 + 70), (cx, y1 + 16)], 3), 1.2, 20 + i), ap, 4.5, CORAL_D)
        arrow_head(d, (cx, y1 + 14), -90, prog(t, tn + 0.15, 0.15), CORAL_D, 18, 4.5, 30 + i)
        write(c, note, cx, y1 + 98, 42, prog(t, tn + 0.15, 0.3), CORAL_D)
    for j, (px, t0) in enumerate([(360, 1.15), (720, 1.8)]):
        p = prog(t, t0, 0.2)
        stroke(d, wobble(resample([(px - 22, BOX_Y), (px + 22, BOX_Y)], 3), 0.8, 40 + j), p, 6)
        stroke(d, wobble(resample([(px, BOX_Y - 22), (px, BOX_Y + 22)], 3), 0.8, 50 + j), prog(t, t0 + 0.1, 0.2), 6)

    # 循环：三段手绘弧 + 箭头
    for k, (a0, a1, s0, col) in enumerate(ARCS):
        p = prog(t, s0, 0.5)
        pts = wobble(arc_pts(LC[0], LC[1], R, a0, a1), 1.6, 60 + k)
        stroke(d, pts, p, 6, col)
        if p > 0.95:
            tip = pts[-1]; a = math.degrees(math.atan2(pts[-1][1] - pts[-4][1], pts[-1][0] - pts[-4][0]))
            arrow_head(d, tip, a, prog(t, s0 + 0.48, 0.12), col, 26, 6, 70 + k)
    write(c, "再判断", *pt(207, R + 92), 44, prog(t, 7.5, 0.3), CORAL_D)

    # 跑动的点 + 当前节点荧光笔
    dot = None
    if t >= DOT_T0:
        dot = 270 + 360 * (((t - DOT_T0) / DOT_PERIOD) % 1)
    for k, (a, word, t0) in enumerate(NODES):
        x, y = pt(a)
        if dot is not None:
            dd = min((dot - a) % 360, (a - dot) % 360)
            if dd < 26:
                highlight(c, x - 70, x + 70, y + 2, 46, 1.0, CORAL, int(190 * (1 - dd / 26)), 80 + k)
        write(c, word, x, y - 2, 52, prog(t, t0, 0.3))
        stroke(d, wobble(ellipse_pts(x, y, 26 + 26 * len(word), 46, seed=k), 1.0, 90 + k),
               prog(t, t0 + 0.2, 0.35), 4.5)
    if dot is not None:
        x, y = pt(dot)
        r = 11
        d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=CORAL_D + (255,))

    if mock:
        f = font(BLK, 70); sub = "大脑是模型 手是工具"
        tw = f.getlength(sub) / S + 44; by = 1190
        d.rounded_rectangle([(540 - tw / 2) * S, (by - 50) * S, (540 + tw / 2) * S, (by + 50) * S], 14 * S,
                            fill=(40, 40, 40, 150))
        d.text((540 * S, by * S), sub, font=f, fill=(255, 255, 255, 255), anchor="mm")
        x0, y0, x1, y1 = 740, 1262, 1040, 1520
        sh = Image.new("RGBA", c.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([(x0 + 4) * S, (y0 + 10) * S, (x1 + 4) * S, (y1 + 10) * S], 34 * S,
                                             fill=(0, 0, 0, 70))
        c.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14 * S)))
        d = ImageDraw.Draw(c)
        d.rounded_rectangle([x0 * S, y0 * S, x1 * S, y1 * S], 34 * S, fill=(150, 140, 135, 255))
        d.text(((x0 + x1) / 2 * S, (y0 + y1) / 2 * S), "人物小窗", font=font(BLK, 40), fill=(255, 255, 255, 255),
               anchor="mm")
    out = c.resize((W, H), Image.LANCZOS)
    if overlay is not None:
        out.alpha_composite(overlay)
    return out.convert("RGB")

def overlay_frames(mov):
    """读透明叠加层 MOV 的帧（RGBA）"""
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", mov, "-f", "rawvideo", "-pix_fmt", "rgba", "-"],
                         stdout=subprocess.PIPE)
    n = W * H * 4
    while True:
        b = p.stdout.read(n)
        if len(b) < n: break
        yield Image.frombuffer("RGBA", (W, H), b, "raw", "RGBA", 0, 1)

if __name__ == "__main__":
    cmd = sys.argv[1]
    mock = "--mock" in sys.argv
    if cmd == "paper":
        make_paper(sys.argv[2])
    elif cmd == "still":
        frame(float(sys.argv[2]), mock).save(sys.argv[3])
    else:
        out = sys.argv[2]; tmp = out[:-4] + ".part.mp4"
        ov = None
        if "--overlay" in sys.argv:
            ov = overlay_frames(sys.argv[sys.argv.index("--overlay") + 1])
        p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                              "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
                              "-pix_fmt", "yuv420p", "-movflags", "+faststart", tmp], stdin=subprocess.PIPE)
        for i in range(int(FPS * DUR)):
            o = next(ov, None) if ov else None
            p.stdin.write(frame(i / FPS, mock, o).tobytes())
        p.stdin.close()
        if p.wait() == 0:
            os.replace(tmp, out); print("ok", out)
        else:
            sys.exit("ffmpeg failed")
