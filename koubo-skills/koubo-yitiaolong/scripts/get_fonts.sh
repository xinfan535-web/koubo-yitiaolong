#!/usr/bin/env bash
# 下载口播流水线要用的开源字体到 ~/fonts（已经有的不重复下）。需要能访问 github.com / raw.githubusercontent.com。
set -u
D="${KOUBO_FONTS:-$HOME/fonts}"
mkdir -p "$D"
get() {   # 文件名 网址
  if [ -s "$D/$1" ]; then echo "已有  $1"; return; fi
  echo "下载  $1 ..."
  if curl -fL --retry 2 -m 300 -o "$D/$1.part" "$2"; then mv "$D/$1.part" "$D/$1"; else rm -f "$D/$1.part"; echo "失败  $1（网络不通就手动下载放进 $D）"; fi
}
get ZCOOLKuaiLe-Regular.ttf  "https://raw.githubusercontent.com/google/fonts/main/ofl/zcoolkuaile/ZCOOLKuaiLe-Regular.ttf"
get LXGWWenKai-Regular.ttf   "https://github.com/lxgw/LxgwWenKai/releases/latest/download/LXGWWenKai-Regular.ttf"
get NotoSansSC-Black.otf     "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/SubsetOTF/SC/NotoSansSC-Black.otf"
get NotoSansSC-Bold.otf      "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/SubsetOTF/SC/NotoSansSC-Bold.otf"
get NotoSerifSC-Black.otf    "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Serif/SubsetOTF/SC/NotoSerifSC-Black.otf"
echo "完成。字体目录：$D"
