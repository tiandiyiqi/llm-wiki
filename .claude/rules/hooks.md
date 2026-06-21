# 钩子系统（Hooks System）

## 钩子类型（Hook Types）

- **工具调用前（PreToolUse）**：在工具执行之前（验证、参数修改）
- **工具调用后（PostToolUse）**：在工具执行之后（自动格式化、检查）
- **会话终止（Stop）**：当会话结束时（最终验证）

## 插件使用显性告知

在工作过程中一旦使用了当前插件的任何功能，必须在对话中显性告知，且使用以下固定格式：

【插件提醒】已使用插件功能：{功能名称}。触发位置：{动作/请求}。

## 当前已配置的钩子（Current Hooks）（位于 ~/.claude/settings.json 中）

### 工具调用前（PreToolUse）

- **tmux 提醒**：针对耗时较长的命令（npm, pnpm, yarn, cargo 等）建议使用 tmux
  - 具备 heredoc 感知：仅检测实际执行的命令，忽略 heredoc/here-string 中的文本内容
- **git push 审查**：在推送（push）之前打开 Zed 进行代码审查
- **文档拦截器（doc blocker）**：拦截不必要的 .md/.txt 文件创建
  - 目录白名单：`docs/`、`specs/`、`design/`、`plans/`、`guides/`、`wiki/`、`.claude/plans/`
  - 文件白名单：README.md、CLAUDE.md、AGENTS.md、CONTRIBUTING.md、CHANGELOG.md
  - 拦截时提供放行指引（如何修改白名单）

### 工具调用后（PostToolUse）

- **PR 创建**：记录 PR URL 和 GitHub Actions 状态
- **Prettier**：编辑后自动格式化 JS/TS 文件
- **TypeScript 检查**：编辑 .ts/.tsx 文件后运行 tsc
- **console.log 警告**：对已编辑文件中的 console.log 发出警告

### 会话终止（Stop）

- **console.log 审计**：在会话结束前检查所有已修改的文件中是否存在 console.log

## 钩子设计原则

1. **heredoc 感知**：Bash 钩子在匹配命令前先剥离 heredoc/here-string 内容，避免将文档文本误判为实际命令
2. **可操作的拦截消息**：被拦截时，钩子会提示具体的放行方式（修改白名单、设置环境变量等）
3. **目录级白名单**：文档拦截器支持目录级放行，而非仅硬编码文件名

## 自动授权许可（Auto-Accept Permissions）

请谨慎使用：

- 仅对受信任且定义明确的任务方案启用
- 在探索性工作中禁用
- 严禁使用 `dangerously-skip-permissions` 标志
- 改为在 `~/.claude.json` 中配置 `allowedTools`

## TodoWrite 最佳实践

使用 TodoWrite 工具（Tool）以：

- 跟踪多步骤任务的进度
- 验证对指令的理解程度
- 实现实时引导（steering）
- 展示细粒度的实现步骤

待办事项列表（Todo list）能够揭示：

- 步骤顺序错乱
- 遗漏项
- 多余的不必要项
- 粒度错误
- 需求误读
