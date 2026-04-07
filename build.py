#!/usr/bin/env python3
"""
build.py — 法律概念 Wiki 静态站点构建脚本

从 /Users/CS/Trae/知识库/wiki/concepts/ 读取概念文章（只读），
生成维基百科风格的静态 HTML 网站到当前目录。

用法:
    cd /Users/CS/Trae/演示案例/网页制作/legalwiki/
    .venv/bin/python3 build.py

依赖: pip install markdown（已通过 venv 安装）
"""

import json
import os
import re
import shutil
import sys
from datetime import date
from pathlib import Path

try:
    import markdown
except ImportError:
    print("需要安装 markdown 库: pip3 install markdown")
    sys.exit(1)

# ──────────────────────────────────────────────────────
# 路径配置
# ──────────────────────────────────────────────────────

WIKI_SRC = Path("/Users/CS/Trae/知识库/wiki/concepts")   # 只读源目录
BUILDER_DIR = Path(__file__).resolve().parent              # 项目目录（输出目录）
BUILD_CACHE = BUILDER_DIR / ".build_cache"                 # 临时缓存
ARTICLE_DIR = BUILDER_DIR / "article"
DOMAIN_DIR = BUILDER_DIR / "domain"

# ──────────────────────────────────────────────────────
# 全局常量
# ──────────────────────────────────────────────────────

WIKILINK_RE = re.compile(r"\[\[([^\]#|]+)(?:#[^\]]*)?\]\]")

MD = markdown.Markdown(extensions=[
    "tables",
    "fenced_code",
    "nl2br",
])

DOMAIN_COLORS = {
    "公司法": "#1e40af", "合同法": "#15803d", "刑法": "#991b1b",
    "仲裁法": "#7c3aed", "侵权法": "#be123c", "破产法": "#6d28d9",
    "行政法": "#475569", "证券法": "#0369a1", "执行与程序": "#0e7490",
    "综合": "#64748b", "房地产": "#92400e", "劳动法": "#0f766e",
    "投融资": "#7c2d12", "民事诉讼法": "#2563eb", "担保法": "#9333ea",
    "数据合规": "#0d9488", "知识产权": "#b45309", "证据与程序": "#1d4ed8",
    "婚姻家事": "#e11d48", "建设工程": "#a16207", "税法": "#0ea5e9",
}

# ──────────────────────────────────────────────────────
# 第一步：数据拷贝（只读源，写入缓存）
# ──────────────────────────────────────────────────────

def copy_to_cache():
    if BUILD_CACHE.exists():
        shutil.rmtree(BUILD_CACHE)
    print(f"  [1/5] 复制源文件到缓存 → {BUILD_CACHE}")
    shutil.copytree(WIKI_SRC, BUILD_CACHE / "concepts")

def clean_cache():
    if BUILD_CACHE.exists():
        shutil.rmtree(BUILD_CACHE)
        print(f"  [5/5] 清理缓存")

# ──────────────────────────────────────────────────────
# 第二步：解析所有概念文章
# ──────────────────────────────────────────────────────

def parse_frontmatter(text):
    """解析 YAML frontmatter，返回 dict"""
    m = re.match(r"^-{3,}\n(.*?)-{3,}\n", text, re.DOTALL)
    if not m:
        return {}, text
    fm_text = m.group(1)
    body = text[m.end():]
    fm = {}
    current_key = None
    for line in fm_text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("- "):
            if current_key and isinstance(fm.get(current_key), list):
                fm[current_key].append(s[2:].strip())
        elif ":" in s:
            key, _, val = s.partition(":")
            key, val = key.strip(), val.strip()
            if val:
                fm[key] = val
                current_key = None
            else:
                current_key = key
                fm[current_key] = []
    return fm, body

def extract_wikilinks(text):
    return set(WIKILINK_RE.findall(text))

def parse_concept(md_path, concept_name):
    """解析单篇概念文章，返回解析结果 dict"""
    text = md_path.read_text(encoding="utf-8", errors="ignore")
    fm, body = parse_frontmatter(text)
    domain = fm.get("domain", md_path.parent.name)
    last_updated = fm.get("last_updated", "")
    related = fm.get("related", [])
    sources_count = fm.get("sources_count", 0)

    # 提取现行基准行
    current_benchmark = ""
    bm = re.search(r">\s*[**]?现行基准[**]?\s*[：:]\s*(.+)", body)
    if bm:
        current_benchmark = bm.group(1).strip()

    # 提取所有 wikilinks
    wikilinks = extract_wikilinks(text)

    # Markdown 转 HTML（去除 frontmatter 部分）
    MD.reset()
    html_body = MD.convert(body)

    return {
        "name": concept_name,
        "domain": domain,
        "last_updated": last_updated,
        "related": related,
        "sources_count": sources_count,
        "current_benchmark": current_benchmark,
        "wikilinks": wikilinks,
        "html_body": html_body,
        "source_path": md_path.relative_to(BUILD_CACHE / "concepts"),
        "full_text": body,   # 用于搜索索引
    }

def scan_concepts():
    """扫描所有概念文章，返回概念列表和映射表"""
    print(f"  [2/5] 扫描概念文章...")
    concepts = []
    concept_map = {}  # name -> {slug, domain}
    slug_used = set()
    total = 0

    cache_concepts = BUILD_CACHE / "concepts"
    for domain_dir in sorted(cache_concepts.iterdir()):
        if not domain_dir.is_dir():
            continue
        for md_file in sorted(domain_dir.glob("*.md")):
            total += 1
            concept_name = md_file.stem
            result = parse_concept(md_file, concept_name)

            # slug 去重
            slug = concept_name
            if slug in slug_used:
                slug = f"{result['domain']}_{concept_name}"
            slug_used.add(slug)

            result["slug"] = slug
            concepts.append(result)
            concept_map[concept_name] = {"slug": slug, "domain": result["domain"]}

    print(f"    解析了 {total} 篇概念文章，{len(concept_map)} 个可用概念（去重后 slug {len(slug_used)} 个）")
    return concepts, concept_map

# ──────────────────────────────────────────────────────
# 第三步：wikilink 转换 + 源文献链接处理
# ──────────────────────────────────────────────────────

def convert_wikilinks(html_body, concept_map):
    """将 HTML 中的 [[wikilink]] 转为 <a> 标签"""
    def replacer(match):
        name = match.group(1).strip()
        if name in concept_map:
            slug = concept_map[name]["slug"]
            return f'<a href="../article/{slug}.html" class="wikilink">{name}</a>'
        else:
            return f'<span class="broken-wikilink" title="概念未找到: {name}">{name}</span>'
    return WIKILINK_RE.sub(replacer, html_body)


def process_source_section(html):
    """
    处理「知识库原始资料索引」区域：将 <a href="../../../...">文本</a>
    转为纯文本 <span class="source-title">文本</span>，不再做超链接。
    目录链接整项移除。仅处理 ../../../ 开头的链接，保留 ../article/ wikilinks。
    """
    SOURCE_LINK_RE = re.compile(
        r'<a\s+href="(\.\./\.\./\.\./[^"]+)"[^>]*>(.*?)</a>'
    )
    DIR_LINK_RE = re.compile(
        r'<a\s+href="(\.\./\.\./\.\./[^"]+/)"[^>]*>(.*?)</a>'
    )
    m = re.search(
        r'(<h2[^>]*>知识库原始资料索引</h2>)(.*?)(?=</div>|$)',
        html, re.DOTALL
    )
    if not m:
        return html

    section = m.group(2)
    # 先移除目录链接（以 / 结尾）的整项（li）
    section = re.sub(
        r'<li>\s*<a\s+href="[^"]+/"[^>]*>.*?</a>\s*</li>',
        '', section
    )
    # 再 ../../../ 链接 → 纯文本 span
    section = SOURCE_LINK_RE.sub(
        r'<span class="source-title">\2</span>',
        section
    )
    # 清理空 li
    section = re.sub(r'<li>\s*</li>', '', section)
    return html[:m.start(2)] + section + html[m.end(2):]

# ──────────────────────────────────────────────────────
# 第四步：计算反向链接
# ──────────────────────────────────────────────────────

def compute_backlinks(concepts, concept_map):
    """计算每个概念被哪些其他概念引用"""
    backlinks = {c["slug"]: [] for c in concepts}
    for c in concepts:
        for wl in c["wikilinks"]:
            if wl in concept_map:
                target_slug = concept_map[wl]["slug"]
                if target_slug != c["slug"] and c["slug"] not in backlinks[target_slug]:
                    backlinks[target_slug].append(c["name"])
    return backlinks

# ──────────────────────────────────────────────────────
# HTML 模板函数
# ──────────────────────────────────────────────────────

def nav_bar(title="法律概念 Wiki", active="首页", page_type="root"):
    """page_type: 'root' for homepage, 'sub' for article/domain pages"""
    pfx = "" if page_type == "root" else "../"
    items = [
        ("首页", f"{pfx}index.html"),
        ("浏览", f"{pfx}browse.html"),
    ]
    links = ""
    for label, href in items:
        cls = "active" if label == active else ""
        links += f'<li><a href="{href}" class="{cls}">{label}</a></li>'
    return f"""<nav class="top-nav">
  <a href="{pfx}index.html" class="nav-logo">{title}</a>
  <ul class="nav-links">{links}</ul>
</nav>"""

def sidebar(concepts, page_type="root"):
    """侧边栏：领域折叠导航"""
    pfx = "" if page_type == "root" else "../"
    domains = {}
    for c in concepts:
        domains.setdefault(c["domain"], []).append(c)

    domain_items = ""
    for domain in sorted(domains.keys()):
        color = DOMAIN_COLORS.get(domain, "#64748b")
        articles = domains[domain]
        domain_items += f"""
    <div class="sidebar-domain" onclick="toggleDomain(this)">
      <span class="sidebar-domain-name" style="color:{color}">{domain}</span>
      <span class="sidebar-count">({len(articles)})</span>
    </div>
    <ul class="sidebar-articles" style="display:none">"""
        for a in sorted(articles, key=lambda x: x["name"]):
            domain_items += f'<li><a href="{pfx}article/{a["slug"]}.html" style="display:block;padding:3px 8px">{a["name"]}</a></li>'
        domain_items += "</ul>"

    return f"""<aside class="sidebar">
  <div class="sidebar-header">
    <a href="{pfx}index.html" class="sidebar-logo">
      <span class="sidebar-logo-icon">⚖</span>法律概念 Wiki
    </a>
  </div>
  <div class="sidebar-search">
    <input type="text" id="sidebar-search" placeholder="搜索概念..." autocomplete="off">
    <div id="sidebar-results" class="search-results"></div>
  </div>
  <div class="sidebar-nav">{domain_items}</div>
</aside>"""

def article_page(concept, concepts, backlinks, concept_map):
    """生成单篇概念文章的 HTML 页面"""
    slug = concept["slug"]
    domain = concept["domain"]
    domain_color = DOMAIN_COLORS.get(domain, "#64748b")
    html = convert_wikilinks(concept["html_body"], concept_map)
    html = process_source_section(html)

    # 提取目录 (TOC)
    h2s = re.findall(r'<h2(?:\s[^>]*)?>(.*?)</h2>', html)
    toc_html = ""
    for i, h2 in enumerate(h2s):
        anchor = f"section-{i}"
        toc_html += f'<li><a href="#{anchor}">{h2}</a></li>'

    # 反向链接
    bl_links = backlinks.get(slug, [])
    bl_html = ""
    if bl_links:
        bl_items = ""
        for bl in bl_links[:10]:
            if bl in concept_map:
                bl_slug = concept_map[bl]["slug"]
                bl_items += f'<li><a href="{bl_slug}.html">{bl}</a></li>'
        bl_html = f"""
<div class="backlinks">
  <h3>参见 · 反向链接</h3>
  <ul>{bl_items}</ul>
</div>""" if bl_items else ""

    # 关联概念
    related_html = ""
    related_items = ""
    for rel in (concept.get("related") or []):
        if rel in concept_map:
            r_slug = concept_map[rel]["slug"]
            related_items += f'<a href="{r_slug}.html" class="related-tag">{rel}</a>'
    if related_items:
        related_html = f'<div class="related-concepts"><h3>关联概念</h3><div class="related-tags">{related_items}</div></div>'

    # 上一篇/下一篇
    domain_concepts = sorted([c for c in concepts if c["domain"] == domain], key=lambda x: x["name"])
    for i, dc in enumerate(domain_concepts):
        if dc["slug"] == slug:
            prev_link = f'<a href="{domain_concepts[i-1]["slug"]}.html">&larr; {domain_concepts[i-1]["name"]}</a>' if i > 0 else "<span>&larr; 无前页</span>"
            next_link = f'<a href="{domain_concepts[i+1]["slug"]}.html">{domain_concepts[i+1]["name"]} &rarr;</a>' if i < len(domain_concepts)-1 else "<span>无后页 &rarr;</span>"
            break
    else:
        prev_link = ""
        next_link = ""

    # 底部来源
    sources_html = ""
    if concept.get("sources_count") and str(concept["sources_count"]) != "0":
        sources_html = f'<div class="sources-info"><p class="sources-count">引用资料: {concept["sources_count"]} 项</p></div>'

    # 效力标签
    benchmark_html = ""
    if concept.get("current_benchmark"):
        benchmark_html = f'<blockquote class="benchmark-quote"><strong>现行基准：</strong>{concept["current_benchmark"]}</blockquote>'

    page_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{concept["name"]} - 法律概念 Wiki</title>
<link rel="stylesheet" href="../style.css">
</head>
<body>
{nav_bar(active=domain, page_type="sub")}
{sidebar(concepts, page_type="sub")}
<div class="main-wrapper">
  {article_breadcrumb(concept["name"], domain)}
  <main class="main">
    <h1 class="article-title">{concept["name"]}</h1>
    <div class="article-meta">
      <span class="domain-tag" style="background:{domain_color}">{domain}</span>
      <span class="meta-item">最后更新: {concept.get('last_updated', '未知')}</span>
      <span class="meta-item">引用来源: {concept.get('sources_count', 0)}</span>
    </div>
    {benchmark_html}
    {related_html}
    <div class="article-toc-toggle" onclick="toggleMobileToc()">📋 显示/隐藏目录</div>
    <nav class="article-toc" id="article-toc">
      <h3>目录</h3>
      <ul>{toc_html if toc_html else '<li>无目录结构</li>'}</ul>
    </nav>
    <h2 id="section-toc-marker" style="display:none"></h2>
    <div class="article-content">
      {html}
    </div>
    {sources_html}
    {bl_html}
    <div class="page-nav">
      <div class="page-nav-item">{prev_link}</div>
      <div class="page-nav-item">{next_link}</div>
    </div>
  </main>
</div>
<footer class="wiki-footer">
  <p>法律概念 Wiki &middot; 基于 Karpathy LLM Wiki 方法论 &middot; 由 AI+CSlawyer 构建和维护</p>
  <p class="visitor-counter" style="font-size:12px;color:#94a3b8;margin-top:6px">
    <span id="busuanzi_container_site_pv">总访问量 <span id="busuanzi_value_site_pv" class="counter-number">--</span> 次</span>
    &middot;
    <span id="busuanzi_container_site_uv"><span id="busuanzi_value_site_uv" class="counter-number">--</span> 位访客</span>
  </p>
</footer>
<script src="../app.js"></script>
<script async src="https://busuanzi.ibruce.info/busuanzi/2.3/busuanzi.pure.mini.js"></script>
</body>
</html>"""
    return page_html

def article_breadcrumb(title, domain):
    return f"""<div class="breadcrumb">
  <a href="../index.html">首页</a> &gt;
  <a href="../domain/{domain}.html">{domain}</a> &gt;
  <span>{title}</span>
</div>"""

# ──────────────────────────────────────────────────────
# 生成页面
# ──────────────────────────────────────────────────────

def generate_articles(concepts, backlinks, concept_map):
    print(f"  [3/5] 生成 {len(concepts)} 篇概念文章页...")
    ARTICLE_DIR.mkdir(exist_ok=True)
    for i, c in enumerate(concepts):
        article_html = article_page(c, concepts, backlinks, concept_map)
        (ARTICLE_DIR / f"{c['slug']}.html").write_text(article_html, encoding="utf-8")
    print(f"    ✓ 生成 {len(concepts)} 篇文章页")

def domain_page_concepts(concepts):
    """按领域分组"""
    domains = {}
    for c in concepts:
        domains.setdefault(c["domain"], []).append(c)
    return domains

def generate_domain_pages(concepts):
    print(f"  [4/5] 生成 {len(domain_page_concepts(concepts))} 个领域索引页...")
    DOMAIN_DIR.mkdir(exist_ok=True)
    domains = domain_page_concepts(concepts)
    for domain, articles in domains.items():
        color = DOMAIN_COLORS.get(domain, "#64748b")
        updated = sorted(articles, key=lambda x: x.get("last_updated", ""), reverse=True)
        items_html = ""
        for a in updated:
            updated_str = a.get("last_updated", "")
            sc = a.get("sources_count", 0)
            items_html += f"""
  <div class="domain-article-card">
    <div class="domain-article-title-area">
      <a href="../article/{a['slug']}.html" class="domain-article-title">{a['name']}</a>
    </div>
    <div class="domain-article-meta">
      <span>最后更新: {updated_str}</span>
      <span>引用: {sc} 项来源</span>
    </div>
  </div>"""

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{domain} - 法律概念 Wiki</title>
<link rel="stylesheet" href="../style.css">
</head>
<body>
{nav_bar(active=domain, page_type="sub")}
{sidebar(concepts, page_type="sub")}
<div class="main-wrapper">
  <div class="breadcrumb">
    <a href="../index.html">首页</a> &gt; <span>{domain}</span>
  </div>
  <main class="main domain-page">
    <h1 class="domain-title" style="border-left:4px solid {color};padding-left:12px">{domain}</h1>
    <p class="domain-count">共 <strong>{len(articles)}</strong> 篇概念文章</p>
    <div class="domain-articles-list">{items_html}</div>
  </main>
</div>
<footer class="wiki-footer">
  <p>法律概念 Wiki &middot; 基于 Karpathy LLM Wiki 方法论 &middot; 由 AI+CSlawyer 构建和维护</p>
  <p class="visitor-counter" style="font-size:12px;color:#94a3b8;margin-top:6px">
    <span id="busuanzi_container_site_pv">总访问量 <span id="busuanzi_value_site_pv" class="counter-number">--</span> 次</span>
    &middot;
    <span id="busuanzi_container_site_uv"><span id="busuanzi_value_site_uv" class="counter-number">--</span> 位访客</span>
  </p>
</footer>
<script src="../app.js"></script>
<script async src="https://busuanzi.ibruce.info/busuanzi/2.3/busuanzi.pure.mini.js"></script>
</body>
</html>"""
        (DOMAIN_DIR / f"{domain}.html").write_text(html, encoding="utf-8")
    print(f"    ✓ 生成 {len(domains)} 个领域页")

def generate_homepage(concepts, backlinks):
    print(f"  [5/5] 生成首页和索引...")

    domains = domain_page_concepts(concepts)

    # 高引用概念 TOP 10
    bl_counts = []
    for c in concepts:
        count = len(backlinks.get(c["slug"], []))
        bl_counts.append((c, count))
    bl_counts.sort(key=lambda x: x[1], reverse=True)
    top_cited = [(c, cnt) for c, cnt in bl_counts[:10]]

    # 最近更新 TOP 10
    updated = sorted(concepts, key=lambda x: x.get("last_updated", ""), reverse=True)[:10]

    # 领域卡片
    domain_cards = ""
    for domain in sorted(domains.keys()):
        color = DOMAIN_COLORS.get(domain, "#64748b")
        count = len(domains[domain])
        domain_cards += f"""
    <a href="domain/{domain}.html" class="domain-card" style="border-top:3px solid {color}">
      <h3>{domain}</h3>
      <span class="domain-card-count">{count} 篇</span>
    </a>"""

    # 高引用
    top_cited_html = ""
    for c, cnt in top_cited:
        top_cited_html += f'<li><a href="article/{c["slug"]}.html">{c["name"]}</a> <span class="cite-count">({cnt} 引用)</span></li>'

    # 最近更新
    recent_html = ""
    for c in updated:
        recent_html += f'<li><a href="article/{c["slug"]}.html">{c["name"]}</a> <span class="date">{c.get("last_updated", "")}</span></li>'

    # 桥接概念
    bridge_count = sum(1 for c in concepts if len(backlinks.get(c["slug"], [])) > 15)
    bridges = [c for c in concepts if len(backlinks.get(c["slug"], [])) > 15][:10]
    bridge_html = ""
    for c in bridges:
        dom = c["domain"]
        dom_color = DOMAIN_COLORS.get(dom, "#64748b")
        bridge_html += f'<li><a href="article/{c["slug"]}.html">{c["name"]}</a> <span class="domain-tag" style="background:{dom_color}">{dom}</span></li>'

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>首页 - 法律概念 Wiki</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
{nav_bar(active="首页")}
{sidebar(concepts)}
<div class="main-wrapper">
  <main class="main homepage">
    <div class="wiki-header">
      <h1 class="wiki-title">法律概念 Wiki</h1>
      <p class="wiki-slogan">专业的中文法律知识查询平台</p>
    </div>

    <div class="wiki-search-home">
      <input type="text" id="home-search" placeholder="搜索法律概念，如「股东出资」「合同解除」..." autocomplete="off">
      <div id="home-results" class="search-results"></div>
    </div>

    <div class="wiki-stats">
      <div class="stat-box"><strong>{len(concepts)}</strong><br>概念文章</div>
      <div class="stat-box"><strong>{len(domains)}</strong><br>法律领域</div>
      <div class="stat-box"><strong>{sum(len(backlinks.get(c['slug'],[])) for c in concepts)}</strong><br>交叉引用</div>
      <div class="stat-box"><strong>{max((len(backlinks.get(c['slug'],[])) for c in concepts), default=0)}</strong><br>最高引用</div>
    </div>

    <div class="wikipedia-two-columns">
      <div class="column-left">
        <div class="wp-section">
          <div class="wp-section-header">📚 特色概念</div>
          <div class="wp-section-content">
            <p>本 Wiki 收录了 <strong>{len(concepts)}</strong> 篇法律概念文章，涵盖 {len(domains)} 个法律领域。每个概念均由专业法律知识库整理而成，包含法条引用、规则沿革、实务要点和原始资料索引。</p>
          </div>
        </div>
        <div class="wp-section">
          <div class="wp-section-header">⭐ 高引用概念 TOP 10</div>
          <div class="wp-section-content">
            <ul class="featured-list">{top_cited_html}</ul>
          </div>
        </div>
        <div class="wp-section">
          <div class="wp-section-header">⚖🔗 桥接概念（跨领域）</div>
          <div class="wp-section-content">
            <ul class="featured-list">{bridge_html}</ul>
          </div>
        </div>
        <div class="wp-section">
          <div class="wp-section-header">📖 浏览全部领域</div>
          <div class="wp-section-content">
            <div class="domain-cards-grid">{domain_cards}</div>
          </div>
        </div>
      </div>
      <div class="column-right">
        <div class="wp-section">
          <div class="wp-section-header">🕐 最近更新</div>
          <div class="wp-section-content">
            <ul class="recent-list">{recent_html}</ul>
          </div>
        </div>
        <div class="wp-section">
          <div class="wp-section-header">⚡ 快速导航</div>
          <div class="wp-section-content">
            <ul class="nav-list">"""

    for domain in sorted(domains.keys()):
        color = DOMAIN_COLORS.get(domain, "#64748b")
        html += f'<li><a href="domain/{domain}.html" style="color:{color}">{domain}</a> <span>({len(domains[domain])})</span></li>'

    html += f"""
            </ul>
          </div>
        </div>
        <div class="wp-section">
          <div class="wp-section-header">💡 关于本 Wiki</div>
          <div class="wp-section-content">
            <p>本法律概念 Wiki 基于 Karpathy LLM Wiki 方法论构建，由 43,000+ 篇原始资料经 LLM 提取、交叉引用、持续维护。</p>
                    <p>所有内容由 AI 自动提取并整理，人类目前还没有时间审核和校正，谨慎采纳。</p>
          </div>
        </div>
      </div>
    </div>

  </main>
</div>
<footer class="wiki-footer">
  <p>法律概念 Wiki &middot; 基于 Karpathy LLM Wiki 方法论 &middot; 由 AI+CSlawyer 构建和维护</p>
  <p class="visitor-counter" style="font-size:12px;color:#94a3b8;margin-top:6px">
    <span id="busuanzi_container_site_pv">总访问量 <span id="busuanzi_value_site_pv" class="counter-number">--</span> 次</span>
    &middot;
    <span id="busuanzi_container_site_uv"><span id="busuanzi_value_site_uv" class="counter-number">--</span> 位访客</span>
  </p>
</footer>
<script src="app.js"></script>
<script async src="https://busuanzi.ibruce.info/busuanzi/2.3/busuanzi.pure.mini.js"></script>
</body>
</html>"""
    (BUILDER_DIR / "index.html").write_text(html, encoding="utf-8")
    print(f"    ✓ 生成首页")

def generate_browse_page(concepts):
    """生成「全部领域」浏览汇总页"""
    print(f"    ✓ 生成浏览汇总页...")
    domains = domain_page_concepts(concepts)

    cards = ""
    for domain in sorted(domains.keys()):
        color = DOMAIN_COLORS.get(domain, "#64748b")
        count = len(domains[domain])
        articles = sorted(domains[domain], key=lambda x: x["name"])
        art_html = ""
        for a in articles[:15]:
            art_html += f'<li><a href="article/{a["slug"]}.html">{a["name"]}</a></li>'
        more = f'<li><a href="domain/{domain}.html" style="color:#3366cc">查看全部 {count} 篇 &rarr;</a></li>' if count > 15 else ''
        cards += f"""
    <div class="browse-domain-card" style="border-top:3px solid {color}">
      <div class="browse-domain-header">
        <a href="domain/{domain}.html" class="browse-domain-title" style="color:{color}">{domain}</a>
        <span class="browse-domain-count">{count} 篇</span>
      </div>
      <ul class="browse-domain-list">{art_html}{more}</ul>
    </div>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>浏览全部领域 - 法律概念 Wiki</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
{nav_bar(active="浏览", page_type="root")}
{sidebar(concepts, page_type="root")}
<div class="main-wrapper">
  <main class="main browse-page">
    <h1 class="browse-title">浏览全部法律领域</h1>
    <p class="browse-subtitle">共 <strong>{len(domains)}</strong> 个领域，<strong>{len(concepts)}</strong> 篇概念文章</p>
    <div class="browse-grid">{cards}</div>
  </main>
</div>
<footer class="wiki-footer">
  <p>法律概念 Wiki &middot; 基于 Karpathy LLM Wiki 方法论 &middot; 由 AI+CSlawyer 构建和维护</p>
  <p class="visitor-counter" style="font-size:12px;color:#94a3b8;margin-top:6px">
    <span id="busuanzi_container_site_pv">总访问量 <span id="busuanzi_value_site_pv" class="counter-number">--</span> 次</span>
    &middot;
    <span id="busuanzi_container_site_uv"><span id="busuanzi_value_site_uv" class="counter-number">--</span> 位访客</span>
  </p>
</footer>
<script src="app.js"></script>
<script async src="https://busuanzi.ibruce.info/busuanzi/2.3/busuanzi.pure.mini.js"></script>
</body>
</html>"""
    (BUILDER_DIR / "browse.html").write_text(html, encoding="utf-8")

def generate_search_index(concepts):
    """生成 search-index.json，截断 body 到 3000 字符"""
    entries = []
    for c in concepts:
        plain_text = re.sub(r'<[^>]+>', '', c["full_text"])[:3000]
        entries.append({
            "t": c["name"],
            "d": c["domain"],
            "b": plain_text,
            "r": c.get("related") or [],
            "s": c.get("sources_count", 0),
            "u": c.get("last_updated", ""),
            "p": f"article/{c['slug']}.html",
        })
    (BUILDER_DIR / "search-index.json").write_text(
        json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    size_mb = os.path.getsize(BUILDER_DIR / "search-index.json") / (1024*1024)
    print(f"    ✓ 生成搜索索引 ({size_mb:.1f} MB, {len(entries)} 条)")

# ──────────────────────────────────────────────────────
# 主入口
# ──────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  法律概念 Wiki —— 静态站点构建")
    print("=" * 60)

    if not WIKI_SRC.exists():
        print(f"错误: 源目录不存在: {WIKI_SRC}")
        sys.exit(1)

    # 确保输出目录
    BUILDER_DIR.mkdir(exist_ok=True)
    ARTICLE_DIR.mkdir(exist_ok=True)
    DOMAIN_DIR.mkdir(exist_ok=True)

    t0 = __import__("time").time()

    copy_to_cache()
    concepts, concept_map = scan_concepts()
    backlinks = compute_backlinks(concepts, concept_map)

    generate_search_index(concepts)
    generate_articles(concepts, backlinks, concept_map)
    generate_domain_pages(concepts)
    generate_browse_page(concepts)
    generate_homepage(concepts, backlinks)
    clean_cache()

    elapsed = __import__("time").time() - t0
    print(f"\n构建完成! 总耗时: {elapsed:.2f}s")

if __name__ == "__main__":
    main()
