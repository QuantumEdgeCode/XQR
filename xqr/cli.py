# -*- coding: utf-8 -*-
"""
XQR 命令行接口。

用法::

    # 生成二维码
    python -m xqr encode "Hello World" output.png
    python -m xqr encode "https://example.com" -p bg.jpg -c -o artistic.png
    python -m xqr encode "你好世界" output.png

    # 解码二维码
    python -m xqr decode input.png

    # 终端输出
    python -m xqr encode "Hello" --terminal
"""

import argparse
import sys

from ._version import __version__


def main(argv=None):
    """``python -m xqr`` 的入口点。"""
    # 确保 stdout 使用 UTF-8 编码（避免 Windows GBK 下中文输出乱码）
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    # 快捷命令：未指定子命令时自动当作 encode
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] not in ('encode', 'decode', 'barcode', '--help', '-h', '-help', '--version', '-V'):
        argv = ['encode'] + argv

    # 兼容 Windows CMD：单引号被当作普通字符传入，自动去除包裹的单引号
    argv = [
        a[1:-1] if len(a) >= 2 and a.startswith("'") and a.endswith("'") else a
        for a in argv
    ]

    # 兼容 CMD 习惯：-help 转为 --help
    argv = ['--help' if a in ('-help', '/?') else a for a in argv]

    parser = argparse.ArgumentParser(
        prog="xqr",
        description="XQR —— 高性能二维码生成与解码工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "快捷用法:\n"
            "  xqr \"Hello World\"             直接生成（默认 encode）\n"
            "  xqr \"你好\" --terminal         终端输出\n"
            "  xqr \"data\" -l H output.png    指定纠错等级\n"
            "\n"
            "完整用法:\n"
            "  xqr encode \"Hello World\" output.png\n"
            "  xqr encode \"https://example.com\" -p bg.jpg -c -o artistic.png\n"
            "  xqr encode \"你好世界\" output.png\n"
            "  xqr decode input.png\n"
            "  xqr encode \"Hello\" --terminal\n"
        ),
    )

    # 版本号
    parser.add_argument(
        "--version", "-V",
        action="version",
        version="xqr {}".format(__version__),
    )

    # 子命令: encode / decode
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # ---- encode 子命令 ------------------------------------------------
    enc_parser = subparsers.add_parser("encode", help="生成二维码")
    enc_parser.add_argument("data", help="要编码的数据（URL、文本、中文等）")
    enc_parser.add_argument("output", nargs="?", default=None,
                            help="输出图像文件路径")

    enc_parser.add_argument("-v", "--version", type=int, default=None,
                            help="二维码版本 1-40（默认: 自动）")
    enc_parser.add_argument("-l", "--level", default="M",
                            choices=["L", "M", "Q", "H"],
                            help="纠错等级（默认: M）")
    enc_parser.add_argument("-p", "--picture", default=None,
                            help="艺术二维码的背景图片路径")
    enc_parser.add_argument("-c", "--colorized", action="store_true",
                            help="使用彩色（配合 -p 使用）")
    enc_parser.add_argument("--contrast", type=float, default=1.0,
                            help="对比度调整（默认: 1.0）")
    enc_parser.add_argument("--brightness", type=float, default=1.0,
                            help="亮度调整（默认: 1.0）")
    enc_parser.add_argument("-t", "--terminal", action="store_true",
                            help="在终端打印二维码")
    enc_parser.add_argument("--fill-color", default="black",
                            help="深色模块颜色（默认: black）")
    enc_parser.add_argument("--back-color", default="white",
                            help="浅色模块颜色（默认: white）")
    enc_parser.add_argument("--box-size", type=int, default=10,
                            help="每个模块的像素大小（默认: 10）")
    enc_parser.add_argument("--border", type=int, default=4,
                            help="边框宽度（模块数，默认: 4）")

    # ---- decode 子命令 ------------------------------------------------
    dec_parser = subparsers.add_parser("decode", help="解码二维码/条形码")
    dec_parser.add_argument("image", help="二维码/条形码图像文件路径")
    dec_parser.add_argument("--multiple", action="store_true",
                            help="尝试解码图像中的多个二维码")

    # ---- barcode 子命令 ------------------------------------------------
    bar_parser = subparsers.add_parser("barcode", help="生成条形码")
    bar_parser.add_argument("data", help="要编码的数据（数字/字母）")
    bar_parser.add_argument("-o", "--output", default=None,
                            help="输出图像文件路径")
    bar_parser.add_argument("--type", default="code128",
                        choices=["code128"],
                        help="条形码类型（目前仅支持 code128）")
    bar_parser.add_argument("--no-text", action="store_true",
                            help="不显示文字")
    bar_parser.add_argument("--module-width", type=int, default=3,
                            help="条宽（像素，默认: 3）")
    bar_parser.add_argument("--module-height", type=int, default=80,
                            help="条高（像素，默认: 80）")

    # 解析参数
    args = parser.parse_args(argv)

    # 如果没有参数，显示帮助
    if args.command is None:
        parser.print_help()
        return

    # ---- 执行命令 ----------------------------------------------------
    if args.command == "decode":
        return _do_decode(args)
    elif args.command == "barcode":
        return _do_barcode(args)
    else:
        return _do_encode(args)


def _do_encode(args):
    """执行编码命令。"""
    from .core import encode
    from ._encoder import DataOverflowError

    try:
        if args.terminal:
            encode(
                args.data,
                version=args.version,
                level=args.level,
                terminal=True,
                box_size=args.box_size,
                border=args.border,
            )
            return

        if args.picture and args.output and args.output.lower().endswith(".gif"):
            # 动态二维码
            encode(
                args.data,
                save_path=args.output,
                picture=args.picture,
                version=args.version,
                level=args.level,
                colorized=args.colorized,
                contrast=args.contrast,
                brightness=args.brightness,
            )
            print("动态二维码已保存到: {}".format(args.output))
            return

        result = encode(
            args.data,
            save_path=args.output,
            version=args.version,
            level=args.level,
            picture=args.picture,
            colorized=args.colorized,
            contrast=args.contrast,
            brightness=args.brightness,
            fill_color=args.fill_color,
            back_color=args.back_color,
            box_size=args.box_size,
            border=args.border,
        )

        if args.output:
            print("二维码已保存到: {}".format(args.output))
        elif isinstance(result, str):
            print(result)
        else:
            # PIL Image 对象 —— 显示它
            try:
                result.show()
            except Exception:
                print("二维码已生成（使用 --output 参数保存到文件）")

    except DataOverflowError as e:
        print("错误: {}".format(e), file=sys.stderr)
        print("提示: 尝试降低纠错等级（-l L）或增加图片大小")
        sys.exit(1)


def _do_decode(args):
    """执行解码命令（QR 码 + 条形码自动检测）。"""
    from .core import decode as qr_decode
    from .barcode import decode as bar_decode

    try:
        # 先试 QR 码
        result = qr_decode(args.image, multiple=args.multiple)

        # QR 没解出来时试条形码
        if not result:
            bar_result = bar_decode(args.image, multiple=args.multiple)
            if bar_result:
                result = bar_result

        if args.multiple:
            if result:
                label = "条形码" if isinstance(result, list) and result and \
                    not any(len(r) > 50 for r in result) else "二维码"
                print("解码完成！找到 {} 个{}:\n".format(len(result), label))
                for i, text in enumerate(result, 1):
                    print("  [{}/{}] {}".format(i, len(result), text))
            else:
                print("未在图像中找到二维码或条形码。")
        else:
            if result:
                label = "条形码" if len(result) < 30 else "二维码"
                print("{}解码结果: {}".format(label, result))
            else:
                print("未在图像中找到二维码或条形码。")

    except FileNotFoundError as e:
        print("错误: {}".format(e), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print("解码失败: {}".format(e), file=sys.stderr)
        sys.exit(1)


def _do_barcode(args):
    """执行条形码生成命令。"""
    from .barcode import encode

    try:
        writer_opts = {
            "write_text": not args.no_text,
            "module_width": args.module_width,
            "module_height": args.module_height,
        }

        result = encode(
            args.data,
            save_path=args.output,
            barcode_type=args.type,
            **writer_opts,
        )

        if args.output:
            print("条形码已保存到: {}".format(args.output))
        else:
            # 无输出路径时打印提示
            print("条形码已生成（使用 output 参数保存到文件）")
            print("数据: {}".format(args.data))
            print("类型: {}".format(args.type))

    except ImportError as e:
        print("错误: {}".format(e), file=sys.stderr)
        print("请运行: pip install python-barcode")
        sys.exit(1)
    except Exception as e:
        print("条形码生成失败: {}".format(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
