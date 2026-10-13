#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
静态站点生成器
用法： python3 tools/build.py
读取中英文配置与 content/articles，输出双语静态页面、文章中心和 sitemap
"""
import html
import json
import os
import posixpath
import re
from copy import deepcopy

try:
    import frontmatter
    import mistune
except ImportError as exc:
    raise SystemExit("Missing article build dependencies. Run: python3 -m pip install -r requirements.txt") from exc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "site.json")
EN_DATA = os.path.join(ROOT, "data", "site.en.json")
ARTICLE_ROOT = os.path.join(ROOT, "content", "articles")
PREVIEW_ROOT = os.path.join(ROOT, ".preview", "drafts")
SITE_URL_PLACEHOLDER = "https://example.github.io/your-site/"

LOCALES = {"zh-CN": "", "en": "en/"}
MARKDOWN = mistune.create_markdown(plugins=["table", "strikethrough"])

# ---------------------------------------------------------------- 图标
ICONS = {
    "home": '<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 22V12h6v10"/>',
    "sparkles": '<path d="M12 3l1.85 5.15L19 10l-5.15 1.85L12 17l-1.85-5.15L5 10l5.15-1.85z"/><path d="M19 15.2l.9 2.4 2.4.9-2.4.9-.9 2.4-.9-2.4-2.4-.9 2.4-.9z"/>',
    "c": '<circle cx="12" cy="12" r="9"/><path d="M15.6 9.1a4.5 4.5 0 1 0 0 5.8"/>',
    "gem": '<path d="M6 3h12l4 6-10 12L2 9z"/><path d="M11 3 8 9l4 12 4-12-3-6"/><path d="M2 9h20"/>',
    "lightbulb": '<path d="M9 18h6"/><path d="M10 22h4"/><path d="M12 2a7 7 0 0 0-4 12.75V18h8v-3.25A7 7 0 0 0 12 2z"/>',
    "rocket": '<path d="M4.5 16.5c-1.5 1.3-2 5-2 5s3.7-.5 5-2"/><path d="m12 15-3-3a15 15 0 0 1 6-9 15 15 0 0 1 3 3 15 15 0 0 1-9 6z"/><path d="M9 12H5s.5-2.8 2-3 3 0 3 0"/><path d="M12 15v4s2.8-.5 3-2 0-3 0-3"/>',
    "x": '<path d="M4 4h3.6l5 6.6L18.2 4H21l-7.2 8.5L21.4 20h-3.6l-5.3-7-5.8 7H4l7.6-9.2z" fill="currentColor" stroke="none"/>',
    "bolt": '<path d="M13 2 4 14h6l-1 8 9-12h-6z"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/>',
    "headset": '<path d="M4 14v-2a8 8 0 0 1 16 0v2"/><path d="M4 14h3v6H5a1 1 0 0 1-1-1z"/><path d="M20 14h-3v6h2a1 1 0 0 0 1-1z"/>',
    "layers": '<path d="m12 2 9 5-9 5-9-5z"/><path d="m3 12 9 5 9-5"/><path d="m3 17 9 5 9-5"/>',
    "cart": '<circle cx="9" cy="20" r="1.6"/><circle cx="18" cy="20" r="1.6"/><path d="M2 3h3l2.7 11.4A2 2 0 0 0 9.6 16H19"/><path d="M6.2 6H21l-2 8H7"/>',
    "book": '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
    "chevron": '<path d="m6 9 6 6 6-6"/>',
    "alert": '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    "arrow": '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
    "message": '<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/>',
    "search": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
}


def icon(name, size=20, cls=""):
    body = ICONS.get(name, ICONS["sparkles"])
    c = ' class="%s"' % cls if cls else ""
    return (
        '<svg%s xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true">%s</svg>' % (c, size, size, body)
    )


def wechat_chips(contact):
    """把多个微信号渲染成一个整体（避免窄屏下 "/" 被单独折行）。"""
    parts = []
    for i, w in enumerate(contact.get("wechatList", [])):
        if i:
            parts.append('<span class="wechat-sep">/</span>')
        parts.append('<span class="wechat-id" data-copy="%s">%s</span>' % (e(w), e(w)))
    return '<span class="wechat-group">%s</span>' % "".join(parts)


def e(text):
    return html.escape(str(text if text is not None else ""), quote=True)


def localized_output_path(logical_page, locale):
    return LOCALES[locale] + logical_page


def relative_page_link(source_page, target_page, source_locale, target_locale=None):
    target_locale = target_locale or source_locale
    source_output = localized_output_path(source_page, source_locale)
    target_output = localized_output_path(target_page, target_locale)
    return posixpath.relpath(target_output, posixpath.dirname(source_output) or ".")


def site_url(cfg, output_path):
    base = (cfg.get("site", {}).get("baseUrl") or "").strip()
    if not base:
        return ""
    if not base.endswith("/"):
        base += "/"
    return base + output_path.lstrip("/")


def canonical_url(cfg, logical_page, locale):
    output_path = LOCALES[locale] if logical_page == "index.html" else localized_output_path(logical_page, locale)
    return site_url(cfg, output_path)


def contains_cjk(value):
    return any("\u4e00" <= char <= "\u9fff" for char in str(value))


def load_articles():
    articles = []
    required = ("title", "description", "date_published", "date_updated", "category", "translation_key", "status")
    for locale in LOCALES:
        locale_dir = os.path.join(ARTICLE_ROOT, locale)
        if not os.path.isdir(locale_dir):
            raise ValueError("Missing article directory: content/articles/%s" % locale)
        for filename in sorted(os.listdir(locale_dir)):
            if not filename.endswith(".md"):
                continue
            source = os.path.join(locale_dir, filename)
            post = frontmatter.load(source, encoding="utf-8")
            meta = dict(post.metadata)
            missing = [key for key in required if not meta.get(key)]
            if missing:
                raise ValueError("%s is missing required front matter: %s" % (source, ", ".join(missing)))
            status = str(meta["status"]).lower()
            if status not in ("published", "draft"):
                raise ValueError("%s status must be 'published' or 'draft'" % source)
            slug = filename[:-3]
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
                raise ValueError("Article filename must use a lowercase hyphenated slug: %s" % filename)
            updated = meta["date_updated"]
            published = meta["date_published"]
            if hasattr(updated, "isoformat"):
                updated = updated.isoformat()
            if hasattr(published, "isoformat"):
                published = published.isoformat()
            articles.append({
                "locale": locale,
                "slug": slug,
                "page": "blog/%s.html" % slug,
                "title": str(meta["title"]),
                "description": str(meta["description"]),
                "date_published": str(published),
                "date_updated": str(updated),
                "category": str(meta["category"]),
                "translation_key": str(meta["translation_key"]),
                "status": status,
                "related_page": str(meta.get("related_page", "purchase-gpt.html")),
                "related_articles": list(meta.get("related_articles", [])),
                "body_html": MARKDOWN(post.content),
                "source": source,
            })

    by_key = {}
    for article in articles:
        by_key.setdefault(article["translation_key"], []).append(article)
    for key, pair in by_key.items():
        if len(pair) != 2 or {article["locale"] for article in pair} != set(LOCALES):
            raise ValueError("Article translation '%s' must have one zh-CN and one en Markdown file" % key)
        if pair[0]["slug"] != pair[1]["slug"]:
            raise ValueError("Paired translations for '%s' must use the same filename/slug" % key)
    return articles


def make_english_config(base_cfg, en_copy):
    badge_translations = {
        "推荐": "Recommended",
        "旗舰": "Flagship",
        "省更多": "Save more",
        "限时特惠": "Special offer",
        "立减20元": "立减20元",
        "立减70元": "CNY 70 off",
        "立减100元": "CNY 100 off",
        "含Grok额度": "Grok access included",
    }
    cfg = deepcopy(base_cfg)
    for section in ("site", "contact"):
        cfg[section].update(deepcopy(en_copy[section]))
    for section in ("noticeBar", "nav", "hero", "home", "ui"):
        cfg[section] = deepcopy(en_copy[section])
    cfg["locale"] = "en"
    cfg["purchase"] = deepcopy(base_cfg["purchase"])

    translated_products = {item["slug"]: item for item in en_copy["products"]}
    base_slugs = {item["slug"] for item in base_cfg["products"]}
    if set(translated_products) != base_slugs:
        missing = sorted(base_slugs - set(translated_products))
        extra = sorted(set(translated_products) - base_slugs)
        raise ValueError("English product list mismatch; missing=%s extra=%s" % (missing, extra))
    products = []
    for source_product in base_cfg["products"]:
        copy_product = translated_products.get(source_product["slug"])
        if not copy_product:
            raise ValueError("Missing English copy for product: %s" % source_product["slug"])
        product = deepcopy(source_product)
        for key in ("page", "navLabel", "title", "metaTitle", "breadcrumb", "subtitle", "icon"):
            if key in copy_product:
                product[key] = copy_product[key]
        product["guideUrl"] = copy_product.get("guideUrl", product.get("guideUrl", ""))
        plan_copy = copy_product.get("plans", {})
        source_plan_names = {
            plan["name"]
            for section in source_product.get("sections", []) if section.get("type") == "plans"
            for plan in section.get("items", [])
        }
        if set(plan_copy) != source_plan_names:
            missing = sorted(source_plan_names - set(plan_copy))
            extra = sorted(set(plan_copy) - source_plan_names)
            raise ValueError("English plan copy mismatch for %s; missing=%s extra=%s" % (source_product["slug"], missing, extra))
        english_sections = []
        for source_section in source_product.get("sections", []):
            kind = source_section.get("type")
            if kind == "notice" and copy_product.get("notice"):
                section = deepcopy(copy_product["notice"])
                section["type"] = "notice"
                english_sections.append(section)
            elif kind == "options" and copy_product.get("options"):
                section = deepcopy(copy_product["options"])
                section["type"] = "options"
                english_sections.append(section)
            elif kind == "plans":
                section = deepcopy(source_section)
                section["title"] = copy_product.get("plansTitle", "Available options")
                translated_items = []
                for source_plan in source_section.get("items", []):
                    plan_text = plan_copy.get(source_plan["name"])
                    if not plan_text:
                        raise ValueError("Missing English plan copy for %s / %s" % (source_product["slug"], source_plan["name"]))
                    plan = deepcopy(source_plan)
                    plan.update({key: deepcopy(value) for key, value in plan_text.items() if key != "sourceName"})
                    plan["price"] = source_plan["price"]
                    try:
                        plan["badges"] = list(dict.fromkeys(badge_translations[badge] for badge in source_plan.get("badges", [])))
                    except KeyError as exc:
                        raise ValueError("Missing English badge translation for %s: %s" % (source_product["slug"], exc))
                    for key in ("originalPrice", "buyUrl", "featured"):
                        if key in source_plan:
                            plan[key] = source_plan[key]
                    if source_plan.get("save"):
                        saved_amount = re.findall(r"\d+(?:\.\d+)?", source_plan["save"].get("amount", ""))
                        saved_percent = re.findall(r"\d+(?:\.\d+)?", source_plan["save"].get("percent", ""))
                        plan["save"] = {
                            "amount": "Save CNY %s" % saved_amount[-1] if saved_amount else "Ask support about the current offer",
                            "percent": "About %s%% off" % saved_percent[0] if saved_percent else "Current offer",
                        }
                    else:
                        plan.pop("save", None)
                    if "unit" not in plan_text and "unit" in source_plan:
                        plan["unit"] = en_copy.get("ui", {}).get("unitTranslations", {}).get(
                            source_plan["unit"], source_plan["unit"]
                        )
                    has_plan_checkout = bool(source_plan.get("buyUrl") or base_cfg.get("purchase", {}).get("defaultBuyUrl"))
                    plan["cta"] = cfg["ui"].get("buyAction", "Go to checkout") if has_plan_checkout else cfg["ui"].get("customerService", "Contact support")
                    if not has_plan_checkout:
                        for option in plan.get("options", []):
                            if option.get("action") == "buy":
                                option["desc"] = "Contact support to confirm the current ordering method."
                    translated_items.append(plan)
                section["items"] = translated_items
                english_sections.append(section)

        notes = copy_product.get("importantNotes", [])
        if notes:
            notes_html = "<ul>%s</ul>" % "".join("<li>%s</li>" % e(note) for note in notes)
            english_sections.append({"type": "rich", "title": cfg["ui"]["importantInfo"], "html": notes_html})
        product["sections"] = english_sections
        products.append(product)
    cfg["products"] = products
    return cfg


def validate_english_copy(en_copy):
    allowed_cjk_values = {("ui", "languageSwitch")}

    def walk(value, path=()):
        if isinstance(value, dict):
            for key, child in value.items():
                walk(child, path + (key,))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, path + (str(index),))
        elif isinstance(value, str) and contains_cjk(value) and path not in allowed_cjk_values:
            raise ValueError("English copy still contains Chinese at %s: %s" % (".".join(path), value[:80]))

    walk(en_copy)


def link_html(url):
    """把正文里出现的链接统一加上新窗口打开。"""
    return url


# ---------------------------------------------------------------- 头部 / 页脚
def config_script(cfg, products, locale, logical_page):
    asset_prefix = "../" * (logical_page.count("/") + (1 if locale == "en" else 0))
    contact = deepcopy(cfg.get("contact", {}))
    contact = {key: value for key, value in contact.items() if not key.startswith("_")}
    if contact.get("qrImage"):
        contact["qrImage"] = asset_prefix + contact["qrImage"]
    purchase = {key: value for key, value in cfg.get("purchase", {}).items() if not key.startswith("_")}
    data = {
        "contact": contact,
        "purchase": purchase,
        "ui": cfg.get("ui", {}),
        "locale": locale,
        "products": [
            {"slug": p["slug"], "page": p["page"], "label": p["navLabel"]} for p in products
        ],
    }
    return (
        '<script id="site-config" type="application/json">'
        + json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
        + "</script>"
    )


def head(cfg, page_title, logical_page, locale, public_pages, description=""):
    site = cfg["site"]
    output_path = localized_output_path(logical_page, locale)
    asset_depth = output_path.count("/")
    p = "../" * asset_depth
    title = page_title or site["title"]
    desc = description or site.get("description") or (
        "提供 GPT、Claude、Gemini、Perplexity、Grok、X Premium 等主流 AI 会员代充值服务，"
        "官方通道、快速到账、不成功全额退款。"
    )
    canonical = canonical_url(cfg, logical_page, locale)
    links = []
    for alternate_locale, hreflang in (("zh-CN", "zh-CN"), ("en", "en")):
        if logical_page in public_pages.get(alternate_locale, set()):
            url = canonical_url(cfg, logical_page, alternate_locale)
            if url:
                links.append('<link rel="alternate" hreflang="%s" href="%s">' % (hreflang, e(url)))
    canonical_tag = '<link rel="canonical" href="%s">' % e(canonical) if canonical else ""
    return f"""<!DOCTYPE html>
<html lang="{e(locale)}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<meta name="theme-color" content="#153d30">
<meta property="og:type" content="website">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
{canonical_tag}
{''.join(links)}
<link rel="icon" href="{p}assets/img/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{p}assets/css/main-header.css">
<link rel="stylesheet" href="{p}assets/css/style.css">
</head>
<body data-page="{e(site.get('pageKey', ''))}" data-locale="{e(locale)}">
"""


def header(cfg, logical_page, locale, public_pages):
    site = cfg["site"]
    depth = logical_page.count("/")
    ui = cfg.get("ui", {})
    current_home = relative_page_link(logical_page, "index.html", locale)
    nav_items = []
    for item in cfg["nav"]:
        target_page = item["href"].split("#", 1)[0]
        active = logical_page == target_page or (target_page == "blog/index.html" and logical_page.startswith("blog/"))
        cls = ' class="nav-active"' if active else ""
        nav_items.append(
            '<li><a href="%s"%s>%s<span>%s</span></a></li>'
            % (e(relative_page_link(logical_page, item["href"], locale)), cls, icon(item.get("icon", "sparkles"), 16), e(item["label"]))
        )

    more = []
    for prod in cfg["products"]:
        more.append(
            '<li><a href="%s">%s</a></li>' % (e(relative_page_link(logical_page, prod["page"], locale)), e(prod["title"]))
        )

    nav_more = (
        '<li class="nav-more-item"><a href="#" onclick="return false">%s<span>%s</span>%s</a>'
        "<ul class=\"nav-more-list\">%s</ul></li>"
        % (icon("layers", 16), e(ui.get("productCatalog", "产品目录")), icon("chevron", 14), "".join(more))
    )

    wechat = wechat_chips(cfg["contact"])

    order_btn = (
        '<button class="query-btn" type="button" data-action="order-query">%s<span>%s</span></button>'
        % (icon("search", 15), e(cfg["contact"].get("orderQueryText", ui.get("queryOrder", "查询订单"))))
    )

    mobile_links = []
    for item in cfg["nav"]:
        target_page = item["href"].split("#", 1)[0]
        active = logical_page == target_page or (target_page == "blog/index.html" and logical_page.startswith("blog/"))
        cls = ' class="nav-active"' if active else ""
        mobile_links.append(
            '<li><a href="%s"%s>%s<span>%s</span></a></li>'
            % (e(relative_page_link(logical_page, item["href"], locale)), cls, icon(item.get("icon", "sparkles"), 17), e(item["label"]))
        )
    for prod in cfg["products"]:
        mobile_links.append('<li><a href="%s">%s</a></li>' % (e(relative_page_link(logical_page, prod["page"], locale)), e(prod["title"])))

    switch_links = []
    for target_locale, label in (("zh-CN", "中文"), ("en", "EN")):
        target_page = logical_page if logical_page in public_pages.get(target_locale, set()) else "blog/index.html"
        cls = ' class="is-current" aria-current="page"' if target_locale == locale else ""
        switch_links.append(
            '<a href="%s" lang="%s" data-language-choice="%s"%s>%s</a>'
            % (e(relative_page_link(logical_page, target_page, locale, target_locale)), target_locale, target_locale, cls, label)
        )

    other_locale = "en" if locale == "zh-CN" else "zh-CN"
    other_page = logical_page if logical_page in public_pages.get(other_locale, set()) else "blog/index.html"
    other_href = relative_page_link(logical_page, other_page, locale, other_locale)
    prompt = ui.get("switchToEnglish" if other_locale == "en" else "switchToChinese", "切换语言")
    suggestion = f'''<div class="language-suggestion" hidden
  data-locale="{e(locale)}" data-target-locale="{e(other_locale)}" data-target-href="{e(other_href)}"
  data-prompt="{e(prompt)}" data-switch-label="{e(ui.get('switchLanguage', '切换语言'))}"
  data-dismiss-label="{e(ui.get('dismiss', '关闭提示'))}">
  <span class="language-suggestion-text"></span>
  <a class="language-suggestion-link" href="{e(other_href)}" data-language-choice="{e(other_locale)}"></a>
  <button class="language-suggestion-dismiss" type="button" aria-label="{e(ui.get('dismiss', '关闭提示'))}">×</button>
</div>'''

    return f"""<header class="main-header">
  <div class="container header-container">
    <a href="{e(current_home)}" class="logo-container" aria-label="{e(site['brandName'])} {e(ui.get('homeLabel', '首页'))}">
      <div class="logo">{e(site['logoText'])}</div>
      <div class="logo-text">
        <h1>{e(site['brandName'])}</h1>
        <div class="subtitle">{e(site.get('tagline', ''))}</div>
      </div>
    </a>

    <nav class="desktop-nav main-nav" aria-label="{e(ui.get('navigationLabel', '主导航'))}">
      <ul>
        {''.join(nav_items)}
        {nav_more}
      </ul>
    </nav>

    <div class="user-actions">
      {order_btn}
      <div class="locale-switch" aria-label="{e(ui.get('languageLabel', 'Language'))}">{''.join(switch_links)}</div>
      <button class="mobile-nav-toggle" type="button" aria-label="{e(ui.get('mobileMenu', '展开菜单'))}" aria-expanded="false">
        {icon('layers', 22)}
      </button>
    </div>
  </div>

  <div class="mobile-nav-menu">
    <ul>
      {''.join(mobile_links)}
    </ul>
    <div class="user-actions-mobile">
      {order_btn}
      <div style="font-size:13px;color:#6c757d">{e(ui.get('contactLabel', '客服微信：'))}{wechat}</div>
      <div class="locale-switch" aria-label="{e(ui.get('languageLabel', 'Language'))}">{''.join(switch_links)}</div>
    </div>
  </div>
</header>
{suggestion}
"""


NOTICE_INLINE_JS = """<script>
/* 公告条高度必须在解析到这里时同步测出来，否则固定头部与 body 的留白会错位。
   （不要用 CSS 变量反过来给公告条设高度，那会变成 0/1px 的死循环） */
(function () {
  var bar = document.querySelector('.notice-bar');
  if (!bar) return;
  try { if (localStorage.getItem('notice-dismissed') === '1') bar.hidden = true; } catch (e) {}
  function apply() {
    var h = (bar && !bar.hidden) ? bar.offsetHeight : 0;
    document.documentElement.style.setProperty('--notice-bar-height', h + 'px');
  }
  apply();
  window.addEventListener('resize', apply);
  window.addEventListener('load', apply);
  window.__applyNoticeHeight = apply;
})();
</script>
"""


def notice_bar(cfg, depth):
    nb = cfg.get("noticeBar", {})
    ui = cfg.get("ui", {})
    if not nb.get("enabled"):        return ""
    link = ""
    if nb.get("linkText"):
        url = nb.get("linkUrl") or ""
        if url and url != "#":
            link = '<a class="notice-link" href="%s" target="_blank" rel="noopener">%s</a>' % (
                e(url),
                e(nb["linkText"]),
            )
        else:
            link = '<a class="notice-link" href="#" data-action="customer-service">%s</a>' % e(
                nb["linkText"]
            )
    return (
        f"""<div class="notice-bar" role="status">
  <div class="notice-inner">
    {icon('alert', 18)}
    <span>{e(nb.get('text', ''))}</span>
    {link}
  </div>
  <button class="notice-close" type="button" aria-label="{e(ui.get('dismissNotice', '关闭公告'))}">
    <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
  </button>
</div>
"""
        + NOTICE_INLINE_JS
    )


def footer(cfg, logical_page, locale):
    depth = logical_page.count("/")
    ui = cfg.get("ui", {})
    site = cfg["site"]
    prod_links = "".join(
        '<li><a href="%s">%s</a></li>' % (e(relative_page_link(logical_page, prod["page"], locale)), e(prod["title"]))
        for prod in cfg["products"]
    )
    wechat = wechat_chips(cfg["contact"])
    home_faq = relative_page_link(logical_page, "index.html#faq", locale)
    home_steps = relative_page_link(logical_page, "index.html#steps", locale)
    blog_index = relative_page_link(logical_page, "blog/index.html", locale)
    return f"""<footer class="main-footer">
  <div class="container">
    <div class="footer-grid">
      <div class="footer-brand">
        <div class="fb-logo">
          <div class="logo">{e(site['logoText'])}</div>
          <strong>{e(site['brandName'])}</strong>
        </div>
        <p>{e(site.get('tagline', ''))}. {e(ui.get('footerTagline', '为主流 AI 服务提供会员选项与支持。'))}</p>
        <p style="margin-top:10px">{e(ui.get('contactLabel', '客服微信：'))}{wechat}</p>
      </div>
      <div class="footer-col">
        <h5>{e(ui.get('footerProducts', '充值服务'))}</h5>
        <ul>{prod_links}</ul>
      </div>
      <div class="footer-col">
        <h5>{e(ui.get('footerHelp', '帮助中心'))}</h5>
        <ul>
          <li><a href="{e(home_faq)}">{e(ui.get('faqLink', '常见问题'))}</a></li>
          <li><a href="{e(home_steps)}">{e(ui.get('stepsLink', '购买流程'))}</a></li>
          <li><a href="{e(blog_index)}">{e(ui.get('articleCenter', '文章指南'))}</a></li>
        </ul>
      </div>
      <div class="footer-col">
        <h5>{e(ui.get('footerContact', '联系我们'))}</h5>
        <ul>
          <li>{e(ui.get('contactLabel', '客服微信：'))}{wechat}</li>
          <li>{e(cfg['contact'].get('workTime', ''))}</li>
          <li><a href="#" data-action="customer-service">{e(ui.get('qrAction', '扫码添加客服'))}</a></li>
        </ul>
      </div>
    </div>
    <div class="footer-bottom">
      <p>{e(site.get('copyright', ''))}</p>
      <p style="margin-top:6px;font-size:12px;color:#6b7280">{e(ui.get('thirdPartyDisclaimer', '本站为第三方服务，与相关品牌无隶属关系。'))}</p>
    </div>
  </div>
</footer>
<script src="{'../' * (depth + (1 if locale == 'en' else 0))}assets/js/site.js" defer></script>
</body>
</html>
"""


# ---------------------------------------------------------------- 区块渲染
def render_button(label, href="#", action=None, buy=None, cls="btn", icon_name=None, target_blank=False):
    attrs = ['class="%s"' % cls, 'href="%s"' % e(href)]
    if action:
        attrs.append('data-action="%s"' % action)
    if buy is not None:
        attrs.append('data-buy="%s"' % e(buy))
    if target_blank and href.startswith("http"):
        attrs += ['target="_blank"', 'rel="noopener"']
    inner = icon(icon_name, 17) if icon_name else ""
    return "<a %s>%s<span>%s</span></a>" % (" ".join(attrs), inner, e(label))


def render_notice(sec, depth):
    tone = sec.get("tone", "info")
    ic = "alert" if tone == "warn" else "info"
    return f"""<div class="notice-box {e(tone)}">
  <div class="nb-icon">{icon(ic, 18)}</div>
  <div>
    <h4>{e(sec.get('title', ''))}</h4>
    {sec.get('html', '')}
  </div>
</div>"""


def render_options(sec, depth, ui):
    p = "../" * depth
    cards = []
    for it in sec.get("items", []):
        href = it.get("href", "#")
        if href.startswith("#"):
            target = href
        else:
            target = p + href
        cards.append(f"""<div class="option-card">
  <div class="o-icon">{icon(it.get('icon', 'cart'), 21)}</div>
  <div>
    <h4>{e(it.get('title', ''))}</h4>
    <p>{e(it.get('desc', ''))}</p>
    {render_button(it.get('cta', '查看'), href=target, cls='btn btn-ghost btn-sm', icon_name='arrow')}
  </div>
</div>""")
    head_html = ""
    if sec.get("title"):
        head_html = f"""<div class="section-head" style="margin-bottom:24px">
  <h2 style="font-size:24px">{e(sec['title'])}</h2>
  {('<p>%s</p>' % e(sec['subtitle'])) if sec.get('subtitle') else ''}
</div>"""
    return head_html + '<div class="options-grid">%s</div>' % "".join(cards)


def render_plans(sec, depth, buy_default, contact, ui):
    items = sec.get("items", [])
    cards = []
    for plan in items:
        buy_url = plan.get("buyUrl") or buy_default or "#"
        badges = "".join(
            '<span class="badge%s">%s</span>'
            % (
                " soft" if b in ("推荐", "旗舰") else (" green" if b == "省更多" else ""),
                e(b),
            )
            for b in plan.get("badges", [])
        )
        currency = ui.get("currencySymbol", "¥")
        price_html = '<span class="cur">%s</span><span class="amount">%s</span>' % (e(currency), e(plan.get("price", "")))
        if plan.get("unit"):
            price_html += '<span class="unit">%s</span>' % e(plan["unit"])
        if plan.get("originalPrice"):
            price_html += '<span class="origin">%s %s%s</span>' % (
                e(ui.get("originalPriceLabel", "原价")), e(currency), e(plan["originalPrice"])
            )

        save_html = ""
        if plan.get("save"):
            save_html = '<div class="plan-save">💰 %s · %s</div>' % (
                e(plan["save"].get("amount", "")),
                e(plan["save"].get("percent", "")),
            )

        tags = "".join("<span>%s</span>" % e(t) for t in plan.get("tags", []))
        feats = "".join("<li>%s</li>" % e(f) for f in plan.get("features", []))
        tags_html = '<div class="plan-tags">%s</div>' % tags if tags else ""
        feats_html = '<ul class="plan-features">%s</ul>' % feats if feats else '<div style="flex-grow:1"></div>'

        options_html = ""
        if plan.get("options"):
            rows = []
            ids = " / ".join(contact["wechatList"])
            for op in plan["options"]:
                desc = op.get("desc", "")
                if op.get("action") == "wechat":
                    contact_label = ui.get("wechatLabel", "微信号：")
                    desc = "%s (%s %s)" % (desc, contact_label, ids) if desc else "%s %s" % (contact_label, ids)
                    act = (
                        '<button class="po-link" type="button" data-action="customer-service">%s</button>'
                        % e(ui.get("contactAction", "联系客服 →"))
                    )
                else:
                    option_action_label = ui.get("buyAction", "去下单") if buy_url != "#" else ui.get("supportAction", "联系客服")
                    act = (
                        '<button class="po-link" type="button" data-buy="%s">%s</button>'
                        % (e(buy_url), e(option_action_label))
                    )
                rows.append(
                    '<div class="plan-option"><div><div class="po-label">%s</div>'
                    '<div class="po-desc">%s</div></div>%s</div>'
                    % (e(op.get("label", "")), e(desc), act)
                )
            options_html = '<div class="plan-options">%s</div>' % "".join(rows)

        cta = render_button(
            plan.get("cta", "立即购买"),
            href=buy_url,
            buy=buy_url,
            cls="btn btn-block",
            icon_name="cart",
            target_blank=True,
        )

        cards.append(f"""<div class="plan-card{' featured' if plan.get('featured') else ''}">
  <div class="plan-badges">{badges}</div>
  <h3>{e(plan.get('name', ''))}</h3>
  <div class="plan-sub">{e(plan.get('subtitle', ''))}</div>
  <div class="plan-price">{price_html}</div>
  {save_html}
  <div class="plan-desc">{e(plan.get('desc', ''))}</div>
  {tags_html}
  {feats_html}
  {options_html}
  {cta}
  <p class="plan-note">{e(ui.get('planNote', '下单前请与客服确认账号状态'))}</p>
</div>""")

    anchor = ' id="%s"' % e(sec["id"]) if sec.get("id") else ""
    title_html = ""
    if sec.get("title"):
        title_html = f"""<div class="section-head" style="margin-bottom:24px">
  <h2 style="font-size:24px">{e(sec['title'])}</h2>
</div>"""
    return f'<div{anchor}>{title_html}<div class="plans-grid">{"".join(cards)}</div></div>'


def render_table(sec, depth):
    head = "".join("<th>%s</th>" % e(h) for h in sec.get("head", []))
    rows = "".join(
        "<tr>%s</tr>" % "".join("<td>%s</td>" % e(c) for c in row) for row in sec.get("rows", [])
    )
    return f"""<div>
  <h3 style="font-size:19px;margin-bottom:14px">{e(sec.get('title', ''))}</h3>
  <div class="table-wrap">
    <table class="cmp">
      <thead><tr>{head}</tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</div>"""


def render_rich(sec, depth):
    return f"""<div class="rich-box">
  <h3>{e(sec.get('title', ''))}</h3>
  {sec.get('html', '')}
</div>"""


def render_steps(sec, depth):
    steps = "".join(
        f"""<div class="guide-step">
  <div class="gs-num">{i + 1}</div>
  <div><h4>{e(s.get('title', ''))}</h4><p>{e(s.get('desc', ''))}</p></div>
</div>"""
        for i, s in enumerate(sec.get("items", []))
    )
    title = (
        '<h3 style="font-size:19px;margin-bottom:14px">%s</h3>' % e(sec["title"])
        if sec.get("title")
        else ""
    )
    return f'<div>{title}<div class="guide-steps">{steps}</div></div>'


RENDERERS = {
    "notice": render_notice,
    "options": render_options,
    "plans": render_plans,
    "table": render_table,
    "rich": render_rich,
    "steps": render_steps,
}


def render_sections(sections, depth, buy_default, contact, ui):
    out = []
    for sec in sections:
        fn = RENDERERS.get(sec.get("type"))
        if not fn:
            continue
        if sec["type"] == "plans":
            out.append(fn(sec, depth, buy_default, contact, ui))
        elif sec["type"] == "options":
            out.append(fn(sec, depth, ui))
        else:
            out.append(fn(sec, depth))
    return "\n".join(out)


# ---------------------------------------------------------------- 页面
def article_card(article, source_page, locale, ui):
    href = relative_page_link(source_page, article["page"], locale)
    return f'''<a class="article-card" href="{e(href)}">
  <div class="article-card-meta"><span>{e(article['category'])}</span><time datetime="{e(article['date_updated'])}">{e(article['date_updated'])}</time></div>
  <h3>{e(article['title'])}</h3>
  <p>{e(article['description'])}</p>
  <span class="article-read">{e(ui.get('readArticle', '阅读指南'))} {icon('arrow', 15)}</span>
</a>'''


def article_cards(articles, source_page, locale, ui, limit=None):
    ordered = sorted(articles, key=lambda item: item["date_updated"], reverse=True)
    if limit is not None:
        ordered = ordered[:limit]
    if not ordered:
        return '<div class="article-empty">%s</div>' % e(ui.get("articleEmpty", "暂无文章。"))
    return "".join(article_card(article, source_page, locale, ui) for article in ordered)


def build_index(cfg, locale, public_pages, articles):
    site = cfg["site"]
    home = cfg["home"]
    hero = cfg["hero"]
    contact = cfg["contact"]
    ui = cfg.get("ui", {})
    logical_page = "index.html"
    wechat = wechat_chips(contact)

    stats = "".join(
        '<div class="hero-stat"><div class="v">%s</div><div class="l">%s</div></div>'
        % (e(item["value"]), e(item["label"]))
        for item in hero.get("stats", [])
    )
    promises = "".join(
        f'''<div class="hero-promise">
  <div class="promise-icon">{icon(item.get('icon', 'shield'), 18)}</div>
  <div><h3>{e(item.get('title', ''))}</h3><p>{e(item.get('desc', ''))}</p></div>
</div>'''
        for item in hero.get("promises", [])
    )
    services = "".join(
        f'''<div class="service-card">
  <div class="icon">{icon(item.get('icon', 'sparkles'), 26)}</div>
  <h3>{e(item['name'])}</h3>
  <p>{e(item['desc'])}</p>
  {render_button(item.get('cta', ui.get('viewPlan', '查看套餐')), href=item['href'], cls='btn btn-sm', icon_name='arrow')}
</div>'''
        for item in home.get("services", [])
    )
    steps = "".join(
        f'''<div class="step-card"><div class="num">{i + 1}</div><h4>{e(item['title'])}</h4><p>{e(item['desc'])}</p></div>'''
        for i, item in enumerate(home.get("steps", []))
    )
    guarantees = "".join(
        f'''<div class="guarantee"><div class="g-icon">{icon(item.get('icon', 'bolt'), 22)}</div><h4>{e(item['title'])}</h4><p>{e(item['desc'])}</p></div>'''
        for item in home.get("guarantees", [])
    )
    faq = "".join(
        f'''<div class="faq-item"><button class="faq-q" type="button"><span>{e(item['q'])}</span><span class="chev">{icon('chevron', 18)}</span></button><div class="faq-a">{e(item['a'])}</div></div>'''
        for item in home.get("faq", [])
    )
    latest_articles = article_cards(articles, logical_page, locale, ui, limit=3)
    blog_index = relative_page_link(logical_page, "blog/index.html", locale)

    body = f"""{notice_bar(cfg, 0)}
{header(cfg, logical_page, locale, public_pages)}

<section class="hero">
  <div class="container hero-container">
    <div class="hero-layout">
      <div class="hero-inner">
        <div class="hero-eyebrow">{icon('bolt', 15)}<span>{e(hero.get('eyebrow', ''))}</span></div>
        <h1>{e(hero.get('title', ''))}<br><span class="hl">{e(hero.get('highlight', ''))}</span></h1>
        <p class="lead">{e(hero.get('subtitle', ''))}</p>
        <div class="hero-cta">
          {render_button(hero['primaryCta']['label'], href=hero['primaryCta'].get('href', '#services'), icon_name='arrow')}
          {render_button(hero['secondaryCta']['label'], href='#', action='customer-service', cls='btn btn-outline-light', icon_name='message')}
        </div>
        <div class="wechat-strip">{icon('message', 17)}<span>{e(ui.get('contactLabel', '客服微信：'))}</span>{wechat}<span class="wechat-hint">{e(contact.get('wechatHint', ''))}</span></div>
      </div>
      <aside class="hero-proof" aria-label="{e(ui.get('servicePromise', '服务承诺'))}">
        <div class="hero-proof-label">{e(ui.get('servicePromiseEnglish', 'SERVICE PROMISE'))}<span>{e(ui.get('servicePromise', '服务承诺'))}</span></div>
        <h2>{e(ui.get('heroProofTitle', '下单前，先把关心的事说清楚。'))}</h2>
        <div class="hero-promise-list">{promises}</div>
        <a class="hero-proof-link" href="#steps">{e(ui.get('heroFlowLink', '看看购买流程'))} {icon('arrow', 15)}</a>
      </aside>
    </div>
    <div class="hero-stats">{stats}</div>
  </div>
</section>

<section class="section" id="services"><div class="container"><div class="section-head"><h2>{e(home.get('servicesTitle', '支持的 AI 服务'))}</h2><p>{e(home.get('servicesSubtitle', ''))}</p></div><div class="services-grid">{services}</div></div></section>

<section class="section bg-white article-preview-section"><div class="container"><div class="section-head"><h2>{e(ui.get('latestGuides', '最新指南'))}</h2><p>{e(ui.get('articleCenterSubtitle', ''))}</p></div><div class="article-grid">{latest_articles}</div><div class="article-index-action"><a href="{e(blog_index)}">{e(ui.get('viewAllArticles', '查看全部文章'))} {icon('arrow', 15)}</a></div></div></section>

<section class="section bg-white" id="steps"><div class="container"><div class="section-head"><h2>{e(home.get('stepsTitle', '购买流程'))}</h2><p>{e(ui.get('stepsSectionSubtitle', '四步完成充值，全程有客服跟进'))}</p></div><div class="steps-grid">{steps}</div></div></section>

<section class="section"><div class="container"><div class="section-head"><h2>{e(home.get('guaranteesTitle', '为什么选择我们'))}</h2></div><div class="guarantees-grid">{guarantees}</div></div></section>

<section class="section bg-white" id="faq"><div class="container"><div class="section-head"><h2>{e(home.get('faqTitle', '常见问题'))}</h2><p>{e(ui.get('faqSectionSubtitle', '还有其他问题？点击右下角客服按钮咨询'))}</p></div><div class="faq-list">{faq}</div></div></section>

{footer(cfg, logical_page, locale)}"""
    return head(cfg, site["title"], logical_page, locale, public_pages, site.get("description", "")) + config_script(cfg, cfg["products"], locale, logical_page) + body


def build_product(cfg, prod, locale, public_pages):
    contact = cfg["contact"]
    ui = cfg.get("ui", {})
    logical_page = prod["page"]
    buy_default = cfg.get("purchase", {}).get("defaultBuyUrl", "")
    wechat = wechat_chips(contact)
    actions = [
        render_button(ui.get("viewPlan", "查看套餐价格"), href="#plans", icon_name="cart"),
        render_button(ui.get("customerService", "联系客服"), href="#", action="customer-service", cls="btn btn-outline-light", icon_name="message"),
    ]
    if prod.get("guideUrl"):
        actions.append(render_button(ui.get("registrationGuide", "注册教程"), href=prod["guideUrl"], cls="btn btn-outline-light", icon_name="book"))

    sections = render_sections(prod.get("sections", []), 0, buy_default, contact, ui)
    others = [item for item in cfg["products"] if item["slug"] != prod["slug"]]
    cross = "".join(
        f'''<a class="service-card" href="{e(relative_page_link(logical_page, item['page'], locale))}" style="text-decoration:none"><div class="icon">{icon(item.get('icon', 'sparkles'), 24)}</div><h3>{e(item['navLabel'])}</h3><p>{e(item.get('title', ''))}</p><span class="btn btn-ghost btn-sm" style="margin-top:16px;align-self:flex-start">{e(ui.get('viewPlan', '前往查看'))} {icon('arrow', 15)}</span></a>'''
        for item in others
    )
    notice = ""
    if prod.get("notice"):
        notice = render_notice(prod["notice"], 0)
    has_external_checkout = bool(buy_default) or any(
        plan.get("buyUrl")
        for section in prod.get("sections", []) if section.get("type") == "plans"
        for plan in section.get("items", [])
    )
    checkout_note = '<p class="checkout-language-note">%s</p>' % e(ui["checkoutLanguageNote"]) if locale == "en" and has_external_checkout else ""
    contact_strip = f'''<div class="wechat-strip" style="background:rgba(255,255,255,.14);border-color:rgba(255,255,255,.35);color:#fff">{icon('message', 17)}<span>{e(ui.get('contactLabel', '客服微信：'))}</span>{wechat}<span style="color:rgba(255,255,255,.85)">{e(ui.get('copyWechat', '（点击复制）'))}</span></div>'''

    body = f"""{notice_bar(cfg, 0)}
{header(cfg, logical_page, locale, public_pages)}
<section class="page-hero"><div class="container"><nav class="breadcrumb" aria-label="{e(ui.get('breadcrumbLabel', '面包屑'))}"><a href="index.html">{e(ui.get('homeLabel', '首页'))}</a><span>/</span><span>{e(prod['breadcrumb'])}</span></nav><div class="ph-title"><div class="icon">{icon(prod.get('icon', 'sparkles'), 26)}</div><h1>{e(prod['title'])}</h1></div><p class="ph-sub">{e(prod['subtitle'])}</p><div class="ph-actions">{''.join(actions)}</div>{contact_strip}</div></section>
<main class="section"><div class="container"><div class="stack-lg">{notice}{sections}{checkout_note}</div></div></main>
<section class="section bg-white"><div class="container"><div class="section-head"><h2>{e(ui.get('relatedServices', '其他充值服务'))}</h2><p>{e(ui.get('relatedServicesSubtitle', '一站购齐主流 AI 会员'))}</p></div><div class="services-grid">{cross}</div></div></section>
{footer(cfg, logical_page, locale)}"""
    return head(cfg, prod.get("metaTitle") or prod["title"], logical_page, locale, public_pages, prod.get("metaDescription", prod["subtitle"])) + config_script(cfg, cfg["products"], locale, logical_page) + body


def build_article_index(cfg, articles, locale, public_pages):
    ui = cfg.get("ui", {})
    logical_page = "blog/index.html"
    cards = article_cards(articles, logical_page, locale, ui)
    description = ui.get("articleCenterSubtitle", "")
    body = f"""{notice_bar(cfg, 1)}
{header(cfg, logical_page, locale, public_pages)}
<section class="page-hero"><div class="container"><nav class="breadcrumb" aria-label="{e(ui.get('breadcrumbLabel', '面包屑'))}"><a href="../index.html">{e(ui.get('homeLabel', '首页'))}</a><span>/</span><span>{e(ui.get('articleCenter', '文章指南'))}</span></nav><div class="ph-title"><div class="icon">{icon('book', 26)}</div><h1>{e(ui.get('articleCenter', '文章指南'))}</h1></div><p class="ph-sub">{e(description)}</p></div></section>
<main class="section"><div class="container"><div class="article-grid">{cards}</div></div></main>
{footer(cfg, logical_page, locale)}"""
    return head(cfg, ui.get("articleCenter", "文章指南"), logical_page, locale, public_pages, description) + config_script(cfg, cfg["products"], locale, logical_page) + body


def build_article(cfg, article, locale, public_pages, published_articles):
    ui = cfg.get("ui", {})
    logical_page = article["page"]
    depth = logical_page.count("/")
    home_href = relative_page_link(logical_page, "index.html", locale)
    hub_href = relative_page_link(logical_page, "blog/index.html", locale)
    product_page = article.get("related_page", "purchase-gpt.html")
    product_href = relative_page_link(logical_page, product_page, locale)
    related = []
    for key in article.get("related_articles", []):
        found = next((item for item in published_articles if item["translation_key"] == key and item["locale"] == locale), None)
        if found and found["page"] != logical_page:
            related.append('<li><a href="%s">%s</a></li>' % (e(relative_page_link(logical_page, found["page"], locale)), e(found["title"])))
    related_html = '<section class="article-related"><h2>%s</h2><ul>%s</ul></section>' % (e(ui.get("relatedArticles", "相关文章")), "".join(related)) if related else ""
    body = f"""{notice_bar(cfg, depth)}
{header(cfg, logical_page, locale, public_pages)}
<section class="page-hero"><div class="container"><nav class="breadcrumb" aria-label="{e(ui.get('breadcrumbLabel', '面包屑'))}"><a href="{e(home_href)}">{e(ui.get('homeLabel', '首页'))}</a><span>/</span><a href="{e(hub_href)}">{e(ui.get('articleCenter', '文章指南'))}</a><span>/</span><span>{e(article['category'])}</span></nav><div class="ph-title"><div class="icon">{icon('book', 26)}</div><h1>{e(article['title'])}</h1></div><p class="ph-sub">{e(article['description'])}</p><div class="article-meta"><span>{e(article['category'])}</span><span>{e(ui.get('updated', '更新于'))} {e(article['date_updated'])}</span></div><div class="ph-actions">{render_button(ui.get('customerService', '联系客服'), href='#', action='customer-service', cls='btn btn-outline-light', icon_name='message')}{render_button(ui.get('backToProduct', '查看 GPT 套餐'), href=product_href, icon_name='arrow')}</div></div></section>
<main class="section"><div class="container article-container"><article class="article-body">{article['body_html']}</article><aside class="article-cta"><h2>{e(ui.get('articleCtaTitle', '需要 ChatGPT 会员选项？'))}</h2><p>{e(ui.get('articleCtaText', '查看当前列出的服务方式和套餐信息。'))}</p>{render_button(ui.get('backToProduct', '查看 GPT 套餐'), href=product_href, icon_name='arrow')}</aside>{related_html}</div></main>
{footer(cfg, logical_page, locale)}"""
    return head(cfg, article["title"], logical_page, locale, public_pages, article["description"]) + config_script(cfg, cfg["products"], locale, logical_page) + body


# ---------------------------------------------------------------- 主流程
def main():
    with open(DATA, encoding="utf-8") as f:
        zh_cfg = json.load(f)
    with open(EN_DATA, encoding="utf-8") as f:
        en_copy = json.load(f)

    validate_english_copy(en_copy)
    en_cfg = make_english_config(zh_cfg, en_copy)
    articles = load_articles()
    known_products = {product["page"] for product in zh_cfg["products"]}
    for article in articles:
        if article["related_page"] not in known_products:
            raise ValueError("Unknown related_page in %s: %s" % (article["source"], article["related_page"]))
        for related_key in article["related_articles"]:
            if not any(item["translation_key"] == related_key for item in articles):
                raise ValueError("Unknown related article '%s' in %s" % (related_key, article["source"]))

    published_by_locale = {
        locale: sorted((item for item in articles if item["locale"] == locale and item["status"] == "published"),
                       key=lambda item: item["date_updated"], reverse=True)
        for locale in LOCALES
    }
    public_pages = {
        locale: {"index.html", "blog/index.html"} | {product["page"] for product in cfg["products"]} |
                {article["page"] for article in published_by_locale[locale]}
        for locale, cfg in (("zh-CN", zh_cfg), ("en", en_cfg))
    }

    written = []

    def write(rel, content, public=True):
        root = ROOT if public else PREVIEW_ROOT
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        content = re.sub(r"[ \t]+(?=\r?$)", "", content, flags=re.MULTILINE)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        written.append(("" if public else ".preview/drafts/") + rel)

    for locale, cfg in (("zh-CN", zh_cfg), ("en", en_cfg)):
        output_prefix = LOCALES[locale]
        write(output_prefix + "index.html", build_index(cfg, locale, public_pages, published_by_locale[locale]))
        for product in cfg["products"]:
            write(output_prefix + product["page"], build_product(cfg, product, locale, public_pages))
        write(output_prefix + "blog/index.html", build_article_index(cfg, published_by_locale[locale], locale, public_pages))
        for article in published_by_locale[locale]:
            write(output_prefix + article["page"], build_article(cfg, article, locale, public_pages, published_by_locale[locale]))

    # Drafts are rendered only under the ignored preview directory for local review.
    for article in articles:
        if article["status"] == "draft":
            cfg = zh_cfg if article["locale"] == "zh-CN" else en_cfg
            preview_path = "%s/%s" % (article["locale"], article["page"])
            draft_html = build_article(cfg, article, article["locale"], public_pages, published_by_locale[article["locale"]])
            # Draft previews sit four levels below the site root; point assets back to the shared site files.
            draft_html = draft_html.replace('href="../assets/', 'href="../../../../assets/')
            draft_html = draft_html.replace('src="../assets/', 'src="../../../../assets/')
            draft_html = draft_html.replace('href="../../assets/', 'href="../../../../assets/')
            draft_html = draft_html.replace('src="../../assets/', 'src="../../../../assets/')
            draft_html = draft_html.replace('"qrImage": "../assets/', '"qrImage": "../../../../assets/')
            draft_html = draft_html.replace('"qrImage": "../../assets/', '"qrImage": "../../../../assets/')
            write(preview_path, draft_html, public=False)

    # 站点地图 & robots（baseUrl 在 data/site.json 里配置）
    base = (zh_cfg["site"].get("baseUrl") or "").strip()
    if base and not base.endswith("/"):
        base += "/"
    if base:
        sitemap = ['<?xml version="1.0" encoding="UTF-8"?>',
                   '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
        for locale in LOCALES:
            for logical_page in sorted(public_pages[locale]):
                url = canonical_url(zh_cfg, logical_page, locale)
                sitemap.append("  <url>")
                sitemap.append("    <loc>%s</loc>" % e(url))
                for alternate_locale, hreflang in (("zh-CN", "zh-CN"), ("en", "en")):
                    if logical_page in public_pages[alternate_locale]:
                        alt_url = canonical_url(zh_cfg, logical_page, alternate_locale)
                        sitemap.append('    <xhtml:link rel="alternate" hreflang="%s" href="%s" />' % (hreflang, e(alt_url)))
                sitemap.append("  </url>")
        sitemap.append("</urlset>")
        write("sitemap.xml", "\n".join(sitemap) + "\n")
        write("robots.txt", "User-agent: *\nAllow: /\n\nSitemap: %ssitemap.xml\n" % base)
    else:
        write("robots.txt", "User-agent: *\nAllow: /\n")

    # GitHub Pages 用它跳过 Jekyll 处理，避免下划线开头的文件被吞掉
    write(".nojekyll", "")

    # 生成 favicon.svg
    site = zh_cfg["site"]
    favicon = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        '<rect width="64" height="64" rx="14" fill="#d6ed75"/>'
        '<text x="32" y="43" text-anchor="middle" font-family="Helvetica,Arial,sans-serif" '
        'font-size="30" font-weight="700" fill="#183b2b">%s</text></svg>'
        % html.escape(site["logoText"][:2])
    )
    write("assets/img/favicon.svg", favicon)

    print("已生成 %d 个文件，其中草稿只写入本地预览目录：" % len(written))
    for w in written:
        print("  -", w)


if __name__ == "__main__":
    main()
