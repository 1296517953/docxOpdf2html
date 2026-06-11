# docx → HTML (pandoc + Python)

**v2.0 — pandoc 统一转换 + Python 站点生成。**

将 Word 文档（.docx）转换为带层级目录导航、全文搜索的静态 HTML 站点。

## 流水线

```
input/*.docx
    │
    ▼  pandoc --from docx --to gfm
    │  提取图片 → media/
content/*.md
    │
    ▼  SUMMARY.md 自动生成（H1-H3 标题 + 层级序号）
    │  build_site.py (Python, 零 Node.js)
    │
    ▼
output/          ← 静态 HTML 站点
  ├─ index.html
  ├─ 文档.html
  ├─ media/      ← 图片
  └─ static/     ← CSS + 搜索 JS
```

## 依赖

```bash
scoop install pandoc          # 转换引擎
pip install markdown          # Python 站点生成
```

## 使用

1. 将 `.docx` 文件放入 `input/`
2. 双击 `build.bat`，或运行 `.\build.ps1`
3. 打开 `output/index.html`

## SUMMARY.md

`SUMMARY.md` 由流水线自动生成，扫描所有 .md 文件的 H1-H3 标题并添加层级序号。
如需自定义目录结构，在 `build_site.py` 阶段 2 和阶段 3 之间手动编辑 `content/SUMMARY.md`。

## 项目结构

```
input/               ← 原始 .docx 文件（不入库）
content/             ← pandoc 输出 + SUMMARY.md（不入库）
output/              ← 最终 HTML 站点（不入库）
scripts/
  pipeline.ps1       ← 完整流水线
book.json            ← gitbook 站点配置
```

## v1 说明

本项目的 v1.0（htmlGENERATOR，python-docx + PyMuPDF 独立 exe）
已封存，代码保留在 git 历史中。
