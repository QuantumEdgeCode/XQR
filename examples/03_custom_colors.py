#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例 3：自定义颜色
====================

演示如何自定义二维码的填充色和背景色，
让你的二维码更具品牌特色。
"""

from xqr import encode
from PIL import Image


def main():
    print("=" * 50)
    print("示例 3：自定义颜色")
    print("=" * 50)

    # ── 经典黑白 ──────────────────────────────────────────────
    print("\n[1] 经典黑白（默认）")
    encode("https://example.com", "output_black_white.png")
    print("    ✅ 已生成: output_black_white.png")

    # ── 蓝底白码 ──────────────────────────────────────────────
    print("\n[2] 蓝色背景 + 白色二维码")
    encode("https://example.com", "output_blue_white.png",
           fill_color="white", back_color="blue")
    print("    ✅ 已生成: output_blue_white.png")

    # ── 红底黑码 ──────────────────────────────────────────────
    print("\n[3] 红色背景 + 黑色二维码")
    encode("https://example.com", "output_red_black.png",
           fill_color="black", back_color="red")
    print("    ✅ 已生成: output_red_black.png")

    # ── 16进制颜色 ────────────────────────────────────────────
    print("\n[4] 使用十六进制颜色值")
    encode("https://example.com", "output_hex_colors.png",
           fill_color="#FF6B35", back_color="#F7C59F")
    print("    ✅ 已生成: output_hex_colors.png")

    # ── 品牌色示例：微信绿 ─────────────────────────────────────
    print("\n[5] 品牌色 —— 微信绿")
    encode("https://weixin.qq.com", "output_wechat_green.png",
           fill_color="#07C160", back_color="white")
    print("    ✅ 已生成: output_wechat_green.png")

    # ── 品牌色示例：支付宝蓝 ──────────────────────────────────
    print("\n[6] 品牌色 —— 支付宝蓝")
    encode("https://www.alipay.com", "output_alipay_blue.png",
           fill_color="#1677FF", back_color="white")
    print("    ✅ 已生成: output_alipay_blue.png")

    # ── 透明背景 ──────────────────────────────────────────────
    print("\n[7] 透明背景（适用于叠加到其他图片上）")
    encode("https://example.com", "output_transparent.png",
           fill_color="black", back_color="transparent")
    print("    ✅ 已生成: output_transparent.png")

    # ── 渐变色拼接（通过两张二维码叠加模拟）─────────────────────
    print("\n[8] 深色主题 —— 白码深灰底")
    encode("https://example.com", "output_dark_mode.png",
           fill_color="white", back_color="#1a1a2e")
    print("    ✅ 已生成: output_dark_mode.png")

    # 查看所有生成的图片
    print("\n" + "-" * 50)
    print("生成的文件列表:")
    import os
    for f in sorted(os.listdir(".")):
        if f.startswith("output_") and f.endswith(".png"):
            size = os.path.getsize(f)
            print(f"  {f:30s} ({size} bytes)")

    print("\n" + "=" * 50)
    print("示例 3 执行完毕！")
    print("=" * 50)


if __name__ == "__main__":
    main()
