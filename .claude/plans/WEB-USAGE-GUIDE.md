# llm-wiki Web 服务使用指南

> **更新时间**：2026-06-24
> **服务状态**：✅ 已启动并启用权限

---

## 🎯 快速开始

### 1. 访问登录页面

浏览器已打开：http://localhost:8000/views/login.html

**登录信息**：
- 用户名：`admin`
- 密码：在数据库中（暂无密码字段，可直接登录）

**注意**：当前系统未启用密码验证，管理员用户已创建。

---

## 📊 访问地址

### Web 页面

| 页面 | 地址 | 说明 |
|------|------|------|
| 🏠 主页 | http://localhost:8000/views/index.html | 知识库首页 |
| 🔐 登录 | http://localhost:8000/views/login.html | 用户登录 |
| 📚 知识库管理 | http://localhost:8000/views/admin/kb-managem.html | 管理知识库 |
| 🔑 权限管理 | http://localhost:8000/views/admin/permissions.html | 用户权限 |
| 🖼️ 图像库 | http://localhost:8000/views/media/gallery.html | 图像管理 |
| 🔍 搜索 | http://localhost:8000/views/search/results.html | 知识搜索 |

### API 端点

| API | 地址 | 说明 |
|------|------|------|
| 健康检查 | http://localhost:8000/api/health | 服务状态 |
| 用户状态 | http://localhost:8000/api/status | 当前用户信息 |

---

## 🔐 权限系统

### 已配置

- ✅ 权限已启用（`.kb-access.json`）
- ✅ 管理员用户已创建（`admin`）
- ✅ 默认角色：reader（读者）

### 用户管理

**户**：
```sql
-- 查看所有用户
SELECT id, name, email, global_role, status FROM users;

-- 当前管理员
id: admin
name: 管理员
email: admin@llm-wiki.local
role: admin
status: active
```

---

## 🛠️ 管理命令

### 启动服务

```bash
# 方式 1：使用启动脚本
./open_web.sh

# 方式 2：直接启动
source .venv/bin/activate
python start_server.py --host localhost --port 8000 --kb knowledge-bases
```

### 停止服务

```bash
# 查找进程
lsof -i :8000

# 停止服务
kill $(lsof -t -i :8000)
```

### 测试 API

```bash
# 健康检查
curl http://localhost:8000/api/health

# 用户状态（需要认证）
curl http://localhost:8000/api/status
```

---

## 📝 功能清单

### 已实现的功能

| 功能 | 状态 | 说明 |
|------|:----:|------|
| 知识库管理 | ✅ | 创建、列表、详情 |
| 图像管理 | ✅ | 上传、缩略图、预览 |
| 搜索功能 | ✅ | 全文、向量、混合 |
| OCR 识别 | ✅ | PaddleOCR 集成 |
| 在线预览 | ✅ | PDF/Office/代码 |
| 权限系统 | ✅ | RBAC + RLS |
| 数据加密 | ✅ | pgcrypto 字段加密 |

---

## 🎓 使用流程

### 1. 登录

1. 访问 http://localhost:8000/views/login.html
2. 输入用户名：`admin`
3. 点击登录

### 2. 知识库管理

1. 登录后访问知识库管理页面
2. 创建新知识库或选择现有知识库
3. 添加原子（知识条目）

### 3. 搜索知识

1. 使用搜索框输入关键词
2. 查看高亮显示的搜索结果
3. 点击结果查看详情

### 4. 上传图像

1. 访问图像库页面
2. 拖拽或粘贴图像上传
3. 自动生成缩略图

---

## ⚠️ 注意事项

### 当前限制

1. **密码验证未启用**
   - 管理员用户无密码字段
   - 需要后续添加密码管理

2. **SSO 未配置**
   - Casdoor 已集成但未实际部署
   - 需配置 IdP（企业微信/钉钉）

3. **数据为示例数据**
   - 知识库目录为空
   - 需导入实际知识内容

---

## 🚀 下一步建议

### 完善权限系统

1. **添加密码管理**
   ```sql
   -- 添加密码字段（需要加密）
   ALTER TABLE users ADD COLUMN password_hash VARCHAR(256);
   ```

2. **创建普通用户**
   ```sql
   -- 创建测试用户
   INSERT INTO users (id, name, email, global_role, status)
   VALUES ('testuser', '测试用户', 'test@example.com', 'user', 'active');
   ```

### 导入知识内容

```bash
# 使用 CLI 导入知识
python3 llm-wiki.py ingest raw/document.md --kb knowledge-bases

# 或使用 Web UI 上传
```

---

## 📚 相关文档

- **PLAN-009 报告**：`.claude/plans/PLAN-009-COMPLETION-SUMMARY.md`
- **项目总结**：`.claude/plans/PROJECT-COMPLETION-SUMMARY.md`
- **加密配置**：`Doc/encryption-guide.md`

---

**服务状态**：✅ 正在运行
**访问地址**：http://localhost:8000/views/login.html

浏览器应该已经打开了登录页面！开始使用吧！ 🎊