# AI Pro Service

中英双语静态网站：中文页面保留现有网址，英文页面位于 `/en/`。页面由本地 Python 构建，不需要网站后端或外部 CDN。

## 本地构建

当前项目依赖 Python 3.9 或更高版本。首次构建时安装依赖：

```bash
python3 -m pip install -r requirements.txt
python3 tools/build.py
python3 -m http.server 8080
```

浏览器打开 `http://127.0.0.1:8080/`。英文首页为 `/en/`。文章草稿会生成到忽略目录 `.preview/drafts/`，不会进入公开页面或 sitemap。

## 内容维护

- 中文站点文案和商品价格以 `data/site.json` 为准；英文文案维护在 `data/site.en.json`。英文版本共用中文配置中的价格、套餐标识和购买链接，避免报价分叉。
- 新文章各写一个中文和英文 Markdown 文件，分别放在 `content/articles/zh-CN/` 与 `content/articles/en/`；两份文件使用相同文件名和 `translation_key`。
- Front matter 必填字段：`title`、`description`、`date_published`、`date_updated`、`category`、`translation_key`、`status`。可选字段：`related_page`、`related_articles`。
- `status: draft` 只生成到 `.preview/drafts/`。审核通过后将对应语言文件改成 `status: published`，再重新构建；只有已发布文章进入列表和 sitemap。
- 现有中文注册教程仍使用 `blog/chatgpt-register-guide.html`。不要手改 `index.html`、`en/`、商品页或 `blog/*.html`，这些都是生成文件。

语言版本使用独立 URL、canonical 和 `hreflang`。首次访问时浏览器语言只显示切换提示，不强制跳转；用户可通过顶部语言切换保留偏好。外部店铺和结算页保持中文，英文商品页会标注这一点。

## 托管

这个网站用于商业充值服务。依据 [GitHub Pages 使用限制](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)，GitHub Pages 不适合作为主要商业/电商托管；代码可以保存在 GitHub，公开部署前应迁移到适合商业网站的静态托管平台。当前工作区只做本地构建，不会自动推送或部署。

## 仓库结构

```text
data/site.json                 中文业务内容与价格
data/site.en.json              英文界面与商品文案
content/articles/zh-CN/        中文文章 Markdown
content/articles/en/           英文文章 Markdown
tools/build.py                 静态页面生成器
assets/css/                    全站样式
assets/js/site.js              菜单、语言提示、客服与 FAQ 交互
```
