---
name: supercode-init
description: This skill should be used when initializing or updating Supercode rules in a project. Typical triggers include "initialize supercode", "install rules", "setup supercode", "update rules", and "run supercode init". Provides one-click rule installation and configuration.
---

# Supercode 初始化技能

> 自动安装和配置 Supercode 规则的完整技能

## 概述

这个技能提供一键初始化 Supercode 环境的功能，自动处理规则安装、冲突检测和验证。

## 核心功能

### 1. 环境检测

```bash
# 检测 Claude Code 配置目录
if [ -d ~/.claude ]; then
  echo "✅ Claude Code 已安装"
else
  echo "❌ Claude Code 未安装"
  exit 1
fi

# 检测项目目录
if [ -f package.json ] || [ -f pyproject.toml ] || [ -f go.mod ]; then
  echo "✅ 项目目录已检测"
  PROJECT_DETECTED=true
else
  PROJECT_DETECTED=false
fi
```

### 2. 安装位置选择

**项目级安装（推荐）**
- 位置：`.claude/rules/`
- 范围：仅当前项目
- 优先级：高于用户级规则

**用户级安装**
- 位置：`~/.claude/rules/`
- 范围：所有项目
- 优先级：低于项目级规则

### 3. 规则列表

Supercode 包含以下 6 个规则文件：

```
rules/
├── helpers.md          # 标准化操作参考中心（工作流模板、检查清单、代码模式）
├── coding-style.md     # 代码风格、不可变性
├── git-workflow.md     # Git 工作流、提交格式
├── performance.md      # 模型选择、上下文管理
├── hooks.md            # 钩子系统、自动化
└── agents.md           # 智能体编排、并行执行
```

> 注：TDD、验证、安全审查、并行执行等由 Superpowers skills 覆盖，不再作为独立规则文件。

### 4. 冲突处理

**检测现有规则**
```bash
if [ -d "$TARGET_DIR/rules" ]; then
  echo "⚠️  检测到现有规则"
  # 创建备份
  cp -r "$TARGET_DIR/rules" "$TARGET_DIR/rules.backup.$(date +%s)"
  echo "✅ 已备份到 rules.backup.*"
fi
```

**覆盖策略**
- 自动备份现有规则
- 使用新规则覆盖
- 保留备份供恢复

### 5. 安装流程

```
步骤 1：验证环境
  ✓ Claude Code 已安装
  ✓ 项目目录已检测
  ✓ 权限正确

步骤 2：选择安装位置
  ✓ 项目级（推荐）
  ✓ 用户级

步骤 3：备份现有规则
  ✓ 检测现有规则
  ✓ 创建时间戳备份
  ✓ 验证备份完整

步骤 4：复制新规则
  ✓ 创建目标目录
  ✓ 复制所有规则文件
  ✓ 设置正确权限

步骤 5：验证安装
  ✓ 检查文件数量（6 个）
  ✓ 验证文件内容
  ✓ 检查权限

步骤 6：显示结果
  ✓ 安装位置
  ✓ 已安装规则列表
  ✓ 下一步建议
```

### 6. 验证检查清单

```bash
# 验证所有规则文件
RULES=(
  "helpers.md"
  "coding-style.md"
  "git-workflow.md"
  "performance.md"
  "hooks.md"
  "agents.md"
)

for rule in "${RULES[@]}"; do
  if [ -f "$TARGET_DIR/rules/$rule" ]; then
    echo "✅ $rule"
  else
    echo "❌ $rule (缺失)"
  fi
done
```

### 7. 错误处理

**权限错误**
```bash
if [ ! -w "$TARGET_DIR" ]; then
  echo "❌ 权限不足：无法写入 $TARGET_DIR"
  echo "💡 尝试：sudo chown -R $USER ~/.claude"
  exit 1
fi
```

**磁盘空间**
```bash
REQUIRED_SPACE=1000  # KB
AVAILABLE_SPACE=$(df "$TARGET_DIR" | tail -1 | awk '{print $4}')

if [ "$AVAILABLE_SPACE" -lt "$REQUIRED_SPACE" ]; then
  echo "❌ 磁盘空间不足"
  exit 1
fi
```

**网络问题**
```bash
if ! curl -s https://github.com/tiandiyiqi/supercode > /dev/null; then
  echo "⚠️  无法连接到 GitHub，使用本地规则"
fi
```

## 使用场景

### 场景 1：全新安装

```bash
# 用户刚安装 Supercode 插件
/supercode:init

# 选择：项目级安装
# 结果：规则复制到 .claude/rules/
# 建议：重启 Claude Code
```

### 场景 2：更新规则

```bash
# 用户想更新到最新规则
/supercode:init

# 选择：用户级安装
# 结果：现有规则备份，新规则安装
# 显示：更新了 3 个规则
```

### 场景 3：恢复备份

```bash
# 用户想恢复之前的规则
mv ~/.claude/rules.backup.1234567890 ~/.claude/rules

# 验证恢复
ls -la ~/.claude/rules/
```

## 输出示例

```
🚀 Supercode 初始化

检测环境...
✅ Claude Code 已安装 (~/.claude)
✅ 项目目录已检测 (package.json)
✅ 权限正确

选择安装位置：
1. 项目级安装（推荐）- .claude/rules/
2. 用户级安装 - ~/.claude/rules/

选择 [1-2]: 1

备份现有规则...
✅ 已备份到 .claude/rules.backup.1709000000

复制新规则...
✅ helpers.md
✅ coding-style.md
✅ git-workflow.md
✅ performance.md
✅ hooks.md
✅ agents.md

验证安装...
✅ 所有 6 个规则文件已安装
✅ 文件内容完整
✅ 权限正确

✨ 初始化完成！

已安装位置：.claude/rules/
已安装规则：6 个
备份位置：.claude/rules.backup.1709000000

下一步：
1. 重启 Claude Code
2. 查看 helpers.md 了解标准化操作
3. 开始使用 Supercode 工作流

💡 提示：运行 /supercode:init 可以随时更新规则
```

## 集成点

### 与 plugin.json 的关系

```json
{
  "name": "supercode",
  "skills": ["./skills/", "./commands/"],
  "commands": [
    "./commands/init.md"
  ]
}
```

### 与 marketplace.json 的关系

```json
{
  "plugins": [{
    "name": "supercode",
    "description": "...包含 /supercode:init 命令..."
  }]
}
```

## 故障排除

### 问题 1：权限被拒绝

```bash
# 症状
❌ Permission denied: ~/.claude/rules

# 解决方案
sudo chown -R $USER ~/.claude
chmod -R 755 ~/.claude
```

### 问题 2：规则未生效

```bash
# 症状
规则已安装但 Claude Code 未识别

# 解决方案
1. 重启 Claude Code
2. 检查规则文件权限：chmod 644 ~/.claude/rules/*.md
3. 验证规则格式：head -5 ~/.claude/rules/helpers.md
```

### 问题 3：冲突的规则

```bash
# 症状
多个规则定义了相同的行为

# 解决方案
1. 检查备份：ls -la ~/.claude/rules.backup.*
2. 比较规则：diff ~/.claude/rules.backup.*/helpers.md ~/.claude/rules/helpers.md
3. 手动合并或选择一个版本
```

## 最佳实践

1. **定期更新** - 每月运行一次 `/supercode:init` 以获取最新规则
2. **备份管理** - 定期清理旧备份：`rm ~/.claude/rules.backup.*`
3. **版本控制** - 项目级规则应提交到 git：`git add .claude/rules/`
4. **文档同步** - 规则更新时更新 README 中的说明

## 相关资源

- [helpers.md](../rules/helpers.md) - 标准化操作参考
- [README.zh-CN.md](../README.zh-CN.md) - 完整安装指南
- [MIGRATION.md](../MIGRATION.md) - 迁移指南
