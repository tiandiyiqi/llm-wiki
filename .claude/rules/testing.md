# 测试要求

## 最低测试覆盖率：80%

测试类型（全部必选）：
1. **单元测试（Unit Tests）** - 独立函数、工具类、组件
2. **集成测试（Integration Tests）** - API 终端、数据库操作
3. **端到端测试（E2E Tests）** - 关键用户流程 (Playwright)

## 测试驱动开发（TDD）

参见 helpers.md#通用TDD红绿重构循环

## 测试失败排查

1. 使用 **tdd-guide** 智能体（Agent）
2. 检查测试隔离性
3. 验证 Mock 是否正确
4. 修复实现逻辑，而非测试代码（除非测试代码本身有误）

## 智能体支持（Agent Support）

- **tdd-guide** - 主动用于开发新特性，强制执行“先写测试”原则
- **e2e-runner** - Playwright E2E 测试专家
