# -*- coding: utf-8 -*-
"""
XQR 艺术模块 —— 基于 numpy 加速的二维码图片融合。

与 MyQR 使用 Python 循环逐像素 ``putpixel()`` 不同，本模块在完整的
numpy 数组上操作，性能提升 10-100 倍。

主要函数
--------
- ``blend_artistic()`` —— 将二维码与背景图片融合
- ``process_animated()`` —— 处理 GIF 的每一帧生成动态二维码
- ``is_animated_image()`` —— 检查文件是否为动态 GIF
"""

import io
import os

import numpy as np
from PIL import Image, ImageEnhance


# ---------------------------------------------------------------------------
# 结构元素掩码（模块级别，非像素级别）
# ---------------------------------------------------------------------------

def _get_structural_mask(version):
    """
    返回 N×N 的布尔 numpy 数组，``True`` 表示该模块是结构元素
    （定位图案、分隔符、时序图案或校正图案），在融合时必须保留原文。

    ``N = version * 4 + 17``（二维码模块数/边）。
    """
    N = version * 4 + 17
    mask = np.zeros((N, N), dtype=bool)

    # -- 定位图案（三个角，各 7×7，外加 1 模块宽的分隔符）-----------

    def _finder(topleft_r, topleft_c):
        """绘制一个定位图案及其分隔符"""
        r, c = topleft_r, topleft_c
        mask[r:r + 7, c:c + 7] = True
        # 水平分隔符
        if r + 7 < N:
            mask[r + 7, c:c + 8] = True
        # 垂直分隔符
        if c + 7 < N:
            mask[r:r + 8, c + 7] = True

    # 左上角
    _finder(0, 0)
    # 右上角
    _finder(0, N - 7)
    # 左下角
    _finder(N - 7, 0)

    # -- 时序图案 ----------------------------------------------------
    # 第 6 行，从左分隔符后到右分隔符前
    mask[6, 8:N - 8] = True
    # 第 6 列，同理
    mask[8:N - 8, 6] = True

    # -- 校正图案（每个 5×5，随版本变化）-------------------------------
    from ._encoder import PATTERN_POSITION_TABLE

    positions = PATTERN_POSITION_TABLE[version - 1]

    # 校正图案中心在这些 (row, col) 位置 —— 跳过与定位图案重叠的
    for row_center in positions:
        for col_center in positions:
            # 检查是否与定位图案重叠（前 8 行/列 或 后 8 行/列）
            if row_center <= 8 and col_center <= 8:
                continue  # 左上角定位图案
            if row_center <= 8 and col_center >= N - 9:
                continue  # 右上角定位图案
            if row_center >= N - 9 and col_center <= 8:
                continue  # 左下角定位图案

            # 以 (row_center, col_center) 为中心的 5×5 校正图案
            r_start = row_center - 2
            r_end = row_center + 3
            c_start = col_center - 2
            c_end = col_center + 3

            # 限制在有效范围内
            r_start = max(0, r_start)
            r_end = min(N, r_end)
            c_start = max(0, c_start)
            c_end = min(N, c_end)

            mask[r_start:r_end, c_start:c_end] = True

    return mask


# ---------------------------------------------------------------------------
# numpy 加速融合
# ---------------------------------------------------------------------------

def blend_artistic(qr_img, bg_source, version, colorized=False,
                   contrast=1.0, brightness=1.0, box_size=3):
    """
    使用 numpy 操作将二维码图像与背景图片融合。

    融合策略（保证二维码可读性）：
    1. 白色模块 → 纯白（保证二维码解码器能识别）
    2. 深色模块 → 显示背景图案但降低亮度（保留视觉层次）
    3. 结构元素（定位图案、时序、校正）→ 保留原始黑白

    参数
    ----
    qr_img : PIL.Image
        二维码图像（内部会转换为 RGBA）。
    bg_source : str 或 PIL.Image
        背景图片（文件路径或 PIL Image 对象）。
    version : int
        二维码版本号（1-40）。用于构建结构元素掩码。
    colorized : bool
        如果为 ``True``，保留背景颜色；否则使用灰度融合
        （默认为黑白）。
    contrast : float
        作用于背景的对比度倍率（1.0 = 不变）。
    brightness : float
        作用于背景的亮度倍率（1.0 = 不变）。
    box_size : int
        *qr_img* 中每个二维码模块的像素大小（默认 3）。
        必须与生成二维码时使用的 box_size 一致。

    返回
    ----
    PIL.Image
        融合后的艺术二维码图像，放大 3 倍以获得更清晰的视觉效果。

    说明
    ----
    本实现将 MyQR 中 Python 级别的逐像素循环替换为 numpy 向量化
    操作，性能提升 10-100 倍。
    """
    # 1. 将二维码图像转为灰度 numpy 数组
    qr_gray_full = np.array(qr_img.convert("L"), dtype=np.float32)

    # 2. 加载背景图片
    if isinstance(bg_source, str):
        bg = Image.open(bg_source).convert("RGBA")
    else:
        bg = bg_source.convert("RGBA")

    # 3. 应用对比度 / 亮度调整
    if contrast != 1.0:
        bg = ImageEnhance.Contrast(bg).enhance(contrast)
    if brightness != 1.0:
        bg = ImageEnhance.Brightness(bg).enhance(brightness)

    # 4. 确定尺寸
    N = version * 4 + 17            # 每边模块数
    border_px = 4 * box_size        # 边框像素（像素数）
    inner_px = N * box_size         # 内部数据区像素数

    # 调整背景大小，使其匹配二维码内部数据区
    bg = bg.resize((inner_px, inner_px), Image.LANCZOS)
    bg_np = np.array(bg, dtype=np.uint8)  # shape: (inner, inner, 4)

    # 提取二维码内部数据区（去掉边框）
    inner_qr = qr_gray_full[border_px:-border_px, border_px:-border_px]

    # 5. 构建结构元素掩码（模块级 → 像素级）
    structural = _get_structural_mask(version)
    pixel_structural = np.kron(
        structural, np.ones((box_size, box_size), dtype=bool)
    )

    # 6. 判断哪些像素属于"深色模块"（= 二维码的黑色模块区域）
    is_dark = inner_qr < 128  # True = 深色模块像素

    # 7. 创建融合图像
    #
    #    白色模块区域 → 纯白（255,255,255,255）
    #    深色模块区域 → 背景颜色 * 暗化系数（可逆时显示背景）
    #    结构元素区域 → 保持原始 QR 颜色

    # 暗化系数：白色模块区域纯白，深色模块区域保留背景但暗化
    DARK_FACTOR = 0.45  # 深色模块亮度保留比例，值越小越暗、越易解码

    if colorized:
        # 彩色模式：深色模块显示暗化后的背景色
        bg_dark = (bg_np.astype(np.float32) * DARK_FACTOR).astype(np.uint8)
        # 白色模块显示纯白
        for c in range(3):
            bg_dark[:, :, c][~is_dark] = 255
        bg_dark[:, :, 3][~is_dark] = 255
        inner_output = bg_dark
    else:
        # 黑白模式：深色模块显示暗化后的背景灰度
        bg_gray = np.mean(bg_np[:, :, :3], axis=2).astype(np.float32)
        dark_val = (bg_gray * DARK_FACTOR).astype(np.uint8)
        inner_output = np.full((inner_px, inner_px, 4), 255, dtype=np.uint8)
        # 白色模块所在位置保持白色
        for c in range(3):
            inner_output[:, :, c] = 255
        # 深色模块填入暗化后的灰度背景
        for c in range(3):
            inner_output[:, :, c][is_dark] = dark_val[is_dark]

    # 8. 结构元素区域：恢复为原始 QR 模块颜色
    if colorized:
        qr_rgba = np.array(qr_img.convert("RGBA"), dtype=np.uint8)
        qr_inner = qr_rgba[border_px:-border_px, border_px:-border_px]
        inner_output[pixel_structural] = qr_inner[pixel_structural]
    else:
        # 结构元素处恢复原始黑白 QR
        qr_inner_rgb = np.stack([inner_qr, inner_qr, inner_qr], axis=2).astype(np.uint8)
        qr_inner_rgba = np.concatenate(
            [qr_inner_rgb, np.full((inner_px, inner_px, 1), 255, dtype=np.uint8)], axis=2
        )
        inner_output[pixel_structural] = qr_inner_rgba[pixel_structural]

    # 9. 组装完整图像（包含边框）
    qr_rgba_full = np.array(qr_img.convert("RGBA"), dtype=np.uint8)
    output = np.full_like(qr_rgba_full, 255)
    output[border_px:-border_px, border_px:-border_px] = inner_output
    # 边框也保持原始 QR 颜色
    output[:border_px, :, :3] = 255  # 顶部边框白色
    output[-border_px:, :, :3] = 255  # 底部边框白色
    output[:, :border_px, :3] = 255  # 左侧边框白色
    output[:, -border_px:, :3] = 255  # 右侧边框白色

    # 10. 转回 PIL 并放大 3 倍使图像更清晰
    result = Image.fromarray(output, mode="RGBA")
    result = result.resize(
        (result.width * 3, result.height * 3), Image.NEAREST
    )
    return result


# ---------------------------------------------------------------------------
# 动态二维码（GIF）
# ---------------------------------------------------------------------------

def is_animated_image(path):
    """如果 *path* 指向一个动态 GIF，返回 ``True``。"""
    if isinstance(path, str):
        _, ext = os.path.splitext(path)
        if ext.lower() != ".gif":
            return False
        try:
            with Image.open(path) as im:
                return getattr(im, "is_animated", False)
        except (OSError, IOError):
            return False
    return False


def process_animated(qr_img, bg_source, version, colorized=False,
                     contrast=1.0, brightness=1.0):
    """
    处理动态 GIF 的每一帧，生成动态二维码。

    参数
    ----
    qr_img : PIL.Image
        基础二维码图像（将融合到每一帧中）。
    bg_source : str
        动态 GIF 文件的路径。
    version : int
        二维码版本号。
    colorized : bool
        是否保留颜色。
    contrast : float
        对比度调整。
    brightness : float
        亮度调整。

    返回
    ----
    PIL.Image
        动态 GIF（包含多帧的 PIL Image）。

    注意
    ----
    最多处理 200 帧，超出部分将被自动截断。
    """
    with Image.open(bg_source) as gif:
        frames = []
        durations = []

        try:
            frame_count = 0
            MAX_FRAMES = 200
            while True:
                frame_count += 1
                if frame_count > MAX_FRAMES:
                    import warnings
                    warnings.warn(
                        "动态 GIF 帧数超过 {}，已自动截断至 {} 帧".format(
                            MAX_FRAMES, MAX_FRAMES
                        )
                    )
                    break
                # 将当前帧转为 RGBA
                frame = gif.convert("RGBA")
                durations.append(gif.info.get("duration", 100))

                # 将当前帧与二维码融合
                blended = blend_artistic(
                    qr_img, frame,
                    version=version,
                    colorized=colorized,
                    contrast=contrast,
                    brightness=brightness,
                )
                # 转为调色板模式（P 模式）以兼容 GIF 格式
                blended = blended.convert("P",
                    palette=Image.Palette.ADAPTIVE,
                    colors=256,
                )
                frames.append(blended)

                gif.seek(gif.tell() + 1)
        except EOFError:
            pass  # 已读取所有帧

    if not frames:
        raise ValueError("动态 GIF 中没有找到帧: {}".format(bg_source))

    # 重新组装为动态 GIF
    result = frames[0]
    result.info["duration"] = durations[0]
    if len(frames) > 1:
        result.info["loop"] = 0  # 无限循环

        # 先保存到字节流，再重新打开以创建多帧 GIF
        buf = io.BytesIO()
        result.save(
            buf,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=0,
            disposal=2,
        )
        buf.seek(0)
        result = Image.open(buf)

    return result
