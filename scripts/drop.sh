#!/usr/bin/env bash
# mempack · 把一份已经导出好的记忆（一个文件或一个文件夹）放进收件箱。
# 用法：drop.sh <文件或文件夹> <来源名>      例：drop.sh ~/Downloads/某助手-记忆导出.md 某助手
# 网页版、手机版 AI 导出的文件用它送进去。只放不读：不打开收件箱里已有的东西，也不检查导出文件的内容。
set -euo pipefail
item="${1:-}"; src="${2:-}"
if [ -z "$item" ] || [ -z "$src" ] || [ ! -e "$item" ]; then
  echo "用法：drop.sh <文件或文件夹> <来源名>" >&2; exit 2
fi
case "$src" in */*|-*) echo "来源名里不要带斜杠，也不要以横线开头" >&2; exit 2 ;; esac
. "$(dirname -- "$0")/_config.sh"
name="${src}-$(date +%Y%m%d-%H%M%S)"
if [ -n "$MEMORY_REMOTE" ]; then
  mempack_sweep; staging="$(mktemp -d "${TMPDIR:-/tmp}/mempack-outbox.XXXXXX")"; trap 'rm -rf -- "$staging"' EXIT; trap 'exit 130' INT TERM HUP
  mkdir -p -- "$staging/$name"; cp -Rp -- "$item" "$staging/$name/"; chmod -R go-rwx "$staging"
  if mempack_send "$staging/$name"; then
    echo "已放进 ${mempack_sent_to}；本机临时副本已删，你原来的那份没动。"
  else
    echo "没送到：${MEMORY_REMOTE} 都连不上。什么都没放。" >&2; exit 1
  fi
else
  dest="$MEMORY_HOME/inbox/$name"
  mkdir -p -- "$dest"; cp -Rp -- "$item" "$dest/"; chmod -R go-rwx "$MEMORY_HOME/inbox"
  echo "已放进 ${dest/#$HOME/~}；你原来的那份没动。"
fi
