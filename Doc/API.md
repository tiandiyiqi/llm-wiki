# LLM Wiki API 文档

**版本**: 1.0.0
**基础 URL**: `http://localhost:5000/api`

---

## 概述

LLM Wiki API 提供知识库管理、成员管理、权限管理等功能的 RESTful 接口。

### 认证

所有 API 请求需要在 Header 中携带认证 Token：

```
Authorization: Bearer <token>
```

### 响应格式

所有 API 返回统一的 JSON 格式：

```json
{
  "success": true,
  "data": {},
  "error": null,
  "code": 200
}
```

---

## 知识库管理 API

### 1. 创建知识库

**POST** `/api/kb`

创建新的知识库。

**请求体**:
```json
{
  "name": "我的知识库",
  "description": "知识库描述",
  "scope": "personal",
  "parent_id": null,
  "tags": ["技术", "文档"]
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "kb_id": 1,
    "name": "我的知识库",
    "created_at": "2026-06-22T10:00:00Z"
  }
}
```

### 2. 获取知识库详情

**GET** `/api/kb/{kb_id}`

获取指定知识库的详细信息。

**响应**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "我的知识库",
    "description": "知识库描述",
    "scope": "personal",
    "atom_count": 50,
    "created_at": "2026-06-22T10:00:00Z"
  }
}
```

### 3. 列出知识库

**GET** `/api/kbs`

获取知识库列表，支持分页和筛选。

**查询参数**:
- `page` (int): 页码（默认 1）
- `limit` (int): 每页数量（默认 20）
- `scope` (string): 知识库范围（personal/department/project/company）

**响应**:
```json
{
  "success": true,
  "data": {
    "knowledge_bases": [...],
    "total": 100,
    "page": 1,
    "limit": 20
  }
}
```

### 4. 更新知识库

**PUT** `/api/kb/{kb_id}`

更新知识库信息。

**请求体**:
```json
{
  "name": "新名称",
  "description": "新描述"
}
```

### 5. 删除知识库

**DELETE** `/api/kb/{kb_id}`

删除指定知识库（需要 owner 权限）。

**响应**:
```json
{
  "success": true,
  "data": {
    "deleted_kb_id": 1
  }
}
```

### 6. 搜索知识库

**GET** `/api/kbs/search`

搜索知识库。

**查询参数**:
- `q` (string): 搜索关键词
- `scope` (string): 范围筛选（可选）

---

## 成员管理 API

### 1. 添加成员

**POST** `/api/kb/{kb_id}/members`

向知识库添加成员。

**请求体**:
```json
{
  "user_id": "user123",
  "role": "editor"
}
```

**角色类型**:
- `owner`: 所有者（完全权限）
- `editor`: 编辑者（读写权限）
- `reader`: 读者（只读权限）

### 2. 移除成员

**DELETE** `/api/kb/{kb_id}/members/{user_id}`

从知识库移除成员。

### 3. 更新成员角色

**PUT** `/api/kb/{kb_id}/members/{user_id}`

更新成员角色。

**请求体**:
```json
{
  "role": "editor"
}
```

### 4. 查询成员列表

**GET** `/api/kb/{kb_id}/members`

获取知识库成员列表。

**查询参数**:
- `page` (int): 页码
- `limit` (int): 每页数量

---

## 权限管理 API

### 1. 检查权限

**GET** `/api/permissions/check`

检查用户是否有指定权限。

**查询参数**:
- `user_id` (string): 用户 ID
- `kb_id` (int): 知识库 ID
- `permission` (string): 权限名称

**权限列表**:
- `kb:create`, `kb:read`, `kb:update`, `kb:delete`, `kb:manage`
- `atom:create`, `atom:read`, `atom:update`, `atom:delete`
- `member:manage`

**响应**:
```json
{
  "success": true,
  "data": {
    "has_permission": true
  }
}
```

### 2. 分配角色

**POST** `/api/permissions/roles`

为用户分配角色。

**请求体**:
```json
{
  "user_id": "user123",
  "kb_id": 1,
  "role": "editor"
}
```

### 3. 撤销角色

**DELETE** `/api/permissions/roles`

撤销用户角色。

**请求体**:
```json
{
  "user_id": "user123",
  "kb_id": 1,
  "role": "editor"
}
```

### 4. 查询用户权限

**GET** `/api/permissions/user/{user_id}`

获取用户的所有权限。

**响应**:
```json
{
  "success": true,
  "data": {
    "permissions": ["kb:read", "atom:create", "atom:read"],
    "roles": {
      "1": ["editor"],
      "2": ["owner"]
    }
  }
}
```

### 5. 列出所有角色

**GET** `/api/permissions/roles`

获取所有可用角色。

**响应**:
```json
{
  "success": true,
  "data": {
    "roles": [
      {
        "name": "owner",
        "description": "所有者：完全控制权限",
        "permissions": ["kb:create", "kb:read", ...]
      },
      ...
    ]
  }
}
```

---

## 错误响应

### 错误格式

```json
{
  "success": false,
  "data": null,
  "error": "错误描述",
  "code": 400
}
```

### 常见错误码

| 错误码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 401 | 未授权（缺少或无效 Token） |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 409 | 资源冲突（如重复创建） |
| 500 | 服务器内部错误 |

---

## 示例代码

### Python

```python
import requests

BASE_URL = "http://localhost:5000/api"
TOKEN = "your-token-here"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# 创建知识库
response = requests.post(
    f"{BASE_URL}/kb",
    headers=headers,
    json={
        "name": "我的知识库",
        "description": "技术文档",
        "scope": "personal"
    }
)

print(response.json())
```

### JavaScript

```javascript
const BASE_URL = 'http://localhost:5000/api';
const TOKEN = 'your-token-here';

const headers = {
  'Authorization': `Bearer ${TOKEN}`,
  'Content-Type': 'application/json'
};

// 创建知识库
fetch(`${BASE_URL}/kb`, {
  method: 'POST',
  headers,
  body: JSON.stringify({
    name: '我的知识库',
    description: '技术文档',
    scope: 'personal'
  })
})
  .then(res => res.json())
  .then(data => console.log(data));
```

---

## 速率限制

- **标准用户**: 100 请求/分钟
- **高级用户**: 500 请求/分钟

超过限制将返回 `429 Too Many Requests`。

---

## 版本控制

API 版本通过 URL 前缀控制：
- 当前版本: `/api/v1`
- 历史版本: `/api/v0`（已弃用）

---

**最后更新**: 2026-06-22
**API 版本**: 1.0.0