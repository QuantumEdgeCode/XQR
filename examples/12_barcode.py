#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例 12：条形码生成与解码
==========================

演示使用 XQR 内置的 Code128 条形码引擎（纯自研，零外部依赖）。
"""

from xqr.barcode import encode, decode


def main():
    print("=" * 60)
    print("示例 12：条形码生成与解码")
    print("=" * 60)

    # ── 1. 基本条形码生成 ──────────────────────────────────────
    print("\n[1] 基本条形码生成（保存到文件）")
    encode("ABC-12345", "barcode_basic.png")
    print("    ✅ 已生成: barcode_basic.png")

    # ── 2. 返回 bytes（不保存文件） ─────────────────────────────
    print("\n[2] 返回 PNG bytes（不保存文件）")
    data = encode("Hello World")
    print("    类型:", type(data).__name__)
    print("    大小:", len(data), "bytes")

    # ── 3. 自定义粗细和高度 ─────────────────────────────────────
    print("\n[3] 自定义条宽（4px）和高度（120px）")
    encode("自定义条码", "barcode_custom.png",
           module_width=4, module_height=120)
    print("    ✅ 已生成: barcode_custom.png")

    # ── 4. 不带文字 ────────────────────────────────────────────
    print("\n[4] 不带下方文字")
    encode("NO-TEXT-0001", "barcode_notext.png",
           write_text=False)
    print("    ✅ 已生成: barcode_notext.png")

    # ── 5. 自定义颜色 ──────────────────────────────────────────
    print("\n[5] 自定义颜色（蓝色条码）")
    encode("BLUE-CODE", "barcode_blue.png",
           bar_color="#1677FF", bg_color="#F0F5FF",
           module_width=3, module_height=80)
    print("    ✅ 已生成: barcode_blue.png")

    # ── 6. 宽白边 ──────────────────────────────────────────────
    print("\n[6] 加大左右白边（20px）")
    encode("QUIET-ZONE", "barcode_quiet.png",
           quiet_zone=20, module_width=3, module_height=80)
    print("    ✅ 已生成: barcode_quiet.png")

    # ── 7. 解码 ────────────────────────────────────────────────
    print("\n[7] 解码条形码（从文件）")
    result = decode("barcode_basic.png")
    print("    解码结果:", result)

    print("\n[8] 解码自定义条码")
    result = decode("barcode_custom.png")
    print("    解码结果:", result)

    # ── 9. 从 PIL Image 解码 ───────────────────────────────────
    print("\n[9] 从 PIL Image 对象解码")
    from PIL import Image
    img = Image.open("barcode_notext.png")
    result = decode(img)
    print("    解码结果:", result)

    # ── 10. 生成 → 解码 闭环测试 ───────────────────────────────
    print("\n[10] 生成→解码 闭环测试")
    test_data = "XQR-BARCODE-2024"
    encode(test_data, "barcode_loop.png",
           module_width=3, module_height=80)
    decoded = decode("barcode_loop.png")
    print("    原始数据:", test_data)
    print("    解码结果:", decoded)
    print("    ✅ 匹配!" if test_data == decoded else "    ❌ 不匹配!")

    print("\n" + "=" * 60)
    print("CLI 等效命令：")
    print("  xqr barcode \"ABC-12345\" -o barcode.png")
    print("  xqr barcode \"数据\" --module-width 4 --module-height 100 --no-text")
    print("  xqr barcode \"BLUE-CODE\" --module-width 3 -o blue.png")
    print("  xqr decode barcode.png         # 自动识别 QR / 条形码")
    print("=" * 60)

    # ── 清理 ───────────────────────────────────────────────────
    import os
    for f in ["barcode_basic.png", "barcode_custom.png", "barcode_notext.png",
              "barcode_blue.png", "barcode_quiet.png", "barcode_loop.png"]:
        if os.path.exists(f):
            os.remove(f)


if __name__ == "__main__":
    main()
