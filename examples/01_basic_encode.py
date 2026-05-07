#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例 1：基本二维码生成
========================

演示 XQR 最基础的二维码生成功能 —— 一行代码生成二维码。
"""

from xqr import encode


def main():
    print("=" * 50)
    print("示例 1：基本二维码生成")
    print("=" * 50)

    # ── 最简单的用法：生成并保存到文件 ─────────────────────────
    print("\n[1] 生成二维码并保存到文件")
    encode("https://github.com", "output_github.png")
    print("    ✅ 已生成: output_github.png")

    # ── 不指定路径，返回 PIL Image 对象 ────────────────────────
    print("\n[2] 返回 PIL Image 对象（不保存到文件）")
    img = encode("Hello World")
    print("    类型:", type(img).__name__)
    print("    大小:", img.size)
    print("    模式:", img.mode)

    # ── 编码网址 ──────────────────────────────────────────────
    print("\n[3] 编码网址")
    encode("https://www.python.org", "output_python.png")
    print("    ✅ 已生成: output_python.png")

    # ── 编码纯文本 ────────────────────────────────────────────
    print("\n[4] 编码纯文本")
    encode("XQR 高性能二维码库", "output_text.png")
    print("    ✅ 已生成: output_text.png")

    # ── 指定版本和纠错等级 ─────────────────────────────────────
    print("\n[5] 指定版本（5）和最高纠错等级（H）")
    encode("https://example.com", "output_v5h.png",
           version=5, level="H")
    print("    ✅ 已生成: output_v5h.png")

    print("\n" + "=" * 50)
    print("示例 1 执行完毕！")
    print("=" * 50)


if __name__ == "__main__":
    main()
