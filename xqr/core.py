# -*- coding: utf-8 -*-
"""
XQR 核心模块 —— 高性能二维码生成与解码。

提供 :class:`XQR` 类用于高级控制，以及 :func:`encode` 和 :func:`decode`
便捷函数用于一键式二维码生成和解码。
"""

import io
import os
import sys
import base64
import warnings
import logging

from PIL import Image

from ._encoder import (
    QRCode,
    ERROR_CORRECT_L,
    ERROR_CORRECT_M,
    ERROR_CORRECT_Q,
    ERROR_CORRECT_H,
    make_qr_image,
)

from .artistic import (
    blend_artistic,
    process_animated,
    is_animated_image,
)
from ._version import __version__

logger = logging.getLogger(__name__)


def _safe_resolve_path(path):
    """解析并验证路径安全性，防止目录遍历攻击（如 ``../etc/passwd``）。"""
    if not isinstance(path, str):
        return path
    import os
    # 检查路径中是否包含 '..' 遍历组件
    normalized = os.path.normpath(path)
    parts = normalized.replace("\\", "/").split("/")
    if ".." in parts:
        raise ValueError(
            "路径 '{}' 包含目录遍历（..），已拒绝".format(path)
        )
    return os.path.abspath(normalized)


# 在模块级别重新导出纠错等级常量
__all__ = [
    "XQR",
    "encode",
    "decode",
    "ERROR_CORRECT_L",
    "ERROR_CORRECT_M",
    "ERROR_CORRECT_Q",
    "ERROR_CORRECT_H",
]

# ---------------------------------------------------------------------------
# 内部辅助函数
# ---------------------------------------------------------------------------

_LEVEL_MAP = {
    "L": ERROR_CORRECT_L,
    "M": ERROR_CORRECT_M,
    "Q": ERROR_CORRECT_Q,
    "H": ERROR_CORRECT_H,
}


def _resolve_level(level):
    """将字符串或整数的纠错等级转为整数常量。"""
    if isinstance(level, str):
        level = level.strip().upper()
        if level not in _LEVEL_MAP:
            raise ValueError(
                "纠错等级必须为 'L', 'M', 'Q', 'H' 之一 "
                "（收到: {!r}）".format(level)
            )
        return _LEVEL_MAP[level]
    if level in (ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H):
        return level
    raise ValueError(
        "无效的纠错等级: {!r}".format(level)
    )


def _check_version(version):
    """验证并返回版本号（1-40 或 None 表示自动）。"""
    if version is None:
        return None
    version = int(version)
    if version < 1 or version > 40:
        raise ValueError("版本号必须在 1 到 40 之间（收到: {}）".format(version))
    return version


# ---------------------------------------------------------------------------
# XQR 类
# ---------------------------------------------------------------------------

class XQR(object):
    """
    高性能二维码生成器。

    参数
    ----
    data : str 或 bytes, 可选
        要编码的数据（URL、文本等）。也可以在之后通过 :meth:`add_data` 设置。
    version : int 或 None, 可选
        二维码版本（1-40）。``None``（默认）自动选择最优版本。
    level : str 或 int, 可选
        纠错等级：``'L'``、``'M'``（默认）、``'Q'``、``'H'``
        或对应的 ``ERROR_CORRECT_*`` 常量。
    box_size : int, 可选
        每个二维码模块的像素大小（默认 10）。
    border : int, 可选
        白边框宽度（模块数，默认 4，符合 QR 规范）。
    mask_pattern : int 或 None, 可选
        掩码模式索引（0-7）。``None`` 表示自动选择。
    """

    def __init__(self, data=None, version=None, level="M",
                 box_size=10, border=4, mask_pattern=None):
        self._version = _check_version(version)
        self._level = _resolve_level(level)
        self._box_size = int(box_size)
        self._border = int(border)
        self._mask_pattern = mask_pattern
        self._qr = None  # QRCode 实例（延迟创建）
        self._modules = None
        self._modules_count = 0
        self._data = None

        if data is not None:
            self.add_data(data)

    # -- 数据 -----------------------------------------------------------------

    def add_data(self, data):
        """添加要编码的数据。可以多次调用。"""
        # 安全：限制最大数据量，防止大数据触发 version 1→40 循环 DoS
        if isinstance(data, str):
            raw_len = len(data.encode('utf-8'))
        elif isinstance(data, bytes):
            raw_len = len(data)
        else:
            raw_len = len(str(data))
        max_bytes = 4096
        if raw_len > max_bytes:
            from ._encoder import DataOverflowError
            raise DataOverflowError(
                f"数据超出最大容量（{raw_len} > {max_bytes} 字节）"
            )
        self._data = data
        self._qr = None  # 使缓存的 QR 失效
        return self

    # -- 生成 ----------------------------------------------------------------

    def make(self, fit=True):
        """
        将数据编译为二维码矩阵。

        参数
        ----
        fit : bool
            如果为 ``True``（默认），自动寻找最优版本大小。
        """
        if self._data is None:
            raise ValueError("未提供数据。请先调用 add_data()。")

        self._qr = QRCode(
            version=self._version,
            error_correction=self._level,
            box_size=self._box_size,
            border=self._border,
            mask_pattern=self._mask_pattern,
        )
        self._qr.add_data(self._data)
        self._qr.make(fit=fit)
        self._modules = self._qr.modules
        self._modules_count = self._qr.modules_count
        return self

    def get_matrix(self):
        """
        返回二维码的二维布尔数组（包含边框）。

        返回的矩阵包含由 ``self.border`` 指定的边框区域。
        """
        if self._qr is None:
            self.make()
        return self._qr.get_matrix()

    # -- 属性 -----------------------------------------------------------------

    @property
    def version(self):
        """二维码版本号（1-40）。"""
        if self._qr is None:
            self.make()
        return self._qr.version

    @property
    def modules(self):
        """二维码模块矩阵（二维列表，元素为 bool/None）。"""
        if self._modules is None:
            self.make()
        return self._modules

    @property
    def modules_count(self):
        """每边的模块数（version * 4 + 17）。"""
        if self._qr is None:
            self.make()
        return self._modules_count

    # -- 图像输出 ------------------------------------------------------------

    def to_image(self, fill_color="black", back_color="white"):
        """
        将二维码渲染为 PIL ``Image`` 对象。

        参数
        ----
        fill_color : str 或 tuple
            深色模块的颜色（默认 ``'black'``）。
        back_color : str 或 tuple
            浅色模块的颜色（默认 ``'white'``）。
            使用 ``'transparent'`` 可生成透明背景。

        返回
        ----
        PIL.Image
        """
        if self._qr is None:
            self.make()
        return make_qr_image(self._qr, fill_color=fill_color, back_color=back_color)

    def save(self, path, fill_color="black", back_color="white",
             format=None, **kwargs):
        """
        将二维码图像保存到文件。

        参数
        ----
        path : str
            输出文件路径。扩展名决定格式
            （``.png``、``.jpg``、``.bmp``、``.gif``、``.svg`` 等）。
        fill_color : str 或 tuple
            深色模块的颜色。
        back_color : str 或 tuple
            浅色模块的颜色。
        format : str 或 None
            强制指定图像格式（如 ``'PNG'``）。
            如果为 ``None``，从文件扩展名推断。
        """
        img = self.to_image(fill_color=fill_color, back_color=back_color)
        path = _safe_resolve_path(path)
        if format is None:
            _, ext = os.path.splitext(path)
            format = ext.lstrip(".").upper() or None
        img.save(path, format=format, **kwargs)
        return path

    def to_base64(self, fill_color="black", back_color="white",
                  format="PNG"):
        """
        将二维码编码为 base64 数据 URI 字符串。

        参数
        ----
        fill_color : str 或 tuple
            深色模块的颜色。
        back_color : str 或 tuple
            浅色模块的颜色。
        format : str
            编码使用的图像格式（默认 ``'PNG'``）。

        返回
        ----
        str
            base64 数据 URI，如 ``data:image/png;base64,...``。
        """
        img = self.to_image(fill_color=fill_color, back_color=back_color)
        buf = io.BytesIO()
        img.save(buf, format=format)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        mime = "image/{}".format(format.lower())
        return "data:{};base64,{}".format(mime, b64)

    def to_svg(self, fill_color="black", back_color="white"):
        """
        返回二维码的 SVG 字符串。

        说明
        ----
        此方法使用 ``qrcode`` 库内置的 SVG 图像工厂，而非 PIL。

        参数
        ----
        fill_color : str
            深色模块的颜色（SVG 输出仅支持命名颜色）。
        back_color : str
            浅色模块的颜色。

        返回
        ----
        str
        """
        from ._encoder import make_qr_svg
        if self._qr is None:
            self.make()
        return make_qr_svg(self._qr, fill_color=fill_color, back_color=back_color)

    # -- 终端输出 ------------------------------------------------------------

    def to_terminal(self, out=None, tty=False, invert=False):
        """
        使用 ASCII / ANSI 字符在终端打印二维码。

        参数
        ----
        out : 文件对象 或 None
            输出流（默认 ``sys.stdout``）。
        tty : bool
            使用 TTY 颜色代码（会强制 ``invert=True``）。
        invert : bool
            反转颜色（白底黑字 vs 黑底白字）。
        """
        if self._qr is None:
            self.make()
        self._qr.print_ascii(out=out, tty=tty, invert=invert)

    # -- 艺术二维码 ----------------------------------------------------------

    def to_artistic(self, picture, colorized=False, contrast=1.0,
                    brightness=1.0, save_path=None):
        """
        通过与背景图片融合生成艺术二维码。

        参数
        ----
        picture : str 或 PIL.Image
            背景图片文件路径或 PIL Image 对象。
        colorized : bool
            如果为 ``True``，保留背景颜色；否则为黑白。
        contrast : float
            作用于背景的对比度倍率（默认 1.0）。
        brightness : float
            作用于背景的亮度倍率（默认 1.0）。
        save_path : str 或 None
            可选的结果保存路径。

        返回
        ----
        PIL.Image
            艺术二维码图像。
        """
        if self._qr is None:
            self.make()

        # 检查背景是否为动态图
        if isinstance(picture, str):
            picture = _safe_resolve_path(picture)
        if isinstance(picture, str) and is_animated_image(picture):
            return self._to_animated(
                picture, colorized=colorized, contrast=contrast,
                brightness=brightness, save_path=save_path,
            )

        # 以 3px/模块生成基础二维码图像（统一用于融合）
        qr_box = XQR(
            data=self._data,
            version=self._version,
            level=self._level,
            box_size=3,
            border=self._border,
        )
        qr_box._qr = None
        qr_img = qr_box.to_image(fill_color="black", back_color="white")

        # 执行 numpy 加速融合
        result = blend_artistic(
            qr_img, picture,
            version=self.version,
            colorized=colorized,
            contrast=contrast,
            brightness=brightness,
        )

        if save_path is not None:
            result.save(save_path)

        return result

    def _to_animated(self, picture, colorized=False, contrast=1.0,
                     brightness=1.0, save_path=None):
        """内部方法：从 GIF 背景生成动态二维码。"""
        if self._qr is None:
            self.make()

        # 以 3px/模块生成二维码
        qr_box = XQR(
            data=self._data,
            version=self._version,
            level=self._level,
            box_size=3,
            border=self._border,
        )
        qr_img = qr_box.to_image(fill_color="black", back_color="white")

        result = process_animated(
            qr_img, picture,
            version=self.version,
            colorized=colorized,
            contrast=contrast,
            brightness=brightness,
        )

        if save_path is not None:
            result.save(save_path, save_all=True)

        return result

    # -- 解码 ----------------------------------------------------------------

    @staticmethod
    def decode(image, multiple=False):
        """
        从图像文件中解码二维码内容。

        基于 OpenCV QRCodeDetector 原生实现，无需额外安装依赖。
        支持多个二维码同时检测。

        参数
        ----
        image : str 或 PIL.Image 或 numpy.ndarray
            二维码图像。可以是文件路径、PIL Image 或 numpy 数组。
        multiple : bool
            是否尝试解码图像中的多个二维码
            （基于 OpenCV 原生 ``detectAndDecodeMulti``）。

        返回
        ----
        str 或 list
            如果 ``multiple=False``：返回解码文本字符串，
            未找到时返回空字符串。
            如果 ``multiple=True``：返回解码文本列表，
            未找到时返回空列表。
        """
        return _decode_qr(image, multiple=multiple)



def _load_cv2():
    """按需导入 OpenCV。未安装时抛出友好提示。"""
    try:
        import cv2
        return cv2
    except ImportError:
        raise ImportError(
            "解码功能需要 opencv-python 库。\n"
            "请运行: pip install opencv-python"
        )


def _decode_qr(image, multiple=False):
    """
    从图像中解码二维码。

    基于 OpenCV QRCodeDetector 原生实现，无需外部依赖。
    支持中文在内的所有 UTF-8 编码内容。
    """
    cv2 = _load_cv2()
    import numpy as np

    # 将输入统一转为 numpy 数组（OpenCV 格式 BGR）
    if isinstance(image, str):
        img = cv2.imread(_safe_resolve_path(image))
        if img is None:
            raise FileNotFoundError("无法读取图像文件: {}".format(image))
    elif isinstance(image, Image.Image):
        img = np.array(image.convert("RGB"))
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    elif isinstance(image, np.ndarray):
        img = image
    else:
        raise TypeError("不支持的图像类型: {}".format(type(image).__name__))

    # ── 多二维码模式：使用 OpenCV 原生多码检测 ─────────────
    if multiple:
        return _decode_multi_qr(img, cv2)

    # ── 单二维码模式：多重回退策略 ─────────────────────────
    result = _try_decode_single(img, cv2)
    if result:
        return result

    # 放大后重试（小二维码需要更大尺寸）
    h, w = img.shape[:2]
    if h < 400 or w < 400:
        scale = max(2, 500 // min(h, w))
        enlarged = cv2.resize(img, None, fx=scale, fy=scale,
                              interpolation=cv2.INTER_NEAREST)
        result = _try_decode_single(enlarged, cv2)
        if result:
            return result

    # CLAHE 增强对比度后重试
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        result = _try_decode_single(enhanced, cv2)
        if result:
            return result
    except (cv2.error, RuntimeError, ValueError):
        logger.debug("CLAHE 增强失败")
        pass
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blur, 128, 255, cv2.THRESH_BINARY)
        result = _try_decode_single(thresh, cv2)
        if result:
            return result
    except (cv2.error, RuntimeError, ValueError):
        logger.debug("高斯模糊回退失败")
        pass

    # 直接二值化后重试
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
        result = _try_decode_single(thresh, cv2)
        if result:
            return result
    except (cv2.error, RuntimeError, ValueError):
        logger.debug("二值化回退失败")
        pass

    return ""


def _try_decode_single(img, cv2):
    """尝试用 OpenCV 解码单二维码，成功返回字符串，失败返回 None。"""
    try:
        detector = cv2.QRCodeDetector()
        data, _, _ = detector.detectAndDecode(img)
        if data and data.strip():
            return data
    except (cv2.error, RuntimeError, ValueError):
        logger.debug("单码解码失败")
        pass
    return None


def _decode_multi_qr(img, cv2):
    """使用 OpenCV 原生多二维码检测。"""
    results = []

    # 方案一：直接 detectAndDecodeMulti
    try:
        detector = cv2.QRCodeDetector()
        retval, decoded, points, _ = detector.detectAndDecodeMulti(img)
        if retval and decoded:
            results = [d for d in decoded if d and d.strip()]
            if results:
                return results
    except (cv2.error, RuntimeError, ValueError):
        logger.debug("多码解码策略失败")
        pass

    # 方案二：放大后重试
    h, w = img.shape[:2]
    if h < 600 or w < 600:
        try:
            scale = max(2, 800 // min(h, w))
            enlarged = cv2.resize(img, None, fx=scale, fy=scale,
                                  interpolation=cv2.INTER_NEAREST)
            detector = cv2.QRCodeDetector()
            retval, decoded, points, _ = detector.detectAndDecodeMulti(enlarged)
            if retval and decoded:
                results = [d for d in decoded if d and d.strip()]
                if results:
                    return results
        except (cv2.error, RuntimeError, ValueError):
            pass

    # 方案三：CLAHE 增强后重试
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        detector = cv2.QRCodeDetector()
        retval, decoded, points, _ = detector.detectAndDecodeMulti(enhanced)
        if retval and decoded:
            results = [d for d in decoded if d and d.strip()]
            if results:
                return results
    except (cv2.error, RuntimeError, ValueError):
        pass

    return results


def encode(data, save_path=None, version=None, level="M",
           box_size=10, border=4, mask_pattern=None,
           picture=None, colorized=False, contrast=1.0, brightness=1.0,
           fill_color="black", back_color="white",
           terminal=False, base64=False, svg=False):
    """
    将数据编码为二维码 —— 一站式便捷函数。

    这是快速生成二维码的主要入口。支持普通、艺术、动态、
    终端和 base64 等多种输出方式。

    参数
    ----
    data : str 或 bytes
        要编码的数据（URL、文本、中文等）。
    save_path : str 或 None
        输出图像保存路径。如果为 ``None`` 且未选择特殊输出模式，
        则返回 PIL ``Image`` 对象。
    version : int 或 None
        二维码版本（1-40）。``None`` = 自动。
    level : str
        纠错等级：``'L'``、``'M'``（默认）、``'Q'``、``'H'``。
    box_size : int
        每个模块的像素大小（默认 10）。
    border : int
        白边框宽度（模块数，默认 4）。
    mask_pattern : int 或 None
        掩码模式（0-7）。``None`` = 自动。
    picture : str 或 None
        艺术/动态二维码的背景图片路径。
    colorized : bool
        艺术二维码是否使用彩色（默认为黑白）。
    contrast : float
        背景对比度调整（默认 1.0）。
    brightness : float
        背景亮度调整（默认 1.0）。
    fill_color : str 或 tuple
        普通二维码深色模块的颜色。
    back_color : str 或 tuple
        普通二维码浅色模块的颜色。
    terminal : bool
        如果为 ``True``，在终端打印二维码而非保存文件。
    base64 : bool
        如果为 ``True``，返回 base64 数据 URI 字符串。
    svg : bool
        如果为 ``True``，返回 SVG 字符串。

    返回
    ----
    PIL.Image 或 str 或 None
        - 如果指定了 ``save_path`` 且未使用特殊模式：返回路径字符串。
        - 如果 ``base64=True``：返回 base64 数据 URI 字符串。
        - 如果 ``svg=True``：返回 SVG 字符串。
        - 如果 ``terminal=True``：返回 ``None``（打印到 stdout）。
        - 否则返回 PIL ``Image`` 对象。
    """
    qr = XQR(
        data=data,
        version=version,
        level=level,
        box_size=box_size,
        border=border,
        mask_pattern=mask_pattern,
    )

    # --- 艺术 / 动态输出 ------------------------------------------------
    if picture is not None:
        result_img = qr.to_artistic(
            picture=picture,
            colorized=colorized,
            contrast=contrast,
            brightness=brightness,
        )
        if save_path is not None:
            save_path = _safe_resolve_path(save_path)
            # 处理动态 GIF 保存
            if is_animated_image(picture) or (
                save_path.lower().endswith(".gif")
            ):
                ext = os.path.splitext(save_path)[1].lower()
                if ext == ".gif":
                    kwargs = {"save_all": True}
                else:
                    kwargs = {}
                result_img.save(save_path, **kwargs)
            else:
                result_img.save(save_path)
            return save_path
        return result_img

    # --- 终端输出 --------------------------------------------------------
    if terminal:
        qr.to_terminal()
        return None

    # --- Base64 输出 ----------------------------------------------------
    if base64:
        return qr.to_base64(fill_color=fill_color, back_color=back_color)

    # --- SVG 输出 -------------------------------------------------------
    if svg:
        return qr.to_svg(fill_color=fill_color, back_color=back_color)

    # --- 标准图像输出 ----------------------------------------------------
    if save_path is not None:
        save_path = _safe_resolve_path(save_path)
        return qr.save(save_path, fill_color=fill_color, back_color=back_color)

    # 返回 PIL Image
    return qr.to_image(fill_color=fill_color, back_color=back_color)


def decode(image, multiple=False):
    """
    从图像中解码二维码内容（便捷函数）。

    基于 OpenCV QRCodeDetector 原生实现，无需额外安装依赖。
    支持中文在内的所有 UTF-8 编码内容，支持同时检测多个二维码。

    参数
    ----
    image : str 或 PIL.Image 或 numpy.ndarray
        二维码图像。可以是文件路径、PIL Image 或 numpy 数组。
    multiple : bool
        是否尝试解码图像中的多个二维码
        （基于 OpenCV 原生 ``detectAndDecodeMulti``）。

    返回
    ----
    str 或 list
        如果 ``multiple=False``：返回解码文本字符串，
        未找到时返回空字符串。
        如果 ``multiple=True``：返回解码文本列表，
        未找到时返回空列表。

    示例
    ----
    >>> from xqr import encode, decode

    >>> # 编码
    >>> encode("你好世界", "qr.png")

    >>> # 解码
    >>> text = decode("qr.png")
    >>> print(text)
    你好世界
    """
    return XQR.decode(image, multiple=multiple)


# 兼容 MyQR 的别名
run = encode
