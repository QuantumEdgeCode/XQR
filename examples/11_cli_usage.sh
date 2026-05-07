#!/bin/bash
# -*- coding: utf-8 -*-
"""
示例 11：命令行（CLI）使用
============================

演示通过命令行使用 XQR 的 encode/decode 命令。
这些命令可以直接在终端中运行，无需编写 Python 代码。
"""

# ============================================================
# 快捷命令（无需子命令，自动识别为 encode）
# ============================================================

echo "=== XQR 命令行使用示例 ==="
echo ""

# 快捷命令：直接传数据，不需要 encode 子命令
echo "[快捷] 直接生成（快捷用法）"
xqr "https://github.com"
echo "    ✅ 一行命令生成二维码"
echo ""

echo "[快捷] 中文直接生成"
xqr "你好世界"
echo "    ✅ 中文也没问题"
echo ""

echo "[快捷] 保存到文件"
xqr "https://example.com" github.png
echo "    ✅ 已生成: github.png"
echo ""

# ============================================================
# 基本二维码生成（encode 子命令）
# ============================================================

echo "=== 标准用法（encode 子命令） ==="
echo ""

# 生成英文内容的二维码
echo "[1] 生成英文二维码"
xqr encode "https://github.com" github.png
echo "    ✅ 已生成: github.png"
echo ""

# 生成中文内容的二维码
echo "[2] 生成中文二维码"
xqr encode "你好世界" hello.png
echo "    ✅ 已生成: hello.png"
echo ""

# 指定输出文件名
echo "[3] 指定输出文件"
xqr encode "https://example.com" my_qr.png
echo "    ✅ 已生成: my_qr.png"
echo ""

# ============================================================
# 高级参数
# ============================================================

# 指定纠错等级
echo "[4] 指定纠错等级为 H（最高）"
xqr encode "https://example.com" -l H level_h.png
echo "    ✅ 已生成: level_h.png"
echo ""

# 指定版本
echo "[5] 指定版本为 10"
xqr encode "https://example.com" -v 10 version_10.png
echo "    ✅ 已生成: version_10.png"
echo ""

# 指定自定义颜色
echo "[6] 指定自定义颜色（蓝色填充，白色背景）"
xqr encode "https://example.com" --fill-color "#1677FF" --back-color "white" blue_qr.png
echo "    ✅ 已生成: blue_qr.png"
echo ""

# ============================================================
# 艺术二维码
# ============================================================

echo "[7] 生成黑白艺术二维码"
xqr encode "https://example.com" -p background.jpg art_bw.png
echo "    ✅ 已生成: art_bw.png"
echo ""

echo "[8] 生成彩色艺术二维码"
xqr encode "https://example.com" -p background.jpg -c art_color.png
echo "    ✅ 已生成: art_color.png"
echo ""

echo "[9] 调整对比度和亮度"
xqr encode "https://example.com" -p background.jpg -c --contrast 1.5 --brightness 0.8 art_adjusted.png
echo "    ✅ 已生成: art_adjusted.png"
echo ""

# ============================================================
# 解码
# ============================================================

echo "[10] 解码二维码"
xqr decode github.png
echo ""

echo "[11] 解码中文二维码"
xqr decode hello.png
echo ""

# ============================================================
# 终端输出
# ============================================================

echo "[12] 终端输出二维码"
xqr encode "https://example.com" --terminal
echo ""

echo "[13] 终端输出中文二维码"
xqr encode "你好世界" --terminal
echo ""

# ============================================================
# 清理
# ============================================================

echo "=== 清理 ==="
rm -f github.png hello.png my_qr.png level_h.png version_10.png blue_qr.png
rm -f art_bw.png art_color.png art_adjusted.png
echo "临时文件已清理"
echo ""

echo "=== XQR 命令行示例完成 ==="
echo "提示：使用 xqr --help 查看完整帮助"
