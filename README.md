# htmlGENERATOR [ARCHIVED]

> ⚠️ **本项目已封存，不再维护。** 详见 [中文说明](#中文说明) 底部。

**PDF / DOCX → self-contained HTML converter with near-zero formatting loss.**

Turn your documents into browser-ready HTML files. Images and videos are saved as external files, equations are rendered with MathJax, internal links (TOC) navigate within the page.

---

## Quick Start

1. Double-click `htmlGENERATOR.exe`
2. Drag a `.pdf` or `.docx` file into the window, or click Browse
3. Output path is auto-filled next to the source file — change if needed
4. Click **Start**, then **Open in Browser**

No Python. No dependencies. Just the exe.

### System Requirements

| OS | Status |
|----|:------:|
| Windows 11 | ✅ Supported |
| Windows 10 | ✅ Supported |
| Windows 7 | ❌ Not supported (Python 3.14 runtime) |

---

## Features

| Format | Engine | Output |
|--------|--------|--------|
| **DOCX** | python-docx | HTML + `_files/` directory (images, videos) |
| **PDF** | PyMuPDF (fitz) | Page-based HTML with positioned text, tables, images |

### DOCX elements preserved

Text formatting (bold, italic, underline, strikethrough, color, size, font, highlight),
headings H1–H6, tables, inline images, animated GIFs, hyperlinks,
ordered / unordered lists, line breaks, tabs, symbols, page breaks,
paragraph borders, OMML equations (fractions, radicals, superscripts, matrices, integrals).

### PDF elements preserved

Positioned text (font, size, color, bold/italic), embedded images,
**auto-detected tables**, internal link navigation (TOC / page jumps).

---

## Usage

### GUI

```
htmlGENERATOR.exe
  Input:  drag & drop file, or click Browse
  Output: auto-filled (same folder as source) or custom path
  Convert → Open in Browser
```

### CLI

```bash
python main.py input.docx                      # → input.html
python main.py input.docx -o output.html       # custom path
python main.py input.pdf --open                # auto-open in browser
```

---

## Output Structure

```
output.html              ← lightweight HTML
output_files/            ← extracted media
  media_0001.png
  media_0002.jpg
```

---

## Project Structure

```
htmlGENERATOR/
  htmlGENERATOR.exe          ← Standalone executable
  gui_app.py                 ← GUI source (tkinter + drag & drop)
  main.py                    ← CLI entry point
  converter/                 ← Python source (editable, no rebuild needed)
    __init__.py              ←   Public API exports
    base.py                  ←   Converter ABC + Jinja2 template loading
    utils.py                 ←   Shared helpers (units, colors, fonts, media)
    pdf_converter.py         ←   PDF → HTML (PyMuPDF, tables, links)
    docx_converter.py        ←   DOCX → HTML (full element support)
  templates/                 ← HTML / CSS / XSL (editable, no rebuild needed)
    base.html                ←   Article layout for DOCX
    slide.html               ←   Slide layout
    omml2mml.xsl             ←   OMML → MathML equation mapping
  requirements.txt           ← Python dependencies (developers only)
  build.ps1                  ← PyInstaller build script (developers only)
  README.md
```

---

## How It Works

### Architecture

```
┌─────────────────────────────────────────────┐
│                 htmlGENERATOR.exe            │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │ DOCX →   │  │ PDF →    │  │ Template  │  │
│  │ HTML     │  │ HTML     │  │ Engine    │  │
│  │ (python- │  │ (PyMuPDF)│  │ (Jinja2)  │  │
│  │  docx)   │  │          │  │           │  │
│  └──────────┘  └──────────┘  └───────────┘  │
│                                              │
│  Python 3.14 runtime + all deps bundled      │
└─────────────────────────────────────────────┘
          │ reads at runtime (no rebuild)
          ▼
┌──────────────────────────────────────┐
│  converter/    templates/            │
│  (editable)    (editable)            │
└──────────────────────────────────────┘
```

### DOCX conversion pipeline

```
.docx (ZIP)
  ├─ document.xml  →  paragraphs, runs, tables, lists
  ├─ styles.xml    →  heading levels, formatting
  ├─ media/        →  images saved to _files/
  ├─ math (OMML)   →  XSLT → MathML → MathJax rendering
  ├─ hyperlinks    →  external: target=_blank, internal (TOC): in-page anchor
  └─ bookmarks     →  id attributes for TOC navigation
```

### PDF conversion pipeline

```
.pdf
  ├─ text dict  →  absolutely-positioned <span> (font, size, color, weight)
  ├─ images     →  extracted to _files/, referenced by <img>
  ├─ tables     →  page.find_tables() → <table class='pdf-table'>
  └─ links      →  page.get_links() → <a href='#page-N'> for internal nav
```

---

## Customization — no rebuild needed

Both `converter/` and `templates/` are external folders. Edit them, restart the exe, changes take effect immediately.

### Modify appearance

| File | Controls |
|------|----------|
| `templates/base.html` | Font, colors, page width, table style (DOCX article layout) |
| `templates/omml2mml.xsl` | OMML → MathML equation conversion rules |

### Modify conversion logic

| File | Responsibility |
|------|---------------|
| `converter/docx_converter.py` | DOCX parsing, element rendering, Word → CSS mapping |
| `converter/pdf_converter.py` | PDF text, table, image, link extraction |
| `converter/utils.py` | Units, colors, fonts, media file saving |

### Add a new format

1. Create `converter/xxx_converter.py`, subclass `Converter`, implement `convert()`
2. Register in `converter/__init__.py` and `gui_app.py`
3. Restart the exe — no rebuild needed

```python
from .base import Converter

class XlsxConverter(Converter):
    def convert(self, input_path, output_path):
        self._output_path = output_path
        body = "<p>Your HTML here</p>"
        html = self.render_template("base.html", body=body, title=input_path.stem)
        output_path.write_text(html, encoding="utf-8")
```

---

## Development

### Install dependencies

```bash
pip install -r requirements.txt
pip install tkinterdnd2
```

### Run from source

```bash
python gui_app.py          # GUI
python main.py input.docx  # CLI
```

### Build standalone exe

```bash
powershell -ExecutionPolicy Bypass -File build.ps1
```

Output: `dist/htmlGENERATOR.exe` (~41 MB). Only required when `gui_app.py` is modified.

---

## Dependencies

| Package | Purpose |
|---------|---------|
| python-docx | DOCX reading |
| PyMuPDF | PDF reading, table detection, link extraction |
| Jinja2 | HTML template rendering |
| Pillow | Image handling |
| lxml | XML parsing, OMML→MathML XSLT |
| tkinterdnd2 | GUI drag & drop |

---

# 中文说明

## htmlGENERATOR — PDF / DOCX → HTML 转换器

将文档转为浏览器可直接打开的 HTML 文件，格式损失极小。
图片/视频保存为独立文件，公式由 MathJax 渲染，目录支持页面内跳转。

### 快速开始

1. 双击 `htmlGENERATOR.exe`
2. 拖入 `.pdf` 或 `.docx` 文件，或点击「选择文件」
3. 输出路径自动填充为源文件同目录同名 .html，可手动修改
4. 点击「开始转换」，完成后「用浏览器打开」

无需 Python，无需安装依赖。

### 系统要求

| 操作系统 | 状态 |
|----------|:----:|
| Windows 11 | ✅ |
| Windows 10 | ✅ |
| Windows 7 | ❌（Python 3.14 运行时限制） |

### 功能

| 格式 | 引擎 | 输出 |
|------|------|------|
| **DOCX** | python-docx | HTML + `_files/` 目录（图片/视频） |
| **PDF** | PyMuPDF | 分页 HTML，文字定位 + 表格检测 + 图片 |

**DOCX 支持**：文字格式、标题、表格、图片/GIF、超链接（外部新标签页/内部锚点跳转）、有序/无序列表、换行/制表/符号、分页符、段落边框、OMML 公式。

**PDF 支持**：文字定位（字号/颜色/粗斜体）、图片提取、**表格自动检测**、**内部链接导航**（目录跳转）。

### 使用方法

**GUI**：双击 exe → 拖拽文件 → 转换 → 浏览器打开。

**CLI**：`python main.py input.docx -o output.html --open`

### 输出结构

```
output.html              ← HTML 文件
output_files/            ← 提取的媒体文件
  media_0001.png
```

### 项目结构

参见上方英文部分。

### 自定义扩展 — 无需重新打包

`converter/` 和 `templates/` 均为外部文件夹，编辑后重启 exe 即生效。

| 修改目标 | 编辑文件 |
|----------|----------|
| 改字体/颜色/页面宽度 | `templates/base.html` |
| 改公式转换规则 | `templates/omml2mml.xsl` |
| 改 DOCX 渲染逻辑 | `converter/docx_converter.py` |
| 改 PDF 提取逻辑 | `converter/pdf_converter.py` |
| 添加新格式 | 新建 `converter/xxx_converter.py`，继承 `Converter`，注册后重启 exe |

### 开发

```bash
pip install -r requirements.txt
pip install tkinterdnd2
python gui_app.py                     # 运行 GUI
powershell -ExecutionPolicy Bypass -File build.ps1  # 打包 exe（~41 MB）
```

仅修改 `gui_app.py` 后才需重新打包。

---

## 封存说明

本项目（htmlGENERATOR）自 2026 年 6 月起封存，不再接收功能更新或维护。

- 源代码保留在 [GitHub](https://github.com/1296517953/docxOpdf2html) 供参考
- `result/htmlGENERATOR.exe` 为最后一个可用版本（PDF / DOCX → HTML）
- 如需扩展，可 fork 后自行开发
