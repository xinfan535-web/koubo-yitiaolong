#!/usr/bin/env python3
"""口播字幕动画渲染器  plan.json -> 动画字幕(ASS) + 画面缩框 -> 成片
用法:
  python3 koubo_fx.py plan.json in.mp4 out.mp4        # 渲染成片
  python3 koubo_fx.py plan.json --ass-only out.ass     # 只出字幕文件
字体: Noto Sans SC/CJK Black(白字) + ZCOOL KuaiLe 站酷快乐体(黄字/贴纸/手写)。
      自动在 ~/fonts、系统字体目录里找（见 fontkit.py）；缺了运行 get_fonts.sh。
画幅: plan.json 的 config.orient = "landscape" 时按 1920x1080 横屏排版，默认竖屏 1080x1920。
"""
import json, re, subprocess, sys, os, math, argparse, shutil, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import ImageFont, Image, ImageDraw
import fontkit

W, H = 1080, 1920
BASE_Y = 1300            # 普通字幕中心高度(≈68%)，避开平台底部UI
try:
    F_BASE = fontkit.family("sans_black")     # 普通字幕/章节：黑体最粗
    F_FX = fontkit.family("kuaile")           # 金句/贴纸/手写：站酷快乐体
except fontkit.FontMissing as _e:
    sys.exit(f"❌ {_e}")
_KEY = {F_BASE: "sans_black", F_FX: "kuaile"}
YEL = "&H005AE4FF&"      # #FFE45A 柠檬黄
DARK = "&H00202020&"
RED = "&H002E26B3&"      # #B3262E 章节红
BLUE = "&H00FFA73B&"     # #3BA7FF 爆炸贴蓝
BROWN = "&H001A3A5A&"    # #5A3A1A 贴纸字
PUNCT = r"[，。！？、,\.!；;：:“”\"'‘’…—\-~～\s]+"
REPLACING = {"gold", "keywords", "punch", "chapter"}   # 出现时顶掉普通字幕


def tw(text, family, size, sp=0, fontsdir=None):
    """文字宽度(px)"""
    f = fontkit.truetype(_KEY[family], size)
    return f.getlength(text) + sp * len(text)


def ts(t):
    t = max(0, t)
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def dlg(layer, a, b, text):
    return f"Dialogue: {layer},{ts(a)},{ts(b)},Default,,0,0,0,,{text}"


def rrect(w, h, r):
    """圆角矩形 ASS drawing (左上角为原点)"""
    r = min(r, h / 2, w / 2); w, h = round(w), round(h); r = round(r)
    return (f"m {r} 0 l {w-r} 0 b {w} 0 {w} 0 {w} {r} l {w} {h-r} b {w} {h} {w} {h} {w-r} {h} "
            f"l {r} {h} b 0 {h} 0 {h} 0 {h-r} l 0 {r} b 0 0 0 0 {r} 0")


def star(R, r, n=12):
    pts = []
    for i in range(n * 2):
        rad = R if i % 2 == 0 else r
        a = math.pi * i / n - math.pi / 2
        pts.append((round(R + rad * math.cos(a)), round(R + rad * math.sin(a))))
    return "m %d %d " % pts[0] + " ".join("l %d %d" % p for p in pts[1:])


def reveal(text, t0=0, step=60, dur=140):
    """逐字显影：每字 alpha 淡入 + 去模糊，左对齐时不抖"""
    out = []
    for i, ch in enumerate(text):
        a = t0 + i * step
        out.append(f"{{\\alpha&HFF&\\blur8\\t({a},{a+dur},\\alpha&H00&\\blur0)}}{ch}")
    return "".join(out)


POP = "\\fscx20\\fscy20\\t(0,140,\\fscx110\\fscy110)\\t(140,220,\\fscx100\\fscy100)"


def split_line(text, maxc):
    """超长就拆：优先在原标点(空格)处断，找最接近中点的；没有就均分"""
    if len(text) <= maxc:
        return [text]
    sp = [i for i, c in enumerate(text) if c == " "]
    if sp:
        i = min(sp, key=lambda i: abs(i - len(text) / 2))
        return split_line(text[:i].strip(), maxc) + split_line(text[i + 1:].strip(), maxc)
    # 没有标点可断：在最接近中点、且不会把英文单词劈开的位置断（以前按字数硬切，会出现 mod/el）
    isw = lambda c: c.isascii() and c.isalnum()
    ok = [i for i in range(1, len(text)) if not (isw(text[i - 1]) and isw(text[i]))]
    i = min(ok, key=lambda i: abs(i - len(text) / 2)) if ok else len(text) // 2
    return split_line(text[:i], maxc) + split_line(text[i:], maxc)


def parse_srt(path):
    ev = []
    blocks = re.split(r"\n\s*\n", open(path, encoding="utf-8-sig").read().strip())
    for b in blocks:
        lines = b.strip().splitlines()
        tl = [l for l in lines if "-->" in l]
        if not tl:
            continue
        a, b2 = [x.strip().replace(",", ".") for x in tl[0].split("-->")]
        tosec = lambda s: sum(float(x) * m for x, m in zip(s.split(":")[::-1], [1, 60, 3600]))
        text = "".join(lines[lines.index(tl[0]) + 1:])
        ev.append({"type": "base", "start": tosec(a), "end": tosec(b2), "text": text})
    return ev


def subtract(a, b, cuts):
    segs = [(a, b)]
    for c0, c1 in cuts:
        nxt = []
        for s0, s1 in segs:
            if c1 <= s0 or c0 >= s1:
                nxt.append((s0, s1)); continue
            if c0 > s0: nxt.append((s0, c0))
            if c1 < s1: nxt.append((c1, s1))
        segs = nxt
    return [s for s in segs if s[1] - s[0] > 0.15]


def build(plan, fontsdir=None):
    global W, H
    cfg = plan.get("config", {})
    land = str(cfg.get("orient", "")).lower() in ("landscape", "h", "横屏")   # 横屏 1920×1080，默认竖屏
    W, H = (1920, 1080) if land else (1080, 1920)
    by = cfg.get("base_y", 1010 if land else BASE_Y); maxc = cfg.get("max_chars", 20 if land else 14)
    bc, ba, br = ("&H000000&", "&H10&", 24) if land else ("&H282828&", "&H60&", 14)       # 横屏：纯黑圆角条
    evs = list(plan.get("events", []))
    if plan.get("srt"):
        evs = parse_srt(plan["srt"]) + evs
    cuts = []
    for e in evs:
        if e["type"] in REPLACING or e.get("replace"):
            end = e["start"] + e.get("hold", 1.6) if e["type"] == "chapter" else e["end"]
            cuts.append((e["start"], end))
    L = []
    for e in evs:
        t, a, b = e["type"], e["start"], e.get("end", e["start"] + 2)
        if t == "base":
            txt = re.sub(PUNCT, " ", e["text"]).strip()
            parts = split_line(txt, maxc)
            dur = (b - a) / max(1, sum(len(p) for p in parts))
            t0 = a
            for p in parts:
                t1 = t0 + dur * len(p)
                for s0, s1 in subtract(t0, t1, cuts):
                    fs = cfg.get("base_size", 74 if land else 70); w = (tw(p, F_BASE, fs, fontsdir=fontsdir) * 0.69 + 72) if land else (tw(p, F_BASE, fs, fontsdir=fontsdir) + 44); h = (int(fs * 0.69) + 44) if land else (fs + 30)
                    L.append(dlg(0, s0, s1, f"{{\\an7\\pos({(W-w)/2:.0f},{by-h/2:.0f})\\p1\\bord0\\shad0\\1c{bc}\\1a{ba}}}{rrect(w,h,br)}"))
                    L.append(dlg(1, s0, s1, f"{{\\an5\\pos({W/2},{by})\\fn{F_BASE}\\fs{fs}\\1c&HFFFFFF&\\bord0\\shad0}}{p}"))
                t0 = t1
        elif t == "gold":
            # 金句：黄字放大弹出，顶掉普通字幕；多行逐行叠加
            big = e.get("big", False); fs = 116 if big else 84
            lines = e["lines"] if "lines" in e else [e["text"]]
            starts = e.get("line_starts", [a] * len(lines))
            y0 = e.get("y", by - (20 if big else 0))
            for i, (ln, st) in enumerate(zip(lines, starts)):
                y = y0 + i * (fs + 18)
                fsl = min(fs, int(fs * (W - 100) / max(1, tw(ln, F_FX, fs, fontsdir=fontsdir))))   # 太长就缩小，不出画
                L.append(dlg(2, st, b, f"{{\\an5\\pos({W/2},{y})\\fn{F_FX}\\fs{fsl}\\1c{YEL}\\3c{DARK}\\bord4\\shad4\\4a&H70&{POP}}}{ln}"))
        elif t == "punch":
            # 爆点大字 + 蓝色爆炸贴
            fs = e.get("size", 168); txt = e["text"]; y = e.get("y", by - 40)
            w = tw(txt, F_FX, fs, fontsdir=fontsdir); R = fs * 0.62
            sx, sy = W / 2 + w / 2 - R * 0.9, y - R
            L.append(dlg(2, a, b, f"{{\\an7\\pos({sx:.0f},{sy:.0f})\\p1\\bord0\\shad0\\1c{BLUE}\\frz12\\fscx20\\fscy20\\t(60,200,\\fscx115\\fscy115)\\t(200,280,\\fscx100\\fscy100)}}{star(R, R*0.62, 11)}"))
            L.append(dlg(3, a, b, f"{{\\an5\\pos({W/2},{y})\\fn{F_FX}\\fs{fs}\\1c{YEL}\\3c{DARK}\\bord6\\shad5\\4a&H60&\\fscx0\\fscy0\\t(0,150,\\fscx115\\fscy115)\\t(150,240,\\fscx100\\fscy100)}}{txt}"))
        elif t == "keywords":
            # 并列关键词：左起逐词出现，每词逐字显影
            fs = e.get("size", 78); x = e.get("x", 90); y = e.get("y", by)
            for word, st in e["words"]:
                L.append(dlg(2, st, b, f"{{\\an4\\pos({x:.0f},{y})\\fn{F_FX}\\fs{fs}\\1c{YEL}\\3c{DARK}\\bord4\\shad3\\4a&H70&}}{reveal(word, 0, 90, 150)}"))
                x += tw(word, F_FX, fs, fontsdir=fontsdir) + fs * 0.5
        elif t == "chapter":
            # 章节条：红条从左擦入+序号+标题逐字 → 中间停 hold 秒 → 缩到左上角常驻到 end
            num, title = str(e["num"]), e["title"]; hold = e.get("hold", 1.6)
            for phase, (s0, s1, k, x, y) in enumerate([(a, a + hold, 1.0, None, by), (a + hold, b, 0.5, 40, e.get("pin_y", 150))]):
                if s1 <= s0: continue
                nfs, tfs, sp = 120 * k, 62 * k, 10 * k
                nw = tw(num, F_BASE, nfs, fontsdir=fontsdir); tww = tw(title, F_BASE, tfs, sp, fontsdir=fontsdir)
                bw, bh = nw + tww + 90 * k, 84 * k
                x0 = (W - bw) / 2 if x is None else x; y0 = y - bh / 2
                L.append(dlg(4, s0, s1, f"{{\\an7\\pos({x0:.0f},{y0:.0f})\\p1\\bord0\\shad0\\1c{RED}\\1a&H18&\\clip({x0:.0f},0,{x0+1:.0f},{H})\\t(0,260,\\clip({x0:.0f},0,{x0+bw:.0f},{H}))}}{rrect(bw,bh,4)}"))
                L.append(dlg(5, s0, s1, f"{{\\an1\\pos({x0+22*k:.0f},{y0+bh+14*k:.0f})\\fn{F_BASE}\\fs{nfs:.0f}\\1c&HFFFFFF&\\bord0\\shad3\\4a&H80&\\alpha&HFF&\\t(120,260,\\alpha&H00&)}}{num}"))
                L.append(dlg(5, s0, s1, f"{{\\an4\\pos({x0+nw+56*k:.0f},{y:.0f})\\fn{F_BASE}\\fs{tfs:.0f}\\fsp{sp:.0f}\\1c&HFFFFFF&\\bord0\\shad0}}{reveal(title, 200, 55, 140)}"))
        elif t == "checklist":
            # 打勾清单：左上，逐条累加到 end
            fs = e.get("size", 68); x = e.get("x", 60); y = e.get("y", 300); bs = fs * 0.86
            for i, (item, st) in enumerate(e["items"]):
                yy = y + i * (fs + 30)
                chk = f"m {bs*.22:.0f} {bs*.5:.0f} l {bs*.42:.0f} {bs*.7:.0f} l {bs*.80:.0f} {bs*.24:.0f} l {bs*.90:.0f} {bs*.34:.0f} l {bs*.42:.0f} {bs*.86:.0f} l {bs*.12:.0f} {bs*.6:.0f}"
                L.append(dlg(6, st, b, f"{{\\an7\\pos({x},{yy-bs/2:.0f})\\p1\\bord0\\shad0\\1c{YEL}{POP}}}{rrect(bs,bs,bs*.22)}"))
                L.append(dlg(7, st, b, f"{{\\an7\\pos({x},{yy-bs/2:.0f})\\p1\\bord0\\shad0\\1c&HFFFFFF&\\alpha&HFF&\\t(150,260,\\alpha&H00&)}}{chk}"))
                L.append(dlg(7, st, b, f"{{\\an4\\pos({x+bs+18:.0f},{yy:.0f})\\fn{F_FX}\\fs{fs}\\1c&HFFFFFF&\\3c{DARK}\\bord3\\shad3\\4a&H60&}}{reveal(item, 120, 70, 150)}"))
        elif t == "note":
            # 手写批注/设问：斜放主体旁，逐字显影，和普通字幕共存
            fs = e.get("size", 64); c = YEL if e.get("color") == "yellow" else "&HFFFFFF&"
            x, y = e.get("x", 130), e.get("y", by - 150); ang = e.get("angle", 5)
            L.append(dlg(2, a, b, f"{{\\an4\\pos({x},{y})\\frz{ang}\\fn{F_FX}\\fs{fs}\\1c{c}\\3c{DARK}\\bord3\\shad3\\4a&H60&}}{reveal(e['text'], 0, 70, 160)}"))
        elif t == "sticker":
            # 物件贴纸：黄色胶囊 + 棕字，弹出，贴在物体旁
            fs = e.get("size", 76); x, y = e["x"], e["y"]; txt = e["text"]
            w = tw(txt, F_FX, fs, fontsdir=fontsdir) + fs * 0.9; h = fs * 1.45
            rot = e.get("angle", -4)
            L.append(dlg(6, a, b, f"{{\\an5\\pos({x},{y})\\org({x},{y})\\frz{rot}\\p1\\bord0\\shad2\\4a&HA0&\\1c&H4DD8FF&{POP}}}{rrect(w,h,h/2)}"))
            L.append(dlg(7, a, b, f"{{\\an5\\pos({x},{y})\\org({x},{y})\\frz{rot}\\fn{F_FX}\\fs{fs}\\1c{BROWN}\\bord0\\shad0{POP}}}{txt}"))
        elif t == "booktag":
            # 书名/产品名标签：黄底圆角 + 白字黑边
            fs = e.get("size", 66); txt = e["text"]; x = e.get("x", 300); y = e.get("y", by - 130)
            w = tw(txt, F_FX, fs, fontsdir=fontsdir) + fs * 0.7; h = fs * 1.5
            L.append(dlg(6, a, b, f"{{\\an5\\pos({x},{y})\\p1\\bord0\\shad0\\1c&H4DD8FF&{POP}}}{rrect(w,h,h*.18)}"))
            L.append(dlg(7, a, b, f"{{\\an5\\pos({x},{y})\\fn{F_FX}\\fs{fs}\\1c&HFFFFFF&\\3c{DARK}\\bord4\\shad0{POP}}}{txt}"))
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{F_BASE},60,&H00FFFFFF,&H00FFFFFF,&H00202020,&H80000000,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    return head + "\n".join(L) + "\n"


def _fonts_dir():
    """把用到的两个字体链接到一个纯英文路径的目录，给 ffmpeg 的 ass 滤镜用（路径里的空格/中文/冒号会让滤镜出错）"""
    d = os.path.join(os.path.expanduser("~"), ".cache", "koubo-fonts")
    os.makedirs(d, exist_ok=True)
    for key in ("sans_black", "kuaile"):
        p, _ = fontkit.find(key)
        dst = os.path.join(d, os.path.basename(p))
        if not os.path.exists(dst):
            try:
                os.symlink(p, dst)
            except OSError:
                shutil.copy(p, dst)
    return d


def render(plan, src, out, ass, fontsdir):
    src, out, ass = os.path.abspath(src), os.path.abspath(out), os.path.abspath(ass)
    pr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", src], capture_output=True, text=True).stdout.strip().split(",")
    vw, vh = int(pr[0]), int(pr[1])
    if abs(vw / vh - W / H) > 0.02:
        print(f"⚠️ 视频 {vw}x{vh} 和 plan 的画幅（{W}x{H}）不一致，字幕位置可能偏。横屏视频请在 config 里写 \"orient\": \"landscape\"")
    shr = [e for e in plan.get("events", []) if e["type"] == "shrink"]
    fd = f":fontsdir={_fonts_dir()}"
    ass_name = os.path.basename(ass)             # ffmpeg 在 ass 所在目录运行，滤镜里只写文件名
    if not shr:
        fc = f"[0:v]ass={ass_name}{fd}[v]"; extra = []
    else:
        k = plan.get("config", {}).get("shrink", 0.86)
        sw, sh = int(vw * k) // 2 * 2, int(vh * k) // 2 * 2
        mask = os.path.splitext(out)[0] + "_mask.png"
        im = Image.new("L", (sw, sh), 0); ImageDraw.Draw(im).rounded_rectangle([0, 0, sw - 1, sh - 1], radius=int(sw * 0.045), fill=255); im.save(mask)
        en = "+".join(f"between(t,{e['start']},{e['end']})" for e in shr)
        fc = (f"[0:v]split=2[m][s];[s]scale={sw}:{sh},format=rgba[sv];[1:v]format=gray[mk];[sv][mk]alphamerge[sr];"
              f"[m]drawbox=0:0:iw:ih:black:t=fill:enable='{en}'[mb];[mb][sr]overlay=(W-w)/2:(H-h)/2:enable='{en}'[v1];"
              f"[v1]ass={ass_name}{fd}[v]")
        extra = ["-loop", "1", "-i", mask]
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", src] + extra + ["-filter_complex", fc, "-map", "[v]", "-map", "0:a?",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "copy", "-shortest", out]
    subprocess.run(cmd, check=True, cwd=os.path.dirname(ass))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("src", nargs="?"); ap.add_argument("out")
    ap.add_argument("--ass-only", action="store_true"); ap.add_argument("--fonts", default=None, help="额外的字体目录（可选，默认自动找 ~/fonts 和系统目录）")
    A = ap.parse_args()
    if A.fonts:
        fontkit.add_dir(os.path.expanduser(A.fonts))
    plan = json.load(open(A.plan, encoding="utf-8"))
    ass_txt = build(plan, A.fonts)
    ass = A.out if A.ass_only else os.path.splitext(A.out)[0] + ".ass"
    open(ass, "w", encoding="utf-8").write(ass_txt)
    if not A.ass_only:
        render(plan, A.src, A.out, ass, A.fonts)
    print("ok ->", A.out)
