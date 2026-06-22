# CORS 安全配置说明

## 概述

本文档说明 LLM Wiki API 的 CORS（跨源资源共享）安全配置。

## 配置方式

### 环境变量

通过 `ALLOWED_ORIGINS` 环境变量配置允许的来源白名单：

```bash
# 开发环境
export ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080

# 生产环境
export ALLOWED_ORIGINS=https://example.com,https://app.example.com
```

### 环境区分

通过 `ENV` 环境变量区分环境：

```bash
# 开发环境（默认）
export ENV=development

# 生产环境
export ENV=production
```

**重要：** 生产环境不允许使用通配符 `*`，必须明确指定允许的域名。

## 安全特性

### 1. 白名单验证

- 所有请求的 Origin 标头必须与白名单中的域名完全匹配
- 不在白名单中的来源会被自动拒绝
- 浏览器会阻止跨域请求

### 2. OPTIONS 预检请求

- 支持标准 CORS 预检请求
- 缓存时间：1 小时（3600 秒）
- 允许的方法：GET, POST, PUT, DELETE, OPTIONS
- 允许的标头：Authorization, Content-Type, X-API-Key

### 3. 生产环境保护

- 生产环境禁止使用通配符 `*`
- 强制要求明确指定允许的域名
- 必须使用 HTTPS（建议）

## CORS 标头

响应中包含以下 CORS 标头：

```
Access-Control-Allow-Origin: <origin>
Access-Control-Allow-Credentials: true
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: Authorization, Content-Type, X-API-Key
Access-Control-Max-Age: 3600
```

## 测试验证

### 使用 curl 测试预检请求

```bash
# 测试有效来源
curl -X OPTIONS http://localhost:8000/api/atoms \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET" \
  -v

# 应该返回 200 和 Access-Control-Allow-Origin 标头
```

```bash
# 测试无效来源
curl -X OPTIONS http://localhost:8000/api/atoms \
  -H "Origin: https://malicious.com" \
  -H "Access-Control-Request-Method: GET" \
  -v

# 应该返回 200 但没有 Access-Control-Allow-Origin 标头
```

### 运行自动化测试

```bash
python3 test_cors.py
```

## 常见问题

### Q: 为什么不允许使用 `*` 通配符？

A: 通配符会允许任何网站访问您的 API，存在安全风险。生产环境必须明确指定允许的域名。

### Q: 如何添加新的允许域名？

A: 在 `ALLOWED_ORIGINS` 环境变量中添加，用逗号分隔：

```bash
export ALLOWED_ORIGINS=https://example.com,https://new-domain.com
```

### Q: 开发环境如何配置？

A: 默认支持 localhost 开发环境：
- http://localhost:3000
- http://localhost:8080
- http://127.0.0.1:3000

无需额外配置。

### Q: 如何验证 CORS 配置是否正确？

A: 使用浏览器开发者工具的 Network 标签：
1. 发送跨域请求
2. 检查响应标头是否包含 `Access-Control-Allow-Origin`
3. 确认返回的 origin 与请求的 origin 一致

## 实现细节

### 核心函数

- `get_allowed_origins()`: 从环境变量加载白名单
- `validate_origin()`: 验证请求来源是否在白名单中
- `_set_cors_headers()`: 设置 CORS 响应标头

### 处理流程

```
请求到达
    ↓
提取 Origin 标头
    ↓
验证白名单
    ├─ 在白名单 → 设置 CORS 标头 → 允许访问
    └─ 不在白名单 → 不设置 CORS 标头 → 浏览器阻止
```

## 相关文件

- `/lib/api_server.py`: CORS 实现代码
- `/.env.example`: 环境变量配置示例
- `/test_cors.py`: 自动化测试脚本
- `/test_cors_curl.sh`: curl 测试脚本

## 更新日志

- 2026-06-22: 初始实现
  - 添加白名单验证
  - 支持 OPTIONS 预检请求
  - 生产环境安全保护
