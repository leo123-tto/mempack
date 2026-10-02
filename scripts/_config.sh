# mempack · 读配置。被 collect-local.sh 和 drop.sh 引用，不单独运行。
# 配置文件：~/.config/mempack/config（可用环境变量 MEMPACK_CONFIG 换位置），每行 键=值，只认下面两个键：
#   MEMORY_HOME=记忆文件夹在本机的位置（不写就是 ~/mempack-data）
#   MEMORY_REMOTE=记忆文件夹在另一台机器上的位置，写成 主机:路径（就是 rsync / ssh 认的写法）；
#                 可以写几个，空格隔开，按顺序试，比如家里的地址在前、外出时的地址在后
# 环境变量里设了同名的值，以环境变量为准。配置文件只当数据读，不执行。
mempack_cfg="${MEMPACK_CONFIG:-$HOME/.config/mempack/config}"
if [ -f "$mempack_cfg" ]; then
  while IFS='=' read -r k v; do
    v="${v%\"}"; v="${v#\"}"
    case "$k" in
      MEMORY_HOME)   [ -n "${MEMORY_HOME:-}" ]   || MEMORY_HOME="${v/#\~/$HOME}" ;;
      MEMORY_REMOTE) [ -n "${MEMORY_REMOTE:-}" ] || MEMORY_REMOTE="$v" ;;
    esac
  done < <(grep -E '^(MEMORY_HOME|MEMORY_REMOTE)=' "$mempack_cfg")
fi
MEMORY_HOME="${MEMORY_HOME:-$HOME/mempack-data}"
MEMORY_REMOTE="${MEMORY_REMOTE:-}"

# 把本机的一个文件夹送进远端记忆文件夹的 inbox/。只写不读：不列、不取远端已有的东西。
# 用法：mempack_send <本机文件夹>；成功时把送到的位置写进变量 mempack_sent_to
mempack_send() {
  local pkg="$1" target
  for target in $MEMORY_REMOTE; do
    if rsync -a -e "ssh -o BatchMode=yes -o ConnectTimeout=8" -- "$pkg" "$target/inbox/" 2>/dev/null; then
      mempack_sent_to="$target/inbox/$(basename -- "$pkg")"; return 0
    fi
  done
  return 1
}

# 上一次如果是被强行杀掉的，临时目录里可能剩下一份没送出去的记忆。超过一小时的旧临时目录在这里清掉。
mempack_sweep() {
  find "${TMPDIR:-/tmp}" -maxdepth 1 -type d -name 'mempack-outbox.*' -mmin +60 -exec rm -rf -- {} + 2>/dev/null || true
}
