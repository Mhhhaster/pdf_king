#!/usr/bin/env python3
"""生成 PDFKing 应用图标"""

import subprocess
import tempfile
import os

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("安装 Pillow...")
    subprocess.check_call(["pip", "install", "Pillow"])
    from PIL import Image, ImageDraw, ImageFont


def create_icon():
    size = 1024
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 圆角矩形背景
    margin = 40
    radius = 200
    bg_color = (24, 24, 37, 255)  # #181825
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=radius, fill=bg_color
    )

    # 内部渐变效果 - 中心亮色区域
    center_color = (49, 50, 68, 200)
    draw.rounded_rectangle(
        [margin + 60, margin + 60, size - margin - 60, size - margin - 60],
        radius=radius - 40, fill=center_color
    )

    # PDF 图标形状 (文件折角)
    file_left = 280
    file_top = 180
    file_right = 744
    file_bottom = 750
    fold_size = 120
    file_color = (137, 180, 250, 255)  # #89b4fa

    # 文件主体
    points = [
        (file_left, file_top),
        (file_right - fold_size, file_top),
        (file_right, file_top + fold_size),
        (file_right, file_bottom),
        (file_left, file_bottom),
    ]
    draw.polygon(points, fill=file_color)

    # 折角三角形
    fold_color = (69, 71, 90, 255)
    draw.polygon([
        (file_right - fold_size, file_top),
        (file_right, file_top + fold_size),
        (file_right - fold_size, file_top + fold_size),
    ], fill=fold_color)

    # "PDF" 文字
    try:
        font_pdf = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 140)
    except (OSError, IOError):
        font_pdf = ImageFont.load_default()

    text_color = (24, 24, 37, 255)
    draw.text((350, 380), "PDF", fill=text_color, font=font_pdf)

    # 下方 "King" 文字
    try:
        font_king = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 100)
    except (OSError, IOError):
        font_king = ImageFont.load_default()

    king_color = (166, 227, 161, 255)  # #a6e3a1
    draw.text((330, 800), "King", fill=king_color, font=font_king)

    # 皇冠元素
    crown_color = (249, 226, 175, 255)  # #f9e2af
    crown_points = [
        (390, 160),
        (420, 100),
        (460, 145),
        (512, 80),
        (564, 145),
        (604, 100),
        (634, 160),
    ]
    draw.polygon(crown_points, fill=crown_color)

    # 保存为 PNG
    png_path = "icon.png"
    img.save(png_path, "PNG")
    print(f"✅ 已生成 {png_path}")

    # 转换为 icns (macOS)
    try:
        iconset_dir = tempfile.mkdtemp(suffix=".iconset")
        sizes = [16, 32, 64, 128, 256, 512, 1024]
        for s in sizes:
            resized = img.resize((s, s), Image.LANCZOS)
            resized.save(os.path.join(iconset_dir, f"icon_{s}x{s}.png"))
            if s <= 512:
                resized2x = img.resize((s * 2, s * 2), Image.LANCZOS)
                resized2x.save(os.path.join(iconset_dir, f"icon_{s}x{s}@2x.png"))

        subprocess.run(
            ["iconutil", "-c", "icns", iconset_dir, "-o", "icon.icns"],
            check=True
        )
        print("✅ 已生成 icon.icns")
    except Exception as e:
        print(f"⚠️ icns 转换失败 (不影响使用): {e}")


if __name__ == '__main__':
    create_icon()
