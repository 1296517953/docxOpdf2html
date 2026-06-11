---
name: pandoc-gitbook-pipeline
description: 使用 pandoc + Python 将 DOCX 转为带目录导航的静态 HTML 站点的完整经验
---

# pandoc + Python 静态站点生成流水线

## 架构

```
.docx 源文件
  │  pandoc --from docx --to gfm
  ▼
.md + media/ 图片
  │  build_site.py (markdown + Jinja2)
  ▼
静态 HTML 站点（侧栏导航 + 全文搜索 + 正文目录跳转）
```

## 核心组件

| 文件 | 职责 |
|------|------|
| `scripts/build_site.py` | 站点生成器：SUMMARY.md → 导航、md → HTML、静态资源 |
| `book.json` | 站点元数据（标题、语言） |
| `content/SUMMARY.md` | 目录结构（可自动生成或手动编辑） |

## 关键踩坑记录

### 1. pandoc 图片路径

**问题**：pandoc 从项目根目录运行时，`--extract-media content/media` 会导致图片路径变成 `content/media/media/image.png`（双层嵌套）。

**解决**：从 `content/` 目录内运行 pandoc，使用 `--extract-media=.`。图片引用变为 `./media/image.png`。

```bash
cd content
pandoc ../input/doc.docx -o output.md --extract-media=. --from docx --to gfm
```

### 2. pandoc TOC 自引用链接

**问题**：Word 自动生成的目录在 pandoc 转换后变成自引用格式：
```markdown
[产品概述 [- 1 -](#产品概述)](#产品概述)
```
页面号的括号 `[- 1 -]` 被 markdown 解析为嵌套链接，导致跳转失效。

**解决**：正则清洗为单层链接，将 `[- N -]` 替换为 `(-N-)` 避免二次解析：
```python
re.sub(r'\[(.+)\]\(#([^)]+)\)\]\(#\2\)', ...)
body = re.sub(r'\[-\s*(\d+)\s*-', r'(-\1-)', body)
```

### 3. pandoc vs markdown 库的去重后缀不一致

**问题**：pandoc 对重复标题生成 `-1`, `-2` 后缀（如 `#功能简介-1`），但 Python markdown 库的 toc 扩展生成 `_1`, `_2` 后缀（如 `id="功能简介_1"`）。正文目录链接和标题锚点不匹配。

**解决**：在清洗 TOC 链接时，将 pandoc 的 `-N` 统一转换为 `_N`：
```python
anchor = re.sub(r'-(\d+)$', r'_\1', anchor)
```

### 4. 中文标题的 slugify

**问题**：markdown 库默认 slugify 会删除所有非 ASCII 字符，中文标题变成空字符串，生成 `_1`, `_2` 等无意义 ID。

**解决**：自定义 slugify 函数，保留中文字符：
```python
def _slugify(text, sep=None):
    text = re.sub(r'[^\w\s一-鿿\-]', '', text)  # 保留中文
    text = re.sub(r'[\s_]+', '-', text.strip())
    return text.strip('-').lower() or '_'
```

### 5. 侧栏/正文目录/标题锚点三者对齐

**问题**：三个地方的锚点需要完全一致才能正确跳转：
- 侧栏导航（SUMMARY.md 生成）
- 正文内目录（pandoc 的 TOC）
- 标题元素（markdown 的 id 属性）

**解决**：统一使用 `_slugify()` 生成锚点，在 `_generate_summary` 和 `_fix_toc_link` 中跟踪 `used_anchors` 并为重复项添加 `_N` 后缀。

### 6. 标题序号添加时机

**问题**：如果在 markdown 阶段添加序号（如 `一、产品概述`），会改变锚点 ID（从 `#产品概述` 变成 `#一产品概述`），导致 pandoc 生成的 TOC 链接失效。

**解决**：在 HTML 后处理阶段添加序号（`_add_heading_numbers_html`），保持 markdown 的 ID 不变。侧栏 `_generate_summary` 同步使用相同的序号逻辑生成显示文本，但用原始锚点。

### 7. Word 自动编号丢失

**问题**：Word 的多级列表编号（如 "一、""1." "1.1"）不在段落文本中，而是通过 `w:numPr` 属性控制。pandoc 转换后编号丢失。

**解决**：在 HTML 后处理中按层级重建序号——H1 用中文数字（一、二、三），H2/H3 用阿拉伯数字层级（1.1, 1.2）。

### 8. 空标题污染

**问题**：pandoc 可能产生空内容的标题行（如单独的 `#`），导致侧栏和正文出现无意义条目。

**解决**：在 `_add_heading_numbers_html` 和 `_generate_summary` 中跳过空文本的标题。

## 文件结构约定

```
project/
  input/               ← 原始 .docx（不入库）
  content/             ← pandoc 产物（不入库）
    media/             ← 提取的图片
  output/              ← 最终 HTML 站点（不入库）
    static/            ← CSS/JS
    media/             ← 从 content/media 复制
  scripts/
    pipeline.ps1       ← 一键流水线
    build_site.py      ← Python 站点生成器
  book.json            ← 站点配置
```

## 依赖

- **pandoc**：文档转换（Windows 二进制 ~50MB 或系统安装）
- **Python**：`markdown`, `Pygments`（可选代码高亮）
- **无 Node.js 依赖**：honkit/gitbook 已被 Python 替代
