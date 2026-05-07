#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例 2：二维码解码
====================

演示 XQR 的解码功能 —— 从各种图像来源读取二维码内容。
"""

from xqr import encode, decode
from PIL import Image
import numpy as np


def main():
    print("=" * 50)
    print("示例 2：二维码解码")
    print("=" * 50)

    # 先生成一个测试用的二维码
    test_data = "https://xqr.dev"
    encode(test_data, "temp_qr.png")

    # ── 方式一：从文件路径解码 ────────────────────────────────
    print("\n[1] 从文件路径解码")
    result = decode("temp_qr.png")
    print("    原始内容:", test_data)
    print("    解码结果:", result)
    print("    匹配:", "✅" if result == test_data else "❌")

    # ── 方式二：从 PIL Image 对象解码 ──────────────────────────
    print("\n[2] 从 PIL Image 对象解码")
    img = Image.open("temp_qr.png")
    result = decode(img)
    print("    解码结果:", result)
    print("    匹配:", "✅" if result == test_data else "❌")

    # ── 方式三：从 numpy 数组解码 ─────────────────────────────
    print("\n[3] 从 numpy 数组解码（OpenCV 格式）")
    import cv2
    arr = cv2.imread("temp_qr.png")
    print("    数组形状:", arr.shape)
    result = decode(arr)
    print("    解码结果:", result)
    print("    匹配:", "✅" if result == test_data else "❌")

    # ── 方式四：使用 XQR 类静态方法解码 ─────────────────────────
    print("\n[4] 使用 XQR.decode() 静态方法")
    from xqr import XQR
    result = XQR.decode("temp_qr.png")
    print("    解码结果:", result)
    print("    匹配:", "✅" if result == test_data else "❌")

    # ── 解码中文内容 ──────────────────────────────────────────
    print("\n[5] 解码中文内容")
    chinese_data = "你好世界！这是一个中文二维码"
    encode(chinese_data, "temp_chinese.png")
    result = decode("temp_chinese.png")
    print("    原始内容:", chinese_data)
    print("    解码结果:", result)
    print("    匹配:", "✅" if result == chinese_data else "❌")

    # ── 解码失败时的返回值 ────────────────────────────────────
    print("\n[6] 解码非二维码图片（应返回空字符串）")
    blank = Image.new("RGB", (100, 100), (255, 255, 255))
    blank.save("temp_blank.png")
    result = decode("temp_blank.png")
    print("    空白图片解码结果:", repr(result))
    print("    结果为空:", "✅" if result == "" else "❌")

    # 清理临时文件
    import os
    for f in ["temp_qr.png", "temp_chinese.png", "temp_blank.png"]:
        if os.path.exists(f):
            os.remove(f)

    print("\n" + "=" * 50)
    print("示例 2 执行完毕！")
    print("=" * 50)


if __name__ == "__main__":
    main()
