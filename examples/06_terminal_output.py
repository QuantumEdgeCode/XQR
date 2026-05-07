#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例 6：终端输出二维码
=======================

演示如何在命令行终端中直接打印二维码，
无需图形界面即可展示二维码。
"""

from xqr import encode


def main():
    print("=" * 50)
    print("示例 6：终端输出二维码")
    print("=" * 50)

    # ── 基础终端输出 ──────────────────────────────────────────
    print("\n[1] 网址二维码（终端显示）")
    print("-" * 40)
    encode("https://github.com", terminal=True)

    # ── 中文内容 ──────────────────────────────────────────────
    print("\n[2] 中文内容二维码（终端显示）")
    print("-" * 40)
    encode("你好世界", terminal=True)

    # ── 较长的文本 ────────────────────────────────────────────
    print("\n[3] 长文本二维码（终端显示）")
    print("-" * 40)
    encode("XQR 高性能二维码生成与解码库 v1.0.1", terminal=True)

    # ── 反转颜色 ──────────────────────────────────────────────
    print("\n[4] 反转颜色显示")
    print("-" * 40)
    encode("https://example.com", terminal=True)  # 默认黑底白字

    print("\n" + "=" * 50)
    print("示例 6 执行完毕！")
    print("提示：在深色终端主题下显示效果更佳")
    print("=" * 50)


if __name__ == "__main__":
    main()
