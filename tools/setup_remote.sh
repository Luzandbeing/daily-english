#!/usr/bin/env bash
# 配置 GitHub 远端（只需运行一次）。
#
# 用法：
#   tools/setup_remote.sh <GitHub用户名>/<仓库名> [分支名]
#
# 例：
#   tools/setup_remote.sh luz/english-study
#
# 本脚本只写入仓库级配置（.git/config），不修改 ~/.ssh 或全局 git 配置。
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$PWD"

SLUG="${1:-}"
BRANCH="${2:-main}"

if [ -z "$SLUG" ]; then
  echo "用法：tools/setup_remote.sh <GitHub用户名>/<仓库名> [分支名]" >&2
  exit 1
fi
case "$SLUG" in
  */*) ;;
  *) echo "错误：参数要写成 用户名/仓库名 的形式，例如 luz/english-study" >&2; exit 1 ;;
esac

KEY="$ROOT/.deploy_key"
KNOWN="$ROOT/.gh_known_hosts"

if [ ! -f "$KEY" ]; then
  echo "错误：找不到部署密钥 $KEY" >&2
  exit 1
fi

# --- 1. 准备 GitHub 官方主机密钥（避免 MITM 告警）---------------------------
if [ ! -s "$KNOWN" ]; then
  echo "==> 从 api.github.com/meta 获取 GitHub 官方 SSH 主机密钥"
  tmp="$(mktemp)"
  curl -sS --max-time 25 https://api.github.com/meta -o "$tmp"
  python3 - "$tmp" "$KNOWN" <<'PY'
import json, sys
meta = json.load(open(sys.argv[1]))
keys = meta.get("ssh_keys") or []
if not keys:
    raise SystemExit("api.github.com/meta 未返回 ssh_keys")
with open(sys.argv[2], "w") as f:
    for k in keys:
        f.write(f"github.com {k}\n")
print(f"    已写入 {len(keys)} 条主机密钥到 {sys.argv[2]}")
PY
  rm -f "$tmp"
else
  echo "==> 已存在 .gh_known_hosts，跳过下载"
fi

# --- 2. 仓库级 ssh 配置（不动全局）----------------------------------------
echo "==> 配置仓库级 core.sshCommand"
git config core.sshCommand \
  "ssh -i '$KEY' -o UserKnownHostsFile='$KNOWN' -o IdentitiesOnly=yes"

# --- 3. 远端 ----------------------------------------------------------------
echo "==> 配置 origin = git@github.com:$SLUG.git"
git remote remove origin 2>/dev/null || true
git remote add origin "git@github.com:$SLUG.git"

# --- 4. 验证认证 ------------------------------------------------------------
echo "==> 验证 SSH 认证"
if out="$(ssh -i "$KEY" -o UserKnownHostsFile="$KNOWN" -o IdentitiesOnly=yes \
          -o ConnectTimeout=12 -T git@github.com 2>&1)"; then
  echo "    $out"
  echo "    ✅ 认证成功"
else
  case "$out" in
    *"successfully authenticated"*)
      echo "    ✅ 认证成功" ;;
    *)
      echo "    ❌ 认证失败："
      echo "$out" | sed 's/^/       /'
      echo
      echo "    请确认：已把下面这把公钥添加到 GitHub（Settings → SSH and GPG keys，"
      echo "    或仓库 Settings → Deploy keys 并勾选 Allow write access）："
      echo
      sed 's/^/      /' "$KEY.pub"
      exit 1 ;;
  esac
fi

# --- 5. 当前分支 ------------------------------------------------------------
cur="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '')"
if [ "$cur" != "$BRANCH" ]; then
  echo "==> 把当前分支 ${cur:-?} 改名为 $BRANCH"
  git branch -M "$BRANCH"
fi

echo
echo "配置完成。接着执行：  tools/publish.sh"
