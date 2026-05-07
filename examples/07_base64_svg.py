#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例 7：Base64 与 SVG 输出
============================

演示如何将二维码输出为 Base64 数据 URI 或 SVG 矢量图，
适用于 Web 开发和不生成临时文件的场景。
"""

from xqr import encode
from PIL import Image
import io
import base64


def main():
    print("=" * 50)
    print("示例 7：Base64 与 SVG 输出")
    print("=" * 50)

    # ── Base64 输出 ───────────────────────────────────────────
    print("\n[1] 生成 Base64 数据 URI")
    b64 = encode("https://github.com", base64=True)
    print("    长度:", len(b64), "字符")
    print("    前缀:", b64[:60] + "...")
    print("    可用作 HTML img 的 src 属性:")
    print('    <img src="{}" />'.format(b64[:50] + "..."))

    # ── 自定义颜色的 Base64 ───────────────────────────────────
    print("\n[2] 自定义颜色的 Base64 二维码")
    b64_blue = encode("https://example.com", base64=True,
                      fill_color="#1677FF", back_color="white")
    print("    长度:", len(b64_blue), "字符")

    # ── SVG 矢量输出 ──────────────────────────────────────────
    print("\n[3] 生成 SVG 矢量二维码")
    svg = encode("https://github.com", svg=True)
    print("    长度:", len(svg), "字符")
    print("    前 100 字符:", svg[:100])

    # ── 保存 SVG 到文件 ──────────────────────────────────────
    print("\n[4] 保存 SVG 到文件")
    svg = encode("https://example.com", svg=True)
    with open("output_qr.svg", "w", encoding="utf-8") as f:
        f.write(svg)
    print("    ✅ 已生成: output_qr.svg")
    print("    可以在浏览器中直接打开")

    # ── Base64 转为 PIL Image ─────────────────────────────────
    print("\n[5] Base64 转回 PIL Image")
    b64 = encode("Hello World", base64=True)
    # 从 Base64 数据 URI 提取图片数据
    header, encoded = b64.split(",", 1)
    img_data = base64.b64decode(encoded)
    img = Image.open(io.BytesIO(img_data))
    print("    类型:", type(img).__name__)
    print("    大小:", img.size)
    print("    模式:", img.mode)

    # ── 综合应用：生成用于网页的多种格式 ──────────────────────
    print("\n[6] 综合应用 —— 为网页生成多种格式")
    data = "https://xqr.dev"

    b64_png = encode(data, base64=True)
    b64_svg = encode(data, svg=True)

    print("    用于 HTML img 标签:")
    print('    <!-- PNG 格式 -->')
    print('    <img src="data:image/png;base64,..." alt="QR" />')
    print('    <!-- SVG 格式 -->')
    print('    <img src="data:image/svg+xml;base64,..." alt="QR" />')
    print()
    print("    用于 Markdown:")
    print("    ![QR](data:image/png;base64,...)")

    print("\n" + "=" * 50)
    print("示例 7 执行完毕！")
    print("=" * 50)


if __name__ == "__main__":
    main()
