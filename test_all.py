"""综合测试脚本 —— 生成包含全部支持元素的 DOCX/PPTX 并转换。

测试覆盖：
DOCX: 标题 / 文字格式 / 表格 / 图片 / 动图 / 公式(行内+块级) /
      超链接 / 有序&无序列表 / 换行符 / 制表符 / 分页符 / 段落边框
PPTX: 标题页 / 文本框 / 图片 / 表格 / 组合
"""

import io
import struct
import sys
from pathlib import Path

# 确保项目根在 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lxml import etree
from docx import Document
from docx.shared import Pt, Inches, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT

from PIL import Image as PILImage

from converter import DocxConverter, PptxConverter

# ═══════════════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════════════

MATH_NS  = "http://schemas.openxmlformats.org/officeDocument/2006/math"
W_NS     = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS     = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
XML_NS   = "http://www.w3.org/XML/1998/namespace"
TEST_DIR = Path(__file__).resolve().parent / "test_files"


def M(tag: str):
    """创建带 OMML 命名空间的 XML 元素。"""
    return etree.Element(f"{{{MATH_NS}}}{tag}")


def math_run(parent, text: str):
    """向 OMML 父元素添加 <m:r><m:t>text</m:t></m:r>。"""
    r = etree.SubElement(parent, f"{{{MATH_NS}}}r")
    t = etree.SubElement(r, f"{{{MATH_NS}}}t")
    t.text = text
    t.set(f"{{{XML_NS}}}space", "preserve")
    return r


def create_test_image(width=200, height=80, color=(66, 133, 244)):
    """生成 PNG 图片字节。"""
    img = PILImage.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def create_test_gif(width=200, height=80):
    """生成一个简单 GIF（2 帧循环）以验证动图支持。"""
    frames = [
        PILImage.new("RGB", (width, height), (234, 67, 53)),
        PILImage.new("RGB", (width, height), (52, 168, 83)),
    ]
    buf = io.BytesIO()
    frames[0].save(
        buf, format="GIF", save_all=True,
        append_images=frames[1:], duration=500, loop=0)
    return buf.getvalue()


def add_inline_math(paragraph, omath_el):
    """将行内 OMML 公式插入段落。"""
    paragraph._element.append(omath_el)


def add_block_math(doc, omathpara_el, after_paragraph=None):
    """将块级 OMML 公式插入文档 body，默认插入到 after_paragraph 之后。"""
    if after_paragraph is not None:
        body = doc.element.body
        idx = list(body).index(after_paragraph._element) + 1
        body.insert(idx, omathpara_el)
    else:
        doc.element.body.append(omathpara_el)


def add_hyperlink(doc, paragraph, url: str, text: str):
    """在段落后添加一个超链接元素（作为独立块）。"""
    rId = doc.part.relate_to(url, RT.HYPERLINK, is_external=True)
    hl = etree.Element(f"{{{W_NS}}}hyperlink")
    hl.set(f"{{{R_NS}}}id", rId)
    r = etree.SubElement(hl, f"{{{W_NS}}}r")
    rPr = etree.SubElement(r, f"{{{W_NS}}}rPr")
    c = etree.SubElement(rPr, f"{{{W_NS}}}color")
    c.set(f"{{{W_NS}}}val", "1a0dab")
    u = etree.SubElement(rPr, f"{{{W_NS}}}u")
    u.set(f"{{{W_NS}}}val", "single")
    sz = etree.SubElement(rPr, f"{{{W_NS}}}sz")
    sz.set(f"{{{W_NS}}}val", "24")
    t = etree.SubElement(r, f"{{{W_NS}}}t")
    t.text = text
    t.set(f"{{{XML_NS}}}space", "preserve")
    # 插在 paragraph 在 body 中的位置之后
    body = doc.element.body
    body.insert(list(body).index(paragraph._element) + 1, hl)


# ═══════════════════════════════════════════════════════════════════════
# 构建 DOCX
# ═══════════════════════════════════════════════════════════════════════

def build_docx():
    doc = Document()

    # ── 标题 ────────────────────────────────────────────────────
    doc.add_heading("综合测试文档", level=1)
    doc.add_paragraph("本文档覆盖转换器支持的 DOCX 全部元素类型。")

    # ── h2 ~ h6 ─────────────────────────────────────────────────
    for i in range(2, 7):
        doc.add_heading(f"这是 H{i} 标题", level=i)

    # ── 文字格式 ────────────────────────────────────────────────
    doc.add_heading("文字格式", level=2)

    p = doc.add_paragraph()
    p.add_run("粗体").bold = True
    p.add_run(" · ")
    p.add_run("斜体").italic = True
    p.add_run(" · ")
    p.add_run("下划线").underline = True
    p.add_run(" · ")
    p.add_run("粗体+斜体+下划线").bold = True
    run = p.add_run(" combined")
    run.bold = True
    run.italic = True
    run.underline = True

    # 颜色 & 字号
    p = doc.add_paragraph()
    r = p.add_run("红色 18pt 文字")
    r.font.color.rgb = RGBColor(0xE0, 0x00, 0x00)
    r.font.size = Pt(18)
    p.add_run("  |  ")
    r = p.add_run("蓝色 Courier")
    r.font.color.rgb = RGBColor(0x00, 0x70, 0xFF)
    r.font.name = "Courier New"

    # 高亮
    p = doc.add_paragraph()
    r = p.add_run("这段文字有黄色高亮背景")
    r.font.highlight_color = 7  # YELLOW in WD_COLOR_INDEX

    # 删除线
    p = doc.add_paragraph()
    r = p.add_run("这段文字有删除线")
    # 删除线需通过 XML 设置
    rPr = r._element.find(f"{{{W_NS}}}rPr")
    if rPr is None:
        rPr = etree.SubElement(r._element, f"{{{W_NS}}}rPr")
        r._element.insert(0, rPr)
    strike = etree.SubElement(rPr, f"{{{W_NS}}}strike")
    strike.set(f"{{{W_NS}}}val", "true")

    # ── 列表 ────────────────────────────────────────────────────
    doc.add_heading("列表", level=2)
    doc.add_paragraph("无序列表（List Bullet）：")
    for item in ["苹果", "香蕉", "橙子", "葡萄"]:
        doc.add_paragraph(item, style="List Bullet")

    doc.add_paragraph("有序列表（List Number）：")
    for item in ["第一步：准备材料", "第二步：混合搅拌", "第三步：烘烤 30 分钟", "第四步：冷却完成"]:
        doc.add_paragraph(item, style="List Number")

    # ── 表格 ────────────────────────────────────────────────────
    doc.add_heading("表格", level=2)
    table = doc.add_table(rows=4, cols=3, style="Table Grid")
    headers = ["名称", "数量", "单价"]
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        for p in cell.paragraphs:
            for r in p.runs:
                r.bold = True
    data = [("Widget A", "100", "$12.00"),
            ("Widget B", "50",  "$8.50"),
            ("Widget C", "200", "$3.25")]
    for row_idx, (name, qty, price) in enumerate(data, start=1):
        table.rows[row_idx].cells[0].text = name
        table.rows[row_idx].cells[1].text = qty
        table.rows[row_idx].cells[2].text = price

    # ── 图片 ────────────────────────────────────────────────────
    doc.add_heading("图片", level=2)

    p = doc.add_paragraph()
    p.add_run("以下是一张蓝色内联图片 → ")
    png_bytes = create_test_image(200, 60, (66, 133, 244))
    png_path = TEST_DIR / "_test_img.png"
    png_path.parent.mkdir(parents=True, exist_ok=True)
    png_path.write_bytes(png_bytes)
    run = p.add_run()
    run.add_picture(str(png_path), width=Inches(2.0))
    p.add_run(" ← 图片结束，文字继续。")

    # ── 动图 ────────────────────────────────────────────────────
    doc.add_heading("动图 (GIF)", level=2)
    p = doc.add_paragraph()
    p.add_run("以下是一张 GIF 动图 → ")
    gif_bytes = create_test_gif(200, 60)
    gif_path = TEST_DIR / "_test_anim.gif"
    gif_path.write_bytes(gif_bytes)
    run = p.add_run()
    run.add_picture(str(gif_path), width=Inches(2.0))
    p.add_run(" ← 动图结束。在浏览器中应自动播放。")

    # ── 换行符 & 制表符 ────────────────────────────────────────
    doc.add_heading("换行符 / 制表符", level=2)
    p = doc.add_paragraph()
    p.add_run("第一行")
    run = p.add_run()
    run._element.append(etree.Element(f"{{{W_NS}}}br"))
    p.add_run("这是换行后的文字")
    p2 = doc.add_paragraph()
    p2.add_run("列A")
    run = p2.add_run()
    run._element.append(etree.Element(f"{{{W_NS}}}tab"))
    p2.add_run("列B")
    run = p2.add_run()
    run._element.append(etree.Element(f"{{{W_NS}}}tab"))
    p2.add_run("列C")

    # ── 超链接 ──────────────────────────────────────────────────
    doc.add_heading("超链接", level=2)
    ref_p = doc.add_paragraph("（超链接在下一行）")
    add_hyperlink(doc, ref_p, "https://www.example.com", "点此访问 Example.com")

    # ── 公式 ────────────────────────────────────────────────────
    doc.add_heading("公式", level=2)

    # 行内公式：E = mc²
    p = doc.add_paragraph("行内公式示例：")
    omath = M("oMath")
    math_run(omath, "E")
    math_run(omath, "=")
    math_run(omath, "m")
    ssup = M("sSup")
    e = M("e"); math_run(e, "c"); ssup.append(e)
    sup = M("sup"); math_run(sup, "2"); ssup.append(sup)
    omath.append(ssup)
    add_inline_math(p, omath)
    p.add_run(" ，文字与公式混排。")

    # 行内分式：(a+b)/(c+d)
    p = doc.add_paragraph("行内分式：")
    omath2 = M("oMath")
    frac = M("f")
    num = M("num"); math_run(num, "a+b"); frac.append(num)
    den = M("den"); math_run(den, "c+d"); frac.append(den)
    omath2.append(frac)
    add_inline_math(p, omath2)
    p.add_run(" 。")

    # 行内根式：∛x
    p = doc.add_paragraph("行内立方根：")
    omath3 = M("oMath")
    rad = M("rad")
    ee = M("e"); math_run(ee, "x"); rad.append(ee)
    deg = M("deg"); math_run(deg, "3"); rad.append(deg)
    omath3.append(rad)
    add_inline_math(p, omath3)
    p.add_run(" 。")

    # 块级公式：一元二次方程求根公式
    p = doc.add_paragraph("块级公式（独占一行）：")
    omathpara = M("oMathPara")
    omath_b = M("oMath")
    math_run(omath_b, "x")
    math_run(omath_b, "=")
    # 分式
    frac2 = M("f")
    num2 = M("num")
    math_run(num2, "-b")
    # ± 符号
    sym_run = M("r"); sym_t = M("t"); sym_t.text = "±"; sym_t.set(f"{{{XML_NS}}}space", "preserve")
    sym_run.append(sym_t)
    num2.append(sym_run)
    # 根式
    rad2 = M("rad")
    e2 = M("e")
    # b² - 4ac
    sup_b = M("sSup"); e_b = M("e"); math_run(e_b, "b"); sup_b.append(e_b)
    sup2_b = M("sup"); math_run(sup2_b, "2"); sup_b.append(sup2_b)
    e2.append(sup_b)
    math_run(e2, "-4ac")
    rad2.append(e2)
    num2.append(rad2)
    frac2.append(num2)
    den2 = M("den"); math_run(den2, "2a"); frac2.append(den2)
    omath_b.append(frac2)
    omathpara.append(omath_b)
    add_block_math(doc, omathpara, after_paragraph=p)

    # ── 分页符 / 分隔线 ──────────────────────────────────────────
    doc.add_heading("分页符 / 分隔线", level=2)
    p = doc.add_paragraph("这页内容之后有分页符。")
    run = p.add_run()
    br_el = etree.SubElement(run._element, f"{{{W_NS}}}br")
    br_el.set(f"{{{W_NS}}}type", "page")
    doc.add_paragraph("分页符之后的内容。")

    # 带底部边框的段落（转为 <hr>）
    p_bdr = doc.add_paragraph("这条线上方有边框分隔线。")
    pPr = p_bdr._element.find(f"{{{W_NS}}}pPr")
    if pPr is None:
        pPr = etree.SubElement(p_bdr._element, f"{{{W_NS}}}pPr")
        p_bdr._element.insert(0, pPr)
    pBdr = etree.SubElement(pPr, f"{{{W_NS}}}pBdr")
    bottom = etree.SubElement(pBdr, f"{{{W_NS}}}bottom")
    bottom.set(f"{{{W_NS}}}val", "single")
    bottom.set(f"{{{W_NS}}}sz", "12")
    bottom.set(f"{{{W_NS}}}color", "888888")
    doc.add_paragraph("边框线下方的段落。")

    # 保存
    docx_path = TEST_DIR / "test_docx_all.docx"
    doc.save(str(docx_path))
    print(f"[生成] {docx_path}")
    return docx_path


# ═══════════════════════════════════════════════════════════════════════
# 构建 PPTX
# ═══════════════════════════════════════════════════════════════════════

def build_pptx():
    from pptx import Presentation
    from pptx.util import Inches, Pt, Emu
    from pptx.enum.text import PP_ALIGN
    from pptx.dml.color import RGBColor as PptRGB

    prs = Presentation()
    prs.slide_width  = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # 标题页
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    left = Inches(1); top = Inches(2); w = Inches(11); h = Inches(1.5)
    txBox = slide.shapes.add_textbox(left, top, w, h)
    tf = txBox.text_frame
    tf.paragraphs[0].text = "PPT 综合测试"
    tf.paragraphs[0].font.size = Pt(44)
    tf.paragraphs[0].font.bold = True
    tf.paragraphs[0].font.color.rgb = PptRGB(0x1a, 0x23, 0x34)
    tf.paragraphs[0].alignment = PP_ALIGN.CENTER

    # 文本格式页
    slide2 = prs.slides.add_slide(prs.slide_layouts[6])
    txBox2 = slide2.shapes.add_textbox(Inches(1), Inches(1), Inches(11), Inches(5))
    tf2 = txBox2.text_frame
    p = tf2.paragraphs[0]; p.text = "文字格式测试"; p.font.size = Pt(36); p.font.bold = True
    p2 = tf2.add_paragraph(); p2.text = ""
    p3 = tf2.add_paragraph()
    r = p3.add_run(); r.text = "粗体"; r.font.bold = True
    p3.add_run().text = " · "
    r = p3.add_run(); r.text = "斜体"; r.font.italic = True
    p3.add_run().text = " · "
    r = p3.add_run(); r.text = "下划线"; r.font.underline = True
    p3.add_run().text = " · "
    r = p3.add_run(); r.text = "红色文字"; r.font.color.rgb = PptRGB(0xE0, 0x00, 0x00)

    # 图片页
    slide3 = prs.slides.add_slide(prs.slide_layouts[6])
    png_bytes = create_test_image(400, 200, (251, 188, 5))
    png_path = TEST_DIR / "_test_ppt_img.png"
    png_path.write_bytes(png_bytes)
    slide3.shapes.add_picture(str(png_path), Inches(3), Inches(2), Inches(7), Inches(3.5))
    txBox3 = slide3.shapes.add_textbox(Inches(3), Inches(5.8), Inches(7), Inches(0.8))
    tf3 = txBox3.text_frame
    tf3.paragraphs[0].text = "图片测试"
    tf3.paragraphs[0].font.size = Pt(20)
    tf3.paragraphs[0].alignment = PP_ALIGN.CENTER

    # 表格页
    slide4 = prs.slides.add_slide(prs.slide_layouts[6])
    rows, cols = 4, 3
    tbl_shape = slide4.shapes.add_table(rows, cols, Inches(2), Inches(1.5), Inches(9), Inches(4))
    tbl = tbl_shape.table
    hdr_data = ["项目", "状态", "备注"]
    for ci, h in enumerate(hdr_data):
        tbl.cell(0, ci).text = h
    row_data = [("功能A", "✅ 完成", ""), ("功能B", "🔄 进行中", "预计下周"), ("功能C", "⏳ 待开始", "")]
    for ri, (a, b, c) in enumerate(row_data, start=1):
        tbl.cell(ri, 0).text = a
        tbl.cell(ri, 1).text = b
        tbl.cell(ri, 2).text = c

    pptx_path = TEST_DIR / "test_pptx.pptx"
    prs.save(str(pptx_path))
    print(f"[生成] {pptx_path}")
    return pptx_path


# ═══════════════════════════════════════════════════════════════════════
# 执行测试
# ═══════════════════════════════════════════════════════════════════════

def run_tests():
    TEST_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  生成测试文件 …")
    print("=" * 60)

    docx_path = build_docx()
    pptx_path = build_pptx()

    print()
    print("=" * 60)
    print("  开始转换 …")
    print("=" * 60)

    # DOCX → HTML
    print()
    docx_out = TEST_DIR / "test_docx_all.html"
    converter = DocxConverter()
    converter.convert(docx_path.resolve(), docx_out.resolve())
    docx_size = docx_out.stat().st_size
    print(f"  DOCX → HTML: {docx_out} ({docx_size / 1024:.1f} KB)")

    # PPTX → HTML
    print()
    pptx_out = TEST_DIR / "test_pptx.html"
    converter2 = PptxConverter()
    converter2.convert(pptx_path.resolve(), pptx_out.resolve())
    pptx_size = pptx_out.stat().st_size
    print(f"  PPTX → HTML: {pptx_out} ({pptx_size / 1024:.1f} KB)")

    print()
    print("=" * 60)
    print("  转换完成，检查以下文件：")
    print(f"    {docx_out}")
    print(f"    {pptx_out}")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
