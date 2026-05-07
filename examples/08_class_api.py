#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例 8：XQR 类接口
====================

演示使用 XQR 类的完整功能，适合需要精细控制的场景。
类接口提供比 encode() 函数更多的控制选项。
"""

from xqr import XQR, ERROR_CORRECT_H, ERROR_CORRECT_L
from PIL import Image


def main():
    print("=" * 50)
    print("示例 8：XQR 类接口")
    print("=" * 50)

    # ── 基础用法：创建 XQR 实例 ───────────────────────────────
    print("\n[1] 创建 XQR 实例并生成")
    qr = XQR(data="https://github.com")
    qr.make()
    print("    版本号:", qr.version)
    print("    模块数:", qr.modules_count)
    img = qr.to_image()
    img.save("output_class_basic.png")
    print("    ✅ 已生成: output_class_basic.png")

    # ── 指定版本和纠错等级 ────────────────────────────────────
    print("\n[2] 指定版本（5）和最高纠错等级（H）")
    qr = XQR(
        data="https://example.com/very/long/url/that/needs/more/space",
        version=5,
        level=ERROR_CORRECT_H,
    )
    qr.make()
    print("    版本号:", qr.version)
    print("    模块数:", qr.modules_count)
    qr.save("output_class_v5h.png", fill_color="black", back_color="white")
    print("    ✅ 已生成: output_class_v5h.png")

    # ── 获取二维码矩阵 ────────────────────────────────────────
    print("\n[3] 获取二维码矩阵数据")
    qr = XQR(data="Hello", version=1)
    qr.make()
    matrix = qr.get_matrix()
    print("    矩阵维度: {}×{}".format(len(matrix), len(matrix[0])))
    print("    前 3 行前 10 列:")
    for row in matrix[:3]:
        print("    ", "".join("█" if c else " " for c in row[:10]))

    # ── 多种输出格式 ──────────────────────────────────────────
    print("\n[4] 多种输出格式")
    qr = XQR(data="https://xqr.dev")
    qr.make()

    # 保存 PNG
    qr.save("output_class_png.png", format="PNG")
    print("    ✅ PNG: output_class_png.png")

    # 输出终端
    print("    终端输出:")
    qr.to_terminal()

    # Base64
    b64 = qr.to_base64()
    print("    Base64 长度:", len(b64), "字符")

    # SVG
    svg = qr.to_svg()
    print("    SVG 长度:", len(svg), "字符")

    # ── 艺术融合 ──────────────────────────────────────────────
    print("\n[5] 类接口 —— 艺术二维码融合")
    # 创建一个渐变背景
    bg = Image.new("RGB", (150, 150), (255, 255, 255))
    for y in range(150):
        r = int(200 - 100 * y / 150)
        g = int(100 + 155 * y / 150)
        b = int(255 - 200 * y / 150)
        for x in range(150):
            bg.putpixel((x, y), (r, g, b))
    bg.save("temp_bg.png")

    qr = XQR(data="https://xqr.dev")
    qr.make()
    art_img = qr.to_artistic("temp_bg.png", colorized=True)
    art_img.save("output_class_artistic.png")
    print("    ✅ 已生成: output_class_artistic.png")

    # ── 添加数据后重新生成 ────────────────────────────────────
    print("\n[6] 修改数据重新生成")
    qr = XQR()
    qr.add_data("第一段数据")
    qr.make()
    print("    第一次生成版本:", qr.version)

    qr.add_data("第二段数据（更长的内容会使用更大的版本）")
    qr.make()
    print("    第二次生成版本:", qr.version)
    qr.save("output_class_update.png")
    print("    ✅ 已生成: output_class_update.png")

    # ── 自定义模块大小 ────────────────────────────────────────
    print("\n[7] 自定义模块大小（box_size=20 大尺寸二维码）")
    qr = XQR(data="https://example.com", box_size=20, border=4)
    qr.make()
    img = qr.to_image()
    print("    图像大小:", img.size)
    img.save("output_class_large.png")
    print("    ✅ 已生成: output_class_large.png")

    # ── 类方法解码 ────────────────────────────────────────────
    print("\n[8] XQR.decode() 静态方法解码")
    XQR(data="https://xqr.dev/class-decode-test").save("temp_decode.png")
    result = XQR.decode("temp_decode.png")
    print("    解码结果:", result)

    import os
    for f in ["temp_bg.png", "temp_decode.png"]:
        if os.path.exists(f):
            os.remove(f)

    print("\n" + "-" * 50)
    print("生成的文件列表:")
    import os
    for f in sorted(os.listdir(".")):
        if f.startswith("output_class_") and f.endswith(".png"):
            size = os.path.getsize(f)
            print(f"  {f:30s} ({size} bytes)")

    print("\n" + "=" * 50)
    print("示例 8 执行完毕！")
    print("=" * 50)


if __name__ == "__main__":
    main()
