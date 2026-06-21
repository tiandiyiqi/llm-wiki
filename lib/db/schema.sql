-- ============================================================================
-- llm-wiki PostgreSQL Schema Definition
-- Version: 1.0
-- Created: 2026-06-21
-- Description: 核心表结构定义，支持多租户知识库管理
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 扩展启用
-- ----------------------------------------------------------------------------

-- 启用 pgvector 扩展（向量索引）
CREATE EXTENSION IF NOT EXISTS vector;

-- 启用 pgcrypto 扩展（字段加密）
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 启用 uuid-ossp 扩展（UUID 生成）
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ----------------------------------------------------------------------------
-- 枚举类型定义
-- ----------------------------------------------------------------------------

-- 知识库类型
CREATE TYPE kb_type AS ENUM (
    'personal',     -- 个人知识库
    'department',   -- 部门知识库
    'project',      -- 项目知识库
    'company'       -- 公司知识库
);

-- 知识库可见性
CREATE TYPE kb_visibility AS ENUM (
    'private',      -- 私有（仅成员可见）
    'team',         -- 团队（组织内可见）
    'public'        -- 公开（所有人可见）
);

-- 知识库存储模式
CREATE TYPE kb_storage_mode AS ENUM (
    'file',         -- 文件模式（Markdown）
    'db'            -- 数据库模式（PostgreSQL）
);

-- 知识原子类型
CREATE TYPE atom_type AS ENUM (
    'method',       -- 方法
    'fact',         -- 事实
    'definition',   -- 定义
    'opinion',      -- 观点
    'data',         -- 数据
    'question',     -- 问题
    'reference'     -- 参考
);

-- 知识原子状态
CREATE TYPE atom_status AS ENUM (
    'active',       -- 活跃
    'archived',     -- 已归档
    'draft'         -- 草稿
);

-- 成员角色
CREATE TYPE member_role AS ENUM (
    'owner',        -- 所有者（完全权限）
    'editor',       -- 编辑者（读写权限）
    'reader'        -- 读者（只读权限）
);

-- 链接类型
CREATE TYPE link_type AS ENUM (
    'reference',    -- 参考
    'citation',     -- 引用
    'seealso',      -- 参见
    'related'       -- 相关
);

-- 审计操作类型
CREATE TYPE audit_action AS ENUM (
    'create',       -- 创建
    'update',       -- 更新
    'delete',       -- 删除
    'view',         -- 查看
    'export',       -- 导出
    'import',       -- 导入
    'login',        -- 登录
    'logout'        -- 登出
);

-- 审计资源类型
CREATE TYPE audit_resource_type AS ENUM (
    'atom',         -- 知识原子
    'kb',           -- 知识库
    'user',         -- 用户
    'asset',        -- 资产
    'version'       -- 版本
);

-- ----------------------------------------------------------------------------
-- 组织架构表
-- ----------------------------------------------------------------------------

-- 组织表
CREATE TABLE organizations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(256) NOT NULL,
    slug VARCHAR(128) UNIQUE NOT NULL,

    -- 配置
    settings JSONB DEFAULT '{}',

    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE organizations IS '组织表';
COMMENT ON COLUMN organizations.slug IS 'URL 友好标识';

-- 部门表
CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(256) NOT NULL,
    slug VARCHAR(128),

    -- 层级结构
    parent_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,

    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(org_id, slug)
);

COMMENT ON TABLE departments IS '部门表';
COMMENT ON COLUMN departments.parent_id IS '上级部门ID';

-- 项目表（临时知识库关联）
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    org_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(256) NOT NULL,
    slug VARCHAR(128),

    -- 项目周期
    start_date DATE,
    end_date DATE,

    -- 状态
    status VARCHAR(16) DEFAULT 'active',

    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(org_id, slug)
);

COMMENT ON TABLE projects IS '项目表';

-- ----------------------------------------------------------------------------
-- 用户表
-- ----------------------------------------------------------------------------

CREATE TABLE users (
    id VARCHAR(64) PRIMARY KEY,              -- Casdoor 用户 ID
    name VARCHAR(256) NOT NULL,
    email VARCHAR(256),
    phone VARCHAR(32),

    -- 加密字段（敏感信息）
    phone_encrypted BYTEA,                   -- pgcrypto 加密
    email_encrypted BYTEA,

    -- 组织关系
    organization_id INTEGER REFERENCES organizations(id) ON DELETE SET NULL,
    department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,

    -- 全局角色
    global_role VARCHAR(32) DEFAULT 'user',  -- admin/user

    -- 状态
    status VARCHAR(16) DEFAULT 'active',

    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE
);

COMMENT ON TABLE users IS '用户表（与 Casdoor 同步）';
COMMENT ON COLUMN users.id IS 'Casdoor 用户 ID';
COMMENT ON COLUMN users.global_role IS '全局角色：admin/user';

-- ----------------------------------------------------------------------------
-- 知识库表
-- ----------------------------------------------------------------------------

CREATE TABLE knowledge_bases (
    id SERIAL PRIMARY KEY,
    name VARCHAR(256) NOT NULL,
    slug VARCHAR(128) UNIQUE NOT NULL,       -- URL 友好标识
    type kb_type NOT NULL,                   -- 知识库类型
    description TEXT,

    -- 关联关系
    organization_id INTEGER REFERENCES organizations(id) ON DELETE SET NULL,
    owner_id VARCHAR(64) REFERENCES users(id) ON DELETE SET NULL,
    department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,

    -- 权限配置
    visibility kb_visibility DEFAULT 'private',
    is_aggregated BOOLEAN DEFAULT false,     -- 是否为聚合知识库

    -- 存储模式
    storage_mode kb_storage_mode DEFAULT 'db',

    -- 元数据
    settings JSONB DEFAULT '{}',             -- 知识库配置
    created_by VARCHAR(64) REFERENCES users(id),

    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- 约束
    CONSTRAINT chk_kb_project_owner CHECK (
        type != 'project' OR project_id IS NOT NULL
    )
);

COMMENT ON TABLE knowledge_bases IS '知识库表';
COMMENT ON COLUMN knowledge_bases.slug IS 'URL 友好标识';
COMMENT ON COLUMN knowledge_bases.visibility IS '可见性：private/team/public';
COMMENT ON COLUMN knowledge_bases.is_aggregated IS '是否为聚合知识库（公司知识库）';

-- ----------------------------------------------------------------------------
-- 知识库成员表
-- ----------------------------------------------------------------------------

CREATE TABLE kb_members (
    kb_id INTEGER NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role member_role NOT NULL DEFAULT 'reader',

    -- 扩展权限
    permissions JSONB DEFAULT '{}',

    -- 时间戳
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    invited_by VARCHAR(64) REFERENCES users(id),

    PRIMARY KEY (kb_id, user_id)
);

COMMENT ON TABLE kb_members IS '知识库成员表';
COMMENT ON COLUMN kb_members.role IS '角色：owner/editor/reader';
COMMENT ON COLUMN kb_members.permissions IS '扩展权限配置';

-- ----------------------------------------------------------------------------
-- 知识库聚合表
-- ----------------------------------------------------------------------------

CREATE TABLE kb_aggregations (
    parent_kb_id INTEGER NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    child_kb_id INTEGER NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,

    -- 聚合配置
    include_private BOOLEAN DEFAULT false,   -- 是否包含私有内容
    priority INTEGER DEFAULT 0,              -- 搜索优先级

    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    PRIMARY KEY (parent_kb_id, child_kb_id),

    -- 禁止自引用
    CONSTRAINT chk_no_self_aggregate CHECK (parent_kb_id != child_kb_id)
);

COMMENT ON TABLE kb_aggregations IS '知识库聚合关系表（公司知识库包含子知识库）';

-- ----------------------------------------------------------------------------
-- 知识原子表
-- ----------------------------------------------------------------------------

CREATE TABLE atoms (
    id SERIAL PRIMARY KEY,
    kb_id INTEGER NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,

    -- 基本字段
    title VARCHAR(512) NOT NULL,
    slug VARCHAR(256),                       -- URL 友好标识
    type atom_type NOT NULL,                 -- 知识原子类型
    description TEXT,
    content TEXT NOT NULL,

    -- 元数据（JSONB 存储 frontmatter）
    metadata JSONB DEFAULT '{}',             -- tags, confidence, source, etc.

    -- 关联关系
    author_id VARCHAR(64) REFERENCES users(id) ON DELETE SET NULL,

    -- 向量嵌入（pgvector，384 维对应 all-MiniLM-L6-v2）
    embedding vector(384),

    -- 全文索引（自动生成）
    content_tsv TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(content, '')), 'C')
    ) STORED,

    -- 状态
    status atom_status DEFAULT 'active',
    is_locked BOOLEAN DEFAULT false,         -- 编辑锁

    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- 唯一约束
    UNIQUE(kb_id, slug)
);

COMMENT ON TABLE atoms IS '知识原子表';
COMMENT ON COLUMN atoms.slug IS 'URL 友好标识';
COMMENT ON COLUMN atoms.type IS '知识原子类型：method/fact/definition/opinion/data/question/reference';
COMMENT ON COLUMN atoms.metadata IS '元数据（JSONB 存储 frontmatter）';
COMMENT ON COLUMN atoms.embedding IS '向量嵌入（pgvector，384 维）';
COMMENT ON COLUMN atoms.content_tsv IS '全文索引（自动生成）';
COMMENT ON COLUMN atoms.is_locked IS '编辑锁（防止并发编辑）';

-- ----------------------------------------------------------------------------
-- 知识原子链接表
-- ----------------------------------------------------------------------------

CREATE TABLE atom_links (
    id SERIAL PRIMARY KEY,
    source_atom_id INTEGER NOT NULL REFERENCES atoms(id) ON DELETE CASCADE,
    target_atom_id INTEGER NOT NULL REFERENCES atoms(id) ON DELETE CASCADE,
    link_type link_type DEFAULT 'reference',

    -- 元数据
    metadata JSONB DEFAULT '{}',

    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- 唯一约束
    UNIQUE(source_atom_id, target_atom_id, link_type),

    -- 禁止自链接
    CONSTRAINT chk_no_self_link CHECK (source_atom_id != target_atom_id)
);

COMMENT ON TABLE atom_links IS '知识原子链接关系表';
COMMENT ON COLUMN atom_links.link_type IS '链接类型：reference/citation/seealso/related';

-- ----------------------------------------------------------------------------
-- 标签表
-- ----------------------------------------------------------------------------

CREATE TABLE tags (
    id SERIAL PRIMARY KEY,
    kb_id INTEGER REFERENCES knowledge_bases(id) ON DELETE CASCADE,

    -- 标签信息
    name VARCHAR(128) NOT NULL,
    slug VARCHAR(128),
    color VARCHAR(7),                        -- HEX 颜色值
    description TEXT,

    -- 层级结构
    parent_id INTEGER REFERENCES tags(id) ON DELETE SET NULL,

    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(kb_id, slug)
);

COMMENT ON TABLE tags IS '标签表';
COMMENT ON COLUMN tags.color IS 'HEX 颜色值，如 #FF5733';

-- ----------------------------------------------------------------------------
-- 原子标签关联表
-- ----------------------------------------------------------------------------

CREATE TABLE atom_tags (
    atom_id INTEGER NOT NULL REFERENCES atoms(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,

    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    PRIMARY KEY (atom_id, tag_id)
);

COMMENT ON TABLE atom_tags IS '知识原子与标签的关联表';

-- ----------------------------------------------------------------------------
-- 版本快照表
-- ----------------------------------------------------------------------------

CREATE TABLE snapshots (
    id SERIAL PRIMARY KEY,
    kb_id INTEGER NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,

    -- 快照信息
    name VARCHAR(256) NOT NULL,
    description TEXT,
    snapshot_type VARCHAR(32) DEFAULT 'manual',  -- manual/auto/scheduled

    -- 快照内容（汇总信息）
    atom_count INTEGER DEFAULT 0,
    asset_count INTEGER DEFAULT 0,
    size_bytes BIGINT DEFAULT 0,

    -- 校验
    checksum VARCHAR(64),                    -- SHA256

    -- 创建者
    created_by VARCHAR(64) REFERENCES users(id),

    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE snapshots IS '版本快照表';
COMMENT ON COLUMN snapshots.snapshot_type IS '快照类型：manual/auto/scheduled';

-- 快照项表
CREATE TABLE snapshot_items (
    id SERIAL PRIMARY KEY,
    snapshot_id INTEGER NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
    atom_id INTEGER NOT NULL REFERENCES atoms(id) ON DELETE CASCADE,

    -- 版本信息
    version_number INTEGER NOT NULL,

    -- 快照内容
    title VARCHAR(512),
    content TEXT,
    metadata JSONB,
    assets_snapshot JSONB,                   -- 关联图像资产快照

    -- 变更信息
    change_summary VARCHAR(512),
    change_type VARCHAR(16) DEFAULT 'update',  -- create/update/delete

    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(snapshot_id, atom_id)
);

COMMENT ON TABLE snapshot_items IS '快照项表';
COMMENT ON COLUMN snapshot_items.version_number IS '原子版本号';

-- ----------------------------------------------------------------------------
-- 图像资产表
-- ----------------------------------------------------------------------------

CREATE TABLE atom_assets (
    id SERIAL PRIMARY KEY,
    atom_id INTEGER NOT NULL REFERENCES atoms(id) ON DELETE CASCADE,

    -- 基本信息
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255),
    mime_type VARCHAR(64) NOT NULL,
    size INTEGER NOT NULL,                   -- 字节数

    -- 存储方式
    storage_type VARCHAR(16) NOT NULL,       -- inline/external

    -- 内联存储（小文件，< 1MB）
    data BYTEA,

    -- 外部存储（大文件）
    storage_path VARCHAR(512),
    storage_provider VARCHAR(32),            -- local/minio/s3/oss

    -- 校验
    checksum VARCHAR(64),                    -- SHA256

    -- 图像元数据
    width INTEGER,
    height INTEGER,
    thumbnail BYTEA,                         -- 缩略图

    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(64) REFERENCES users(id),

    -- 存储一致性约束
    CONSTRAINT chk_storage_consistency CHECK (
        (storage_type = 'inline' AND data IS NOT NULL) OR
        (storage_type = 'external' AND storage_path IS NOT NULL)
    )
);

COMMENT ON TABLE atom_assets IS '知识原子图像资产表';
COMMENT ON COLUMN atom_assets.storage_type IS '存储类型：inline（内联）/external（外部）';
COMMENT ON COLUMN atom_assets.storage_provider IS '外部存储提供商：local/minio/s3/oss';

-- ----------------------------------------------------------------------------
-- 审计日志表（分区表）
-- ----------------------------------------------------------------------------

-- 创建父表（分区）
CREATE TABLE audit_logs (
    id BIGSERIAL,                            -- 注意：分区表不能使用 PRIMARY KEY

    -- 操作信息
    user_id VARCHAR(64) REFERENCES users(id),
    action audit_action NOT NULL,
    resource_type audit_resource_type,
    resource_id VARCHAR(64),

    -- 详细信息
    details JSONB,
    ip_address VARCHAR(45),                  -- 支持 IPv6
    user_agent TEXT,

    -- 链式哈希（不可篡改）
    record_hash VARCHAR(64) NOT NULL,        -- 当前记录哈希
    prev_hash VARCHAR(64),                   -- 前一条记录哈希

    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- 分区键
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

COMMENT ON TABLE audit_logs IS '审计日志表（不可篡改，按时间分区）';
COMMENT ON COLUMN audit_logs.record_hash IS '当前记录哈希（SHA256）';
COMMENT ON COLUMN audit_logs.prev_hash IS '前一条记录哈希（链式结构）';

-- 创建默认分区（当前月份）
CREATE TABLE audit_logs_default
    PARTITION OF audit_logs DEFAULT;

-- 创建初始分区（2026年6月）
CREATE TABLE audit_logs_2026_06
    PARTITION OF audit_logs
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');

-- 创建下月分区（2026年7月）
CREATE TABLE audit_logs_2026_07
    PARTITION OF audit_logs
    FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');

-- ----------------------------------------------------------------------------
-- 触发器：自动更新 updated_at
-- ----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 应用到各表
CREATE TRIGGER organizations_updated_at
    BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER knowledge_bases_updated_at
    BEFORE UPDATE ON knowledge_bases
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER atoms_updated_at
    BEFORE UPDATE ON atoms
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- ----------------------------------------------------------------------------
-- 初始化数据
-- ----------------------------------------------------------------------------

-- 创建默认组织
INSERT INTO organizations (name, slug, settings)
VALUES ('Default Organization', 'default', '{}')
ON CONFLICT (slug) DO NOTHING;

-- 创建系统用户（用于系统操作）
INSERT INTO users (id, name, global_role, status)
VALUES ('system', 'System', 'admin', 'active')
ON CONFLICT (id) DO NOTHING;
