# 支持哪些 AI

两种收法：

- **导出提示词**：任何能对话的 AI 都行。把 [`references/export-prompt.md`](../references/export-prompt.md) 里那段话发给它。
- **复制原始记忆文件**：记忆本来就是你电脑上的文件的那些 AI。括号里是脚本用的来源名。

| AI | 怎么收 | 记忆在哪 | 状态 |
|---|---|---|---|
| 任何能对话的 AI（豆包、各种网页版助手……） | 导出提示词 | 在它的服务器上 | 在三个云端助手上实测过，包括让它们每周定时导出 |
| Claude Code（`claude-code`） | 复制文件 | `~/.claude/projects/*/memory/` | 已实测 |
| OpenClaw（`openclaw`） | 复制文件 | 主工作区 `~/.openclaw/workspace/` 的 `MEMORY.md`、`USER.md`、`DREAMS.md` 和 `memory/` | 在作者的一台机器上实测：试运行找到了文件，凭据闸门拦下 2 份；让它替主人把一份导出文件放进收件箱也试过 |
| Codex CLI（`codex`） | 复制文件 | `~/.codex/memories/` | 在一台机器上试运行找到了文件，未完整实测 |
| WorkBuddy（`workbuddy`） | 复制文件 + 导出提示词 | `~/.workbuddy/` 下的几份 Markdown、`~/.workbuddy/memory/`、各工作区的 `.workbuddy/memory/` | 试运行找到了文件；它设置面板里的「记忆」是否也在这些文件里没有核实，所以两种都做 |
| 千问办公（`qwenwork`）/ QoderWork（`qoderwork`） | 复制文件 | `~/.qwenworkcn/awareness/main/`、`~/qoderwork/awareness/main/` | 按官方文档写的，未实测。它自己也有「备份与恢复」 |
| Qoder CLI（`qoder`） | 复制文件 | `~/.qoder/memory/`、`~/.qoder/projects/*/memory/` | 按官方文档写的，未实测。自动记忆默认是关的 |
| Qwen Code（`qwen-code`） | 复制文件 | `~/.qwen/projects/*/memory/` | 按官方文档写的，未实测 |
| 智谱 ZCode（`zcode`） | 复制文件 | `~/.zcode/cli/memories/projects/*/memory/` | 按官方文档写的，未实测。记忆默认是关的，没开过就没有文件 |
| 智谱 AutoClaw | 导出提示词 | 本机有记忆文件，但路径只有第三方说法、新版可能变了 | 路径核实前先用导出提示词 |
| 智谱清言、Z.ai、AutoGLM | 导出提示词 | 在它的服务器上；官方没查到记忆功能 | 未实测。它可能回答「我没有关于你的记忆」，那是实话 |
| Grok Build（`grok-build`） | 复制文件 | `~/.grok/memory-v2/` | 按本机目录写的，未实测 |
| Pi（`pi`） | 复制文件 | `~/.pi/agent/memory/` | 在作者的一台机器上实测过一次（2026-10-08） |

豆包聊天版官方只能查看和删除记忆、没有导出，用导出提示词。

不装技能也能复制文件：在终端运行 `bash scripts/collect-local.sh <来源名> --dry-run` 先看会交什么，去掉 `--dry-run` 就是真的复制。

复制文件的脚本带一道凭据闸门（像是有密码、密钥的文件不复制，只列文件名）。它只认常见写法，不是保证；`tests/guard-test.sh` 是它的自测。
