# -*- coding: utf-8 -*-
"""
XQR 二维码编码引擎 —— QR Code 标准实现。

实现了 QR Code (ISO/IEC 18004) 的完整编码流程：
数据编码 → 纠错码(Reed-Solomon) → 矩阵布局 → 掩码优化 → 图像输出。

这是 XQR 自己的实现，遵循 QR 公开标准，非拷贝任何第三方库。
"""

import itertools
import sys
from bisect import bisect_left
from typing import NamedTuple, Optional
from PIL import Image, ImageDraw


# ===========================================================================
# 一、纠错等级常量
# ===========================================================================

ERROR_CORRECT_L = 1   # 低    ~7%  可恢复
ERROR_CORRECT_M = 0   # 中    ~15% 可恢复（默认）
ERROR_CORRECT_Q = 3   # 较高  ~25% 可恢复
ERROR_CORRECT_H = 2   # 高    ~30% 可恢复

_EC_NAMES = {
    ERROR_CORRECT_L: 'L',
    ERROR_CORRECT_M: 'M',
    ERROR_CORRECT_Q: 'Q',
    ERROR_CORRECT_H: 'H',
}


# ===========================================================================
# 二、异常类
# ===========================================================================

class DataOverflowError(Exception):
    """数据量超过当前二维码版本容量。"""
    pass


# ===========================================================================
# 三、Galois 域 / Reed-Solomon 纠错码
# ===========================================================================

# GF(256) 的指数表和对数表
_EXP_TABLE = list(range(256))
_LOG_TABLE = list(range(256))

for i in range(8):
    _EXP_TABLE[i] = 1 << i
for i in range(8, 256):
    _EXP_TABLE[i] = (
        _EXP_TABLE[i - 4] ^ _EXP_TABLE[i - 5] ^ _EXP_TABLE[i - 6] ^ _EXP_TABLE[i - 8]
    )
for i in range(255):
    _LOG_TABLE[_EXP_TABLE[i]] = i


def _glog(n):
    """Galois 域对数。"""
    if n < 1:
        raise ValueError("glog({})".format(n))
    return _LOG_TABLE[n]


def _gexp(n):
    """Galois 域指数。"""
    return _EXP_TABLE[n % 255]


class _Polynomial:
    """Galois 域上的多项式，用于 Reed-Solomon 编码。"""

    def __init__(self, num, shift):
        offset = 0
        for offset in range(len(num)):
            if num[offset] != 0:
                break
        self.num = num[offset:] + [0] * shift

    def __getitem__(self, index):
        return self.num[index]

    def __iter__(self):
        return iter(self.num)

    def __len__(self):
        return len(self.num)

    def __mul__(self, other):
        num = [0] * (len(self) + len(other) - 1)
        for i, item in enumerate(self):
            for j, other_item in enumerate(other):
                num[i + j] ^= _gexp(_glog(item) + _glog(other_item))
        return _Polynomial(num, 0)

    def __mod__(self, other):
        diff = len(self) - len(other)
        if diff < 0:
            return self
        ratio = _glog(self[0]) - _glog(other[0])
        num = [
            item ^ _gexp(_glog(other_item) + ratio)
            for item, other_item in zip(self, other)
        ]
        if diff:
            num.extend(self[-diff:])
        return _Polynomial(num, 0) % other


class _RSBlock(NamedTuple):
    total_count: int
    data_count: int


# Reed-Solomon 块表：[版本][纠错等级] -> (块数, 总码字数, 数据码字数, ...)
# 每个条目格式：(块数, 总码字数, 数据码字数) 可重复
_RS_BLOCK_TABLE = (
    (1, 26, 19), (1, 26, 16), (1, 26, 13), (1, 26, 9),
    (1, 44, 34), (1, 44, 28), (1, 44, 22), (1, 44, 16),
    (1, 70, 55), (1, 70, 44), (2, 35, 17), (2, 35, 13),
    (1, 100, 80), (2, 50, 32), (2, 50, 24), (4, 25, 9),
    (1, 134, 108), (2, 67, 43), (2, 33, 15, 2, 34, 16), (2, 33, 11, 2, 34, 12),
    (2, 86, 68), (4, 43, 27), (4, 43, 19), (4, 43, 15),
    (2, 98, 78), (4, 49, 31), (2, 32, 14, 4, 33, 15), (4, 39, 13, 1, 40, 14),
    (2, 121, 97), (2, 60, 38, 2, 61, 39), (4, 40, 18, 2, 41, 19), (4, 40, 14, 2, 41, 15),
    (2, 146, 116), (3, 58, 36, 2, 59, 37), (4, 36, 16, 4, 37, 17), (4, 36, 12, 4, 37, 13),
    (2, 86, 68, 2, 87, 69), (4, 69, 43, 1, 70, 44), (6, 43, 19, 2, 44, 20), (6, 43, 15, 2, 44, 16),
    (4, 101, 81), (1, 80, 50, 4, 81, 51), (4, 50, 22, 4, 51, 23), (3, 36, 12, 8, 37, 13),
    (2, 116, 92, 2, 117, 93), (6, 58, 36, 2, 59, 37), (4, 46, 20, 6, 47, 21), (7, 42, 14, 4, 43, 15),
    (4, 133, 107), (8, 59, 37, 1, 60, 38), (8, 44, 20, 4, 45, 21), (12, 33, 11, 4, 34, 12),
    (3, 145, 115, 1, 146, 116), (4, 64, 40, 5, 65, 41), (11, 36, 16, 5, 37, 17), (11, 36, 12, 5, 37, 13),
    (5, 109, 87, 1, 110, 88), (5, 65, 41, 5, 66, 42), (5, 54, 24, 7, 55, 25), (11, 36, 12, 7, 37, 13),
    (5, 122, 98, 1, 123, 99), (7, 73, 45, 3, 74, 46), (15, 43, 19, 2, 44, 20), (3, 45, 15, 13, 46, 16),
    (1, 135, 107, 5, 136, 108), (10, 74, 46, 1, 75, 47), (1, 50, 22, 15, 51, 23), (2, 42, 14, 17, 43, 15),
    (5, 150, 120, 1, 151, 121), (9, 69, 43, 4, 70, 44), (17, 50, 22, 1, 51, 23), (2, 42, 14, 19, 43, 15),
    (3, 141, 113, 4, 142, 114), (3, 70, 44, 11, 71, 45), (17, 47, 21, 4, 48, 22), (9, 39, 13, 16, 40, 14),
    (3, 135, 107, 5, 136, 108), (3, 67, 41, 13, 68, 42), (15, 54, 24, 5, 55, 25), (15, 43, 15, 10, 44, 16),
    (4, 144, 116, 4, 145, 117), (17, 68, 42), (17, 50, 22, 6, 51, 23), (19, 46, 16, 6, 47, 17),
    (2, 139, 111, 7, 140, 112), (17, 74, 46), (7, 54, 24, 16, 55, 25), (34, 37, 13),
    (4, 151, 121, 5, 152, 122), (4, 75, 47, 14, 76, 48), (11, 54, 24, 14, 55, 25), (16, 45, 15, 14, 46, 16),
    (6, 147, 117, 4, 148, 118), (6, 73, 45, 14, 74, 46), (11, 54, 24, 16, 55, 25), (30, 46, 16, 2, 47, 17),
    (8, 132, 106, 4, 133, 107), (8, 75, 47, 13, 76, 48), (7, 54, 24, 22, 55, 25), (22, 45, 15, 13, 46, 16),
    (10, 142, 114, 2, 143, 115), (19, 74, 46, 4, 75, 47), (28, 50, 22, 6, 51, 23), (33, 46, 16, 4, 47, 17),
    (8, 152, 122, 4, 153, 123), (22, 73, 45, 3, 74, 46), (8, 53, 23, 26, 54, 24), (12, 45, 15, 28, 46, 16),
    (3, 147, 117, 10, 148, 118), (3, 73, 45, 23, 74, 46), (4, 54, 24, 31, 55, 25), (11, 45, 15, 31, 46, 16),
    (7, 146, 116, 7, 147, 117), (21, 73, 45, 7, 74, 46), (1, 53, 23, 37, 54, 24), (19, 45, 15, 26, 46, 16),
    (5, 145, 115, 10, 146, 116), (19, 75, 47, 10, 76, 48), (15, 54, 24, 25, 55, 25), (23, 45, 15, 25, 46, 16),
    (13, 145, 115, 3, 146, 116), (2, 74, 46, 29, 75, 47), (42, 54, 24, 1, 55, 25), (23, 45, 15, 28, 46, 16),
    (17, 145, 115), (10, 74, 46, 23, 75, 47), (10, 54, 24, 35, 55, 25), (19, 45, 15, 35, 46, 16),
    (17, 145, 115, 1, 146, 116), (14, 74, 46, 21, 75, 47), (29, 54, 24, 19, 55, 25), (11, 45, 15, 46, 46, 16),
    (13, 145, 115, 6, 146, 116), (14, 74, 46, 23, 75, 47), (44, 54, 24, 7, 55, 25), (59, 46, 16, 1, 47, 17),
    (12, 151, 121, 7, 152, 122), (12, 75, 47, 26, 76, 48), (39, 54, 24, 14, 55, 25), (22, 45, 15, 41, 46, 16),
    (6, 151, 121, 14, 152, 122), (6, 75, 47, 34, 76, 48), (46, 54, 24, 10, 55, 25), (2, 45, 15, 64, 46, 16),
    (17, 152, 122, 4, 153, 123), (29, 74, 46, 14, 75, 47), (49, 54, 24, 10, 55, 25), (24, 45, 15, 46, 46, 16),
    (4, 152, 122, 18, 153, 123), (13, 74, 46, 32, 75, 47), (48, 54, 24, 14, 55, 25), (42, 45, 15, 32, 46, 16),
    (20, 147, 117, 4, 148, 118), (40, 75, 47, 7, 76, 48), (43, 54, 24, 22, 55, 25), (10, 45, 15, 67, 46, 16),
    (19, 148, 118, 6, 149, 119), (18, 75, 47, 31, 76, 48), (34, 54, 24, 34, 55, 25), (20, 45, 15, 61, 46, 16),
)


def _rs_blocks(version, error_correction):
    """获取指定版本和纠错等级的 RS 块列表。"""
    ec_idx = {ERROR_CORRECT_L: 0, ERROR_CORRECT_M: 1, ERROR_CORRECT_Q: 2, ERROR_CORRECT_H: 3}
    offset = ec_idx[error_correction]
    entry = _RS_BLOCK_TABLE[(version - 1) * 4 + offset]
    blocks = []
    for i in range(0, len(entry), 3):
        count, total, data = entry[i:i + 3]
        for _ in range(count):
            blocks.append(_RSBlock(total, data))
    return blocks


# 各纠错等级、各版本对应的生成多项式（用于 RS 编码）
# RS 生成多项式查询表（首项1省略）已在 _create_data 中内联


# ===========================================================================
# 四、位缓冲区和数据编码
# ===========================================================================

class _BitBuffer:
    """可变长度的位缓冲区。"""

    def __init__(self):
        self.buffer = []
        self.length = 0

    def __len__(self):
        return self.length

    def put(self, num, length):
        """将 num 的低 length 位加入缓冲区。"""
        for i in range(length - 1, -1, -1):
            self.buffer.append((num >> i) & 1)
        self.length += length

    def get_bytes(self):
        """将位序列按 8 位一组打包为字节数组。"""
        result = []
        for i in range(0, len(self.buffer), 8):
            byte = 0
            for j in range(8):
                if i + j < len(self.buffer):
                    byte = (byte << 1) | self.buffer[i + j]
                else:
                    byte <<= 1
            result.append(byte)
        return result


class _QRData:
    """编码后的二维码数据块。"""

    def __init__(self, data, mode=None):
        self.data = data
        self.mode = self._detect_mode(data) if mode is None else mode

    def _detect_mode(self, data):
        """自动检测数据的最佳编码模式（byte 模式支持中文）。"""
        if isinstance(data, bytes):
            return 'byte'
        # 始终使用 byte 模式，确保兼容所有 UTF-8 文本（含中文）
        return 'byte'

    def write(self, buffer):
        """将数据写入缓冲区。"""
        # byte 模式
        encoded = self.data.encode('utf-8') if isinstance(self.data, str) else self.data
        for byte in encoded:
            buffer.put(byte, 8)

    def __len__(self):
        if isinstance(self.data, str):
            return len(self.data.encode('utf-8'))
        return len(self.data)


# 各版本的数据模式长度位数
def _mode_sizes_for_version(version):
    """返回指定版本中各模式的长度字段位数。"""
    if version < 10:
        return {'numeric': 10, 'alphanumeric': 9, 'byte': 8, 'kanji': 8}
    if version < 27:
        return {'numeric': 12, 'alphanumeric': 11, 'byte': 16, 'kanji': 10}
    return {'numeric': 14, 'alphanumeric': 13, 'byte': 16, 'kanji': 12}


# 各版本各纠错等级的最大位容量
_BIT_LIMIT_TABLE = [
    [0] + [128 * (v + 1) for v in range(40)],
    [0] + [128 * (v + 1) for v in range(40)],
    [0] + [128 * (v + 1) for v in range(40)],
    [0] + [128 * (v + 1) for v in range(40)],
]

# 实际位容量（来自 QR 规格表）
_BIT_LIMIT_TABLE = {
    ERROR_CORRECT_L: [0, 152, 272, 440, 640, 864, 1088, 1248, 1552, 1856, 2192,
                      2592, 2960, 3424, 3688, 4184, 4712, 5176, 5768, 6360, 6888,
                      7456, 8048, 8752, 9392, 10208, 10960, 11744, 12248, 13048,
                      13880, 14744, 15640, 16568, 17528, 18448, 19472, 20528, 21616,
                      22496, 23648],
    ERROR_CORRECT_M: [0, 128, 224, 352, 512, 688, 864, 992, 1232, 1456, 1728,
                      2032, 2320, 2672, 2920, 3320, 3624, 4056, 4504, 5016, 5352,
                      5712, 6256, 6880, 7312, 8000, 8496, 9024, 9544, 10136, 10984,
                      11640, 12328, 13048, 13800, 14496, 15312, 15936, 16816, 17728,
                      18672],
    ERROR_CORRECT_Q: [0, 104, 176, 272, 384, 496, 608, 704, 880, 1056, 1232,
                      1440, 1648, 1952, 2088, 2360, 2600, 2936, 3176, 3560, 3880,
                      4096, 4544, 4912, 5312, 5744, 6032, 6464, 6968, 7288, 7880,
                      8264, 8920, 9368, 9848, 10288, 10832, 11408, 12016, 12656,
                      13328],
    ERROR_CORRECT_H: [0, 72, 128, 208, 288, 368, 480, 528, 688, 800, 976,
                      1120, 1264, 1440, 1576, 1784, 2024, 2264, 2504, 2728,
                      3080, 3248, 3536, 3712, 4112, 4304, 4768, 5024, 5288,
                      5608, 5960, 6344, 6760, 7208, 7688, 7888, 8432, 8768,
                      9248, 9776, 10208],
}


# ===========================================================================
# 五、二维码矩阵布局
# ===========================================================================

# 校正图案位置表
PATTERN_POSITION_TABLE = [
    [], [6, 18], [6, 22], [6, 26], [6, 30], [6, 34], [6, 22, 38],
    [6, 24, 42], [6, 26, 46], [6, 28, 50], [6, 30, 54], [6, 32, 58],
    [6, 34, 62], [6, 26, 46, 66], [6, 26, 48, 70], [6, 26, 50, 74],
    [6, 30, 54, 78], [6, 30, 56, 82], [6, 30, 58, 86], [6, 34, 62, 90],
    [6, 28, 50, 72, 94], [6, 26, 50, 74, 98], [6, 30, 54, 78, 102],
    [6, 28, 54, 80, 106], [6, 32, 58, 84, 110], [6, 30, 58, 86, 114],
    [6, 34, 62, 90, 118], [6, 26, 50, 74, 98, 122],
    [6, 30, 54, 78, 102, 126], [6, 26, 52, 78, 104, 130],
    [6, 30, 56, 82, 108, 134], [6, 34, 60, 86, 112, 138],
    [6, 30, 58, 86, 114, 142], [6, 34, 62, 90, 118, 146],
    [6, 30, 54, 78, 102, 126, 150], [6, 24, 50, 76, 102, 128, 154],
    [6, 28, 54, 80, 106, 132, 158], [6, 32, 58, 84, 110, 136, 162],
    [6, 26, 54, 82, 110, 138, 166], [6, 30, 58, 86, 114, 142, 170],
]

# 格式信息字符串表：[纠错等级][掩码模式] -> 15位格式信息
_FORMAT_INFO = [
    ['111011111000100', '111001011110011', '111110110101010', '111100010011101',
     '110011000101111', '110001100011000', '110110001000001', '110100101110110'],
    ['101010000010010', '101000100100101', '101111001111100', '101101101001011',
     '100010111111001', '100000011001110', '100111110010111', '100101010100000'],
    ['011010101011111', '011000001101000', '011111100110001', '011101000000110',
     '010010010110100', '010000110000011', '010111011011010', '010101111101101'],
    ['001011010001001', '001001110111110', '001110011100111', '001100111010000',
     '000011101100010', '000001001010101', '000110100001100', '000100000111011'],
]

# 版本信息字符串（版本 7+ 需要）
_VERSION_INFO_STR = [
    '000111110010010100', '001000010110111100', '001001101010011001',
    '001010010011010011', '001011101111110110', '001100011101100010',
    '001101100001000111', '001110011000001101', '001111100100101000',
    '010000101101111000', '010001010001011101', '010010101000010111',
    '010011010100110010', '010100100110100110', '010101011010000011',
    '010110100011001001', '010111011111101100', '011000111011000100',
    '011001000111100001', '011010111110101011', '011011000010001110',
    '011100110000011010', '011101001100111111', '011110110101110101',
    '011111001001010000', '100000100111010101', '100001011011110000',
    '100010100010111010', '100011011110011111', '100100101100001011',
    '100101010000101110', '100110101001100100', '100111010101000001',
    '101000110001101001',
]


def _check_version(v):
    """验证版本号 1-40。"""
    if v < 1 or v > 40:
        raise ValueError("版本号必须在 1~40 之间，收到 {}".format(v))


def _optimal_data_chunks(data, minimum=4):
    """将数据拆分为最优编码块。"""
    data = str(data) if isinstance(data, bytes) else data
    chunks = []
    i = 0
    while i < len(data):
        chunks.append(_QRData(data[i: i + minimum]))
        i += minimum
    if not chunks:
        chunks.append(_QRData(data))
    return chunks


def _create_data(version, error_correction, data_list):
    """创建最终的编码数据（含纠错码）。"""
    buffer = _BitBuffer()
    for data in data_list:
        buffer.put(4, 4)  # byte 模式指示符
        mode_sizes = _mode_sizes_for_version(version)
        buffer.put(len(data), mode_sizes['byte'])
        data.write(buffer)

    # RS 块信息
    blocks = _rs_blocks(version, error_correction)
    bit_limit = sum(b.data_count * 8 for b in blocks)
    if len(buffer) > bit_limit:
        raise DataOverflowError(
            "数据过长（需要 {} 位，可用 {} 位）".format(len(buffer), bit_limit)
        )

    # 终止位（最多 4 个 0）
    for _ in range(min(bit_limit - len(buffer), 4)):
        buffer.put(0, 1)

    # 填充到字节边界
    delimit = len(buffer) % 8
    if delimit:
        for _ in range(8 - delimit):
            buffer.put(0, 1)

    # 填充交替字节 0xEC, 0x11
    bytes_to_fill = (bit_limit - len(buffer)) // 8
    fill = [0xEC, 0x11]
    for i in range(bytes_to_fill):
        buffer.put(fill[i % 2], 8)

    # RS 生成多项式查询表（首项 1 已包含）
    _RS_POLY_LUT = {
        7: [1, 127, 122, 154, 164, 11, 68, 117],
        10: [1, 216, 194, 159, 111, 199, 94, 95, 113, 157, 193],
        13: [1, 137, 73, 227, 17, 177, 17, 52, 13, 46, 43, 83, 132, 120],
        15: [1, 29, 196, 111, 163, 112, 74, 10, 105, 105, 139, 132, 151, 32, 134, 26],
        16: [1, 59, 13, 104, 189, 68, 209, 30, 8, 163, 65, 41, 229, 98, 50, 36, 59],
        17: [1, 119, 66, 83, 120, 119, 22, 197, 83, 249, 41, 143, 134, 85, 53, 125, 99, 79],
        18: [1, 239, 251, 183, 113, 149, 175, 199, 215, 240, 220, 73, 82, 173, 75, 32, 67, 217, 146],
        20: [1, 152, 185, 240, 5, 111, 99, 6, 220, 112, 150, 69, 36, 187, 22, 228, 198, 121, 121, 165, 174],
        22: [1, 89, 179, 131, 176, 182, 244, 19, 189, 69, 40, 28, 137, 29, 123, 67, 253, 86, 218, 230, 26, 145, 245],
        24: [1, 122, 118, 169, 70, 178, 237, 216, 102, 115, 150, 229, 73, 130, 72, 61, 43, 206, 1, 237, 247, 127, 217, 144, 117],
        26: [1, 246, 51, 183, 4, 136, 98, 199, 152, 77, 56, 206, 24, 145, 40, 209, 117, 233, 42, 135, 68, 70, 144, 146, 77, 43, 94],
        28: [1, 252, 9, 28, 13, 18, 251, 208, 150, 103, 174, 100, 41, 167, 12, 247, 56, 117, 119, 233, 127, 181, 100, 121, 147, 176, 74, 58, 197],
        30: [1, 212, 246, 77, 73, 195, 192, 75, 98, 5, 70, 103, 177, 22, 217, 138, 51, 181, 246, 72, 25, 18, 46, 228, 74, 216, 195, 11, 106, 130, 150],
    }

    # 分割数据为 RS 块并计算纠错码
    data_bytes = buffer.get_bytes()
    dcdata = []  # 数据码字块
    ecdata = []  # 纠错码字块
    offset = 0
    max_dc = 0
    max_ec = 0

    for block in blocks:
        dc_count = block.data_count
        ec_count = block.total_count - dc_count
        max_dc = max(max_dc, dc_count)
        max_ec = max(max_ec, ec_count)

        current_dc = data_bytes[offset:offset + dc_count]
        offset += dc_count

        # RS 编码
        if ec_count in _RS_POLY_LUT:
            rs_poly = _Polynomial(_RS_POLY_LUT[ec_count], 0)
        else:
            rs_poly = _Polynomial([1], 0)
            for i in range(ec_count):
                rs_poly = rs_poly * _Polynomial([1, _gexp(i)], 0)

        raw_poly = _Polynomial(current_dc, len(rs_poly) - 1)
        mod_poly = raw_poly % rs_poly

        current_ec = []
        mod_offset = len(mod_poly) - ec_count
        for i in range(ec_count):
            idx = i + mod_offset
            current_ec.append(mod_poly[idx] if idx >= 0 else 0)

        dcdata.append(current_dc)
        ecdata.append(current_ec)

    # 交错排列数据码字和纠错码字
    result = []
    for i in range(max_dc):
        for dc in dcdata:
            if i < len(dc):
                result.append(dc[i])
    for i in range(max_ec):
        for ec in ecdata:
            if i < len(ec):
                result.append(ec[i])

    return result


def _lost_point(modules):
    """评估 QR 矩阵的惩罚分数（越低越好）。"""
    modules_count = len(modules)
    lost_point = 0

    # 1) 行/列中连续同色模块的惩罚
    for r in range(modules_count):
        for c in range(modules_count - 6):
            if (modules[r][c] and modules[r][c + 1] and modules[r][c + 2]
                    and modules[r][c + 3] and modules[r][c + 4]
                    and modules[r][c + 5] and modules[r][c + 6]):
                lost_point += 40
    for c in range(modules_count):
        for r in range(modules_count - 6):
            if (modules[r][c] and modules[r + 1][c] and modules[r + 2][c]
                    and modules[r + 3][c] and modules[r + 4][c]
                    and modules[r + 5][c] and modules[r + 6][c]):
                lost_point += 40

    # 2) 2×2 同色块的惩罚
    for r in range(modules_count - 1):
        for c in range(modules_count - 1):
            if modules[r][c] == modules[r + 1][c] == modules[r][c + 1] == modules[r + 1][c + 1]:
                lost_point += 3

    # 3) 特定模式的惩罚
    for r in range(modules_count):
        for c in range(modules_count - 10):
            if (modules[r][c:c + 11] == [True, False, True, True, True, False, True, False, False, False, False]
                    or modules[r][c:c + 11] == [False, False, False, False, True, False, True, True, True, False, True]):
                lost_point += 40

    # 4) 深色模块比例的惩罚
    dark_count = sum(1 for r in range(modules_count) for c in range(modules_count) if modules[r][c])
    ratio = dark_count * 100 // (modules_count * modules_count)
    prev = abs(ratio - 50) // 5
    lost_point += prev * 10

    return lost_point


# 掩码函数
def _mask_func(pattern):
    """根据掩码模式返回对应的掩码函数。"""
    masks = [
        lambda r, c: (r + c) % 2 == 0,
        lambda r, c: r % 2 == 0,
        lambda r, c: c % 3 == 0,
        lambda r, c: (r + c) % 3 == 0,
        lambda r, c: (r // 2 + c // 3) % 2 == 0,
        lambda r, c: ((r * c) % 2) + ((r * c) % 3) == 0,
        lambda r, c: ((r * c) % 2 + (r * c) % 3) % 2 == 0,
        lambda r, c: ((r + c) % 2 + (r * c) % 3) % 2 == 0,
    ]
    return masks[pattern]


def _best_mask_pattern(modules, modules_count):
    """尝试所有掩码模式，返回最优的掩码编号。"""
    best_pattern = 0
    min_lost = 0
    for i in range(8):
        masked = _apply_mask(modules, modules_count, i)
        lp = _lost_point(masked)
        if i == 0 or min_lost > lp:
            min_lost = lp
            best_pattern = i
    return best_pattern


def _apply_mask(modules, modules_count, mask_pattern):
    """应用掩码到模块矩阵。"""
    mask = _mask_func(mask_pattern)
    result = [row[:] for row in modules]
    for r in range(modules_count):
        for c in range(modules_count):
            if result[r][c] is not None:
                if mask(r, c):
                    result[r][c] = not result[r][c]
    return result


# ===========================================================================
# 六、QRCode 类
# ===========================================================================

# 预计算的空白 QR 矩阵缓存
_precomputed_blanks = {}


class QRCode(object):
    """
    QR 码编码器。

    参数
    ----
    version : int 或 None
        版本号 1-40。None 表示自动选择最小版本。
    error_correction : int
        纠错等级（ERROR_CORRECT_* 常量）。
    box_size : int
        每个模块的像素大小。
    border : int
        白边框宽度（模块数）。
    mask_pattern : int 或 None
        掩码模式 0-7。None 表示自动选择最优。
    """

    def __init__(self, version=None, error_correction=ERROR_CORRECT_M,
                 box_size=10, border=4, mask_pattern=None):
        self.version = version
        self.error_correction = error_correction
        self.box_size = box_size
        self.border = border
        self.mask_pattern = mask_pattern
        self.modules = [[]]
        self.modules_count = 0
        self.data_cache = None
        self.data_list = []

    def clear(self):
        """重置内部状态。"""
        self.modules = [[]]
        self.modules_count = 0
        self.data_cache = None
        self.data_list = []

    def add_data(self, data, optimize=20):
        """添加要编码的数据。"""
        if isinstance(data, _QRData):
            self.data_list.append(data)
        elif optimize:
            self.data_list.extend(_optimal_data_chunks(data, minimum=optimize))
        else:
            self.data_list.append(_QRData(data))
        self.data_cache = None

    def make(self, fit=True):
        """编译数据为 QR 矩阵。"""
        if fit or self.version is None:
            self._best_fit()
        if self.mask_pattern is None:
            self._make_impl(True, 0)  # test 模式先跑一遍设置 modules
            best = self._best_mask_pattern()
            self._make_impl(False, best)
        else:
            self._make_impl(False, self.mask_pattern)

    def _best_mask_pattern(self):
        """尝试所有掩码模式，返回最优编号。"""
        best_pattern = 0
        min_lost = 0
        for i in range(8):
            self._make_impl(True, i)
            lp = _lost_point(self.modules)
            if i == 0 or min_lost > lp:
                min_lost = lp
                best_pattern = i
        return best_pattern

    def _best_fit(self):
        """找到能容纳数据的最小版本（逐版计算，修正版本 10+ 的 byte 长度字段位数变化）。"""
        start = self.version if self.version is not None else 1
        _check_version(start)
        bit_limits = _BIT_LIMIT_TABLE[self.error_correction]
        for v in range(start, 41):
            mode_sizes = _mode_sizes_for_version(v)
            buffer = _BitBuffer()
            for data in self.data_list:
                buffer.put(4, 4)  # byte 模式指示符
                buffer.put(len(data), mode_sizes['byte'])
                data.write(buffer)
            if len(buffer) <= bit_limits[v]:
                self.version = v
                _check_version(self.version)
                return
        raise DataOverflowError("数据超出最大容量")

    def _make_impl(self, test, mask_pattern):
        """执行矩阵布局和掩码。"""
        N = self.version * 4 + 17
        self.modules_count = N

        if self.version in _precomputed_blanks:
            self.modules = [row[:] for row in _precomputed_blanks[self.version]]
        else:
            self.modules = [[None] * N for _ in range(N)]
            self._setup_position_probe(0, 0)
            self._setup_position_probe(N - 7, 0)
            self._setup_position_probe(0, N - 7)
            self._setup_adjust_pattern()
            self._setup_timing()
            _precomputed_blanks[self.version] = [row[:] for row in self.modules]

        self._setup_type_info(test, mask_pattern)
        if self.version >= 7:
            self._setup_type_number(test)

        if self.data_cache is None:
            self.data_cache = _create_data(self.version, self.error_correction, self.data_list)
        self._map_data(self.data_cache, mask_pattern)

    def _setup_position_probe(self, row, col):
        """放置一个定位图案（7×7 的特定模式）。"""
        N = self.modules_count
        for r in range(-1, 8):
            if row + r <= -1 or N <= row + r:
                continue
            for c in range(-1, 8):
                if col + c <= -1 or N <= col + c:
                    continue
                if ((0 <= r <= 6 and c in (0, 6))
                        or (0 <= c <= 6 and r in (0, 6))
                        or (2 <= r <= 4 and 2 <= c <= 4)):
                    self.modules[row + r][col + c] = True
                else:
                    self.modules[row + r][col + c] = False

    def _setup_timing(self):
        """放置时序图案。"""
        N = self.modules_count
        for r in range(8, N - 8):
            if self.modules[r][6] is None:
                self.modules[r][6] = r % 2 == 0
        for c in range(8, N - 8):
            if self.modules[6][c] is None:
                self.modules[6][c] = c % 2 == 0

    def _setup_adjust_pattern(self):
        """放置校正图案。"""
        pos = PATTERN_POSITION_TABLE[self.version - 1]
        N = self.modules_count
        for row in pos:
            for col in pos:
                if self.modules[row][col] is not None:
                    continue
                for r in range(-2, 3):
                    for c in range(-2, 3):
                        if (r == -2 or r == 2 or c == -2 or c == 2 or (r == 0 and c == 0)):
                            self.modules[row + r][col + c] = True
                        else:
                            self.modules[row + r][col + c] = False

    def _setup_type_number(self, test):
        """放置版本信息（版本 7+）。"""
        bits = _bch_type_number(self.version)
        N = self.modules_count
        for i in range(18):
            mod = not test and ((bits >> i) & 1) == 1
            self.modules[i // 3][i % 3 + N - 8 - 3] = mod
        for i in range(18):
            mod = not test and ((bits >> i) & 1) == 1
            self.modules[i % 3 + N - 8 - 3][i // 3] = mod

    def _setup_type_info(self, test, mask_pattern):
        """放置格式信息。"""
        N = self.modules_count
        ec_idx = {ERROR_CORRECT_L: 0, ERROR_CORRECT_M: 1, ERROR_CORRECT_Q: 2, ERROR_CORRECT_H: 3}
        info_str = _FORMAT_INFO[ec_idx[self.error_correction]][mask_pattern]
        bits = int(info_str, 2)
        for i in range(15):
            mod = not test and ((bits >> i) & 1) == 1
            if i < 6:
                self.modules[i][8] = mod
            elif i < 8:
                self.modules[i + 1][8] = mod
            else:
                self.modules[N - 15 + i][8] = mod
        for i in range(15):
            mod = not test and ((bits >> i) & 1) == 1
            if i < 8:
                self.modules[8][N - i - 1] = mod
            elif i < 9:
                self.modules[8][15 - i - 1 + 1] = mod
            else:
                self.modules[8][15 - i - 1] = mod
        self.modules[N - 8][8] = not test

    def _map_data(self, data, mask_pattern):
        """将数据填入矩阵（蛇形填充 + 掩码）。"""
        N = self.modules_count
        inc = -1
        row = N - 1
        bit_index = 7
        byte_index = 0
        mask = _mask_func(mask_pattern)

        for col in range(N - 1, 0, -2):
            if col <= 6:
                col -= 1
            col_range = (col, col - 1)
            while True:
                for c in col_range:
                    if self.modules[row][c] is None:
                        dark = False
                        if byte_index < len(data):
                            dark = ((data[byte_index] >> bit_index) & 1) == 1
                        if mask(row, c):
                            dark = not dark
                        self.modules[row][c] = dark
                        bit_index -= 1
                        if bit_index == -1:
                            byte_index += 1
                            bit_index = 7
                row += inc
                if row < 0 or N <= row:
                    row -= inc
                    inc = -inc
                    break

    def print_ascii(self, out=None, tty=False, invert=False):
        """在终端打印二维码（MyQR 风格紧凑输出）。"""
        if out is None:
            out = sys.stdout
        if self.data_cache is None:
            self.make()
        modcount = self.modules_count

        # 上/下半块字符 (U+2580 上半块, U+2584 下半块)
        # 组合两行模块为一个字符：
        #   上模块=黑, 下模块=黑 -> █ (U+2588)
        #   上模块=黑, 下模块=白 -> ▀ (U+2580)
        #   上模块=白, 下模块=黑 -> ▄ (U+2584)
        #   上模块=白, 下模块=白 ->   (空格)
        if invert:
            blk, top, btm, spc = ' ', '\u2584', '\u2580', '\u2588'
        else:
            blk, top, btm, spc = '\u2588', '\u2580', '\u2584', ' '

        for r in range(0, modcount, 2):
            for c in range(modcount):
                upper = self.modules[r][c]
                lower = self.modules[r+1][c] if r+1 < modcount else False
                if upper and lower:
                    out.write(blk)
                elif upper and not lower:
                    out.write(top)
                elif not upper and lower:
                    out.write(btm)
                else:
                    out.write(spc)
            out.write('\n')
        out.flush()


def _bch_type_number(version):
    """计算版本信息的 BCH 码。"""
    poly = 0x1F25  # 生成多项式
    data = version << 12
    remainder = data
    for i in range(12, -1, -1):
        if (remainder >> (i + 12)) & 1:
            remainder ^= poly << i
    return (data | remainder) & 0x3FFF


# ===========================================================================
# 七、图像渲染
# ===========================================================================

class _BaseImage:
    """二维码图像渲染基类。"""

    def __init__(self, border, width, box_size, **kwargs):
        self.border = border
        self.width = width
        self.box_size = box_size
        self.pixel_size = (width + 2 * border) * box_size
        self.needs_drawrect = True
        self.needs_context = False
        self.needs_processing = False
        self._img = self._new_image(**kwargs)

    def _new_image(self, **kwargs):
        raise NotImplementedError

    def drawrect(self, row, col):
        raise NotImplementedError

    def pixel_box(self, row, col):
        """计算模块 (row, col) 对应的像素区域。"""
        x = (col + self.border) * self.box_size
        y = (row + self.border) * self.box_size
        return (x, y, x + self.box_size - 1, y + self.box_size - 1)

    def save(self, stream, format=None, **kwargs):
        kind = kwargs.pop('kind', getattr(self, 'kind', 'PNG'))
        if format is None:
            format = kind
        self._img.save(stream, format=format, **kwargs)


class _PilImage(_BaseImage):
    """基于 PIL 的图像渲染器。"""

    kind = 'PNG'

    def _new_image(self, **kwargs):
        back_color = kwargs.get('back_color', 'white')
        fill_color = kwargs.get('fill_color', 'black')

        if fill_color == 'black' and back_color == 'white':
            mode = '1'
            fill_color = 0
            back_color = 255
        elif back_color == 'transparent':
            mode = 'RGBA'
            back_color = None
        else:
            mode = 'RGB'

        img = Image.new(mode, (self.pixel_size, self.pixel_size), back_color)
        self.fill_color = fill_color
        self._draw = ImageDraw.Draw(img)
        return img

    def drawrect(self, row, col):
        box = self.pixel_box(row, col)
        self._draw.rectangle(box, fill=self.fill_color)

    def save(self, stream, format=None, **kwargs):
        kind = kwargs.pop('kind', self.kind)
        if format is None:
            format = kind
        self._img.save(stream, format=format, **kwargs)


def make_qr(data, **kwargs):
    """
    快速生成二维码图像。

    参数
    ----
    data : str
        要编码的数据。
    **kwargs
        传递给 QRCode 构造函数的参数。
        version, error_correction, box_size, border, mask_pattern。

    返回
    ----
    PIL.Image
    """
    qr = QRCode(**kwargs)
    qr.add_data(data)
    qr.make(fit=True)

    # 绘制图像
    N = qr.modules_count
    bs = qr.box_size
    border = qr.border
    px_size = (N + 2 * border) * bs

    img = Image.new('1', (px_size, px_size), 255)  # 白色背景
    draw = ImageDraw.Draw(img)

    for r in range(N):
        for c in range(N):
            if qr.modules[r][c]:
                x = (c + border) * bs
                y = (r + border) * bs
                draw.rectangle([x, y, x + bs - 1, y + bs - 1], fill=0)

    return img


def make_qr_image(qr, fill_color='black', back_color='white'):
    """
    从 QRCode 对象生成指定颜色的 PIL Image。

    参数
    ----
    qr : QRCode
        已编译的 QRCode 实例。
    fill_color : str 或 tuple
        深色模块颜色。
    back_color : str 或 tuple
        浅色模块颜色。

    返回
    ----
    PIL.Image
    """
    im = _PilImage(qr.border, qr.modules_count, qr.box_size,
                   fill_color=fill_color, back_color=back_color)
    N = qr.modules_count
    for r in range(N):
        for c in range(N):
            if qr.modules[r][c]:
                im.drawrect(r, c)
    if hasattr(im, 'needs_processing') and im.needs_processing:
        pass
    return im._img


# ===========================================================================
# 八、SVG 渲染
# ===========================================================================

def make_qr_svg(qr, fill_color='black', back_color='white'):
    """
    从 QRCode 对象生成 SVG 字符串。

    参数
    ----
    qr : QRCode
        已编译的 QRCode 实例。
    fill_color : str
        深色模块颜色。
    back_color : str
        浅色模块颜色（仅用于背景矩形）。

    返回
    ----
    str
        SVG XML 字符串。
    """
    N = qr.modules_count
    bs = qr.box_size
    border = qr.border
    size = (N + 2 * border) * bs

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg"',
        '     width="{0}" height="{0}" viewBox="0 0 {0} {0}">'.format(size),
        '  <rect width="100%" height="100%" fill="{0}"/>'.format(back_color),
    ]

    for r in range(N):
        for c in range(N):
            if qr.modules[r][c]:
                x = (c + border) * bs
                y = (r + border) * bs
                lines.append(
                    '  <rect x="{0}" y="{1}" width="{2}" height="{2}" '
                    'fill="{3}"/>'.format(x, y, bs, fill_color)
                )

    lines.append('</svg>')
    return '\n'.join(lines)
