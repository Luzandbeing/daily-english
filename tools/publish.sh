#!/usr/bin/env bash
# 一键发布：重建目录页 → 提交 → 推送到 GitHub Pages。
#
# 首次使用前，请先运行一次：
#   tools/setup_remote.sh <你的GitHub用户名>/<仓库名>
#
# 之后每次生成新的学习页，只要执行：
#   tools/publish.sh
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$PWD"

if [ ! -d .git ]; then
  echo "错误：当前目录还不是 git 仓库。请先执行 tools/setup_remote.sh" >&2
  exit 1
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  echo "错误：还没有配置 origin 远端。请先执行 tools/setup_remote.sh <用户名>/<仓库名>" >&2
  exit 1
fi

echo "==> 1/4 重建目录页 index.html"
python3 tools/build_index.py

echo "==> 2/4 暂存改动"
git add -A
if git diff --cached --quiet; then
  echo "    没有新改动，直接检查是否需推送。"
else
  git status --short
fi

echo "==> 3/4 提交"
if ! git diff --cached --quiet; then
  stamp="$(date '+%Y-%m-%d %H:%M')"
  git commit -q -m "更新学习页 ${stamp}"
  echo "    已提交：更新学习页 ${stamp}"
else
  echo "    无需提交。"
fi

echo "==> 4/4 推送"
branch="$(git rev-parse --abbrev-ref HEAD)"
git push origin "$branch"
echo
echo "完成。站点地址（首次需等 1-2 分钟构建）："
echo "  $(git remote get-url origin | sed -E 's#git@github.com:([^/]+)/(.+)\.git#https://\1.github.io/\2/#')"
