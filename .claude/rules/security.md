# 安全指南 (Security Guidelines)

## 强制安全检查 (Mandatory Security Checks)

参见 helpers.md#安全检查清单

## 凭据管理 (Secret Management)

```typescript
// 严禁：硬编码凭据
const apiKey = "sk-proj-xxxxx"

// 推荐：环境变量
const apiKey = process.env.OPENAI_API_KEY

if (!apiKey) {
  throw new Error('OPENAI_API_KEY not configured')
}
```

## 安全响应协议 (Security Response Protocol)

如果发现安全问题：
1. 立即停止（STOP）
2. 使用 **security-reviewer** 智能体（Agent）
3. 在继续之前修复严重（CRITICAL）问题
4. 轮换任何暴露的凭据
5. 审查整个代码库是否存在类似问题
