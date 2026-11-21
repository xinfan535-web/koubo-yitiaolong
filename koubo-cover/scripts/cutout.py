#!/usr/bin/env python3
"""人物抠图：照片 -> 透明背景 PNG（rembg，isnet-general-use 模型）。
用法: python3 cutout.py 照片.png 抠图.png
首次运行 rembg 会自动下载模型（约 170MB，存 ~/.rembg）。装法: pip3 install 'rembg[cpu]'
抠完务必放大检查头发丝和镜框边缘；背景有书架/杂物时会有残留，宁可让用户重拍。
"""
import sys
from PIL import Image

if len(sys.argv) != 3:
    sys.exit(__doc__)
try:
    from rembg import new_session, remove
except ImportError:
    sys.exit("缺 rembg：pip3 install 'rembg[cpu]'")
im = Image.open(sys.argv[1]).convert("RGB")
out = remove(im, session=new_session("isnet-general-use"))
out.save(sys.argv[2])
print("ok ->", sys.argv[2], out.size)
