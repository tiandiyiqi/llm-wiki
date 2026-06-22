-- ============================================================================
-- llm-wiki PostgreSQL Indexes Definition
-- Version: 1.0
-- Created: 2026-06-21
-- Description: 索引定义，包括全文索引、向量索引和常用查询索引
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 组织架构索引
-- ----------------------------------------------------------------------------

-- 部门表索引
CREATE INDEX idx_departments_org ON departments(org_id);
CREATE INDEX idx_departments_parent ON departments(parent_id);

-- 项目表索引
CREATE INDEX idx_projects_org ON projects(org_id);
CREATE INDEX idx_projects_status ON projects(status);

-- 用户表索引
CREATE INDEX idx_users_org ON users(organization_id);
CREATE INDEX idx_users_dept ON users(department_id);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_email ON users(email) WHERE email IS NOT NULL;
CREATE INDEX idx_users_global_role ON users(global_role);

-- ----------------------------------------------------------------------------
-- 知识库索引
-- ----------------------------------------------------------------------------

-- 知识库表索引
CREATE INDEX idx_kb_type ON knowledge_bases(type);
CREATE INDEX idx_kb_owner ON knowledge_bases(owner_id);
CREATE INDEX idx_kb_org ON knowledge_bases(organization_id);
CREATE INDEX idx_kb_dept ON knowledge_bases(department_id);
CREATE INDEX idx_kb_visibility ON knowledge_bases(visibility);
CREATE INDEX idx_kb_storage_mode ON knowledge_bases(storage_mode);
CREATE INDEX idx_kb_created ON knowledge_bases(created_at DESC);

-- 知识库成员表索引
CREATE INDEX idx_kb_members_user ON kb_members(user_id);
CREATE INDEX idx_kb_members_role ON kb_members(role);
CREATE INDEX idx_kb_members_kb_role ON kb_members(kb_id, role);

-- 知识库聚合表索引
CREATE INDEX idx_kb_aggregations_parent ON kb_aggregations(parent_kb_id);
CREATE INDEX idx_kb_aggregations_child ON kb_aggregations(child_kb_id);

-- ----------------------------------------------------------------------------
-- 知识原子索引
-- ----------------------------------------------------------------------------

-- 基本索引
CREATE INDEX idx_atoms_kb ON atoms(kb_id);
CREATE INDEX idx_atoms_type ON atoms(type);
CREATE INDEX idx_atoms_author ON atoms(author_id);
CREATE INDEX idx_atoms_status ON atoms(status);
CREATE INDEX idx_atoms_created ON atoms(created_at DESC);
CREATE INDEX idx_atoms_updated ON atoms(updated_at DESC);

-- slug 索引（用于 URL 查询）
CREATE INDEX idx_atoms_slug ON atoms(kb_id, slug) WHERE slug IS NOT NULL;

-- 元数据索引（GIN，支持 JSONB 查询）
CREATE INDEX idx_atoms_metadata ON atoms USING GIN(metadata);

-- 标签查询索引
CREATE INDEX idx_atoms_tags ON atoms USING GIN((metadata->'tags'));

-- 置信度查询索引
CREATE INDEX idx_atoms_confidence ON atoms((metadata->>'confidence'))
    WHERE metadata->>'confidence' IS NOT NULL;

-- 来源查询索引
CREATE INDEX idx_atoms_source ON atoms((metadata->>'source'))
    WHERE metadata->>'source' IS NOT NULL;

-- ----------------------------------------------------------------------------
-- 全文索引（tsvector）
-- ----------------------------------------------------------------------------

-- 全文搜索索引（GIN）
CREATE INDEX idx_atoms_tsv ON atoms USING GIN(content_tsv);

-- 优化短语搜索（可选，占用更多空间）
-- CREATE INDEX idx_atoms_tsv_phrase ON atoms USING GIN(content_tsv gin_fast_ops);

-- 中文全文索引（如需中文支持，需安装 zhparser 扩展）
-- CREATE INDEX idx_atoms_tsv_chinese ON atoms USING GIN(
--     to_tsvector('zhparser', coalesce(title, '') || ' ' || coalesce(content, ''))
-- );

-- ----------------------------------------------------------------------------
-- pg_trgm 模糊搜索索引
-- ----------------------------------------------------------------------------

-- 标题模糊匹配索引（支持 LIKE '%keyword%' 和相似度搜索）
CREATE INDEX IF NOT EXISTS idx_atoms_title_trgm ON atoms USING gin(title gin_trgm_ops);

-- 描述模糊匹配索引
CREATE INDEX IF NOT EXISTS idx_atoms_description_trgm ON atoms USING gin(description gin_trgm_ops)
    WHERE description IS NOT NULL;

-- 搜索历史表（用于搜索联想和热门搜索词统计）
CREATE TABLE IF NOT EXISTS search_history (
    id BIGSERIAL PRIMARY KEY,
    query TEXT NOT NULL,
    user_id VARCHAR(64),
    kb_id INTEGER REFERENCES knowledge_bases(id) ON DELETE SET NULL,
    result_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE search_history IS '搜索历史记录表';
COMMENT ON COLUMN search_history.query IS '搜索查询字符串';
COMMENT ON COLUMN search_history.result_count IS '搜索结果数量';

-- 搜索历史索引
CREATE INDEX IF NOT EXISTS idx_search_history_query ON search_history(query);
CREATE INDEX IF NOT EXISTS idx_search_history_user ON search_history(user_id);
CREATE INDEX IF NOT EXISTS idx_search_history_kb ON search_history(kb_id);
CREATE INDEX IF NOT EXISTS idx_search_history_created ON search_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_search_history_query_trgm ON search_history USING gin(query gin_trgm_ops);

-- ----------------------------------------------------------------------------
-- 向量索引（pgvector）
-- ----------------------------------------------------------------------------

-- 注意：向量索引应在数据量较大（>1000 条）后创建
-- 小数据量时，暴力搜索可能更快

-- IVFFlat 索引（适合 < 1M 向量）
-- lists 参数建议：sqrt(行数)
-- 对于 10K 向量：lists = 100
-- 对于 100K 向量：lists = 300
-- 对于 1M 向量：lists = 1000

-- 创建向量索引（延迟创建，等数据量足够）
-- CREATE INDEX idx_atoms_embedding ON atoms
--     USING ivfflat (embedding vector_cosine_ops)
--     WITH (lists = 100);

-- HNSW 索引（适合 > 1M 向量，更高精度但内存占用大）
-- CREATE INDEX idx_atoms_embedding_hnsw ON atoms
--     USING hnsw (embedding vector_cosine_ops)
--     WITH (m = 16, ef_construction = 64);

-- 向量索引创建函数（供迁移脚本调用）
CREATE OR REPLACE FUNCTION create_vector_index_if_needed(
    p_table_name TEXT DEFAULT 'atoms',
    p_column_name TEXT DEFAULT 'embedding',
    p_lists INTEGER DEFAULT 100
) RETURNS VOID AS $$
DECLARE
    v_count INTEGER;
    v_index_name TEXT;
BEGIN
    -- 检查表中的向量数量
    EXECUTE format('SELECT COUNT(*) FROM %I WHERE %I IS NOT NULL', p_table_name, p_column_name)
    INTO v_count;

    -- 只有数据量 >= 1000 时才创建索引
    IF v_count >= 1000 THEN
        v_index_name := format('idx_%s_%s_ivfflat', p_table_name, p_column_name);

        -- 检查索引是否已存在
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes WHERE indexname = v_index_name
        ) THEN
            EXECUTE format(
                'CREATE INDEX %I ON %I USING ivfflat (%I vector_cosine_ops) WITH (lists = %s)',
                v_index_name, p_table_name, p_column_name, p_lists
            );
            RAISE NOTICE 'Created vector index % with lists = %', v_index_name, p_lists;
        END IF;
    ELSE
        RAISE NOTICE 'Skipping vector index creation: only % vectors (need >= 1000)', v_count;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ----------------------------------------------------------------------------
-- 链接关系索引
-- ----------------------------------------------------------------------------

CREATE INDEX idx_atom_links_source ON atom_links(source_atom_id);
CREATE INDEX idx_atom_links_target ON atom_links(target_atom_id);
CREATE INDEX idx_atom_links_type ON atom_links(link_type);

-- 反向链接查询优化
CREATE INDEX idx_atom_links_target_type ON atom_links(target_atom_id, link_type);

-- ----------------------------------------------------------------------------
-- 标签索引
-- ----------------------------------------------------------------------------

CREATE INDEX idx_tags_kb ON tags(kb_id);
CREATE INDEX idx_tags_parent ON tags(parent_id);
CREATE INDEX idx_tags_name ON tags(kb_id, name);

-- 原子标签关联索引
CREATE INDEX idx_atom_tags_atom ON atom_tags(atom_id);
CREATE INDEX idx_atom_tags_tag ON atom_tags(tag_id);

-- ----------------------------------------------------------------------------
-- 版本快照索引
-- ----------------------------------------------------------------------------

CREATE INDEX idx_snapshots_kb ON snapshots(kb_id);
CREATE INDEX idx_snapshots_created ON snapshots(created_at DESC);
CREATE INDEX idx_snapshots_type ON snapshots(snapshot_type);
CREATE INDEX idx_snapshots_creator ON snapshots(created_by);

-- 快照项索引
CREATE INDEX idx_snapshot_items_snapshot ON snapshot_items(snapshot_id);
CREATE INDEX idx_snapshot_items_atom ON snapshot_items(atom_id);
CREATE INDEX idx_snapshot_items_version ON snapshot_items(atom_id, version_number DESC);

-- ----------------------------------------------------------------------------
-- 资产索引
-- ----------------------------------------------------------------------------

CREATE INDEX idx_atom_assets_atom ON atom_assets(atom_id);
CREATE INDEX idx_atom_assets_type ON atom_assets(storage_type);
CREATE INDEX idx_atom_assets_creator ON atom_assets(created_by);
CREATE INDEX idx_atom_assets_mime ON atom_assets(mime_type);

-- 大文件查询优化（外部存储）
CREATE INDEX idx_atom_assets_external ON atom_assets(storage_provider, storage_path)
    WHERE storage_type = 'external';

-- ----------------------------------------------------------------------------
-- 审计日志索引
-- ----------------------------------------------------------------------------

-- 用户查询
CREATE INDEX idx_audit_user ON audit_logs(user_id);

-- 操作类型查询
CREATE INDEX idx_audit_action ON audit_logs(action);

-- 资源查询
CREATE INDEX idx_audit_resource ON audit_logs(resource_type, resource_id);

-- 时间范围查询
CREATE INDEX idx_audit_time ON audit_logs(created_at DESC);

-- 组合查询（用户 + 时间）
CREATE INDEX idx_audit_user_time ON audit_logs(user_id, created_at DESC);

-- 组合查询（资源 + 时间）
CREATE INDEX idx_audit_resource_time ON audit_logs(resource_type, resource_id, created_at DESC);

-- ----------------------------------------------------------------------------
-- 部分索引（优化常用查询）
-- ----------------------------------------------------------------------------

-- 活跃原子查询
CREATE INDEX idx_atoms_active ON atoms(kb_id, created_at DESC)
    WHERE status = 'active';

-- 未锁定原子查询
CREATE INDEX idx_atoms_unlocked ON atoms(kb_id, updated_at DESC)
    WHERE is_locked = false;

-- 有嵌入的原子查询
CREATE INDEX idx_atoms_with_embedding ON atoms(kb_id)
    WHERE embedding IS NOT NULL;

-- 公开知识库查询
CREATE INDEX idx_kb_public ON knowledge_bases(type, created_at DESC)
    WHERE visibility = 'public';

-- ----------------------------------------------------------------------------
-- 表达式索引
-- ----------------------------------------------------------------------------

-- 标题首字母索引（快速筛选）
CREATE INDEX idx_atoms_title_initial ON atoms(kb_id, LOWER(LEFT(title, 1)));

-- 内容长度索引（用于筛选短/长内容）
CREATE INDEX idx_atoms_content_length ON atoms(kb_id, LENGTH(content));

-- 元数据标签数组长度索引
CREATE INDEX idx_atoms_tag_count ON atoms(kb_id, jsonb_array_length(metadata->'tags'))
    WHERE metadata->'tags' IS NOT NULL;

-- ----------------------------------------------------------------------------
-- 并发索引创建说明
-- ----------------------------------------------------------------------------

-- 对于生产环境的大表，建议使用 CONCURRENTLY 创建索引，避免锁表：
-- CREATE INDEX CONCURRENTLY idx_name ON table(column);
--
-- 注意：
-- 1. CONCURRENTLY 不能在事务中使用
-- 2. 创建时间更长，但不会阻塞写入
-- 3. 如果失败，索引会标记为 invalid，需要删除重建
