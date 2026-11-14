"""字体查找：跨 macOS / Linux，找不到就明确报错，不静默换字体。

用法：
    import fontkit
    path, idx = fontkit.find("hand")       # 返回 (文件路径, ttc 序号)
    fam = fontkit.family("sans_black")     # ASS 里 \\fn 要用的字体名
    fontkit.add_dir("/some/dir")           # 额外搜索目录（也可设环境变量 KOUBO_FONTS）
字体放哪都行，优先 ~/fonts。缺什么运行 koubo-yitiaolong/scripts/get_fonts.sh 下载。
"""
import os, sys

HOME = os.path.expanduser("~")
_DIRS = [os.environ.get("KOUBO_FONTS", ""), os.path.join(HOME, "fonts"),
         os.path.join(HOME, "Library/Fonts"), "/Library/Fonts", "/System/Library/Fonts",  # portable-ok
         "/usr/share/fonts", "/usr/local/share/fonts"]                                    # portable-ok
SPECS = {   # key: (候选文件名, ttc 里简体中文的序号)
    "hand":        (["LXGWWenKai-Regular.ttf"], 0),
    "kuaile":      (["ZCOOLKuaiLe-Regular.ttf"], 0),
    "sans_black":  (["NotoSansSC-Black.otf", "NotoSansCJKsc-Black.otf", "NotoSansCJK-Black.ttc"], 2),
    "sans_bold":   (["NotoSansSC-Bold.otf", "NotoSansCJKsc-Bold.otf", "NotoSansCJK-Bold.ttc"], 2),
    "serif_black": (["NotoSerifSC-Black.otf", "NotoSerifCJKsc-Black.otf", "NotoSerifCJK-Black.ttc"], 2),
}
_cache = {}


class FontMissing(RuntimeError):
    pass


def add_dir(d):
    if d and d not in _DIRS:
        _DIRS.insert(0, d)
        _cache.clear()


def _scan(d, names, depth=3):
    if not d or not os.path.isdir(d):
        return None
    low = {n.lower(): n for n in names}
    base = d.rstrip(os.sep).count(os.sep)
    for root, dirs, files in os.walk(d):
        if root.count(os.sep) - base >= depth:
            dirs[:] = []
        for f in files:
            if f.lower() in low:
                return os.path.join(root, f), f
    return None


def find(key):
    if key in _cache:
        return _cache[key]
    names, ttc_idx = SPECS[key]
    for n in names:                       # 候选按优先级：先单语言 otf，再 ttc
        for d in _DIRS:
            hit = _scan(d, [n])
            if hit:
                p = hit[0]
                _cache[key] = (p, ttc_idx if p.lower().endswith(".ttc") else 0)
                return _cache[key]
    raise FontMissing(f"缺字体 {names[0]}（key={key}）。运行 koubo-yitiaolong/scripts/get_fonts.sh 下载到 ~/fonts，"
                      f"或设环境变量 KOUBO_FONTS 指向字体目录。")


def family(key):
    """字体文件里的 family 名，给 ASS 的 \\fn 用。"""
    from PIL import ImageFont
    p, i = find(key)
    fam, style = ImageFont.truetype(p, 20, index=i).getname()
    # 粗体字重在 style 里（如 Noto Sans SC / Black），ASS 要写成 "Noto Sans SC Black" 才选得中
    return fam if style.lower() in ("regular", "normal", "book") else f"{fam} {style}"


def truetype(key, size):
    from PIL import ImageFont
    p, i = find(key)
    return ImageFont.truetype(p, int(size), index=i)


if __name__ == "__main__":
    bad = 0
    for k in SPECS:
        try:
            p, i = find(k); print(f"OK   {k:12s} {p} (index {i})")
        except FontMissing as e:
            bad += 1; print(f"缺   {k:12s}")
    sys.exit(1 if bad else 0)
