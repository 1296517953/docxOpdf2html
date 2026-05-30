"""PDF → HTML：通过 PyMuPDF (fitz) 内置实现。

文字块绝对定位还原，自动检测并渲染表格，
图片提取保存到 _files/ 目录。"""

from pathlib import Path
import fitz

from .base import Converter
from .utils import (
    esc,
    pt_to_px,
    save_media,
)


class PdfConverter(Converter):
    """使用 PyMuPDF 将 PDF 转换为 HTML。

    文字、表格、图片均按原始位置渲染。
    """

    def convert(self, input_path: Path, output_path: Path) -> None:
        self._output_path = output_path
        doc = fitz.open(str(input_path))
        pages_html = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            pages_html.append(self._render_page(page, doc, page_num + 1))

        doc.close()

        body = "\n".join(pages_html)
        full_html = _TEMPLATE.format(
            title=input_path.stem, body=body, page_count=len(pages_html))
        output_path.write_text(full_html, encoding="utf-8")

    # ── 单页渲染 ────────────────────────────────────────────────

    def _render_page(self, page, doc, page_num: int) -> str:
        pw = pt_to_px(page.rect.width)
        ph = pt_to_px(page.rect.height)

        # 1. 表格检测（优先处理，确定需要排除的文字区域）
        table_parts, table_bboxes = self._render_page_tables(page)

        # 2. 文字（跳过已落入表格区域的 span）
        text_parts = self._render_page_text(page, table_bboxes)

        # 3. 图片
        img_parts = self._render_page_images(page, doc)

        # 4. 内部链接（目录跳转等）
        link_parts = self._render_page_links(page)

        inner = "".join(table_parts) + "".join(text_parts) + "".join(img_parts) + "".join(link_parts)
        return (
            f"<section class='pdf-page' id='page-{page_num}' "
            f"style='position:relative;width:{pw:.0f}px;height:{ph:.0f}px'>"
            f"{inner}"
            f"<span class='page-num'>{page_num}</span>"
            f"</section>"
        )

    # ── 表格检测与渲染 ──────────────────────────────────────────

    def _render_page_tables(self, page) -> tuple[list, list]:
        """检测页面上的表格，渲染为绝对定位的 HTML <table>。

        返回 (table_html_list, table_bbox_list)。
        """
        parts = []
        bboxes = []
        try:
            finder = page.find_tables()
        except Exception:
            return parts, bboxes

        if finder is None:
            return parts, bboxes

        for table in finder.tables:
            tb = table.bbox  # (x0, y0, x1, y1) in pt
            bboxes.append(tb)

            left = pt_to_px(tb[0])
            top = pt_to_px(tb[1])

            # 提取表格数据（每个 cell 的文本和行列位置）
            cells = table.extract()  # list of lists of strings

            rows_html = []
            for row_cells in cells:
                cells_html = "".join(
                    f"<td>{esc(c)}</td>" if c else "<td></td>"
                    for c in row_cells
                )
                rows_html.append(f"<tr>{cells_html}</tr>")

            parts.append(
                f"<table class='pdf-table' "
                f"style='position:absolute;left:{left:.1f}px;top:{top:.1f}px'>"
                f"{''.join(rows_html)}</table>"
            )

        return parts, bboxes

    # ── 文字渲染（跳过表格区域）─────────────────────────────────

    def _render_page_text(self, page, table_bboxes: list) -> str:
        """渲染页面文字，跳过落入表格区域的 span。"""
        parts = []
        text_dict = page.get_text("dict")
        for block in text_dict.get("blocks", []):
            if block["type"] != 0:  # 只处理文本块
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    if self._inside_any(span["bbox"], table_bboxes):
                        continue

                    bbox = span["bbox"]
                    left = pt_to_px(bbox[0])
                    top = pt_to_px(bbox[1])
                    size = span["size"]
                    font = span.get("font", "sans-serif")
                    color_int = span.get("color", 0)
                    color = f"#{color_int:06x}" if color_int else "#000"
                    flags = span.get("flags", 0)

                    styles = [
                        f"position:absolute;left:{left:.1f}px;top:{top:.1f}px",
                        f"font-size:{pt_to_px(size):.1f}px",
                        f"font-family:'{font}',sans-serif",
                        f"color:{color}",
                        "white-space:nowrap",
                    ]
                    if flags & 2: styles.append("font-weight:bold")
                    if flags & 1: styles.append("font-style:italic")

                    text = esc(span["text"])
                    parts.append(
                        f"<span style='{'; '.join(styles)}'>{text}</span>")
        return "".join(parts)

    @staticmethod
    def _inside_any(span_bbox, table_bboxes: list) -> bool:
        """检查 span bbox 是否落入任意表格区域内（留少量容差）。"""
        if not table_bboxes:
            return False
        sx0, sy0, sx1, sy1 = span_bbox
        for tb in table_bboxes:
            # span 完全在表格内则跳过
            if (sx0 >= tb[0] - 3 and sy0 >= tb[1] - 3 and
                sx1 <= tb[2] + 3 and sy1 <= tb[3] + 3):
                return True
        return False

    # ── 内部链接（目录跳转等）───────────────────────────────────

    def _render_page_links(self, page) -> list:
        """扫描页面上所有内部跳转链接，渲染为绝对定位的 <a> 标签。

        PDF 的 TOC / 目录通过 link annotations 实现，
        每个链接包含源矩形区域和目标页码。
        """
        parts = []
        for link in page.get_links():
            kind = link.get("kind", 0)
            # LINK_GOTO=1 (页面跳转), LINK_NAMED=4 (命名目标)
            if kind not in (1, 4):
                continue
            target_page = link.get("page", -1)
            if target_page < 0:
                continue

            bbox = link.get("from")
            if bbox is None:
                continue

            left = pt_to_px(bbox[0])
            top = pt_to_px(bbox[1])
            w = pt_to_px(bbox[2] - bbox[0])
            h = pt_to_px(bbox[3] - bbox[1])

            # HTML 页码从 1 开始，PDF 内部从 0 开始
            target_id = f"page-{target_page + 1}"

            parts.append(
                f"<a href='#{target_id}' "
                f"style='position:absolute;left:{left:.1f}px;top:{top:.1f}px;"
                f"width:{w:.1f}px;height:{h:.1f}px;z-index:3'></a>"
            )
        return parts

    # ── 图片 ────────────────────────────────────────────────────

    def _render_page_images(self, page, doc) -> list:
        parts = []
        for img_info in page.get_image_info(xrefs=True):
            xref = img_info.get("xref", 0)
            bbox = img_info.get("bbox")
            if not xref or not bbox:
                continue
            try:
                base = doc.extract_image(xref)
                blob = base["image"]
                ext = base.get("ext", "png")
            except Exception:
                continue

            rel_path = save_media(self._output_path, blob, ext)
            left = pt_to_px(bbox[0])
            top = pt_to_px(bbox[1])
            w = pt_to_px(bbox[2] - bbox[0])
            h = pt_to_px(bbox[3] - bbox[1])

            parts.append(
                f"<img src='{rel_path}' "
                f"style='position:absolute;left:{left:.1f}px;top:{top:.1f}px;"
                f"width:{w:.1f}px;height:{h:.1f}px' />"
            )
        return parts


# ── PDF 输出模板 ───────────────────────────────────────────────────

_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #666;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    padding: 16px 0;
    font-family: sans-serif;
  }}
  .pdf-page {{
    background: #fff;
    box-shadow: 0 2px 16px rgba(0,0,0,0.2);
    overflow: hidden;
    flex-shrink: 0;
  }}
  .pdf-table {{
    border-collapse: collapse;
    z-index: 2;
  }}
  .pdf-table td {{
    border: 1px solid #999;
    padding: 4px 8px;
    vertical-align: middle;
    font-size: 13px;
    background: #fff;
  }}
  .page-num {{
    position: absolute;
    bottom: 8px;
    right: 12px;
    font-size: 10px;
    color: #999;
    pointer-events: none;
  }}
</style>
</head>
<body>
{body}
</body>
</html>"""
