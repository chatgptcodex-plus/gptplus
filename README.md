# AI 会员代充值站（静态站）

多页静态站：**首页 + 6 个产品购买页 + 注册教程页**，
纯 HTML/CSS/JS，没有任何后端和外部 CDN 依赖，可以直接丢到 GitHub Pages / 任何静态托管上。

## 目录结构

```
.
├── index.html                    ← 首页（生成物，勿手改）
├── purchase-gpt.html             ← GPT / ChatGPT 充值页（生成物）
├── purchase-claude.html          ← Claude 充值页
├── purchase-gemini.html          ← Gemini / Google AI 充值页
├── purchase-perplexity.html      ← Perplexity 充值页
├── purchase-grok.html            ← Grok / SuperGrok 充值页
├── purchase-premium.html         ← X Premium(+) 充值页
├── blog/chatgpt-register-guide.html
├── sitemap.xml / robots.txt      ← 生成物
├── data/site.json                ← ★ 所有文案、价格、套餐、微信号都在这里
├── tools/build.py                ← 生成器：把 site.json 编译成上面的 HTML
├── tools/shot.sh                 ← 截图小工具（本地预览用，可删）
└── assets/
    ├── css/main-header.css       ← 导航栏 / 公告条样式
    ├── css/style.css             ← 全站样式
    ├── js/site.js                ← 交互：移动端菜单、客服弹窗、复制微信、FAQ、公告条
    └── img/wechat-qr.svg         ← ★ 二维码占位图，替换成你自己的
```

> `index.html`、`purchase-*.html`、`blog/*.html` 都是 `tools/build.py` 生成的。
> 直接改 HTML 也能用，但下次重新生成会被覆盖 —— 要改内容请改 `data/site.json` 再重新生成。

## 三步改成你自己的站

### 1. 改 data/site.json

改完执行：

```bash
python3 tools/build.py
```

最常改的几项：

| 位置 | 含义 |
| --- | --- |
| `site.brandName` / `site.logoText` | 品牌名、左上角 logo 文字 |
| `contact.wechatList` | 客服微信号（可以有多个） |
| `contact.orderQueryUrl` | 「查询订单」按钮跳转的地址；留空则点开客服弹窗 |
| `purchase.defaultBuyUrl` | **充值店铺链接**。填上之后，全站所有「立即购买」都会跳转过去 |
| `noticeBar.text` | 顶部黄色公告条文案（`enabled: false` 可关掉） |
| `products[].sections` | 每个产品页的套餐、价格、对比表、说明 |

给单个套餐单独设置链接（覆盖上面的默认值），在 `sections` 里对应套餐对象加一行：

```json
{ "name": "ChatGPT Plus", "price": "179", "buyUrl": "https://你的店铺.com/plus", ... }
```

### 2. 换二维码

把你的微信二维码图片覆盖到 `assets/img/wechat-qr.svg` 这个路径就行（PNG 也可以，把
`contact.qrImage` 改成 `assets/img/wechat-qr.png`）。

### 3. 发布到 GitHub Pages

**方式一：命令行一键发布（推荐）**

先在 GitHub 网页上新建一个空仓库（不要勾选 Add README），然后在终端里跑：

```bash
tools/publish.sh <你的GitHub用户名> <仓库名>
# 例如： tools/publish.sh zhangsan gptplus
```

脚本会自动完成：写回 `baseUrl` → 重新生成页面 → `git init/commit` → 推送；
密码处粘贴 [Personal Access Token](https://github.com/settings/tokens)（勾选 `repo` 权限），
不是登录密码。推送完去仓库 `Settings → Pages`，Source 选 `Deploy from a branch`、
分支 `main`、目录 `/ (root)`，等 1-2 分钟即可访问：

- 仓库名普通：`https://<用户名>.github.io/<仓库名>/`
- 仓库名写成 `<用户名>.github.io`：`https://<用户名>.github.io/`（地址最干净）

**方式二：网页拖拽上传（零命令行）**

GitHub 新建仓库 → `Add file → Upload files` → 把 `index.html`、`purchase-*.html`、
`blog/`、`assets/`、`.nojekyll` 一起拖进去 → Commit → 再去 `Settings → Pages` 开分支。
（`data/`、`tools/` 是源文件，传不传都不影响页面。）

> 发布后记得把 `data/site.json` 里的 `site.baseUrl` 填成真实网址，再跑一次
> `python3 tools/build.py`，`sitemap.xml` 和 `robots.txt` 里的地址才正确。
> 仓库里已包含 `.nojekyll`，避免 GitHub 的 Jekyll 处理干扰静态文件。

**本地预览**（推荐，直接双击 html 也能看）：

```bash
python3 -m http.server 8080
# 浏览器打开 http://127.0.0.1:8080
```

## 交互与细节（都是自动的，不用配）

- 顶部固定导航 + 移动端汉堡菜单，`更多服务` 下拉列出全部页面
- 顶部公告条可关闭，关闭状态记在 localStorage，不会每次弹
- 右下角悬浮「客服」按钮 → 弹窗展示服务清单 + 二维码 + 微信号（点微信号即复制）
- 购买页套餐卡片的「立即购买」：配了店铺链接就新窗口打开，没配就弹客服
- 首页常见问题手风琴折叠
- 无外链 CDN，图标全部内联 SVG，断网也能正常显示

## 部署前请自行确认

- 页脚已注明「本站为第三方代充值服务平台，与 OpenAI、Anthropic、Google、xAI 等公司无隶属关系」，
  请保留这句风险提示；如果你的经营主体有备案号，填到 `site.icp`。
- 页面里的价格、权益、到账时效目前是示例数据，**上线前必须核对成你的真实报价**。
- 优惠幅度（`save.percent`）是按示例价算的，改价后记得同步改。
