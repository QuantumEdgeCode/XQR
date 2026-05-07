# -*- coding: utf-8 -*-
"""
条形码生成与解码模块（零外部依赖——仅用 PIL/Pillow + OpenCV）。

生成的条形码使用 Code128B 编码标准，支持全部 ASCII 字符（32-126）。
解码使用 OpenCV 原生的 BarcodeDetector（已为依赖），无需额外安装。

用法::

    from xqr.barcode import encode, decode

    # 生成条形码
    encode("Hello Barcode", "barcode.png")

    # 解码
    text = decode("barcode.png")
    print(text)
"""

import io
import os
import warnings

from PIL import Image, ImageDraw, ImageFont


# ===========================================================================
# Code128 编码表 —— 107 个字符，每个 11 位（1=黑条, 0=白空）
# 前 3 个是 Start A / Start B / Start C，后 3 个是 Code A / Code B / Code C / FNC1-4，最后是 Stop
# 此处只实现 Start B + Code128B（覆盖所有可打印 ASCII）
# ===========================================================================

# 107 个 Code128 字符的 11 位图案
_CODE128_PATTERNS = [
    0b11011001100, 0b11001101100, 0b11001100110, 0b10010011000,
    0b10010001100, 0b10001001100, 0b10011001000, 0b10011000100,
    0b10001100100, 0b11001001000, 0b11001000100, 0b11000100100,
    0b10110011100, 0b10011011100, 0b10011001110, 0b10111001100,
    0b10011101100, 0b10011100110, 0b11001110010, 0b11001011100,
    0b11001001110, 0b11011100100, 0b11001110100, 0b11101101110,
    0b11101001100, 0b11100101100, 0b11100100110, 0b11101100100,
    0b11100110100, 0b11100110010, 0b11011011000, 0b11011000110,
    0b11000110110, 0b10100011000, 0b10001011000, 0b10001000110,
    0b10110001000, 0b10001101000, 0b10001100010, 0b11010001000,
    0b11000101000, 0b11000100010, 0b10110111000, 0b10110001110,
    0b10001101110, 0b10111011000, 0b10111000110, 0b10001110110,
    0b11101110110, 0b11010001110, 0b11000101110, 0b11011101000,
    0b11011100010, 0b11011101110, 0b11101011000, 0b11101000110,
    0b11100010110, 0b11101101000, 0b11101100010, 0b11100011010,
    0b11101111010, 0b11001000010, 0b11110001010, 0b10100110000,
    0b10100001100, 0b10010110000, 0b10010000110, 0b10000101100,
    0b10000100110, 0b10110010000, 0b10110000100, 0b10011010000,
    0b10011000010, 0b10000110100, 0b10000110010, 0b11000010010,
    0b11001010000, 0b11110111010, 0b11000010100, 0b10001111010,
    0b10100111100, 0b10010111100, 0b10010011110, 0b10111100100,
    0b10011110100, 0b10011110010, 0b11110100100, 0b11110010100,
    0b11110010010, 0b11011011110, 0b11011110110, 0b11110110110,
    0b10101111000, 0b10100011110, 0b10001011110, 0b10111101000,
    0b10111100010, 0b10001111010, 0b10111011110, 0b10111101110,
    0b11101011110, 0b11110101110,
    0b11010000100,  # 104 = Start A
    0b11010010000,  # 105 = Start B
    0b11010011100,  # 106 = Start C / Stop
]

_CODE128_STOP = 0b1100011101011  # Stop 图案（13 位）

# Code128B 字符映射表：字符 → 值（32=' ', 33='!', ..., 126='~'）
_CODE128B_VALUES = {}
for _i in range(95):
    _CODE128B_VALUES[chr(32 + _i)] = _i


def _bits_to_widths(pattern, bits):
    """将二进制图案转为条空宽度列表（奇数索引=黑条，偶数索引=白空）。"""
    widths = []
    current = 0
    prev_bit = None
    for i in range(bits - 1, -1, -1):
        bit = (pattern >> i) & 1
        if bit == prev_bit:
            current += 1
        else:
            if prev_bit is not None:
                widths.append(current)
            current = 1
            prev_bit = bit
    widths.append(current)
    return widths


def _encode_code128(data):
    """编码数据为 Code128 条空宽度序列。

    返回
    ----
    list[int]
        条空宽度列表（偶数索引=黑条, 奇数索引=白空）。
    """
    # 1) 计算校验和
    checksum = 104  # Start B 的值
    values = []
    for ch in str(data):
        v = _CODE128B_VALUES.get(ch)
        if v is None:
            if not hasattr(_encode_code128, '_warned'):
                warnings.warn(
                    "Code128 不支持字符 {!r}（位置 {}），已替换为 '?'".format(
                        ch, len(values)
                    ),
                    UserWarning,
                )
                _encode_code128._warned = True
            v = _CODE128B_VALUES.get('?', 0)
        values.append(v)

    for i, v in enumerate(values):
        checksum += v * (i + 1)
    checksum %= 103

    # 2) 生成条空宽度序列
    result = []
    for pat in [
        _CODE128_PATTERNS[104],  # Start B
    ] + [_CODE128_PATTERNS[v] for v in values] + [
        _CODE128_PATTERNS[checksum],  # 校验位
        _CODE128_STOP,  # Stop
    ]:
        result.extend(_bits_to_widths(pat, 13 if pat == _CODE128_STOP else 11))

    return result


def encode(data, save_path=None, barcode_type="code128",
           module_width=2, module_height=60, quiet_zone=10,
           write_text=True, bar_color="black", bg_color="white",
           **kwargs):
    """
    生成条形码（纯自研，零外部依赖）。

    参数
    ----
    data : str
        要编码的数据（支持 ASCII 字符 32-126）。
    save_path : str 或 None
        保存路径（None 则返回 PNG bytes）。
    barcode_type : str
        仅支持 ``'code128'``（默认）—— 最通用的条码标准。
    module_width : int
        每个模块的像素宽度（默认 2）。
    module_height : int
        条码高度（默认 60）。
    quiet_zone : int
        左右空白边距（默认 10）。
    write_text : bool
        是否在条码下方显示文字（默认 True）。
    bar_color : str
        条码颜色（默认 black）。
    bg_color : str
        背景色（默认 white）。

    返回
    ----
    bytes 或 str
        save_path 为 None 时返回 PNG bytes，否则返回路径。
    """
    widths = _encode_code128(data)
    total_modules = sum(widths)

    # 图像尺寸
    img_w = quiet_zone * 2 + total_modules * module_width
    img_h = quiet_zone * 2 + module_height + (20 if write_text else 0)

    # 用纯二值图像（mode='1'）消除抗锯齿
    img = Image.new("1", (img_w, img_h), 1)  # 1=white
    draw = ImageDraw.Draw(img)

    x = quiet_zone
    for i, w in enumerate(widths):
        pw = w * module_width
        if i % 2 == 0:  # 黑条
            draw.rectangle([x, quiet_zone, x + pw - 1, quiet_zone + module_height],
                           fill=0)  # 0=black
        x += pw

    # 转 RGB 以支持文字
    img = img.convert("RGB")

    # 下方文字
    if write_text:
        try:
            font = ImageFont.truetype("arial.ttf", 14)
        except (OSError, IOError):
            font = ImageFont.load_default()
        _, _, tw, th = draw.textbbox((0, 0), data, font=font)
        tx = (img_w - tw) // 2
        ty = quiet_zone + module_height + 4
        draw = ImageDraw.Draw(img)
        draw.text((tx, ty), data, fill=bar_color, font=font)

    # 输出
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    image_bytes = buf.getvalue()

    if save_path:
        with open(save_path, "wb") as f:
            f.write(image_bytes)
        return save_path

    return image_bytes


# ===========================================================================
# 解码（同时尝试 OpenCV BarcodeDetector + 自研 Code128 图案解码）
# ===========================================================================

def _load_image(image):
    """将各种输入转为 OpenCV BGR numpy 数组。"""
    import cv2
    import numpy as np
    from PIL import Image as PILImage

    if isinstance(image, str):
        return cv2.imread(image)
    elif isinstance(image, PILImage.Image):
        arr = np.array(image.convert("RGB"))
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    elif isinstance(image, np.ndarray):
        return image
    return None


def decode(image, multiple=False):
    """
    解码条形码。

    使用 OpenCV BarcodeDetector 解码 + 自研 Code128 图案解码器双重引擎，
    零额外依赖。

    参数
    ----
    image : str 或 PIL.Image 或 numpy.ndarray
        条形码图像。
    multiple : bool
        是否检测多个条形码。

    返回
    ----
    str 或 list
        单码返回字符串，多码返回列表。未找到返回空字符串/空列表。
    """
    img = _load_image(image)
    if img is None:
        raise FileNotFoundError("无法读取图像")

    # 引擎1：OpenCV 原生解码
    result = _decode_opencv(img, multiple=multiple)
    if result:
        return result

    # 引擎2：自研 Code128 图案匹配解码
    result = _decode_code128_from_image(img, multiple=multiple)
    if result:
        return result

    return [] if multiple else ""


def _decode_opencv(img, multiple=False):
    """使用 OpenCV BarcodeDetector 解码（多重预处理策略）。"""
    import cv2

    strategies = [("原图", img)]

    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img

    strategies.append(("灰度", cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)))
    _, thresh = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
    strategies.append(("二值化", cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)))

    adapt = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 51, 10)
    strategies.append(("自适应", cv2.cvtColor(adapt, cv2.COLOR_GRAY2BGR)))

    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    strategies.append(("CLAHE", cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)))

    detector = cv2.barcode.BarcodeDetector()
    seen = set()

    for _, proc_img in strategies:
        try:
            if multiple:
                ret, decoded, _, _ = detector.detectAndDecodeWithType(proc_img)
                if ret:
                    for d in decoded:
                        d = d.strip()
                        if d and d not in seen:
                            seen.add(d)
                continue

            _, decoded, _ = detector.detectAndDecode(proc_img)
            if decoded and decoded.strip():
                return decoded.strip()
        except (cv2.error, RuntimeError):
            continue

    # 放大后重试
    h, w = img.shape[:2]
    if h < 400 or w < 400:
        scale = max(2, 500 // min(h, w))
        big = cv2.resize(img, None, fx=scale, fy=scale,
                         interpolation=cv2.INTER_NEAREST)
        for name in ["原图", "灰度", "二值化"]:
            proc = big
            if name == "灰度":
                g = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)
                proc = cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)
            elif name == "二值化":
                g = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)
                _, t = cv2.threshold(g, 128, 255, cv2.THRESH_BINARY)
                proc = cv2.cvtColor(t, cv2.COLOR_GRAY2BGR)
            try:
                _, decoded, _ = detector.detectAndDecode(proc)
                if decoded and decoded.strip():
                    return decoded.strip()
            except (cv2.error, RuntimeError):
                continue

    if multiple:
        return list(seen)
    return ""


# ── 自研 Code128 图案匹配解码器 ──────────────────────────

def _decode_code128_from_image(img, multiple=False):
    """使用图像处理 + 图案匹配解码 Code128 条形码。"""
    import cv2
    import numpy as np
    import cv2
    import numpy as np

    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img

    results = []

    # 扫描多条水平线取最清晰的
    h, w = gray.shape
    scan_rows = []
    scan_rows.append(h // 2)

    for offset in range(5, 20, 5):
        if h // 2 + offset < h:
            scan_rows.append(h // 2 + offset)
        if h // 2 - offset >= 0:
            scan_rows.append(h // 2 - offset)

    for row in scan_rows:
        decoded = _decode_code128_scanline(gray[row, :])
        if decoded:
            if decoded not in results:
                results.append(decoded)
            if not multiple:
                return decoded

    if multiple:
        return results
    return results[0] if results else ""


def _decode_code128_scanline(line):
    """从单行像素中解码 Code128 条形码（宽度归一化匹配，抗锯齿容错）。"""
    import numpy as np
    binary = np.where(line > 128, 255, 0).astype(np.uint8)
    start = next((i for i, p in enumerate(binary) if p < 128), None)
    if start is None:
        return ""
    end = next((len(binary) - 1 - i for i, p in enumerate(reversed(binary)) if p < 128), None)
    if end is None or end - start < 30:
        return ""

    widths = []
    cnt = 1
    prev = binary[start]
    for i in range(start + 1, end + 1):
        cur = binary[i]
        if (cur < 128) == (prev < 128):
            cnt += 1
        else:
            widths.append(cnt)
            cnt = 1
            prev = cur
    widths.append(cnt)
    if len(widths) < 12:
        return ""

    # 估算模块宽度
    sorted_w = sorted(widths)
    module_w = sorted_w[len(sorted_w) // 20] if len(sorted_w) >= 20 else sorted_w[0]
    module_w = max(module_w, 1)

    # 构建归一化匹配表（共享缓存）
    if not hasattr(_decode_code128_scanline, "_cache"):
        _cache = []
        for val in range(len(_CODE128_PATTERNS)):
            w = _bits_to_widths(_CODE128_PATTERNS[val], 11)
            m = max(w)
            _cache.append((tuple(max(1, round(x * 10 / m)) for x in w), val))
        sw = _bits_to_widths(_CODE128_STOP, 13)
        m = max(sw)
        _cache.append((tuple(max(1, round(x * 10 / m)) for x in sw), 106))
        _decode_code128_scanline._cache = _cache
    cache = _decode_code128_scanline._cache

    def _best(chunk, allow_stop=False):
        m = max(chunk)
        if m == 0:
            return None
        norm = tuple(max(1, round(x * 10 / m)) for x in chunk)
        best, best_d = None, 999
        for t, v in cache:
            if len(t) != len(norm):
                continue
            if v == 106 and not allow_stop:
                continue
            d = sum(abs(a - b) for a, b in zip(norm, t))
            if d < best_d:
                best_d = d
                best = v
        return best if best_d <= len(norm) * 3 else None

    # 找 Start（6 元素）
    pos = 0
    start_val = None
    while pos + 6 <= len(widths):
        c6 = widths[pos:pos + 6]
        total_mod = sum(c6) / module_w
        if 9 <= total_mod <= 13:
            v = _best(c6, allow_stop=False)
            if v in (103, 104, 105):
                start_val = v
                pos += 6
                break
        pos += 1
    if start_val is None:
        return ""

    # 解码后续：优先 6 元素，否则 7 元素（数据或 Stop）
    values = [start_val]
    stop_found = False
    for _ in range(20):
        if pos >= len(widths):
            break
        found = False
        
        # 如果只剩最后 7 个元素，强制试 Stop
        if pos + 7 == len(widths):
            c7 = widths[pos:pos + 7]
            if 11 <= sum(c7) / module_w <= 15:
                v = _best(c7, allow_stop=True)
                if v == 106:
                    stop_found = True
                    break
        
        # 尝试 6 元素（数据字符）
        if pos + 6 <= len(widths):
            c6 = widths[pos:pos + 6]
            if 9 <= sum(c6) / module_w <= 13:
                v = _best(c6, allow_stop=False)
                if v is not None and 0 <= v <= 105:
                    values.append(v)
                    pos += 6
                    found = True
        # 尝试 7 元素（Stop 或数据）
        if not found and pos + 7 <= len(widths):
            c7 = widths[pos:pos + 7]
            t7 = sum(c7) / module_w
            if 11 <= t7 <= 15:
                v = _best(c7, allow_stop=True)
                if v == 106:
                    stop_found = True
                    break
                if v is not None and 0 <= v <= 105:
                    values.append(v)
                    pos += 7
                    found = True
        if not found:
            pos += 2

    if not stop_found or len(values) < 2:
        return ""

    # Code128B: 去掉 Start 和 Checksum
    chars = []
    for v in values[1:-1]:
        if 0 <= v <= 94:
            chars.append(chr(32 + v))
        else:
            chars.append('?')
    return "".join(chars)


def _bits_to_int(bits, start, length):
    """将位序列从 start 开始的 length 位转为整数（高位在前）。"""
    val = 0
    for i in range(length):
        if start + i < len(bits):
            val = (val << 1) | bits[start + i]
    return val


def _match_pattern(bits, start, pattern, length):
    """在 bits 中从 start 开始匹配指定长度的 pattern（精确匹配）。"""
    if start + length > len(bits):
        return -1
    for i in range(length):
        expected = (pattern >> (length - 1 - i)) & 1
        if bits[start + i] != expected:
            return -1
    return start
