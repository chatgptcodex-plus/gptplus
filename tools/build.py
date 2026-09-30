#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
静态站点生成器
用法： python3 tools/build.py
读取 data/site.json，输出 index.html、purchase-*.html、blog/*.html
"""
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "site.json")
SITE_URL_PLACEHOLDER = "https://example.github.io/your-site/"

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


def link_html(url):
    """把正文里出现的链接统一加上新窗口打开。"""
    return url


# ---------------------------------------------------------------- 头部 / 页脚
def config_script(cfg, products):
    data = {
        "contact": cfg.get("contact", {}),
        "purchase": cfg.get("purchase", {}),
        "products": [
            {"slug": p["slug"], "page": p["page"], "label": p["navLabel"]} for p in products
        ],
    }
    return (
        '<script id="site-config" type="application/json">'
        + json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
        + "</script>"
    )


def head(cfg, page_title, depth, description=""):
    site = cfg["site"]
    p = "../" * depth
    title = page_title or site["title"]
    desc = description or site.get("description") or (
        "提供 GPT、Claude、Gemini、Perplexity、Grok、X Premium 等主流 AI 会员代充值服务，"
        "官方通道、快速到账、不成功全额退款。"
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<meta name="theme-color" content="#6f42c1">
<meta property="og:type" content="website">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<link rel="icon" href="{p}assets/img/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{p}assets/css/main-header.css">
<link rel="stylesheet" href="{p}assets/css/style.css">
</head>
<body data-page="{e(site.get('pageKey', ''))}">
"""


def header(cfg, depth, active):
    site = cfg["site"]
    p = "../" * depth
    nav_items = []
    for item in cfg["nav"]:
        cls = ' class="nav-active"' if item["href"].endswith(active or "\0") else ""
        nav_items.append(
            '<li><a href="%s"%s>%s<span>%s</span></a></li>'
            % (p + item["href"], cls, icon(item.get("icon", "sparkles"), 16), e(item["label"]))
        )

    more = []
    for prod in cfg["products"]:
        more.append(
            '<li><a href="%s">%s</a></li>' % (p + prod["page"], e(prod["title"]))
        )
    for art in cfg.get("blog", []):
        more.append('<li><a href="%s">%s</a></li>' % (p + art["page"], e(art["title"])))

    nav_more = (
        '<li class="nav-more-item"><a href="#" onclick="return false">%s<span>更多服务</span>%s</a>'
        "<ul class=\"nav-more-list\">%s</ul></li>"
        % (icon("layers", 16), icon("chevron", 14), "".join(more))
    )

    wechat = wechat_chips(cfg["contact"])

    order_btn = (
        '<button class="query-btn" type="button" data-action="order-query">%s<span>%s</span></button>'
        % (icon("search", 15), e(cfg["contact"].get("orderQueryText", "查询订单")))
    )

    mobile_links = []
    for item in cfg["nav"]:
        cls = ' class="nav-active"' if item["href"].endswith(active or "\0") else ""
        mobile_links.append(
            '<li><a href="%s"%s>%s<span>%s</span></a></li>'
            % (p + item["href"], cls, icon(item.get("icon", "sparkles"), 17), e(item["label"]))
        )
    for prod in cfg["products"]:
        mobile_links.append('<li><a href="%s">%s</a></li>' % (p + prod["page"], e(prod["title"])))

    return f"""<header class="main-header">
  <div class="container header-container">
    <a href="{p}index.html" class="logo-container" aria-label="{e(site['brandName'])} 首页">
      <div class="logo">{e(site['logoText'])}</div>
      <div class="logo-text">
        <h1>{e(site['brandName'])}</h1>
        <div class="subtitle">{e(site.get('tagline', ''))}</div>
      </div>
    </a>

    <nav class="desktop-nav main-nav" aria-label="主导航">
      <ul>
        {''.join(nav_items)}
        {nav_more}
      </ul>
    </nav>

    <div class="user-actions">
      {order_btn}
      <button class="mobile-nav-toggle" type="button" aria-label="展开菜单" aria-expanded="false">
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
      <div style="font-size:13px;color:#6c757d">客服微信：{wechat}</div>
    </div>
  </div>
</header>
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
  <button class="notice-close" type="button" aria-label="关闭公告">
    <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
  </button>
</div>
"""
        + NOTICE_INLINE_JS
    )


def footer(cfg, depth):
    p = "../" * depth
    site = cfg["site"]
    prod_links = "".join(
        '<li><a href="%s">%s</a></li>' % (p + prod["page"], e(prod["title"]))
        for prod in cfg["products"]
    )
    blog_links = "".join(
        '<li><a href="%s">%s</a></li>' % (p + art["page"], e(art["title"]))
        for art in cfg.get("blog", [])
    )
    wechat = wechat_chips(cfg["contact"])
    return f"""<footer class="main-footer">
  <div class="container">
    <div class="footer-grid">
      <div class="footer-brand">
        <div class="fb-logo">
          <div class="logo">{e(site['logoText'])}</div>
          <strong>{e(site['brandName'])}</strong>
        </div>
        <p>{e(site.get('tagline', ''))}。为个人与团队提供主流 AI 会员代充值服务，官方通道、快速到账、售后无忧。</p>
        <p style="margin-top:10px">客服微信：{wechat}</p>
      </div>
      <div class="footer-col">
        <h5>充值服务</h5>
        <ul>{prod_links}</ul>
      </div>
      <div class="footer-col">
        <h5>帮助中心</h5>
        <ul>
          <li><a href="{p}index.html#faq">常见问题</a></li>
          <li><a href="{p}index.html#steps">购买流程</a></li>
          {blog_links}
        </ul>
      </div>
      <div class="footer-col">
        <h5>联系我们</h5>
        <ul>
          <li>客服微信：{wechat}</li>
          <li>{e(cfg['contact'].get('workTime', ''))}</li>
          <li><a href="#" data-action="customer-service">扫码添加客服</a></li>
        </ul>
      </div>
    </div>
    <div class="footer-bottom">
      <p>{e(site.get('copyright', ''))}</p>
      <p style="margin-top:6px;font-size:12px;color:#6b7280">本站为第三方代充值服务平台，与 OpenAI、Anthropic、Google、xAI 等公司无隶属关系；所有商标归其各自所有者所有。</p>
    </div>
  </div>
</footer>
<script src="{p}assets/js/site.js" defer></script>
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


def render_options(sec, depth):
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


def render_plans(sec, depth, buy_default, contact):
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
        price_html = '<span class="cur">¥</span><span class="amount">%s</span>' % e(plan.get("price", ""))
        if plan.get("unit"):
            price_html += '<span class="unit">%s</span>' % e(plan["unit"])
        if plan.get("originalPrice"):
            price_html += '<span class="origin">原价 ¥%s</span>' % e(plan["originalPrice"])

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
                    desc = "%s（微信：%s）" % (desc, ids) if desc else "微信：%s" % ids
                    act = (
                        '<button class="po-link" type="button" data-action="customer-service">%s</button>'
                        % "联系客服 →"
                    )
                else:
                    act = (
                        '<button class="po-link" type="button" data-buy="%s">%s</button>'
                        % (e(buy_url), "去下单")
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
  <p class="plan-note">下单前请与客服确认账号状态</p>
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


def render_sections(sections, depth, buy_default, contact):
    out = []
    for sec in sections:
        fn = RENDERERS.get(sec.get("type"))
        if not fn:
            continue
        if sec["type"] == "plans":
            out.append(fn(sec, depth, buy_default, contact))
        else:
            out.append(fn(sec, depth))
    return "\n".join(out)


# ---------------------------------------------------------------- 页面
def build_index(cfg):
    site = cfg["site"]
    home = cfg["home"]
    hero = cfg["hero"]
    contact = cfg["contact"]

    wechat = wechat_chips(contact)

    stats = "".join(
        '<div class="hero-stat"><div class="v">%s</div><div class="l">%s</div></div>'
        % (e(s["value"]), e(s["label"]))
        for s in hero.get("stats", [])
    )

    services = "".join(
        f"""<div class="service-card">
  <div class="icon">{icon(s.get('icon', 'sparkles'), 26)}</div>
  <h3>{e(s['name'])}</h3>
  <p>{e(s['desc'])}</p>
  {render_button(s.get('cta', '立即充值'), href=s['href'], cls='btn btn-sm', icon_name='arrow')}
</div>"""
        for s in home.get("services", [])
    )

    steps = "".join(
        f"""<div class="step-card">
  <div class="num">{i + 1}</div>
  <h4>{e(s['title'])}</h4>
  <p>{e(s['desc'])}</p>
</div>"""
        for i, s in enumerate(home.get("steps", []))
    )

    guarantees = "".join(
        f"""<div class="guarantee">
  <div class="g-icon">{icon(g.get('icon', 'bolt'), 22)}</div>
  <h4>{e(g['title'])}</h4>
  <p>{e(g['desc'])}</p>
</div>"""
        for g in home.get("guarantees", [])
    )

    faq = "".join(
        f"""<div class="faq-item">
  <button class="faq-q" type="button">
    <span>{e(f['q'])}</span>
    <span class="chev">{icon('chevron', 18)}</span>
  </button>
  <div class="faq-a">{e(f['a'])}</div>
</div>"""
        for f in home.get("faq", [])
    )

    body = f"""{(notice_bar(cfg, 0))}
{header(cfg, 0, 'index.html')}

<section class="hero">
  <div class="container">
    <div class="hero-inner">
      <div class="hero-eyebrow">{icon('bolt', 15)}<span>{e(hero.get('eyebrow', ''))}</span></div>
      <h1>{e(hero.get('title', ''))}<br><span class="hl">安全 · 快速 · 售后无忧</span></h1>
      <p class="lead">{e(hero.get('subtitle', ''))}</p>
      <div class="hero-cta">
        {render_button(hero['primaryCta']['label'], href=hero['primaryCta'].get('href', '#services'), icon_name='arrow')}
        {render_button(hero['secondaryCta']['label'], href='#', action='customer-service', cls='btn btn-outline-light', icon_name='message')}
      </div>
      <div class="hero-stats">{stats}</div>
      <div class="wechat-strip">
        {icon('message', 17)}
        <span>客服微信：</span>{wechat}
        <span style="color:#b45309">{e(contact.get('wechatHint', ''))}</span>
      </div>
    </div>
  </div>
</section>

<section class="section" id="services">
  <div class="container">
    <div class="section-head">
      <h2>{e(home.get('servicesTitle', '支持的 AI 服务'))}</h2>
      <p>{e(home.get('servicesSubtitle', ''))}</p>
    </div>
    <div class="services-grid">{services}</div>
  </div>
</section>

<section class="section bg-white" id="steps">
  <div class="container">
    <div class="section-head">
      <h2>{e(home.get('stepsTitle', '购买流程'))}</h2>
      <p>四步完成充值，全程有客服跟进</p>
    </div>
    <div class="steps-grid">{steps}</div>
  </div>
</section>

<section class="section">
  <div class="container">
    <div class="section-head">
      <h2>{e(home.get('guaranteesTitle', '为什么选择我们'))}</h2>
    </div>
    <div class="guarantees-grid">{guarantees}</div>
  </div>
</section>

<section class="section bg-white" id="faq">
  <div class="container">
    <div class="section-head">
      <h2>{e(home.get('faqTitle', '常见问题'))}</h2>
      <p>还有其他问题？点击右下角客服按钮咨询</p>
    </div>
    <div class="faq-list">{faq}</div>
  </div>
</section>

{footer(cfg, 0)}"""

    return head(cfg, site["title"], 0) + config_script(cfg, cfg["products"]) + body


def build_product(cfg, prod):
    contact = cfg["contact"]
    buy_default = cfg.get("purchase", {}).get("defaultBuyUrl", "")
    wechat = wechat_chips(contact)

    actions = [
        render_button("查看套餐价格", href="#plans", icon_name="cart"),
        render_button("联系客服", href="#", action="customer-service", cls="btn btn-outline-light", icon_name="message"),
    ]
    if prod.get("guideUrl"):
        actions.append(
            render_button("注册教程", href=prod["guideUrl"], cls="btn btn-outline-light", icon_name="book")
        )

    sections = render_sections(prod.get("sections", []), 0, buy_default, contact)

    # 其他服务交叉导流
    others = [p for p in cfg["products"] if p["slug"] != prod["slug"]]
    cross = "".join(
        f"""<a class="service-card" href="{e(o['page'])}" style="text-decoration:none">
  <div class="icon">{icon(o.get('icon', 'sparkles'), 24)}</div>
  <h3>{e(o['navLabel'])}</h3>
  <p>{e(o.get('title', ''))}</p>
  <span class="btn btn-ghost btn-sm" style="margin-top:16px;align-self:flex-start">前往查看 {icon('arrow', 15)}</span>
</a>"""
        for o in others
    )

    body = f"""{notice_bar(cfg, 0)}
{header(cfg, 0, prod['page'])}

<section class="page-hero">
  <div class="container">
    <nav class="breadcrumb" aria-label="面包屑">
      <a href="index.html">首页</a><span>/</span><span>{e(prod['breadcrumb'])}</span>
    </nav>
    <div class="ph-title">
      <div class="icon">{icon(prod.get('icon', 'sparkles'), 26)}</div>
      <h1>{e(prod['title'])}</h1>
    </div>
    <p class="ph-sub">{e(prod['subtitle'])}</p>
    <div class="ph-actions">{''.join(actions)}</div>
    <div class="wechat-strip" style="background:rgba(255,255,255,.14);border-color:rgba(255,255,255,.35);color:#fff">
      {icon('message', 17)}<span>客服微信：</span>{wechat}
      <span style="color:rgba(255,255,255,.85)">（点击复制）</span>
    </div>
  </div>
</section>

<main class="section">
  <div class="container">
    <div class="stack-lg">{sections}</div>
  </div>
</main>

<section class="section bg-white">
  <div class="container">
    <div class="section-head">
      <h2>其他充值服务</h2>
      <p>一站购齐主流 AI 会员</p>
    </div>
    <div class="services-grid">{cross}</div>
  </div>
</section>

{footer(cfg, 0)}"""

    return head(cfg, prod.get("metaTitle") or prod["title"], 0) + config_script(cfg, cfg["products"]) + body


def build_article(cfg, art):
    depth = art["page"].count("/")
    sections = render_sections(art.get("sections", []), depth, "", cfg["contact"])
    body = f"""{notice_bar(cfg, depth)}
{header(cfg, depth, art['page'])}

<section class="page-hero">
  <div class="container">
    <nav class="breadcrumb" aria-label="面包屑">
      <a href="{'../' * depth}index.html">首页</a><span>/</span>
      <a href="{'../' * depth}purchase-gpt.html">GPT 充值</a><span>/</span><span>注册教程</span>
    </nav>
    <div class="ph-title">
      <div class="icon">{icon('book', 26)}</div>
      <h1>{e(art['title'])}</h1>
    </div>
    <p class="ph-sub">{e(art['subtitle'])}</p>
    <div class="ph-actions">
      {render_button('联系客服协助', href='#', action='customer-service', cls='btn btn-outline-light', icon_name='message')}
      {render_button('返回 GPT 充值', href='../' * depth + 'purchase-gpt.html', icon_name='arrow')}
    </div>
  </div>
</section>

<main class="section">
  <div class="container" style="max-width:900px">
    <div class="stack-lg">{sections}</div>
  </div>
</main>

{footer(cfg, depth)}"""
    return head(cfg, art.get("metaTitle") or art["title"], depth) + config_script(cfg, cfg["products"]) + body


# ---------------------------------------------------------------- 主流程
def main():
    with open(DATA, encoding="utf-8") as f:
        cfg = json.load(f)

    written = []

    def write(rel, content):
        path = os.path.join(ROOT, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        written.append(rel)

    write("index.html", build_index(cfg))
    for prod in cfg["products"]:
        write(prod["page"], build_product(cfg, prod))
    for art in cfg.get("blog", []):
        write(art["page"], build_article(cfg, art))

    # 站点地图 & robots（baseUrl 在 data/site.json 里配置）
    # 没填 baseUrl 时不生成 sitemap，避免把 example 占位域名发给搜索引擎
    base = (cfg["site"].get("baseUrl") or "").strip()
    if base and not base.endswith("/"):
        base += "/"
    if base:
        urls = ["index.html"] + [p["page"] for p in cfg["products"]] + [a["page"] for a in cfg.get("blog", [])]
        sitemap = ['<?xml version="1.0" encoding="UTF-8"?>',
                   '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        for u in urls:
            sitemap.append("  <url><loc>%s</loc></url>" % (base + u))
        sitemap.append("</urlset>")
        write("sitemap.xml", "\n".join(sitemap) + "\n")
        write("robots.txt", "User-agent: *\nAllow: /\n\nSitemap: %ssitemap.xml\n" % base)
    else:
        write("robots.txt", "User-agent: *\nAllow: /\n")
        stale = os.path.join(ROOT, "sitemap.xml")
        if os.path.exists(stale):
            os.remove(stale)

    # GitHub Pages 用它跳过 Jekyll 处理，避免下划线开头的文件被吞掉
    write(".nojekyll", "")

    # 生成 favicon.svg
    site = cfg["site"]
    favicon = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#4f46e5"/><stop offset="1" stop-color="#7c3aed"/>'
        "</linearGradient></defs>"
        '<rect width="64" height="64" rx="14" fill="url(#g)"/>'
        '<text x="32" y="43" text-anchor="middle" font-family="Helvetica,Arial,sans-serif" '
        'font-size="30" font-weight="700" fill="#ffffff">%s</text></svg>'
        % html.escape(site["logoText"][:2])
    )
    write("assets/img/favicon.svg", favicon)

    print("已生成 %d 个文件：" % len(written))
    for w in written:
        print("  -", w)


if __name__ == "__main__":
    main()
