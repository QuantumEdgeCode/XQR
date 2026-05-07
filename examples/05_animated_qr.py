#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例 5：动态二维码（GIF）
==========================

演示如何从动态 GIF 背景生成动态二维码。
动态二维码的每一帧都融合了二维码图案，播放时背景会动起来。
"""

from xqr import encode, decode
from PIL import Image
import os


def create_test_gif(filename, num_frames=8, width=150, height=150):
    """创建一个测试用的动态 GIF（彩色渐变）"""
    frames = []
    for i in range(num_frames):
        hue = int(360 * i / num_frames)
        # 创建 HSL 颜色
        r = int(128 + 127 * __import__("math").sin(hue * 3.14159 / 180))
        g = int(128 + 127 * __import__("math").sin((hue + 120) * 3.14159 / 180))
        b = int(128 + 127 * __import__("math").sin((hue + 240) * 3.14159 / 180))
        frame = Image.new("RGB", (width, height), (r, g, b))
        frames.append(frame)

    frames[0].save(
        filename,
        save_all=True,
        append_images=frames[1:],
        duration=200,  # 每帧 200ms
        loop=0,        # 无限循环
    )
    return filename


def create_moving_ball_gif(filename, num_frames=10, width=150, height=150):
    """创建一个小球移动的动画 GIF"""
    frames = []
    for i in range(num_frames):
        frame = Image.new("RGB", (width, height), (255, 255, 255))
        from PIL import ImageDraw
        draw = ImageDraw.Draw(frame)
        x = int(width * i / num_frames)
        y = int(height / 2)
        r = 15
        draw.ellipse([(x - r, y - r), (x + r, y + r)], fill=(255, 100, 100))
        frames.append(frame)

    frames[0].save(
        filename,
        save_all=True,
        append_images=frames[1:],
        duration=150,
        loop=0,
    )
    return filename


def main():
    print("=" * 50)
    print("示例 5：动态二维码（GIF）")
    print("=" * 50)

    # 创建测试 GIF
    gif_color = create_test_gif("anim_color.gif")
    gif_ball = create_moving_ball_gif("anim_ball.gif")

    # ── 生成彩色渐变动态二维码 ────────────────────────────────
    print("\n[1] 彩色渐变动态二维码")
    encode("https://example.com", "output_anim_color.gif",
           picture=gif_color, colorized=True)
    print("    ✅ 已生成: output_anim_color.gif")

    # ── 验证动态二维码的帧数 ──────────────────────────────────
    print("\n[2] 验证动态二维码属性")
    with Image.open("output_anim_color.gif") as im:
        print("    帧数:", im.n_frames)
        print("    是否循环:", im.info.get("loop", 0) == 0)
        print("    每帧时长:", im.info.get("duration", "N/A"), "ms")

    # ── 生成小球移动动态二维码 ────────────────────────────────
    print("\n[3] 小球移动动态二维码")
    encode("https://example.com", "output_anim_ball.gif",
           picture=gif_ball, colorized=True)
    print("    ✅ 已生成: output_anim_ball.gif")

    # ── 黑白动态二维码 ────────────────────────────────────────
    print("\n[4] 黑白动态二维码")
    encode("https://example.com", "output_anim_bw.gif",
           picture=gif_color, colorized=False)
    print("    ✅ 已生成: output_anim_bw.gif")

    # ── 中文内容的动态二维码 ──────────────────────────────────
    print("\n[5] 中文内容动态二维码")
    encode("你好世界！动态二维码", "output_anim_chinese.gif",
           picture=gif_color, colorized=True)
    print("    ✅ 已生成: output_anim_chinese.gif")

    # ── 生成指定时长 ─────────────────────────────────────────
    print("\n[6] 生成帧数更多的动态二维码（15帧）")
    gif_long = create_test_gif("anim_long.gif", num_frames=15)
    encode("https://example.com", "output_anim_long.gif",
           picture=gif_long, colorized=True)
    with Image.open("output_anim_long.gif") as im:
        print("    帧数:", im.n_frames)
    print("    ✅ 已生成: output_anim_long.gif")

    # 清理背景 GIF
    for f in [gif_color, gif_ball, "anim_long.gif"]:
        if os.path.exists(f):
            os.remove(f)

    print("\n" + "-" * 50)
    print("生成的动态二维码文件:")
    for f in sorted(os.listdir(".")):
        if f.startswith("output_anim_") and f.endswith(".gif"):
            size = os.path.getsize(f)
            print(f"  {f:30s} ({size} bytes)")

    print("\n" + "=" * 50)
    print("示例 5 执行完毕！")
    print("提示：用浏览器打开 .gif 文件查看动画效果")
    print("=" * 50)


if __name__ == "__main__":
    main()
