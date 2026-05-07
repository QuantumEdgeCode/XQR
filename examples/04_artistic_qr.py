#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例 4：艺术二维码
====================

演示如何将二维码与背景图片融合，生成艺术风格二维码。
艺术二维码不仅美观，而且仍然可以被扫码器识别和解码。
"""

from xqr import encode, decode
from PIL import Image, ImageDraw, ImageFont
import os


def create_test_background(filename, width=300, height=300):
    """创建一个测试用的渐变背景图片"""
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    for y in range(height):
        r = int(100 + 155 * y / height)
        g = int(180 - 80 * y / height)
        b = int(255 - 155 * y / height)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    img.save(filename)
    return filename


def create_pattern_background(filename, width=300, height=300):
    """创建一个带棋盘格图案的背景"""
    img = Image.new("RGB", (width, height), (240, 240, 245))
    draw = ImageDraw.Draw(img)
    size = 30
    for x in range(0, width, size):
        for y in range(0, height, size):
            if (x // size + y // size) % 2 == 0:
                draw.rectangle([x, y, x + size - 1, y + size - 1],
                               fill=(200, 220, 240))
    img.save(filename)
    return filename


def create_photo_like_background(filename, width=300, height=300):
    """创建一个类似照片的背景"""
    img = Image.new("RGB", (width, height), (135, 206, 235))
    draw = ImageDraw.Draw(img)
    # 草地
    draw.rectangle([(0, 200), (width, height)], fill=(34, 139, 34))
    # 太阳
    draw.ellipse([(200, 30), (270, 100)], fill=(255, 215, 0))
    # 云朵
    draw.ellipse([(50, 50), (120, 90)], fill=(255, 255, 255))
    draw.ellipse([(80, 40), (150, 80)], fill=(255, 255, 255))
    img.save(filename)
    return filename


def main():
    print("=" * 50)
    print("示例 4：艺术二维码")
    print("=" * 50)

    # 创建各种测试背景
    bg_gradient = create_test_background("bg_gradient.png")
    bg_pattern = create_pattern_background("bg_pattern.png")
    bg_photo = create_photo_like_background("bg_photo.png")

    # ── 黑白艺术二维码 ────────────────────────────────────────
    print("\n[1] 黑白艺术二维码")
    encode("https://example.com", "output_art_bw.png",
           picture=bg_gradient, colorized=False)
    print("    ✅ 已生成: output_art_bw.png")

    # ── 彩色艺术二维码 ────────────────────────────────────────
    print("\n[2] 彩色艺术二维码")
    encode("https://example.com", "output_art_color.png",
           picture=bg_gradient, colorized=True)
    print("    ✅ 已生成: output_art_color.png")

    # ── 使用不同背景图片 ──────────────────────────────────────
    print("\n[3] 棋盘格背景的艺术二维码")
    encode("https://example.com", "output_art_pattern.png",
           picture=bg_pattern, colorized=True)
    print("    ✅ 已生成: output_art_pattern.png")

    # ── 风景风格背景 ──────────────────────────────────────────
    print("\n[4] 风景风格背景")
    encode("https://example.com", "output_art_photo.png",
           picture=bg_photo, colorized=True)
    print("    ✅ 已生成: output_art_photo.png")

    # ── 调整对比度和亮度 ──────────────────────────────────────
    print("\n[5] 高对比度（contrast=2.0, brightness=0.7）")
    encode("https://example.com", "output_art_contrast.png",
           picture=bg_gradient, colorized=True,
           contrast=2.0, brightness=0.7)
    print("    ✅ 已生成: output_art_contrast.png")

    # ── 低对比度柔和效果 ──────────────────────────────────────
    print("\n[6] 低对比度柔和效果（contrast=0.6, brightness=1.3）")
    encode("https://example.com", "output_art_soft.png",
           picture=bg_gradient, colorized=True,
           contrast=0.6, brightness=1.3)
    print("    ✅ 已生成: output_art_soft.png")

    # ── 艺术二维码解码验证 ────────────────────────────────────
    print("\n[7] 验证：艺术二维码能否被解码")
    test_url = "https://xqr.dev/art-test"
    encode(test_url, "temp_art_decode_test.png",
           picture=bg_gradient, colorized=True)
    result = decode("temp_art_decode_test.png")
    print("    原始内容:", test_url)
    print("    解码结果:", result)
    print("    匹配:", "✅" if result == test_url else "❌")
    os.remove("temp_art_decode_test.png")

    # ── 中文艺术二维码 ────────────────────────────────────────
    print("\n[8] 中文内容的艺术二维码")
    encode("你好世界！艺术二维码", "output_art_chinese.png",
           picture=bg_gradient, colorized=True)
    result = decode("output_art_chinese.png")
    print("    解码结果:", result)
    print("    匹配:", "✅" if "你好世界" in result else "❌")

    # 清理背景文件
    for f in [bg_gradient, bg_pattern, bg_photo]:
        if os.path.exists(f):
            os.remove(f)

    print("\n" + "-" * 50)
    print("生成的艺术二维码文件:")
    for f in sorted(os.listdir(".")):
        if f.startswith("output_art_") and f.endswith(".png"):
            size = os.path.getsize(f)
            print(f"  {f:35s} ({size} bytes)")

    print("\n" + "=" * 50)
    print("示例 4 执行完毕！")
    print("=" * 50)


if __name__ == "__main__":
    main()
