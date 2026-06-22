---
name: PLAN-002-dual-mode-multi-level-kb
description: 阶段 1.2 双模式架构 + 阶段 1.3 多级知识库管理实施计划
status: pending
created: 2026-06-22
updated: 2026-06-22
phase: 阶段 1（核心基础）
depends_on: PLAN-001-postgresql-migration
---

# 实施计划：阶段 1.2 双模式架构 + 阶段 1.3 多级知识库管理

## 目标

实现 llm-wiki 企业化改造的第二阶段：
1. **双模式架构**：file_mode（Skill 模式）+ db_mode（企业模式）可通过配置切换
2. **多级知识库**：personal/department/project/company 四级知识库体系
3. **用户权限系统**：基于 PostgreSQL RLS 的细粒度权限控制

**核心理念**：保留 file_mode 的 Skill 特性，同时为 db_mode 添加企业级多用户协作能力。

---

## 需求重述

一句话概括：通过配置项 `storage.type = file | db` 切换存储模式，同时支持 personal/department/project/company 四级知识库架构和基于 RLS 的权限控制。

---

## 实施阶段

### 阶段 1：双模式存储抽象层（2 周）

**目标**：统一 API 接口层，支持 file_mode 和 db_mode 透明切换

### 阶段 2：多级知识库模型扩展（2 周）

**目标**：扩展现有知识库模型，支持 personal/department/project/company 四级架构和层级继承

### 阶段 3：权限系统实现（3 周）

**目标**：基于 PostgreSQL RLS 实现细粒度权限控制，支持角色继承和权限传递

### 阶段 4：知识库管理 API（2 周）

**目标**：实现知识库的 CRUD API、成员管理、聚合管理等企业功能

### 阶段 5：集成测试与验证（1 周）

**目标**：验证双模式切换、多级知识库、权限控制的正确性

---

## 详细实施步骤

### 阶段 1：双模式存储抽象层（2 周）

#### 步骤 1.1：扩展 StorageFactory 实现（3 天）

**文件变更**：
- 修改：`lib/core/factory.py`（扩展 StorageFactory）

**实现内容**：
- 扩展 StorageFactory，支持 `storage.type = file | db` 配置
- 实现 StorageInterface 统一抽象接口
- file_mode 使用现有 FileSystemManager（封装 SQLite + 文件操作）
- db_mode 使用现有 PostgreSQLManager

**代码示例**：
```python
class StorageFactory:
    @staticmethod
    def create(config: Dict) -> StorageInterface:
        storage_type = config.get('storage', {}).get('type', 'file')
        
        if storage_type == 'db':
            return DatabaseStorage(config['database'])
        else:
            return FileSystemStorage(config['storage']['path'])
```

**依赖项**：PLAN-001 完成的 DatabaseManager 抽象层

---

#### 步骤 1.2：实现 StorageInterface 统一接口（3 天）

**文件变更**：
- 新建：`lib/core/storage_interface.py`

**实现内容**：
- 定义 StorageInterface 抽象类，统一 file_mode 和 db_mode API
- 方法：create/read/update/delete_atom, create/read/update/delete_kb
- 方法：search_atoms, get_stats
- 事务支持：begin/commit/rollback
- 模式检测：is_file_mode, is_db_mode

**关键方法签名**：
```python
class StorageInterface(ABC):
    @property
    def mode(self) -> str:  # 'file' or 'db'
        pass
    
    @property
    def supports_rls(self) -> bool:
        """是否支持行级安全策略"""
        pass
    
    async def initialize(self) -> None:
        pass
    
    # 知识库操作
    async def create_kb(self, kb_data: Dict) -> int: ...
    async def get_kb(self, kb_id: int) -> Optional[Dict]: ...
    async def list_kbs(self, user_id: Optional[str], scope: str) -> List[Dict]: ...
    async def update_kb(self, kb_id: int, kb_data: Dict) -> bool: ...
    async def delete_kb(self, kb_id: int) -> bool: ...
    
    # 知识原子操作
    async def create_atom(self, atom_data: Dict) -> int: ...
    async def get_atom(self, atom_id: int) -> Optional[Dict]: ...
    async def update_atom(self, atom_id: int, atom_data: Dict) -> bool: ...
    async def delete_atom(self, atom_id: int) -> bool: ...
    async def list_atoms(self, kb_id: int, **kwargs) -> List[Dict]: ...
    
    # 搜索操作
    async def search_atoms(self, query: str, **kwargs) -> List[Dict]: ...
    
    # 事务支持
    async def begin_transaction(self) -> None: ...
    async def commit_transaction(self) -> None: ...
    async def rollback_transaction(self) -> None: ...
```

---

#### 步骤 1.3：实现 FileSystemStorage 文件模式适配器（3 天）

**文件变更**：
- 新建：`lib/core/file_storage.py`

**实现内容**：
- 实现 StorageInterface 抽象类
- 封装现有文件操作（registry.json + Markdown 文件）
- 将文件系统操作映射到统一 API
- 支持读写分离优化

**核心适配逻辑**：
```python
class FileSystemStorage(StorageInterface):
    """文件模式存储适配器
    
    将文件系统操作（registry.json + Markdown）适配到统一 API。
    保留 file_mode 的 Skill 特性（Claude 直接操作文件）。
    """
    
    def __init__(self, kb_path: Path):
        self.kb_path = Path(kb_path)
        self.registry = Registry(kb_path)
        # ... 封装现有文件操作
    
    @property
    def mode(self) -> str:
        return 'file'
    
    @property
    def supports_rls(self) -> bool:
        return False  # 文件模式不支持 RLS
```

---

#### 步骤 1.4：实现 DatabaseStorage 数据库模式适配器（3 天）

**文件变更**：
- 新建：`lib/core/db_storage.py`

**实现内容**：
- 实现 StorageInterface 抽象类
- 封装 PostgreSQLManager
- 集成 RLS 上下文
- 支持事务和批量操作

**核心适配逻辑**：
```python
class DatabaseStorage(StorageInterface):
    """数据库模式存储适配器
    
    将 PostgreSQL 操作适配到统一 API。
    支持 RLS、行级权限、审计日志。
    """
    
    def __init__(self, db_config: Dict):
        self.db_manager = PostgreSQLManager(db_config)
    
    @property
    def mode(self) -> str:
        return 'db'
    
    @property
    def supports_rls(self) -> bool:
        return True  # 数据库模式支持 RLS
    
    def set_current_user(self, user_id: str, roles: List[str]) -> None:
        """设置当前用户上下文（用于 RLS）"""
        self.db_manager.set_rls_context(user_id, roles)
```

---

#### 步骤 1.5：配置文件扩展（1 天）

**文件变更**：
- 新建：`config/storage.example.yaml`
- 修改：`lib/core/config.py`（支持新配置项）

**配置项设计**：
```yaml
# config/storage.yaml
storage:
  type: file  # file | db
  
  # file_mode 配置
  file:
    path: ./knowledge-bases
    auto_discover: true
    watch_changes: true
  
  # db_mode 配置
  db:
    # PostgreSQL 连接配置
    host: ${DB_HOST:localhost}
    port: ${DB_PORT:5432}
    database: ${DB_NAME:llmwiki}
    user: ${DB_USER:llmwiki}
    password: ${DB_PASSWORD:}
    
    # 连接池配置
    pool:
      min_size: 5
      max_size: 20
      max_overflow: 10
      pool_timeout: 30
    
    # RLS 配置
    rls:
      enabled: true
      current_user_var: llmwiki.current_user_id()
      current_roles_var: llmwiki.current_user_roles()
```

---

#### 步骤 1.6：单元测试覆盖（2 天）

**文件变更**：
- 新建：`tests/unit/test_storage_interface.py`
- 新建：`tests/unit/test_file_storage.py`
- 新建：`tests/unit/test_db_storage.py`

**测试覆盖**：
- StorageFactory 模式切换
- FileSystemStorage 完整 API
- DatabaseStorage 完整 API
- 异常场景处理

---

### 阶段 2：多级知识库模型扩展（2 周）

#### 步骤 2.1：知识库类型扩展（2 天）

**文件变更**：
- 修改：`lib/core/storage_interface.py`（扩展接口定义）
- 修改：`lib/core/db_storage.py`（实现扩展方法）

**扩展内容**：
- 支持 kb_type: personal/department/project/company
- 支持 visibility: private/team/public
- 支持 is_aggregated: 聚合知识库标记

**Schema 已有支撑**：
```sql
-- knowledge_bases 表已定义
CREATE TYPE kb_type AS ENUM (
    'personal',     -- 个人知识库
    'department',   -- 部门知识库
    'project',      -- 项目知识库
    'company'       -- 公司知识库
);

CREATE TYPE kb_visibility AS ENUM (
    'private',      -- 私有
    'team',         -- 团队
    'public'        -- 公开
);
```

---

#### 步骤 2.2：层级继承逻辑实现（3 天）

**文件变更**：
- 新建：`lib/core/hierarchy.py`

**实现内容**：
- 层级关系查询：get_ancestors, get_descendants
- 权限继承：inherit_permissions
- 可见性传递：compute_visibility
- 聚合查询：aggregate_kbs

**核心逻辑**：
```python
class KnowledgeBaseHierarchy:
    """多级知识库层级管理"""
    
    async def get_ancestors(self, kb_id: int) -> List[Dict]:
        """获取知识库的层级祖先（递归向上）
        
        personal → department → project → company
        """
        pass
    
    async def get_child_kbs(self, kb_id: int, 
                           recursive: bool = False) -> List[Dict]:
        """获取子知识库列表
        
        Args:
            kb_id: 知识库 ID
            recursive: 是否递归获取所有后代
        """
        pass
    
    async def inherit_permissions(self, kb_id: int, 
                                  parent_roles: Dict) -> Dict:
        """权限继承计算
        
        子知识库继承父知识库的基础权限，可被覆盖。
        """
        pass
    
    async def compute_visibility(self, kb_id: int) -> str:
        """计算最终可见性
        
        规则：
        - personal 默认 private
        - department 默认 team
        - project 默认 team
        - company 默认 public
        - 子知识库可收紧可见性，不可放宽
        """
        pass
```

---

#### 步骤 2.3：知识库聚合功能（2 天）

**文件变更**：
- 修改：`lib/core/hierarchy.py`（添加聚合方法）
- 修改：`lib/core/db_storage.py`（实现聚合查询）

**实现内容**：
- company 类型知识库作为聚合容器
- kb_aggregations 表管理聚合关系
- 聚合搜索：搜索公司知识库时自动包含子知识库内容

**Schema 已有支撑**：
```sql
CREATE TABLE kb_aggregations (
    parent_kb_id INTEGER REFERENCES knowledge_bases(id),
    child_kb_id INTEGER REFERENCES knowledge_bases(id),
    include_private BOOLEAN DEFAULT false,
    priority INTEGER DEFAULT 0,
    PRIMARY KEY (parent_kb_id, child_kb_id)
);
```

---

#### 步骤 2.4：知识库管理 CLI 扩展（2 天）

**文件变更**：
- 修改：`lib/cli_commands.py`（添加知识库管理命令）

**新增命令**：
```bash
# 知识库类型管理
llm-wiki kb create --name "部门知识库" --type department --dept engineering
llm-wiki kb create --name "项目知识库" --type project --project "P001"

# 层级关系
llm-wiki kb list --type company
llm-wiki kb children "公司知识库"
llm-wiki kb aggregate "公司知识库" --add "部门知识库"

# 知识库属性
llm-wiki kb set-visibility "个人知识库" --visibility private
llm-wiki kb info "知识库名称"
```

---

#### 步骤 2.5：多级知识库 API（2 天）

**文件变更**：
- 新建：`lib/api/kb_management.py`
- 修改：`lib/api_server.py`（注册路由）

**API 端点设计**：
```python
# 知识库 CRUD
POST   /api/kb                    # 创建知识库
GET    /api/kb                    # 列出知识库
GET    /api/kb/:id                # 获取知识库详情
PUT    /api/kb/:id                # 更新知识库
DELETE /api/kb/:id                # 删除知识库

# 层级关系
GET    /api/kb/:id/ancestors      # 获取祖先知识库
GET    /api/kb/:id/children       # 获取子知识库
GET    /api/kb/:id/parent         # 获取父知识库

# 成员管理
GET    /api/kb/:id/members        # 获取成员列表
POST   /api/kb/:id/members        # 添加成员
PUT    /api/kb/:id/members/:user_id  # 更新成员角色
DELETE /api/kb/:id/members/:user_id  # 删除成员

# 聚合管理
GET    /api/kb/:id/aggregations   # 获取聚合配置
POST   /api/kb/:id/aggregations   # 添加子知识库
DELETE /api/kb/:id/aggregations/:child_id  # 移除子知识库
```

---

#### 步骤 2.6：单元测试（1 天）

**文件变更**：
- 新建：`tests/unit/test_hierarchy.py`
- 新建：`tests/unit/test_kb_api.py`

---

### 阶段 3：权限系统实现（3 周）

#### 步骤 3.1：角色体系设计（2 天）

**文件变更**：
- 新建：`lib/auth/rbac.py`

**角色设计**：
```python
# 全局角色（users.global_role）
ROLE_SUPER_ADMIN = 'super_admin'    # 超级管理员（全系统）
ROLE_ADMIN = 'admin'                 # 管理员（组织级）
ROLE_USER = 'user'                   # 普通用户

# 知识库角色（kb_members.role）
KB_ROLE_OWNER = 'owner'              # 所有者（完全控制）
KB_ROLE_EDITOR = 'editor'            # 编辑者（读写）
KB_ROLE_READER = 'reader'            # 读者（只读）

# 角色权限映射
ROLE_PERMISSIONS = {
    KB_ROLE_OWNER: ['read', 'write', 'delete', 'manage_members', 'manage_settings'],
    KB_ROLE_EDITOR: ['read', 'write', 'comment'],
    KB_ROLE_READER: ['read', 'comment'],
}
```

---

#### 步骤 3.2：PostgreSQL RLS 策略实现（4 天）

**文件变更**：
- 新建：`lib/auth/rls_policies.sql`（RLS 策略 SQL）
- 新建：`lib/auth/rls_manager.py`（RLS 管理器）

**RLS 策略设计**：
```sql
-- 1. 用户只能访问自己有权限的知识库
CREATE POLICY kb_access_policy ON knowledge_bases
    FOR SELECT USING (
        -- 超级管理员可访问所有
        EXISTS (SELECT 1 FROM users WHERE id = current_user_id() AND global_role = 'super_admin')
        OR
        -- 知识库所有者
        owner_id = current_user_id()
        OR
        -- 知识库成员
        EXISTS (SELECT 1 FROM kb_members WHERE kb_id = knowledge_bases.id AND user_id = current_user_id())
        OR
        -- 公开知识库
        visibility = 'public'
    );

-- 2. 知识库成员只能修改自己有权限的知识库
CREATE POLICY kb_update_policy ON knowledge_bases
    FOR UPDATE USING (
        owner_id = current_user_id()
        OR
        EXISTS (
            SELECT 1 FROM kb_members 
            WHERE kb_id = knowledge_bases.id 
            AND user_id = current_user_id()
            AND role IN ('owner', 'editor')
        )
    );

-- 3. 原子操作权限（读/写/删）
CREATE POLICY atom_read_policy ON atoms
    FOR SELECT USING (
        -- 用户对知识库有读权限
        EXISTS (
            SELECT 1 FROM knowledge_bases kb
            JOIN kb_members km ON kb.id = km.kb_id
            WHERE kb.id = atoms.kb_id
            AND (km.user_id = current_user_id() OR kb.visibility = 'public')
        )
    );
```

**RLS 管理器**：
```python
class RLSManager:
    """PostgreSQL 行级安全策略管理器"""
    
    def __init__(self, db_manager: PostgreSQLManager):
        self.db = db_manager
    
    def set_session_context(self, user_id: str, roles: List[str]) -> None:
        """设置当前用户会话上下文（用于 RLS 策略判断）"""
        # 设置 search_path 包含 RLS 函数
        # 设置当前用户 ID
        # 设置当前用户角色列表
        pass
    
    def enable_rls(self, table: str) -> None:
        """启用表的 RLS"""
        pass
    
    def disable_rls(self, table: str) -> None:
        """禁用表的 RLS"""
        pass
    
    def add_policy(self, table: str, policy_name: str, sql: str) -> None:
        """添加 RLS 策略"""
        pass
    
    def verify_rls(self, table: str) -> bool:
        """验证 RLS 策略是否正确配置"""
        pass
```

---

#### 步骤 3.3：权限检查中间件（3 天）

**文件变更**：
- 新建：`lib/auth/permission_middleware.py`
- 修改：`lib/api_server.py`（注册中间件）

**实现内容**：
- 请求级别的权限检查
- 支持装饰器：@require_permission('read'), @require_role('editor')
- 审计日志自动记录

**代码示例**：
```python
class PermissionMiddleware:
    """API 权限检查中间件"""
    
    def __init__(self, auth_manager: RBACManager):
        self.auth = auth_manager
    
    async def check_permission(self, request: Request, 
                               resource: str, action: str) -> bool:
        """检查用户是否有权限执行操作
        
        Args:
            request: FastAPI 请求对象
            resource: 资源类型（kb/atom/asset）
            action: 操作类型（read/write/delete/manage）
        
        Returns:
            是否有权限
        """
        user_id = request.state.user_id
        resource_id = request.path_params.get('id')
        
        return await self.auth.check_permission(
            user_id=user_id,
            resource_type=resource,
            resource_id=resource_id,
            action=action
        )
    
    async def __call__(self, scope, receive, send):
        # 中间件逻辑
        pass


# 装饰器使用示例
@router.get('/kb/{kb_id}/atoms')
@require_permission('kb', 'read')
async def list_atoms(kb_id: int, ...):
    """列出知识库原子（需要读权限）"""
    pass


@router.post('/kb/{kb_id}/atoms')
@require_permission('kb', 'write')
async def create_atom(kb_id: int, ...):
    """创建知识原子（需要写权限）"""
    pass


@router.delete('/kb/{kb_id}/members/{user_id}')
@require_permission('kb', 'manage_members')
async def remove_member(kb_id: int, user_id: str, ...):
    """移除成员（需要管理成员权限）"""
    pass
```

---

#### 步骤 3.4：原子级权限控制（3 天）

**文件变更**：
- 修改：`lib/auth/rbac.py`（扩展权限模型）
- 修改：`lib/core/storage_interface.py`（添加权限参数）

**实现内容**：
- 基于角色的访问控制（RBAC）
- 基于属性的访问控制（ABAC）扩展
- 原子级权限覆盖（可覆盖知识库级别的权限）

**权限模型**：
```python
# 权限粒度
PERMISSION_SCOPES = {
    'knowledge_base': '知识库级别权限',
    'atom': '原子级别权限',
    'asset': '资产级别权限',
}

# 权限继承链
PERMISSION_INHERITANCE = {
    'kb_read': ['atom_read', 'asset_read'],
    'kb_write': ['atom_write', 'asset_write'],
    'kb_delete': ['atom_delete', 'asset_delete'],
}

# 原子级权限覆盖
class AtomPermissionOverride:
    """原子级权限覆盖（可临时放宽或收紧权限）"""
    
    atom_id: int
    user_id: str
    allowed_actions: List[str]  # 额外允许的操作
    denied_actions: List[str]   # 额外禁止的操作
    expires_at: Optional[datetime]
```

---

#### 步骤 3.5：与 Casdoor SSO 集成准备（2 天）

**文件变更**：
- 修改：`lib/auth/rbac.py`（添加 SSO 用户同步）
- 新建：`lib/auth/sso_sync.py`

**实现内容**：
- SSO 用户自动同步到 users 表
- 用户属性映射（Casdoor → llm-wiki）
- 组织/部门自动创建

**注意**：Casdoor 集成是阶段 2 的任务，此处仅做准备工作（预留接口）

---

#### 步骤 3.6：单元测试（1 天）

**文件变更**：
- 新建：`tests/unit/test_rbac.py`
- 新建：`tests/unit/test_rls.py`
- 新建：`tests/unit/test_permission_middleware.py`

---

### 阶段 4：知识库管理 API（2 周）

#### 步骤 4.1：知识库 CRUD 完整实现（3 天）

**文件变更**：
- 修改：`lib/api/kb_management.py`

**实现内容**：
- 完整 CRUD API（创建、读取、更新、删除）
- 知识库类型自动校验（project 必须关联 project_id）
- 可见性校验（子知识库不可宽于父知识库）
- 层级循环检测（防止 A→B→A）

---

#### 步骤 4.2：成员管理 API（3 天）

**文件变更**：
- 修改：`lib/api/kb_management.py`（扩展成员管理）

**实现内容**：
- 邀请成员（发送邀请、设置初始角色）
- 批量成员操作（批量添加/移除）
- 角色变更历史记录
- 成员列表分页和过滤

---

#### 步骤 4.3：权限继承 API（2 天）

**文件变更**：
- 新建：`lib/api/permission_api.py`

**实现内容**：
- 查询用户对某知识库的权限
- 查询用户的有效权限（继承 + 覆盖）
- 权限变更通知

---

#### 步骤 4.4：Web UI 集成（3 天）

**文件变更**：
- 新建：`webui/components/KBManagement.jsx`
- 修改：`webui/routes/kb.jsx`

**实现内容**：
- 知识库列表页面（支持类型过滤）
- 知识库创建/编辑页面
- 成员管理界面（添加/移除/角色变更）
- 层级关系可视化

---

#### 步骤 4.5：集成测试（1 天）

**文件变更**：
- 新建：`tests/integration/test_kb_management.py`

---

### 阶段 5：集成测试与验证（1 周）

#### 步骤 5.1：双模式切换测试（2 天）

**测试场景**：
- 配置切换为 file_mode：操作文件存储
- 配置切换为 db_mode：操作 PostgreSQL
- 切换过程中数据一致性

---

#### 步骤 5.2：多级知识库功能测试（2 天）

**测试场景**：
- 创建 personal/department/project/company 四类知识库
- 验证层级关系正确
- 验证聚合搜索功能
- 验证可见性继承规则

---

#### 步骤 5.3：权限系统测试（2 天）

**测试场景**：
- RLS 策略生效（未授权用户无法访问）
- 角色权限正确（owner/editor/reader）
- 权限继承正确
- 原子级权限覆盖生效

---

#### 步骤 5.4：性能与压力测试（1 天）

**测试场景**：
- 并发读写性能
- 大规模知识库查询性能
- RLS 对查询性能的影响

---

## 文件变更汇总

### 新建文件
| 文件路径 | 说明 |
|----------|------|
| `lib/core/storage_interface.py` | 存储抽象接口 |
| `lib/core/file_storage.py` | 文件模式存储适配器 |
| `lib/core/db_storage.py` | 数据库模式存储适配器 |
| `lib/core/hierarchy.py` | 多级知识库层级管理 |
| `lib/core/__init__.py` | 导出更新 |
| `lib/auth/rbac.py` | RBAC 权限管理 |
| `lib/auth/rls_manager.py` | RLS 策略管理 |
| `lib/auth/rls_policies.sql` | RLS 策略 SQL 脚本 |
| `lib/auth/permission_middleware.py` | 权限检查中间件 |
| `lib/auth/sso_sync.py` | SSO 用户同步 |
| `lib/api/kb_management.py` | 知识库管理 API |
| `lib/api/permission_api.py` | 权限 API |
| `config/storage.example.yaml` | 存储配置示例 |
| `webui/components/KBManagement.jsx` | Web UI 知识库管理 |
| `tests/unit/test_storage_interface.py` | 存储接口测试 |
| `tests/unit/test_file_storage.py` | 文件存储测试 |
| `tests/unit/test_db_storage.py` | 数据库存储测试 |
| `tests/unit/test_hierarchy.py` | 层级管理测试 |
| `tests/unit/test_kb_api.py` | 知识库 API 测试 |
| `tests/unit/test_rbac.py` | RBAC 测试 |
| `tests/unit/test_rls.py` | RLS 测试 |
| `tests/unit/test_permission_middleware.py` | 权限中间件测试 |
| `tests/integration/test_kb_management.py` | 知识库集成测试 |

### 修改文件
| 文件路径 | 修改内容 |
|----------|----------|
| `lib/core/factory.py` | 扩展 StorageFactory 支持双模式 |
| `lib/core/config.py` | 添加存储配置支持 |
| `lib/cli_commands.py` | 添加知识库管理命令 |
| `lib/api_server.py` | 注册新路由和中间件 |
| `lib/auth.py` | 集成新的 RBAC 模块 |
| `webui/routes/kb.jsx` | 添加知识库管理页面 |

---

## 依赖关系

### 阶段间依赖
```
阶段 1（双模式存储抽象）
    ↓
阶段 2（多级知识库模型）← 依赖阶段 1 完成的 StorageInterface
    ↓
阶段 3（权限系统）← 依赖阶段 2 的知识库模型 + PostgreSQL Schema
    ↓
阶段 4（知识库管理 API）← 依赖阶段 2 + 3
    ↓
阶段 5（集成测试）← 依赖阶段 1-4 全部完成
```

### 外部依赖
| 依赖项 | 用途 | 说明 |
|--------|------|------|
| PostgreSQL | 数据库存储 | PLAN-001 已实现连接层 |
| asyncpg | PostgreSQL 异步驱动 | PLAN-001 已引入 |
| pgvector | 向量索引 | PLAN-001 已启用扩展 |
| FastAPI | API 框架 | 现有依赖 |

### 与 PLAN-001 的关系
- **前置条件**：PLAN-001（PostgreSQL 迁移）必须完成
- **复用资产**：
  - DatabaseManager 抽象基类
  - PostgreSQLManager 实现
  - SQLiteManager 实现
  - PostgreSQL Schema 定义
  - 搜索适配层（lib/search/）

---

## 风险评估

| 风险 | 等级 | 影响 | 缓解措施 |
|------|:----:|------|----------|
| RLS 策略配置错误导致数据泄露 | HIGH | 权限系统失效，数据泄露 | 安全审查、集成测试覆盖权限边界、RLS 验证工具 |
| 双模式切换导致数据不一致 | HIGH | 模式切换后数据丢失或损坏 | 切换前数据校验、事务保护、切换引导文档 |
| 权限继承逻辑复杂度高 | MEDIUM | 权限判断不准确 | 设计阶段详细评审、单元测试覆盖边界条件 |
| 向量检索与 RLS 冲突 | MEDIUM | 带权限的向量搜索失败 | 分离查询：先 RLS 过滤再向量检索 |
| file_mode 性能下降 | LOW | 适配器层增加开销 | 关键路径优化、必要时直接调用底层实现 |
| 多级知识库循环引用 | MEDIUM | 层级死循环 | 创建时检测循环、数据库约束禁止自引用 |

---

## 预估复杂度

**等级**：高（HIGH）

| 阶段 | 工作量 | 说明 |
|------|--------|------|
| 阶段 1：双模式存储抽象 | 50-70 小时 | 统一接口 + 双实现 |
| 阶段 2：多级知识库模型 | 40-55 小时 | 层级逻辑 + 聚合 |
| 阶段 3：权限系统 | 70-95 小时 | RLS + RBAC + 中间件（最复杂） |
| 阶段 4：知识库管理 API | 50-70 小时 | CRUD + 成员 + UI |
| 阶段 5：集成测试 | 30-40 小时 | 完整功能测试 |
| **总计** | **240-330 小时** | 约 6-8 周（1 人） |

---

## 技术决策

| 决策项 | 选定方案 | 理由 |
|--------|----------|------|
| 存储抽象 | StorageInterface 统一接口 | 保持 file_mode 独立性，便于未来扩展 |
| file_mode 保留 | 完整保留，封装为适配器 | 项目初心不能丢 |
| RLS 实现 | PostgreSQL 原生 RLS | 原生支持、性能最好 |
| 权限粒度 | KB 级为主，原子级可选覆盖 | 简化管理，平衡灵活性 |
| 权限继承 | 自动继承 + 显式覆盖 | 符合直觉，减少配置 |
| 模式切换 | 配置项 + 运行时检测 | 灵活切换，无需重启 |
| 聚合搜索 | 联合查询 + 优先级排序 | 一次查询返回所有相关结果 |

---

## 实施顺序建议

### 串行任务（必须按顺序）
1. 阶段 1：双模式存储抽象（为后续所有阶段提供基础）
2. 阶段 2：多级知识库模型（依赖阶段 1 的存储接口）
3. 阶段 3：权限系统（依赖阶段 2 的知识库模型）
4. 阶段 4：知识库管理 API（依赖阶段 2 + 3）
5. 阶段 5：集成测试（依赖阶段 1-4）

### 可并行任务（在各自阶段内）
- 阶段 1 内：步骤 1.5（配置扩展）可与 1.1-1.4 并行
- 阶段 2 内：步骤 2.4（CLI）可与 2.1-2.3 并行
- 阶段 3 内：步骤 3.4（原子级权限）与 3.2（RLS）可部分并行

---

## 验收标准

### 阶段 1 验收
- [ ] StorageFactory 可通过配置创建不同存储实例
- [ ] StorageInterface 统一 API 完整定义
- [ ] FileSystemStorage 实现完整，兼容现有 file_mode 功能
- [ ] DatabaseStorage 实现完整，兼容现有 db_mode 功能
- [ ] 配置项 `storage.type` 切换生效
- [ ] 单元测试覆盖率 > 80%

### 阶段 2 验收
- [ ] 可创建 personal/department/project/company 四类知识库
- [ ] 层级关系正确（personal → department → project → company）
- [ ] 知识库聚合功能正常（company 包含子知识库内容）
- [ ] 可见性继承规则正确（不可放宽，只能收紧）
- [ ] CLI 命令正常执行
- [ ] API 端点正确响应

### 阶段 3 验收
- [ ] RLS 策略正确配置，未授权用户无法访问
- [ ] 角色权限正确（owner/editor/reader）
- [ ] 权限继承正确工作
- [ ] 权限检查中间件正确拦截未授权请求
- [ ] 原子级权限覆盖生效

### 阶段 4 验收
- [ ] 知识库 CRUD API 完整
- [ ] 成员管理 API 完整
- [ ] Web UI 知识库管理功能可用
- [ ] 集成测试通过

### 阶段 5 验收
- [ ] 双模式切换测试通过
- [ ] 多级知识库功能测试通过
- [ ] 权限系统测试通过
- [ ] 性能测试达标（查询延迟 < 200ms）
- [ ] 文档更新完成

---

## 下一步行动

1. **确认 PLAN-001 状态**：确保 PostgreSQL 迁移已完成
2. **确认资源投入**：6-8 周开发周期
3. **启动阶段 1**：双模式存储抽象层实现
4. **准备测试环境**：PostgreSQL 测试实例

---

**计划创建时间**：2026-06-22
**最后更新时间**：2026-06-22