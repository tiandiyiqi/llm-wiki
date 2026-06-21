# 沟通规范 (Communication Guidelines)

## 语言使用规则

**默认语言：中文**

在与用户沟通时，必须使用中文，除非遇到以下情况：

### 必须使用英文的场景

1. **代码相关内容**
   - 变量名、函数名、类名
   - 代码注释（如果项目约定使用英文）
   - Git 提交信息（遵循 Conventional Commits 规范）
   - API 端点命名

2. **技术术语**
   - 保留原始英文术语，但可在首次出现时提供中文解释
   - 例如：Repository（仓储）、Hook（钩子）、Agent（智能体）

3. **命令行操作**
   - Shell 命令
   - 工具名称
   - 配置文件路径

4. **用户明确要求使用英文**

### 推荐的沟通风格

- 使用简洁、专业的中文表达
- 技术术语首次出现时提供中英文对照
- 代码示例中的注释使用中文
- 错误信息和日志可保留英文原文，但需提供中文解释

### 示例

```typescript
// 正确：中文沟通 + 英文代码
// 创建用户仓储接口
interface UserRepository {
  findById(id: string): Promise<User | null>
  create(data: CreateUserDto): Promise<User>
}

// 这个函数用于验证用户输入
function validateUserInput(input: unknown): User {
  return userSchema.parse(input)
}
```

## 文档编写

- 项目文档优先使用中文
- README.md 可提供中英文双语版本
- 代码注释根据团队约定选择语言
- API 文档建议使用中文，便于团队理解
