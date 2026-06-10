"""各转换器共用的工具函数。"""

import base64
import html as _html
import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════
# 文件类型检测
# ═══════════════════════════════════════════════════════════════════════

def detect_format(filepath: Path) -> str:
    """根据文件扩展名（忽略大小写）返回格式标识：'pdf' / 'docx'。"""
    ext = filepath.suffix.lower()
    mapping = {".pdf": "pdf", ".docx": "docx", ".doc": "doc"}
    if ext not in mapping:
        raise ValueError(f"不支持的文件格式: {ext}")
    return mapping[ext]


# ═══════════════════════════════════════════════════════════════════════
# 临时目录管理
# ═══════════════════════════════════════════════════════════════════════

@contextmanager
def temp_dir(prefix: str = "htmlgen_"):
    """上下文管理器：创建临时目录，退出时自动清理。

    用法：
        with temp_dir() as work:
            # work 是一个 Path 对象
            ...
    """
    path = Path(tempfile.mkdtemp(prefix=prefix))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════════════
# 媒体文件落盘（图片/视频保存为独立文件，HTML 以相对路径引用）
# ═══════════════════════════════════════════════════════════════════════

# 全局计数器，确保同一输出目录下的媒体文件不重名
_media_counters: dict[str, int] = {}


def media_dir(output_path: Path) -> Path:
    """返回输出 HTML 对应的 _files 媒体目录，若不存在则创建。"""
    d = output_path.parent / f"{output_path.stem}_files"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_media(output_path: Path, blob: bytes, ext: str = "png") -> Path:
    """将媒体二进制保存到 _files/ 目录下，返回 HTML 可引用的相对路径。

    返回值示例：report_files/img_001.png
    """
    md = media_dir(output_path)
    key = str(output_path.resolve())
    if key not in _media_counters:
        _media_counters[key] = 1
    while True:
        filename = f"media_{_media_counters[key]:04d}.{ext}"
        filepath = md / filename
        if not filepath.exists():
            break
        _media_counters[key] += 1
    filepath.write_bytes(blob)
    # 返回 HTML 可用的相对路径（正斜杠）
    return (Path(f"{output_path.stem}_files") / filename).as_posix()


# ═══════════════════════════════════════════════════════════════════════
# 图片内联编码（保留兼容）
# ═══════════════════════════════════════════════════════════════════════

def image_to_data_uri(image_bytes: bytes, ext: str = "png") -> str:
    """将图片二进制编码为 base64 data URI，可直接嵌入 <img src="...">。

    参数：
        image_bytes: 图片原始字节
        ext: 图片扩展名（如 'png' / 'jpeg'）
    返回：
        data:image/<ext>;base64,... 格式的字符串
    """
    b64 = base64.b64encode(image_bytes).decode("ascii")
    return f"data:image/{ext};base64,{b64}"


def guess_image_ext(blob: bytes) -> str:
    """通过文件头魔数（magic bytes）猜测图片格式。

    参数：
        blob: 图片字节数据
    返回：
        扩展名字符串：'png' / 'jpeg' / 'gif' / 'webp'（默认 'png'）
    """
    if blob[:4] == b"\x89PNG":
        return "png"
    if blob[:2] == b"\xff\xd8":
        return "jpeg"
    if blob[:3] == b"GIF":
        return "gif"
    if blob[:4] in (b"RIFF", b"WEBP"):
        return "webp"
    return "png"


# ═══════════════════════════════════════════════════════════════════════
# 单位换算
# ═══════════════════════════════════════════════════════════════════════

def emu_to_px(emu: int, dpi: int = 96) -> float:
    """EMU（English Metric Units，Office 文档内部单位）→ CSS 像素。

    换算关系：1 英寸 = 914400 EMU = dpi 像素
    """
    return emu * dpi / 914400


def pt_to_px(pt: float, dpi: int = 96) -> float:
    """磅（point）→ CSS 像素。

    换算关系：1 英寸 = 72 pt = dpi 像素
    """
    return pt * dpi / 72


# ═══════════════════════════════════════════════════════════════════════
# 颜色转换
# ═══════════════════════════════════════════════════════════════════════

def rgb_to_hex(rgb) -> str:
    """将 python-docx / python-pptx 的 RGBColor 对象转为 CSS 十六进制色值。

    参数：
        rgb: RGBColor 对象或整数值
    返回：
        '#RRGGBB' 格式字符串，解析失败则返回空字符串
    """
    if rgb is None:
        return ""
    try:
        # 如果是整数，直接格式化为 hex；否则尝试字符串表示
        return f"#{rgb:06X}" if isinstance(rgb, int) else str(rgb)
    except Exception:
        return ""


# ═══════════════════════════════════════════════════════════════════════
# 文本安全处理
# ═══════════════════════════════════════════════════════════════════════

def esc(text: str) -> str:
    """对字符串做 HTML 转义，防止 < > & 等字符被浏览器解析为标签。"""
    return _html.escape(str(text))


# ═══════════════════════════════════════════════════════════════════════
# 字体栈归一化
# ═══════════════════════════════════════════════════════════════════════

# 三类字体的 fallback 栈，确保在任意操作系统都有合适的降级字体
_SANS_FALLBACK = (
    "'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
)
_SERIF_FALLBACK = (
    "Georgia, 'Times New Roman', serif"
)
_MONO_FALLBACK = (
    "'Cascadia Code', 'Fira Code', 'Courier New', monospace"
)

def normalize_font(name: Optional[str]) -> str:
    """在字体名称后追加合理的 fallback 字体栈。

    参数：
        name: 原始字体名（可为 None）
    返回：
        带引号包裹的字体名 + fallback 栈的 CSS font-family 值
    """
    if not name:
        return _SANS_FALLBACK
    name_lower = name.lower()
    # 衬线字体关键字 → 追加衬线 fallback
    if any(k in name_lower for k in ("times", "garamond", "georgia")):
        return f"'{name}', {_SERIF_FALLBACK}"
    # 等宽字体关键字 → 追加等宽 fallback
    if any(k in name_lower for k in ("consolas", "courier", "monaco", "mono", "code")):
        return f"'{name}', {_MONO_FALLBACK}"
    # 默认走无衬线 fallback
    return f"'{name}', {_SANS_FALLBACK}"
