#!/usr/bin/env bash
# mempack · 上传记忆：把一个本机命令行 AI 自己的记忆文件原样复制到投递箱。
# 用法：collect-local.sh <来源> [--dry-run]
# 来源：claude-code codex grok-build openclaw pi qoder qwen-code qwenwork qoderwork workbuddy zcode
# 只复制、不读取投递箱；疑似含凭据的文件不复制，只在清单里列出文件名。
# 不跟随软链接：find 不带 -L，软链进来的目录不会被遍历，软链的文件也跳过。
# 记忆文件夹在另一台机器上时（配置了 MEMORY_REMOTE，见 _config.sh），先收到本机临时目录，送过去之后删掉本机这份。
set -euo pipefail

src="${1:-}"; dry="${2:-}"
. "$(dirname -- "$0")/_config.sh"
stamp="$(date +%Y%m%d-%H%M%S)"
staging=""
if [ -n "$MEMORY_REMOTE" ] && [ -z "${MEMORY_INBOX:-}" ]; then
  [ "$dry" = "--dry-run" ] || { mempack_sweep; staging="$(mktemp -d "${TMPDIR:-/tmp}/mempack-outbox.XXXXXX")"; trap 'rm -rf -- "$staging"' EXIT; trap 'exit 130' INT TERM HUP; }
  inbox="${staging:-/nonexistent}"
else
  inbox="${MEMORY_INBOX:-$MEMORY_HOME/inbox}"
fi

# 每个来源的记忆位置：plan 里每一行是「根目录|find 条件」
case "$src" in
  claude-code) plan=("$HOME/.claude/projects|-path */memory/* -name *.md") ;;
  codex)       plan=("$HOME/.codex/memories|-name *.md -not -path */skills/* -not -path */extensions/* -not -path */.git/* -not -path */.tmp/*") ;;
  grok-build)  plan=("$HOME/.grok/memory-v2|-name *.md") ;;
  openclaw)    plan=("${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}|-maxdepth 1 ( -name MEMORY.md -o -name USER.md -o -name DREAMS.md )" "${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}/memory|-name *.md") ;;
  pi)          plan=("$HOME/.pi/agent/memory|-name *.md") ;;
  qoder)       plan=("$HOME/.qoder/memory|-name *.md" "$HOME/.qoder/projects|-path */memory/* -name *.md") ;;
  qwen-code)   plan=("$HOME/.qwen/projects|-path */memory/* -name *.md") ;;
  qwenwork)    plan=("$HOME/.qwenworkcn/awareness/main|-name *.md") ;;
  qoderwork)   plan=("$HOME/qoderwork/awareness/main|-name *.md") ;;
  zcode)       plan=("$HOME/.zcode/cli/memories|-path */memory/* -name *.md") ;;
  workbuddy)   plan=("$HOME/.workbuddy|-maxdepth 1 -name *.md" "$HOME/.workbuddy/memory|-name *.md" "$HOME/WorkBuddy|-path */.workbuddy/memory/* -name *.md") ;;
  *) echo "用法：collect-local.sh <来源> [--dry-run]；来源可选：claude-code codex grok-build openclaw pi qoder qwen-code qwenwork qoderwork workbuddy zcode" >&2; exit 2 ;;
esac

# 凭据闸门：「密码/口令」后面紧跟带引号的值或 = 某个值、expect 脚本里的 send "…\r"、常见密钥形状。
# 宁可多拦：拦下的只列文件名，由主人决定。
guard='(密码|口令|password|passwd|passphrase)[^"'"'"'「“`]{0,12}["'"'"'「“`][A-Za-z0-9!@#$%^&*._+-]{4,}["'"'"'」”`]|(密码|口令|password|passwd|passphrase)[[:space:]]*[:：=][[:space:]]*[A-Za-z0-9!@#$%^&*._+-]{4,}|send[[:space:]]+"[^"]{4,}\\r"|(密码|口令)(是|为)[[:space:]]*[A-Za-z0-9!@#$%^&*._+-]{4,}|授权码[^A-Za-z0-9]{0,6}[A-Za-z0-9]{8,}|[a-z][a-z0-9+]*://[^/[:space:]:@]+:[^@[:space:]/]{4,}@|Bearer[[:space:]]+[A-Za-z0-9._-]{20,}|eyJ[A-Za-z0-9_-]{20,}|xox[bap]-[A-Za-z0-9-]{10,}|sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sbp_[A-Za-z0-9]{20,}|AKIA[A-Z0-9]{12,}|BEGIN [A-Z ]*PRIVATE KEY|(token|secret|api[_-]?key)[[:space:]]*[:：=][[:space:]]*[A-Za-z0-9_.-]{20,}'

dest="$inbox/${src}-$stamp"
copied=0; bytes=0; blocked=()

set -f  # find 条件里的 * 不让 shell 展开
for item in "${plan[@]}"; do
  root="${item%%|*}"; args="${item#*|}"
  [ -d "$root" ] || continue
  tag="$(basename -- "$root")"
  while IFS= read -r -d '' f; do
    [ -L "$f" ] && continue
    if grep -Eiq -- "$guard" "$f"; then
      blocked+=("${f#"$HOME"/}"); continue
    fi
    rel="$tag/${f#"$root"/}"
    if [ "$dry" != "--dry-run" ]; then
      mkdir -p -- "${dest}/files/$(dirname -- "$rel")"
      cp -p -- "$f" "${dest}/files/$rel"
    fi
    copied=$((copied+1)); bytes=$((bytes + $(wc -c <"$f")))
  done < <(find "$root" -type f $args -print0)
done
set +f

if [ "${copied}" -eq 0 ] && [ "${#blocked[@]}" -eq 0 ]; then
  echo "没有找到 ${src} 的记忆文件。这个来源可能没装、没开记忆功能，或记忆不在本机。" >&2; exit 1
fi

if [ "$dry" = "--dry-run" ]; then
  echo "【试运行，未复制】来源 ${src}：可交 ${copied} 份，约 $((bytes/1024)) KB；会被凭据闸门拦下 ${#blocked[@]} 份。"
else
  {
    echo "---"
    echo "schema: mempack/push-v1"
    echo "source_agent: ${src}"
    echo "pushed_at: $(date +%Y-%m-%dT%H:%M:%S%z)"
    echo "kind: native-files"
    echo "files: ${copied}"
    echo "bytes: $bytes"
    echo "blocked_by_credential_guard: ${#blocked[@]}"
    echo "---"
    echo
    echo "# 已拦下（疑似含密码、口令或密钥，未复制；请主人自己处理）"
    if [ "${#blocked[@]}" -eq 0 ]; then echo "无"; else printf -- '- %s\n' "${blocked[@]}"; fi
  } > "${dest}/MANIFEST.md"
  chmod -R go-rwx "$inbox"
  if [ -n "$staging" ]; then
    if mempack_send "$dest"; then
      echo "已交 ${copied} 份，约 $((bytes/1024)) KB，送到 ${mempack_sent_to}；本机没有留副本；被凭据闸门拦下 ${#blocked[@]} 份。"
    else
      echo "没送到：${MEMORY_REMOTE} 都连不上。什么都没交，本机也没有留副本。检查网络或 ssh 之后再说一次「上传记忆」。" >&2; exit 1
    fi
  else
    echo "已交 ${copied} 份，约 $((bytes/1024)) KB，放在 ${dest/#$HOME/~}；被凭据闸门拦下 ${#blocked[@]} 份。"
  fi
fi
if [ "${#blocked[@]}" -gt 0 ]; then
  echo "被拦下的文件（只列文件名）："; printf -- '- %s\n' "${blocked[@]}"
fi
