#!/usr/bin/env bash
# 一键发布到 GitHub Pages
# 用法： tools/publish.sh <GitHub用户名> [仓库名]
#   仓库名默认 gptplus；如果想用 https://<用户名>.github.io/ 这种根域名，把仓库名写成 <用户名>.github.io
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

USER="${1:-}"
REPO="${2:-gptplus}"

if [ -z "$USER" ]; then
  printf 'GitHub 用户名: '
  read -r USER
fi
[ -n "$USER" ] || { echo "用户名不能为空"; exit 1; }

if [ "$REPO" = "$USER.github.io" ]; then
  BASE_URL="https://$USER.github.io/"
else
  BASE_URL="https://$USER.github.io/$REPO/"
fi

echo "==> 目标仓库 : https://github.com/$USER/$REPO"
echo "==> 站点地址 : $BASE_URL"
echo

# ---------- 1. git 身份 ----------
if ! git config --get user.name >/dev/null; then
  printf '你的 git 昵称（会出现在提交记录里）: '
  read -r GIT_NAME
  git config --local user.name "$GIT_NAME"
fi
if ! git config --get user.email >/dev/null; then
  printf '你的邮箱（建议用 GitHub 的 noreply 邮箱，可直接回车用 %s@users.noreply.github.com）: ' "$USER"
  read -r GIT_MAIL
  [ -n "$GIT_MAIL" ] || GIT_MAIL="$USER@users.noreply.github.com"
  git config --local user.email "$GIT_MAIL"
fi

# 让 macOS 钥匙串记住 GitHub 凭据，只需输一次令牌
git config --local credential.helper osxkeychain

# ---------- 2. 把站点地址写回配置并重新生成 ----------
if command -v python3 >/dev/null 2>&1; then
  python3 - "$BASE_URL" <<'PY'
import json, re, sys
base = sys.argv[1]
p = "data/site.json"
s = open(p, encoding="utf-8").read()
# 只替换 baseUrl 的值，保留原文件的排版风格
new, n = re.subn(r'("baseUrl"\s*:\s*)"[^"]*"', lambda m: m.group(1) + '"' + base + '"', s, count=1)
if n and new != s:
    json.loads(new)  # 校验一下别写坏
    open(p, "w", encoding="utf-8").write(new)
    print("已把 baseUrl 写进 data/site.json -> " + base)
PY
  python3 tools/build.py >/dev/null && echo "已重新生成页面（sitemap/robots 用的是真实网址）"
fi

# ---------- 3. 初始化并提交 ----------
if [ ! -d .git ]; then
  git init -b main >/dev/null
  echo "已初始化 git 仓库（分支 main）"
fi

git add -A
if git diff --cached --quiet; then
  echo "没有需要提交的改动"
else
  git commit -q -m "发布 AI 会员代充值站" && echo "已提交"
fi

# ---------- 4. 关联远端并推送 ----------
# 装了 GitHub CLI 就顺手把仓库建好，省得去网页点
if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  if ! gh repo view "$USER/$REPO" >/dev/null 2>&1; then
    printf '远端仓库 %s/%s 不存在，用 gh 自动创建？[Y/n] ' "$USER" "$REPO"
    read -r ANSWER
    case "${ANSWER:-Y}" in
      [Yy]*) gh repo create "$USER/$REPO" --public --description "AI 会员代充值站" >/dev/null && echo "已创建 https://github.com/$USER/$REPO";;
      *) echo "跳过创建，请先在网页上建好空仓库再重跑本脚本"; exit 1;;
    esac
  fi
  gh auth setup-git >/dev/null 2>&1 || true
fi

if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "https://github.com/$USER/$REPO.git"
else
  git remote add origin "https://github.com/$USER/$REPO.git"
fi

echo
echo "==> 开始推送。"
if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  echo "    （已检测到 gh 登录，会自动带上凭据，无需输密码）"
else
  echo "    用户名填 GitHub 用户名，密码处粘贴 Personal Access Token（不是登录密码）"
  echo "    还没有令牌？打开 https://github.com/settings/tokens → Generate new token (classic) → 勾选 repo → 生成后复制"
fi
echo
git push -u origin main

cat <<EOF

============================================================
推送完成 ✅

接下来在网页上开一次 Pages（只需一次）：
  1. 打开 https://github.com/$USER/$REPO/settings/pages
  2. Source 选 "Deploy from a branch"
  3. Branch 选 main，目录选 / (root)，点 Save
  4. 等 1-2 分钟，访问：$BASE_URL

以后每次改完内容，只要跑：
  python3 tools/build.py && git add -A && git commit -m "更新" && git push
============================================================
EOF
