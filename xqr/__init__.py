# XQR —— 高性能二维码生成与解码库
#
# 受 MyQR (https://github.com/sylnsfar/qrcode) 启发，XQR 使用 numpy 加速
# 的艺术和动态二维码生成，并提供简洁现代的 Python API。
#
# 主要功能：
#   - 支持二维码生成（PNG、SVG、终端、base64）
#   - 支持二维码解码（从图片中读取二维码内容）
#   - 艺术二维码（与背景图片融合）
#   - 动态二维码（GIF 逐帧融合）
#   - 完全支持中文编码和解码
#   - numpy 加速图像处理（比 MyQR 快 10-100 倍）
#   - Python 3.6+ 兼容
#   - 完整 Unicode 和字节数据支持

from ._version import __version__, __version_info__
from .core import (
    XQR,
    encode,
    decode,
    run,
    ERROR_CORRECT_L,
    ERROR_CORRECT_M,
    ERROR_CORRECT_Q,
    ERROR_CORRECT_H,
)
from . import barcode  # 条形码生成与解码

__all__ = [
    "XQR",
    "encode",
    "decode",
    "run",
    "barcode",
    "ERROR_CORRECT_L",
    "ERROR_CORRECT_M",
    "ERROR_CORRECT_Q",
    "ERROR_CORRECT_H",
    "__version__",
    "__version_info__",
]
