# docx → HTML (pandoc + gitbook)

**v2.0 — pandoc 统一转换 + gitbook 站点生成。**

将 Word 文档（.docx）转换为带目录导航、全文搜索的静态 HTML 站点。

## 流水线

```
input/*.docx
    │
    ▼  pandoc --from docx --to gfm
    │  提取图片 → media/
content/*.md
    │
    ▼  SUMMARY.md 自动生成（从 H1 标题）
    │  book.json  站点配置
    │
    ▼  honkit build
output/          ← 静态 HTML 站点
```

## 依赖

```bash
scoop install pandoc          # 转换引擎
npm install -g honkit         # gitbook 后继
```

## 使用

1. 将 `.docx` 文件放入 `input/`
2. 运行：`.\scripts\pipeline.ps1`
3. 打开 `output/index.html`

## SUMMARY.md

`SUMMARY.md` 由流水线自动生成，从每个 `.md` 文件的 H1 标题提取条目名。
如需自定义目录结构，在阶段 2 和阶段 3 之间手动编辑 `content/SUMMARY.md`。

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
