#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例 9：中文内容编解码
=======================

演示 XQR 对中文内容的完整支持 —— 从生成到解码的完整流程。
XQR 支持所有 Unicode 字符，包括中文、日文、表情符号等。
"""

from xqr import encode, decode


def main():
    print("=" * 50)
    print("示例 9：中文内容编解码")
    print("=" * 50)

    # ── 纯中文文本 ────────────────────────────────────────────
    print("\n[1] 纯中文文本")
    data = "你好世界"
    encode(data, "output_cn_hello.png")
    result = decode("output_cn_hello.png")
    print("    编码:", data)
    print("    解码:", result)
    print("    匹配:", "✅" if result == data else "❌")

    # ── 中文诗词 ──────────────────────────────────────────────
    print("\n[2] 中文诗词")
    data = "床前明月光，疑是地上霜。举头望明月，低头思故乡。"
    encode(data, "output_cn_poem.png")
    result = decode("output_cn_poem.png")
    print("    编码:", data)
    print("    解码:", result)
    print("    匹配:", "✅" if result == data else "❌")

    # ── URL 含中文参数 ────────────────────────────────────────
    print("\n[3] URL 含中文参数")
    data = "https://example.com/search?q=二维码&page=1&lang=zh"
    encode(data, "output_cn_url.png")
    result = decode("output_cn_url.png")
    print("    编码:", data)
    print("    解码:", result)
    print("    匹配:", "✅" if result == data else "❌")

    # ── 中日韩混合 ────────────────────────────────────────────
    print("\n[4] 中日韩混合文本")
    data = "こんにちは世界！안녕하세요！XQR 支持多国语言"
    encode(data, "output_cn_multi.png")
    result = decode("output_cn_multi.png")
    print("    编码:", data)
    print("    解码:", result)
    print("    匹配:", "✅" if result == data else "❌")

    # ── 表情符号 ──────────────────────────────────────────────
    print("\n[5] 含表情符号的文本")
    data = "XQR 🚀 二维码 ✨ 生成+解码 ✅ 高性能 ⚡"
    encode(data, "output_cn_emoji.png")
    result = decode("output_cn_emoji.png")
    print("    编码:", data)
    print("    解码:", result)
    print("    匹配:", "✅" if result == data else "❌")

    # ── 短中文文本（v1 版本，最小二维码）───────────────────────
    print("\n[6] 短中文文本（最小二维码）")
    data = "XQR"
    encode(data, "output_cn_short.png")
    result = decode("output_cn_short.png")
    print("    编码:", data)
    print("    解码:", result)
    print("    匹配:", "✅" if result == data else "❌")

    # ── 中文艺术二维码编解码 ──────────────────────────────────
    print("\n[7] 中文艺术二维码编解码")
    from PIL import Image
    bg = Image.new("RGB", (120, 120), (100, 180, 255))
    bg.save("temp_bg.png")
    data = "中文艺术二维码测试"
    encode(data, "output_cn_art.png", picture="temp_bg.png", colorized=True)
    result = decode("output_cn_art.png")
    print("    编码:", data)
    print("    解码:", result)
    print("    匹配:", "✅" if result == data else "❌")
    import os
    os.remove("temp_bg.png")

    # ── 批量中文编解码 ────────────────────────────────────────
    print("\n[8] 批量中文编解码验证")
    test_cases = [
        "你好",
        "中文测试",
        "二维码生成与解码",
        "XQR高性能库",
        "春风又绿江南岸",
        "https://搜索.中国",
        "a",  # 单字符
        "你好世界！Hello World! 123",
    ]
    all_ok = True
    for i, text in enumerate(test_cases, 1):
        filename = "temp_batch_{}.png".format(i)
        encode(text, filename)
        result = decode(filename)
        ok = result == text
        if not ok:
            all_ok = False
            print("    ❌ 失败:", text, "->", result)
        import os
        os.remove(filename)
    print("    测试 {} 个用例，全部通过: {}".format(
        len(test_cases), "✅" if all_ok else "❌"))

    print("\n" + "-" * 50)
    print("生成的文件列表:")
    import os
    for f in sorted(os.listdir(".")):
        if f.startswith("output_cn_") and f.endswith(".png"):
            size = os.path.getsize(f)
            print(f"  {f:30s} ({size} bytes)")

    print("\n" + "=" * 50)
    print("示例 9 执行完毕！")
    print("提示：XQR 完全支持中文在内的所有 Unicode 字符")
    print("=" * 50)


if __name__ == "__main__":
    main()
