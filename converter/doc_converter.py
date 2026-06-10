""".doc → HTML：通过 LibreOffice 先转为 .docx，再交 DocxConverter 处理。

旧版 .doc 格式为二进制 OLE，无法用纯 Python 读取。
因此依赖 LibreOffice（soffice.exe）做一次性预处理。
若未安装 LibreOffice，转换将失败并给出安装指引。
"""

import shutil
import subprocess
import sys
from pathlib import Path

from .base import Converter
from .docx_converter import DocxConverter
from .utils import temp_dir


class DocConverter(Converter):
    """将 .doc 文件转为 .docx 后交由 DocxConverter 输出 HTML。"""

    def convert(self, input_path: Path, output_path: Path) -> None:
        self._output_path = output_path
        soffice = _find_soffice()

        with temp_dir("docconv_") as work:
            # 1. LibreOffice 将 .doc 转为 .docx
            cmd = [
                soffice,
                "--headless",
                "--convert-to", "docx",
                "--outdir", str(work),
                str(input_path),
            ]
            try:
                subprocess.run(cmd, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                raise RuntimeError(
                    f"LibreOffice 转换失败：\n{e.stderr.strip()}"
                ) from e

            # 2. 找到生成的 .docx
            generated = list(work.glob("*.docx"))
            if not generated:
                raise RuntimeError("LibreOffice 未生成 .docx 文件")

            # 3. 用 DocxConverter 转 HTML
            docx_converter = DocxConverter()
            docx_converter.convert(generated[0], output_path)


def _find_soffice() -> str:
    """查找 soffice.exe；找不到则抛出异常附安装指引。"""
    exe = shutil.which("soffice") or shutil.which("soffice.exe")
    if exe is None:
        print(
            ".doc 转换需要 LibreOffice。\n"
            "下载地址：https://www.libreoffice.org/download/\n"
            "安装后请确保 soffice.exe 在 PATH 中，或程序能自动找到。",
            file=sys.stderr,
        )
        raise FileNotFoundError("未找到 LibreOffice (soffice.exe)")
    return exe
