#!/usr/bin/env bash
# 截图工具：headless Chrome 写完图片后不会自动退出，这里等文件出现再结束进程。
# 用法： tools/shot.sh <页面相对路径> <输出png> <宽> <高>
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PAGE="$1"; OUT="$2"; W="${3:-1440}"; H="${4:-2400}"

mkdir -p "$ROOT/.preview"
rm -f "$OUT"
PROFILE="$(mktemp -d "$ROOT/.cpXXXXXX")"

"$CHROME" --headless --disable-gpu --no-sandbox --no-first-run --no-default-browser-check \
  --disable-extensions --disable-sync --disable-background-networking --disable-features=Translate \
  --user-data-dir="$PROFILE" --hide-scrollbars --force-device-scale-factor=1 \
  --window-size="$W,$H" --screenshot="$OUT" "file://$ROOT/$PAGE" >/dev/null 2>&1 &
CPID=$!

for _ in $(seq 1 60); do
  [ -s "$OUT" ] && { sleep 1; break; }
  sleep 1
done

kill "$CPID" 2>/dev/null
wait "$CPID" 2>/dev/null
rm -rf "$PROFILE"

if [ -s "$OUT" ]; then echo "OK  $OUT"; else echo "FAIL $OUT"; exit 1; fi
