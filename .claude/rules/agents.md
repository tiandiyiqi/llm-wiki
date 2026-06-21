# 智能体编排 (Agent Orchestration)

## 可用智能体 (Available Agents)

位于 `~/.claude/agents/`：

| 智能体 (Agent) | 用途 | 适用场景 |
|-------|---------|-------------|
| planner | 实现规划 | 复杂特性、重构 |
| architect | 系统设计 | 架构决策 |
| tdd-guide | 测试驱动开发 (TDD) | 新特性、Bug 修复 |
| code-reviewer | 代码审查 | 代码编写/修改后 |
| security-reviewer | 安全分析 | 提交代码前 |
| build-error-resolver | 修复构建错误 | 构建失败时 |
| e2e-runner | 端到端 (E2E) 测试 | 关键用户流程 |
| refactor-cleaner | 冗余代码清理 | 代码维护 |
| doc-updater | 文档更新 | 更新文档 |

## 立即调用智能体 (Immediate Agent Usage)

以下情况无需用户提示即可直接调用：
1. 复杂特性请求 - 使用 **planner** 智能体
2. 刚刚编写/修改的代码 - 使用 **code-reviewer** 智能体
3. Bug 修复或新特性 - 使用 **tdd-guide** 智能体
4. 架构决策 - 使用 **architect** 智能体

## 并行任务执行 (Parallel Task Execution)

对于相互独立的操作，**务必**使用并行任务执行。

### 并行执行决策矩阵

| 场景 | 推荐 | 原因 |
|------|------|------|
| 代码审查 + 安全审查 | ✅ 并行 | 完全独立 |
| 规划 + 架构设计 | ✅ 并行 | 可独立进行，后续合成 |
| 多维度分析 | ✅ 并行 | 各维度独立 |
| 多个独立 Bug 修复 | ✅ 并行 | 触及不同文件 |
| 规划 → 编码 | ❌ 顺序 | 编码依赖规划结果 |
| 编码 → 测试 | ❌ 顺序 | 测试依赖实现代码 |
| 构建修复 → 验证 | ❌ 顺序 | 验证依赖修复结果 |

### 预定义并行工作流

```markdown
# parallel-review：多维度并行审查
同时启动：
├→ code-reviewer（代码质量）
├→ security-reviewer（安全性）
└→ architect（架构合理性）
↓ 合成统一审查报告

# parallel-plan：多角度并行规划
同时启动：
├→ planner（实施规划）
├→ architect（架构设计）
└→ security-reviewer（安全分析）
↓ 合成综合规划文档

# hybrid-feature：混合功能开发
阶段 1（顺序）：planner → 实施计划
阶段 2（并行）：tdd-guide + architect
阶段 3（并行）：code-reviewer + security-reviewer
阶段 4（顺序）：合成最终报告
```

### 并行执行要点

- 通过 `Task` 工具的 `run_in_background=true` 实现
- 子智能体提示词必须自包含（看不到主对话）
- 通过文件共享上下文（`.claude/plans/parallel-context.md`）
- 智能体数量不超过 6 个
- 详细模式参见 `skills/parallel-patterns/SKILL.md`
- 协调规范参见 `helpers.md#并行执行协调`

## 多维度分析 (Multi-Perspective Analysis)

针对复杂问题，使用分角色子智能体：
- 事实审查员 (Factual Reviewer)
- 资深工程师 (Senior Engineer)
- 安全专家 (Security Expert)
- 一致性审查员 (Consistency Reviewer)
- 冗余检查员 (Redundancy Checker)
