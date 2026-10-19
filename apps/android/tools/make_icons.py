#!/usr/bin/env python3
"""从站点图标生成 Android 各密度启动图标。

源图 ``assets/images/favicon-180.png`` 本身就是一个完整的图标：蓝色圆角方块 +
白色书本 + 浅蓝声波。所以这里**不再垫任何背景、也不再缩小内容**，直接把整张图
缩放到各密度尺寸即可 —— 早期版本垫了白色画布并把内容缩到 88%，在桌面上看就是
「蓝图标外面套了一圈白边」。

不生成 adaptive icon（``mipmap-anydpi-v26``）：自适应图标要求把前景/背景拆开，
而源图是「底色 + 图案」一张图，拆开后要么图案变小、要么边缘露出背景色，都会再次
出现一圈边。直接用原始图标交给启动器套遮罩，效果最接近站点图标。

需要 Pillow（只在重新生成图标时用一次，不属于构建链路）::

    python tools/make_icons.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
REPOSITORY = ROOT.parent.parent
SOURCE = REPOSITORY / "assets" / "images" / "favicon-180.png"

# 密度 -> 传统图标边长（48dp 基准）
DENSITIES = {
    "mdpi": 48,
    "hdpi": 72,
    "xhdpi": 96,
    "xxhdpi": 144,
    "xxxhdpi": 192,
}


def main() -> int:
    if not SOURCE.is_file():
        raise SystemExit(f"找不到源图：{SOURCE}")

    source = Image.open(SOURCE).convert("RGBA")

    for density, size in DENSITIES.items():
        directory = ROOT / "res" / f"mipmap-{density}"
        directory.mkdir(parents=True, exist_ok=True)

        icon = source.resize((size, size), Image.LANCZOS)
        icon.save(directory / "ic_launcher.png", format="PNG", optimize=True)

        # 早期版本留下的自适应前景层，删除以免混淆。
        stale = directory / "ic_launcher_foreground.png"
        if stale.exists():
            stale.unlink()

        print(f"mipmap-{density}: ic_launcher {size}px")

    # 自适应图标配置一并移除，让系统直接使用上面的 PNG。
    anydpi = ROOT / "res" / "mipmap-anydpi-v26"
    if anydpi.is_dir():
        for item in anydpi.iterdir():
            item.unlink()
        anydpi.rmdir()
        print("已移除 mipmap-anydpi-v26（改用整张图标）")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
