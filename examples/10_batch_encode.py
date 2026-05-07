#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例 10：批量生成与高级应用
=============================

演示 XQR 在批量场景和高级应用中的使用方式，
包括程序化生成、自定义纠错策略等。
"""

from xqr import encode, decode, XQR
from PIL import Image
import os


def main():
    print("=" * 50)
    print("示例 10：批量生成与高级应用")
    print("=" * 50)

    # ── 批量生成二维码 ────────────────────────────────────────
    print("\n[1] 批量生成二维码")
    urls = [
        "https://github.com",
        "https://www.python.org",
        "https://pypi.org",
        "https://www.google.com",
        "https://stackoverflow.com",
    ]
    for i, url in enumerate(urls, 1):
        filename = "output_batch_{}.png".format(i)
        encode(url, filename)
        print("    ✅ 已生成: {}  <- {}".format(filename, url))

    # ── 批量验证 ──────────────────────────────────────────────
    print("\n[2] 批量验证解码")
    for i, expected in enumerate(urls, 1):
        filename = "output_batch_{}.png".format(i)
        result = decode(filename)
        ok = result == expected
        print("    {} {}  <- {}".format(
            "✅" if ok else "❌", filename, result))
        os.remove(filename)

    # ── 生成不同纠错等级的二维码 ──────────────────────────────
    print("\n[3] 不同纠错等级对比")
    levels = [
        ("L", "最低（7% 可恢复）"),
        ("M", "中等（15% 可恢复）"),
        ("Q", "较高（25% 可恢复）"),
        ("H", "最高（30% 可恢复）"),
    ]
    for level, desc in levels:
        filename = "output_level_{}.png".format(level)
        encode("https://example.com", filename, level=level)
        size = os.path.getsize(filename)
        print("    {} 纠错等级 {} - {}: {} bytes".format(
            "✅" if level else "", level, desc, size))
        os.remove(filename)

    # ── 生成不同版本的二维码 ──────────────────────────────────
    print("\n[4] 不同版本对比（1, 5, 10, 20）")
    for ver in [1, 5, 10, 20]:
        filename = "output_version_{}.png".format(ver)
        # 用足够长的数据填充大版本
        data = "X" * (ver * 10)
        encode(data, filename, version=ver)
        img = Image.open(filename)
        print("    {} 版本 {}: 图像大小 {}×{}".format(
            "✅" if ver else "", ver, img.size[0], img.size[1]))
        img.close()
        os.remove(filename)

    # ── 编码-解码-再编码 循环验证 ─────────────────────────────
    print("\n[5] 编解码循环验证（确保数据不丢失）")
    original = "XQR 二维码库编解码循环测试"
    for i in range(3):  # 编解码 3 次
        encode(original, "temp_cycle.png")
        decoded = decode("temp_cycle.png")
        assert decoded == original, "第 {} 次循环失败".format(i + 1)
        original = decoded  # 用解码结果再次编码
    os.remove("temp_cycle.png")
    print("    ✅ 3 次编解码循环全部成功，数据无损")

    # ── 编码 bytes 类型数据 ──────────────────────────────────
    print("\n[6] 编码 bytes 数据")
    binary_data = b"\\x00\\x01\\x02\\x03\\x04binary data"
    encode(binary_data, "output_bytes.png")
    result = decode("output_bytes.png")
    # 注意：decode 返回 str，bytes 数据会被解码为 UTF-8
    # 对于二进制数据，建议编码为 base64 后再生成二维码
    import base64
    b64_data = base64.b64encode(binary_data).decode("ascii")
    encode(b64_data, "output_b64_bytes.png")
    decoded_b64 = decode("output_b64_bytes.png")
    restored = base64.b64decode(decoded_b64.encode("ascii"))
    print("    原始 bytes:", binary_data)
    print("    还原 bytes:", restored)
    print("    匹配:", "✅" if restored == binary_data else "❌")
    os.remove("output_bytes.png")
    os.remove("output_b64_bytes.png")

    print("\n" + "=" * 50)
    print("示例 10 执行完毕！")
    print("=" * 50)


if __name__ == "__main__":
    main()
