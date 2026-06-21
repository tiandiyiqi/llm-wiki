# Everything Claude Code 强制使用规则

## 核心原则

**必须主动使用 everything-claude-code skills，不等待用户提示。**

## 强制使用场景

### 1. 任务开始前 - 规划阶段

**触发条件：** 收到任何实现任务、新功能、重构请求

**必须执行：**
```
Skill("everything-claude-code:plan")
```

**适用场景：**
- 新功能实现
- 架构变更
- 复杂重构
- 多文件修改

**例外：** 简单的单文件修改（<10 行代码）

---

### 2. 代码编写后 - 审查阶段

**触发条件：** 使用 Edit/Write 工具修改或创建代码文件后

**必须执行：**
```
Skill("everything-claude-code:code-reviewer")
```

**适用场景：**
- 所有代码修改
- 新文件创建
- 重构完成

**例外：** 配置文件修改（.json, .yml, .env）

---

### 3. 新功能/Bug 修复 - TDD 阶段

**触发条件：** 用户要求实现新功能或修复 Bug

**必须执行：**
```
Skill("everything-claude-code:tdd")
```

**工作流程：**
1. 先写测试（RED）
2. 实现功能（GREEN）
3. 重构优化（REFACTOR）
4. 验证覆盖率 80%+

---

### 4. 安全敏感代码 - 安全审查

**触发条件：** 编写以下类型的代码

**必须执行：**
```
Skill("everything-claude-code:security-review")
```

**适用场景：**
- 认证/授权代码
- 用户输入处理
- API 端点
- 数据库查询
- 文件上传
- 支付相关

---

### 5. 数据库相关 - 数据库审查

**触发条件：** 编写 SQL、创建迁移、设计 schema

**必须执行：**
```
Skill("everything-claude-code:database-reviewer")
```

**适用场景：**
- SQL 查询
- 数据库迁移
- Schema 设计
- 索引优化

---

### 6. 构建失败 - 错误修复

**触发条件：** 构建、lint、test 失败

**必须执行：**
```
Skill("everything-claude-code:build-error-resolver")
```

---

### 7. 任务完成后 - 验证循环

**触发条件：** 完成代码修改，准备提交前

**必须执行：**
```
Skill("everything-claude-code:verification-loop")
```

**验证内容：**
- 构建通过
- Lint 通过
- 测试通过
- 覆盖率达标

---

## 语言特定规则

### Go 项目
```
# 代码审查
Skill("everything-claude-code:go-review")

# 构建错误
Skill("everything-claude-code:go-build")

# TDD
Skill("everything-claude-code:go-test")
```

### Python 项目
```
# 代码审查
Skill("everything-claude-code:python-review")
```

### Django 项目
```
# 架构模式
Skill("everything-claude-code:django-patterns")

# 安全
Skill("everything-claude-code:django-security")

# TDD
Skill("everything-claude-code:django-tdd")

# 验证
Skill("everything-claude-code:django-verification")
```

### Spring Boot 项目
```
# 架构模式
Skill("everything-claude-code:springboot-patterns")

# 安全
Skill("everything-claude-code:springboot-security")

# TDD
Skill("everything-claude-code:springboot-tdd")

# 验证
Skill("everything-claude-code:springboot-verification")
```

---

## 架构决策

**触发条件：** 需要做技术选型、架构设计

**必须执行：**
```
Skill("everything-claude-code:architect")
```

---

## E2E 测试

**触发条件：** 实现关键用户流程

**必须执行：**
```
Skill("everything-claude-code:e2e-runner")
```

---

## 执行检查清单

在每次工作开始前，检查：

- [ ] 是否需要规划？→ `plan`
- [ ] 是否涉及安全？→ `security-review`
- [ ] 是否需要测试？→ `tdd`
- [ ] 是否修改代码？→ `code-reviewer`
- [ ] 是否涉及数据库？→ `database-reviewer`
- [ ] 是否需要验证？→ `verification-loop`

---

## 插件使用报告格式

每次使用 skill 后，必须报告：

```
【插件提醒】已使用插件功能：{skill 名称}。触发位置：{具体场景}。
```

例如：
```
【插件提醒】已使用插件功能：code-reviewer。触发位置：完成认证模块代码编写。
```

---

## 违规处理

如果发现自己没有在应该使用的场景下调用 skill：

1. 立即停止
2. 调用相应的 skill
3. 根据 skill 反馈调整代码
4. 向用户说明遗漏原因

---

## 优先级

**P0（必须）：**
- security-review（安全审查）
- tdd（测试驱动）
- verification-loop（验证循环）

**P1（强烈建议）：**
- plan（规划）
- code-reviewer（代码审查）
- database-reviewer（数据库审查）

**P2（建议）：**
- architect（架构决策）
- e2e-runner（E2E 测试）
