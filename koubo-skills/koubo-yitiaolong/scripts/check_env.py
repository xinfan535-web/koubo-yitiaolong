#!/usr/bin/env python3
"""口播流水线环境检查：开工前跑一次，缺什么直接告诉你怎么装。
用法: python3 check_env.py
"""
import importlib, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.dirname(os.path.dirname(HERE))
ok_all = True


def line(ok, name, detail=""):
    global ok_all
    ok_all &= ok
    print(f"{'✅' if ok else '❌'} {name:22s} {detail}")


line(sys.version_info >= (3, 8), "python3", sys.version.split()[0])
for mod, pip in (("PIL", "pillow"), ("numpy", "numpy")):
    try:
        importlib.import_module(mod); line(True, f"python 包 {pip}")
    except ImportError:
        line(False, f"python 包 {pip}", f"装法: pip3 install {pip}（报 externally-managed 就加 --break-system-packages）")
try:
    importlib.import_module("rembg"); line(True, "rembg（封面抠图用）")
except ImportError:
    print("➖ rembg（封面抠图用）     没装也不影响图解/字幕；做封面前装: pip3 install 'rembg[cpu]'")

ff = shutil.which("ffmpeg")
line(bool(ff), "ffmpeg", ff or "装法: macOS 用 brew install ffmpeg")
if ff:
    flt = subprocess.run([ff, "-hide_banner", "-filters"], capture_output=True, text=True).stdout
    line(" ass " in flt, "ffmpeg 的 ass 滤镜", "字幕渲染必需" if " ass " in flt else "缺 libass：brew reinstall ffmpeg（官方 brew 版自带）")
    enc = subprocess.run([ff, "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
    line("libx264" in enc, "ffmpeg 的 libx264")
line(bool(shutil.which("ffprobe")), "ffprobe")

sys.path.insert(0, HERE)
try:
    import fontkit
    for k, label in (("hand", "霞鹜文楷（图解手写字）"), ("kuaile", "站酷快乐体（金句/贴纸）"),
                     ("sans_black", "思源黑体 Black（字幕）"), ("serif_black", "思源宋体 Black（封面标题）")):
        try:
            p, _ = fontkit.find(k); line(True, label, p)
        except fontkit.FontMissing:
            line(False, label, f"运行: bash {HERE}/get_fonts.sh")
except Exception as e:      # noqa
    line(False, "字体检查", str(e))

print("\n其他 skill（可选依赖）：")
for s in ("ra-hook", "ra-renhua"):
    print(f"  {'✅' if os.path.isdir(os.path.join(SKILLS, s)) else '➖'} {s}")
print("\n" + ("环境齐了。" if ok_all else "有 ❌ 的先补上再开工。"))
sys.exit(0 if ok_all else 1)
