#!/usr/bin/env bash
# 在局域网内共享学习页，手机同 Wi-Fi 即可访问，全程不碰互联网。
#
# 用法：
#   tools/serve.sh            # 默认 8000 端口
#   tools/serve.sh 8080       # 指定端口
#
# 按 Ctrl-C 停止。
set -euo pipefail

cd "$(dirname "$0")/.."

PORT="${1:-8000}"

# --- 找出本机在局域网里的 IP ------------------------------------------------
ip=""
for iface in en0 en1 en2; do
  ip="$(ipconfig getifaddr "$iface" 2>/dev/null || true)"
  [ -n "$ip" ] && break
done
if [ -z "$ip" ]; then
  ip="$(route -n get default 2>/dev/null | awk '/interface:/{print $2}' \
        | xargs -I{} ipconfig getifaddr {} 2>/dev/null || true)"
fi

if [ -z "$ip" ]; then
  echo "⚠️  没找到局域网 IP。请确认已连接 Wi-Fi，然后用下面的地址在本机浏览。"
  ip="127.0.0.1"
fi

# --- 端口占用检查 -----------------------------------------------------------
if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "⚠️  端口 $PORT 已被占用，换一个端口试，例如：tools/serve.sh $((PORT+1))"
  exit 1
fi

cat <<EOF

  ┌────────────────────────────────────────────────────────┐
  │  英语学习页 · 局域网服务已启动                          │
  └────────────────────────────────────────────────────────┘

  手机（需与这台 Mac 连同一个 Wi-Fi）打开：

      http://$ip:$PORT/

  本机浏览器打开：

      http://127.0.0.1:$PORT/

  说明：
    · 全程不访问互联网，公司网络拦截也影响不到。
    · 页面是自包含单文件，无外部依赖，手机端功能完整。
    · 此窗口需保持开着；Mac 不要休眠（可用 caffeinate 挡一下）。
    · 停止服务：按 Ctrl-C

EOF

exec python3 -m http.server "$PORT" --bind 0.0.0.0
