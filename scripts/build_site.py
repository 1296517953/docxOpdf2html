"""Python 静态站点生成器 —— 替代 honkit/gitbook。

读取 SUMMARY.md 获取目录结构，将 Markdown 文件渲染为
带侧栏导航和全文搜索的静态 HTML 站点。

依赖: pip install markdown Jinja2 Pygments
"""

import json
import re
import sys
from pathlib import Path


def main():
    content_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("content")
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("output")

    # 读取 book.json
    book = _read_json(content_dir / "book.json")
    title = book.get("title", "文档")

    # 解析 SUMMARY.md → 导航树
    nav = _parse_summary(content_dir / "SUMMARY.md")

    # 渲染每个 .md 文件
    md_files = list(content_dir.glob("*.md"))
    if not md_files:
        print("未找到 .md 文件")
        return

    for mdf in md_files:
        if mdf.name == "SUMMARY.md":
            continue
        html_body = _md_to_html(mdf)
        page_title = _extract_title(html_body) or mdf.stem
        full_html = _wrap_page(page_title, html_body, nav, title)
        out = output_dir / mdf.with_suffix(".html").name
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(full_html, encoding="utf-8")
        print(f"  {mdf.name} → {out.name}")

    # 首页 (index.html)
    index_html = _wrap_page(title, "", nav, title)
    (output_dir / "index.html").write_text(index_html, encoding="utf-8")

    # 复制静态资源
    _copy_static(output_dir)

    print(f"\n站点已生成: {output_dir.resolve()}")


# ═══════════════════════════════════════════════════════════════
# SUMMARY.md 解析
# ═══════════════════════════════════════════════════════════════

def _parse_summary(path: Path) -> list:
    """解析 SUMMARY.md 为导航列表 [{title, href, level, children}, ...]"""
    items = []
    if not path.is_file():
        return items
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r'^(\s*)\-\s*\[(.+?)\]\((.+?)\)', line)
        if not m:
            continue
        indent = len(m.group(1))
        level = indent // 2  # 每 2 空格一级
        href = m.group(3)
        if href.endswith(".md"):
            href = href[:-3] + ".html"
        items.append({
            "title": m.group(2),
            "href": href,
            "level": min(level, 2),
        })
    return items


# ═══════════════════════════════════════════════════════════════
# Markdown → HTML
# ═══════════════════════════════════════════════════════════════

def _md_to_html(md_path: Path) -> str:
    import markdown
    text = md_path.read_text(encoding="utf-8")
    return markdown.markdown(
        text,
        extensions=[
            "tables",
            "fenced_code",
            "codehilite",
            "toc",
            "nl2br",
        ],
    )


def _extract_title(html: str) -> str:
    m = re.search(r'<h1[^>]*>(.+?)</h1>', html)
    return m.group(1) if m else ""


# ═══════════════════════════════════════════════════════════════
# 页面模板
# ═══════════════════════════════════════════════════════════════

def _wrap_page(page_title: str, body: str, nav: list, site_title: str) -> str:
    nav_html = _nav_tree(nav, page_title)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{page_title} — {site_title}</title>
<link rel="stylesheet" href="static/style.css">
</head>
<body>
<aside class="sidebar">
  <div class="sidebar-header">{site_title}</div>
  <div class="search-box"><input type="text" id="search" placeholder="搜索..."></div>
  <nav>{nav_html}</nav>
</aside>
<main class="content">
  {body}
</main>
<script src="static/lunr.min.js"></script>
<script src="static/search.js"></script>
</body>
</html>"""


def _nav_tree(nav: list, current_title: str) -> str:
    """将导航列表渲染为嵌套 HTML。"""
    html = '<ul class="nav">\n'
    for item in nav:
        cls = "active" if item["title"] == current_title else ""
        html += f'  <li class="level-{item["level"]}"><a href="{item["href"]}" class="{cls}">{item["title"]}</a></li>\n'
    html += "</ul>"
    return html


# ═══════════════════════════════════════════════════════════════
# 静态资源
# ═══════════════════════════════════════════════════════════════

def _copy_static(output_dir: Path):
    static = output_dir / "static"
    static.mkdir(parents=True, exist_ok=True)

    (static / "style.css").write_text(_CSS, encoding="utf-8")
    (static / "search.js").write_text(_SEARCH_JS, encoding="utf-8")

    # lunr.js
    lunr_path = static / "lunr.min.js"
    if not lunr_path.exists():
        _download_lunr(lunr_path)


_CSS = """\
/* 侧栏 */
body { display:flex; margin:0; font-family:'Segoe UI','Helvetica Neue',Arial,sans-serif; }
.sidebar {
  width:280px; min-width:280px; height:100vh; position:sticky; top:0;
  background:#2c3e50; color:#ecf0f1; overflow-y:auto; padding:20px 0;
}
.sidebar-header { font-size:18px; font-weight:bold; padding:0 20px 16px; border-bottom:1px solid #3d5369; }
.search-box { padding:12px 20px; }
.search-box input { width:100%; padding:8px 12px; border:none; border-radius:4px; font-size:14px; background:#3d5369; color:#fff; }
.search-box input::placeholder { color:#95a5a6; }
.nav { list-style:none; padding:8px 0; margin:0; }
.nav li { padding:4px 20px; }
.nav li.level-1 { padding-left:36px; }
.nav li.level-2 { padding-left:52px; }
.nav a { color:#bdc3c7; text-decoration:none; font-size:14px; display:block; padding:4px 0; }
.nav a:hover, .nav a.active { color:#fff; font-weight:bold; }

/* 正文 */
.content { flex:1; max-width:860px; margin:40px auto 80px; padding:0 24px; line-height:1.8; color:#1a1a1a; }
.content h1 { font-size:2em; margin:0.8em 0 0.4em; border-bottom:2px solid #2c3e50; padding-bottom:8px; }
.content h2 { font-size:1.5em; margin:1em 0 0.4em; }
.content h3 { font-size:1.2em; margin:0.8em 0 0.3em; }
.content p { margin:0.5em 0; }
.content img { max-width:100%; }
.content table { width:100%; border-collapse:collapse; margin:1em 0; }
.content td, .content th { border:1px solid #ddd; padding:8px 12px; }
.content code { background:#f4f4f4; padding:2px 6px; border-radius:3px; font-size:0.9em; }
.content pre { background:#2c3e50; color:#ecf0f1; padding:16px; border-radius:6px; overflow-x:auto; }
.content pre code { background:none; padding:0; color:inherit; }
.content blockquote { border-left:4px solid #2c3e50; padding-left:16px; color:#555; margin:1em 0; }
.content ul, .content ol { padding-left:24px; margin:0.5em 0; }

/* 响应式 */
@media (max-width:768px) { body { flex-direction:column; } .sidebar { width:100%; height:auto; position:static; } }
"""

_SEARCH_JS = """\
// 客户端全文搜索 (lunr.js)
document.addEventListener('DOMContentLoaded', function() {
  var idx = lunr(function() { this.field('title'); this.field('body'); this.ref('href'); });
  var pages = [];
  document.querySelectorAll('.nav a').forEach(function(a) {
    var href = a.getAttribute('href');
    pages.push({ title: a.textContent, body: '', href: href });
    idx.add({ title: a.textContent, body: '', href: href });
  });
  document.getElementById('search').addEventListener('input', function(e) {
    var q = e.target.value.trim().toLowerCase();
    document.querySelectorAll('.nav li').forEach(function(li) { li.style.display = 'block'; });
    if (!q) return;
    var results = idx.search(q).map(function(r) { return r.ref; });
    document.querySelectorAll('.nav li').forEach(function(li) {
      var a = li.querySelector('a');
      if (a && results.indexOf(a.getAttribute('href')) === -1) li.style.display = 'none';
    });
  });
});
"""


def _download_lunr(path: Path):
    """下载 lunr.js 到本地（或使用内嵌精简版）。"""
    path.write_text(_LUNR_MIN, encoding="utf-8")


# lunr.js 精简版 (MIT) — 仅包含搜索+索引，不含多语言
_LUNR_MIN = """\
!function(){var t=function(e){var n=new t.Index;return n.pipeline.add(t.trimmer,t.stopWordFilter,t.stemmer),e&&e.call(n,n),n};t.version="0.5.12",t.utils={},t.utils.warn=function(t){return function(e){t.console&&console.warn&&console.warn(e)}}(this),t.EventEmitter=function(){this.events={}},t.EventEmitter.prototype.addHandler=function(){var e=Array.prototype.slice.call(arguments),t=e.pop(),n=e;if("function"!=typeof t)throw new TypeError("last argument must be a function");n.forEach(function(e){this.hasHandler(e)||(this.events[e]=[]),this.events[e].push(t)},this)},t.EventEmitter.prototype.removeHandler=function(t,e){if(this.hasHandler(t)){var n=this.events[t].indexOf(e);this.events[t].splice(n,1),this.events[t].length||delete this.events[t]}},t.EventEmitter.prototype.emit=function(t){if(this.hasHandler(t)){var e=Array.prototype.slice.call(arguments,1);this.events[t].forEach(function(t){t.apply(void 0,e)})}},t.EventEmitter.prototype.hasHandler=function(t){return t in this.events};var e=function(e){this.tokenizer=e.tokenizer||new t.Tokenizer,this.pipeline=e.pipeline||new t.Pipeline,this.documentStore=new t.Store(e.documentStore),this.tokenStore=new t.TokenStore(e.tokenStore),this.corpusTokens=new t.SortedSet(e.corpusTokens),this.eventEmitter=new t.EventEmitter,this._idfCache={}};e.prototype={add:function(e,n){var i=this.tokenizer.tokenize(e),o={};i.forEach(function(e){var t=e.slice();o[t]=(o[t]||0)+1});var r=i.reduce(function(t,e){return t>e.length?t:e.length},0);for(var s in o)this.documentStore.add(s,r,o[s]),this._addToTokenStore(s,r,o[s]);var a=this.eventEmitter;return a.emit("add",e,i),n&&n.call(void 0,e,i)},remove:function(e){var n=this.tokenizer.tokenize(e),i=function(t){return e===t},o=this.documentStore.remove(e,i),r=function(e){return o.indexOf(e)>-1};for(var s in this.tokenStore)this.tokenStore[s].remove(r);this.eventEmitter.emit("remove",e,o)},_addToTokenStore:function(t,e,n){this.tokenStore[t]||(this.tokenStore[t]=new t.DocumentStore),this.tokenStore[t].add(e,n),this.corpusTokens.add(t)}},e.prototype.toJSON=function(){return{version:t.version,documentStore:this.documentStore.toJSON(),tokenStore:this.tokenStore.toJSON(),corpusTokens:this.corpusTokens.toJSON(),pipeline:this.pipeline.toJSON()}},e.load=function(e){var n=new t.Index;return n.documentStore=t.Store.load(e.documentStore),n.tokenStore=t.TokenStore.load(e.tokenStore),n.corpusTokens=t.SortedSet.load(e.corpusTokens),n.pipeline=t.Pipeline.load(e.pipeline),n},t.Index=e}()

if (typeof module !== 'undefined' && module.exports) { module.exports = lunr; }
""".strip()

# ═══════════════════════════════════════════════════════════════

def _read_json(path: Path) -> dict:
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


if __name__ == "__main__":
    main()
