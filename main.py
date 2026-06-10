"""htmlGENERATOR —— 把 PDF / DOCX 转换为自包含 HTML 文件。

用法：
    python main.py input.pdf              # → input.html
    python main.py input.docx -o out.html
"""

import argparse
import sys
import webbrowser
from pathlib import Path

from converter import detect_format, PdfConverter, DocxConverter, DocConverter

# 文件扩展名 → 转换器类的映射表
_CONVERTERS = {
    "pdf": PdfConverter,
    "docx": DocxConverter,
    "doc": DocConverter,
}


def main():
    # ── 解析命令行参数 ──────────────────────────────────────────
    parser = argparse.ArgumentParser(
        description="把 PDF / DOCX 转换为自包含 HTML。",
        usage="python main.py INPUT [-o OUTPUT] [--open]",
    )
    parser.add_argument(
        "input", type=Path,
        help="输入文件（.pdf / .docx）",
    )
    parser.add_argument(
        "-o", "--output", type=Path, default=None,
        help="输出 HTML 路径（默认：输入文件名改为 .html 后缀）",
    )
    parser.add_argument(
        "--open", action="store_true",
        help="转换后用默认浏览器打开生成的 HTML",
    )
    args = parser.parse_args()

    # 校验输入文件是否存在
    if not args.input.is_file():
        print(f"错误：找不到文件 —— {args.input}", file=sys.stderr)
        sys.exit(1)

    # 根据扩展名识别格式，确定输出路径
    fmt = detect_format(args.input)
    output = args.output or args.input.with_suffix(".html")

    # 实例化对应转换器并执行转换
    converter = _CONVERTERS[fmt]()
    print(f"正在转换 {fmt.upper()} → HTML …")
    converter.convert(args.input.resolve(), output.resolve())
    print(f"完成 → {output}")

    # 可选：在浏览器中打开结果
    if args.open:
        webbrowser.open(str(output.resolve()))

if __name__ == "__main__":
    main()
