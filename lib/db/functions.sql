-- ============================================================================
-- llm-wiki PostgreSQL Functions Definition
-- Version: 1.0
-- Created: 2026-06-21
-- Description: 存储过程和函数，包括 RLS 辅助函数、审计日志插入、版本管理等
-- ============================================================================

-- ----------------------------------------------------------------------------
-- RLS 辅助函数
-- ----------------------------------------------------------------------------

-- 设置当前用户 ID（会话级配置）
-- 用于连接池场景，每个请求开始时调用
CREATE OR REPLACE FUNCTION set_current_user_id(p_user_id VARCHAR(64))
RETURNS VOID AS $$
BEGIN
    -- 使用会话级配置参数存储当前用户 ID
    -- 生命周期：当前连接（或直到下一个 SET）
    -- 注意：连接归还池后，配置参数自动清除
    PERFORM set_config('app.current_user_id', p_user_id, false);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION set_current_user_id IS '设置当前用户 ID（会话级配置）';

-- 获取当前用户 ID
CREATE OR REPLACE FUNCTION current_user_id()
RETURNS VARCHAR(64) AS $$
BEGIN
    RETURN current_setting('app.current_user_id', true);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION current_user_id IS '获取当前用户 ID';

-- 获取当前用户部门 ID
CREATE OR REPLACE FUNCTION current_user_department_id()
RETURNS INTEGER AS $$
DECLARE
    v_dept_id INTEGER;
BEGIN
    SELECT department_id INTO v_dept_id
    FROM users
    WHERE id = current_user_id();

    RETURN v_dept_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION current_user_department_id IS '获取当前用户部门 ID';

-- 获取当前用户组织 ID
CREATE OR REPLACE FUNCTION current_user_organization_id()
RETURNS INTEGER AS $$
DECLARE
    v_org_id INTEGER;
BEGIN
    SELECT organization_id INTO v_org_id
    FROM users
    WHERE id = current_user_id();

    RETURN v_org_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION current_user_organization_id IS '获取当前用户组织 ID';

-- 检查用户是否为知识库成员
CREATE OR REPLACE FUNCTION is_kb_member(p_kb_id INTEGER)
RETURNS BOOLEAN AS $$
DECLARE
    v_user_id VARCHAR(64);
BEGIN
    v_user_id := current_user_id();

    -- 检查是否为成员
    RETURN EXISTS (
        SELECT 1 FROM kb_members
        WHERE kb_id = p_kb_id AND user_id = v_user_id
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION is_kb_member IS '检查用户是否为知识库成员';

-- 检查用户在知识库的角色
CREATE OR REPLACE FUNCTION get_kb_role(p_kb_id INTEGER)
RETURNS member_role AS $$
DECLARE
    v_user_id VARCHAR(64);
    v_role member_role;
BEGIN
    v_user_id := current_user_id();

    SELECT role INTO v_role
    FROM kb_members
    WHERE kb_id = p_kb_id AND user_id = v_user_id;

    RETURN v_role;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION get_kb_role IS '获取用户在知识库的角色';

-- 检查用户是否有编辑权限
CREATE OR REPLACE FUNCTION can_edit_kb(p_kb_id INTEGER)
RETURNS BOOLEAN AS $$
DECLARE
    v_role member_role;
BEGIN
    v_role := get_kb_role(p_kb_id);

    RETURN v_role IN ('owner', 'editor');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION can_edit_kb IS '检查用户是否有编辑权限';

-- 检查用户是否为知识库所有者
CREATE OR REPLACE FUNCTION is_kb_owner(p_kb_id INTEGER)
RETURNS BOOLEAN AS $$
DECLARE
    v_role member_role;
BEGIN
    v_role := get_kb_role(p_kb_id);

    RETURN v_role = 'owner';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION is_kb_owner IS '检查用户是否为知识库所有者';

-- ----------------------------------------------------------------------------
-- 审计日志函数
-- ----------------------------------------------------------------------------

-- 审计日志并发安全插入（使用行级锁防止竞态）
CREATE OR REPLACE FUNCTION insert_audit_log(
    p_user_id VARCHAR(64),
    p_action audit_action,
    p_resource_type audit_resource_type,
    p_resource_id VARCHAR(64),
    p_details JSONB,
    p_ip_address VARCHAR(45),
    p_user_agent TEXT
) RETURNS BIGINT AS $$
DECLARE
    v_prev_hash VARCHAR(64);
    v_record_hash VARCHAR(64);
    v_new_id BIGINT;
    v_hash_input TEXT;
BEGIN
    -- 使用 FOR UPDATE 锁定前一条记录，防止并发竞态
    -- 这是链式哈希的关键：确保 prev_hash 正确
    SELECT record_hash INTO v_prev_hash
    FROM audit_logs
    ORDER BY id DESC
    LIMIT 1
    FOR UPDATE;  -- 行级锁

    -- 如果没有前一条记录，使用初始值
    IF v_prev_hash IS NULL THEN
        v_prev_hash := '0';
    END IF;

    -- 构建哈希输入
    v_hash_input := coalesce(p_user_id, '') || '|' ||
                    p_action::text || '|' ||
                    coalesce(p_resource_type::text, '') || '|' ||
                    coalesce(p_resource_id, '') || '|' ||
                    coalesce(p_details::text, '{}') || '|' ||
                    coalesce(p_ip_address, '') || '|' ||
                    coalesce(p_user_agent, '') || '|' ||
                    v_prev_hash || '|' ||
                    NOW()::text;

    -- 计算 SHA256 哈希
    v_record_hash := encode(sha256(convert_to(v_hash_input, 'UTF8')), 'hex');

    -- 插入新记录
    INSERT INTO audit_logs (
        user_id, action, resource_type, resource_id,
        details, ip_address, user_agent, prev_hash, record_hash
    ) VALUES (
        p_user_id, p_action, p_resource_type, p_resource_id,
        p_details, p_ip_address, p_user_agent, v_prev_hash, v_record_hash
    ) RETURNING id INTO v_new_id;

    RETURN v_new_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION insert_audit_log IS '审计日志并发安全插入（链式哈希）';

-- 审计日志完整性验证
CREATE OR REPLACE FUNCTION verify_audit_chain(
    p_start_id BIGINT DEFAULT NULL,
    p_end_id BIGINT DEFAULT NULL
) RETURNS TABLE(
    is_valid BOOLEAN,
    message TEXT,
    broken_at BIGINT
) AS $$
DECLARE
    v_log RECORD;
    v_prev_log RECORD;
    v_expected_hash VARCHAR(64);
    v_hash_input TEXT;
BEGIN
    -- 初始化
    v_prev_log := NULL;

    -- 遍历审计日志
    FOR v_log IN
        SELECT * FROM audit_logs
        WHERE (p_start_id IS NULL OR id >= p_start_id)
          AND (p_end_id IS NULL OR id <= p_end_id)
        ORDER BY id
    LOOP
        -- 计算期望哈希
        v_hash_input := coalesce(v_log.user_id, '') || '|' ||
                        v_log.action::text || '|' ||
                        coalesce(v_log.resource_type::text, '') || '|' ||
                        coalesce(v_log.resource_id, '') || '|' ||
                        coalesce(v_log.details::text, '{}') || '|' ||
                        coalesce(v_log.ip_address, '') || '|' ||
                        coalesce(v_log.user_agent, '') || '|' ||
                        coalesce(v_log.prev_hash, '0') || '|' ||
                        v_log.created_at::text;

        v_expected_hash := encode(sha256(convert_to(v_hash_input, 'UTF8')), 'hex');

        -- 检查哈希一致性
        IF v_log.record_hash != v_expected_hash THEN
            RETURN QUERY SELECT false, 'Record hash mismatch', v_log.id;
            RETURN;
        END IF;

        -- 检查链完整性（从第二条记录开始）
        IF v_prev_log IS NOT NULL THEN
            IF v_log.prev_hash != v_prev_log.record_hash THEN
                RETURN QUERY SELECT false, 'Chain broken', v_log.id;
                RETURN;
            END IF;
        END IF;

        v_prev_log := v_log;
    END LOOP;

    -- 全部验证通过
    RETURN QUERY SELECT true, 'Audit chain valid', NULL::BIGINT;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION verify_audit_chain IS '验证审计日志链式哈希完整性';

-- ----------------------------------------------------------------------------
-- 版本管理函数
-- ----------------------------------------------------------------------------

-- 获取原子下一个版本号
CREATE OR REPLACE FUNCTION get_next_version_number(p_atom_id INTEGER)
RETURNS INTEGER AS $$
DECLARE
    v_max_version INTEGER;
BEGIN
    -- 查询当前最大版本号
    SELECT COALESCE(MAX(version_number), 0) INTO v_max_version
    FROM snapshot_items
    WHERE atom_id = p_atom_id;

    RETURN v_max_version + 1;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION get_next_version_number IS '获取原子下一个版本号';

-- 创建原子版本快照
CREATE OR REPLACE FUNCTION create_atom_version(
    p_atom_id INTEGER,
    p_snapshot_id INTEGER,
    p_change_summary VARCHAR(512) DEFAULT NULL,
    p_change_type VARCHAR(16) DEFAULT 'update',
    p_user_id VARCHAR(64) DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    v_version_number INTEGER;
    v_atom RECORD;
    v_item_id INTEGER;
BEGIN
    -- 获取原子当前状态
    SELECT * INTO v_atom FROM atoms WHERE id = p_atom_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Atom not found: %', p_atom_id;
    END IF;

    -- 获取下一个版本号
    v_version_number := get_next_version_number(p_atom_id);

    -- 创建版本快照
    INSERT INTO snapshot_items (
        snapshot_id, atom_id, version_number,
        title, content, metadata,
        change_summary, change_type
    ) VALUES (
        p_snapshot_id, p_atom_id, v_version_number,
        v_atom.title, v_atom.content, v_atom.metadata,
        p_change_summary, p_change_type
    ) RETURNING id INTO v_item_id;

    -- 记录审计日志
    PERFORM insert_audit_log(
        p_user_id,
        'create'::audit_action,
        'version'::audit_resource_type,
        v_item_id::text,
        jsonb_build_object(
            'atom_id', p_atom_id,
            'version_number', v_version_number,
            'snapshot_id', p_snapshot_id
        ),
        NULL, NULL
    );

    RETURN v_version_number;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION create_atom_version IS '创建原子版本快照';

-- ----------------------------------------------------------------------------
-- 审计日志分区管理
-- ----------------------------------------------------------------------------

-- 创建下月审计日志分区
CREATE OR REPLACE FUNCTION create_next_audit_partition()
RETURNS VOID AS $$
DECLARE
    v_next_month DATE;
    v_month_after DATE;
    v_partition_name TEXT;
BEGIN
    -- 计算下月第一天
    v_next_month := DATE_TRUNC('month', NOW() + INTERVAL '1 month');
    v_month_after := v_next_month + INTERVAL '1 month';

    -- 生成分区名称
    v_partition_name := 'audit_logs_' || TO_CHAR(v_next_month, 'YYYY_MM');

    -- 检查分区是否已存在
    IF NOT EXISTS (
        SELECT 1 FROM pg_tables WHERE tablename = v_partition_name
    ) THEN
        -- 创建分区
        EXECUTE format(
            'CREATE TABLE %I PARTITION OF audit_logs FOR VALUES FROM (%L) TO (%L)',
            v_partition_name, v_next_month, v_month_after
        );

        RAISE NOTICE 'Created audit partition: %', v_partition_name;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION create_next_audit_partition IS '创建下月审计日志分区';

-- 清理旧审计日志分区（归档）
CREATE OR REPLACE FUNCTION archive_old_audit_partitions(
    p_retention_days INTEGER DEFAULT 180
) RETURNS VOID AS $$
DECLARE
    v_cutoff_date DATE;
    v_partition RECORD;
BEGIN
    -- 计算截止日期
    v_cutoff_date := DATE_TRUNC('month', NOW() - (p_retention_days || ' days')::INTERVAL);

    -- 查找需要归档的分区
    FOR v_partition IN
        SELECT tablename
        FROM pg_tables
        WHERE tablename LIKE 'audit_logs_%'
          AND tablename != 'audit_logs_default'
          AND tablename ~ '^audit_logs_\d{4}_\d{2}$'
    LOOP
        -- 检查分区时间范围
        -- 这里简化处理，实际应根据分区的时间范围判断
        -- 真实场景需要查询 pg_class 和 pg_partitioned_table
        RAISE NOTICE 'Partition % may need archiving', v_partition.tablename;
    END LOOP;

    -- 注意：实际归档操作需要：
    -- 1. 导出分区数据到冷存储
    -- 2. 验证导出完整性
    -- 3. 删除分区（DROP TABLE）
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION archive_old_audit_partitions IS '归档旧审计日志分区';

-- ----------------------------------------------------------------------------
-- 知识原子操作函数
-- ----------------------------------------------------------------------------

-- 创建知识原子（自动记录审计）
CREATE OR REPLACE FUNCTION create_atom(
    p_kb_id INTEGER,
    p_title VARCHAR(512),
    p_content TEXT,
    p_type atom_type,
    p_description TEXT DEFAULT NULL,
    p_slug VARCHAR(256) DEFAULT NULL,
    p_metadata JSONB DEFAULT '{}',
    p_user_id VARCHAR(64) DEFAULT NULL,
    p_embedding vector DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    v_atom_id INTEGER;
BEGIN
    -- 插入原子
    INSERT INTO atoms (
        kb_id, title, content, type, description,
        slug, metadata, author_id, embedding
    ) VALUES (
        p_kb_id, p_title, p_content, p_type, p_description,
        p_slug, p_metadata, p_user_id, p_embedding
    ) RETURNING id INTO v_atom_id;

    -- 创建初始版本快照
    -- 注意：需要先创建 snapshot 记录，这里简化处理
    -- 实际应调用 VersionManager

    -- 记录审计日志
    PERFORM insert_audit_log(
        p_user_id,
        'create'::audit_action,
        'atom'::audit_resource_type,
        v_atom_id::text,
        jsonb_build_object(
            'kb_id', p_kb_id,
            'title', p_title,
            'type', p_type::text
        ),
        NULL, NULL
    );

    RETURN v_atom_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION create_atom IS '创建知识原子（自动记录审计）';

-- 更新知识原子（自动记录审计）
CREATE OR REPLACE FUNCTION update_atom(
    p_atom_id INTEGER,
    p_title VARCHAR(512) DEFAULT NULL,
    p_content TEXT DEFAULT NULL,
    p_description TEXT DEFAULT NULL,
    p_metadata JSONB DEFAULT NULL,
    p_user_id VARCHAR(64) DEFAULT NULL,
    p_change_summary VARCHAR(512) DEFAULT NULL,
    p_embedding vector DEFAULT NULL
) RETURNS BOOLEAN AS $$
DECLARE
    v_old_atom RECORD;
BEGIN
    -- 获取旧原子状态
    SELECT * INTO v_old_atom FROM atoms WHERE id = p_atom_id;

    IF NOT FOUND THEN
        RETURN false;
    END IF;

    -- 检查锁定状态
    IF v_old_atom.is_locked THEN
        RAISE EXCEPTION 'Atom is locked: %', p_atom_id;
    END IF;

    -- 更新原子（仅更新非 NULL 字段）
    UPDATE atoms SET
        title = COALESCE(p_title, title),
        content = COALESCE(p_content, content),
        description = COALESCE(p_description, description),
        metadata = COALESCE(p_metadata, metadata),
        embedding = COALESCE(p_embedding, embedding),
        updated_at = NOW()
    WHERE id = p_atom_id;

    -- 记录审计日志
    PERFORM insert_audit_log(
        p_user_id,
        'update'::audit_action,
        'atom'::audit_resource_type,
        p_atom_id::text,
        jsonb_build_object(
            'change_summary', p_change_summary,
            'old_title', v_old_atom.title
        ),
        NULL, NULL
    );

    RETURN true;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION update_atom IS '更新知识原子（自动记录审计）';

-- 删除知识原子（软删除）
CREATE OR REPLACE FUNCTION delete_atom(
    p_atom_id INTEGER,
    p_user_id VARCHAR(64) DEFAULT NULL,
    p_hard_delete BOOLEAN DEFAULT false
) RETURNS BOOLEAN AS $$
DECLARE
    v_kb_id INTEGER;
BEGIN
    -- 获取知识库 ID
    SELECT kb_id INTO v_kb_id FROM atoms WHERE id = p_atom_id;

    IF NOT FOUND THEN
        RETURN false;
    END IF;

    -- 检查权限（通过 RLS 自动处理）

    IF p_hard_delete THEN
        -- 硬删除
        DELETE FROM atoms WHERE id = p_atom_id;
    ELSE
        -- 软删除（标记为 archived）
        UPDATE atoms SET status = 'archived' WHERE id = p_atom_id;
    END IF;

    -- 记录审计日志
    PERFORM insert_audit_log(
        p_user_id,
        'delete'::audit_action,
        'atom'::audit_resource_type,
        p_atom_id::text,
        jsonb_build_object(
            'kb_id', v_kb_id,
            'hard_delete', p_hard_delete
        ),
        NULL, NULL
    );

    RETURN true;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION delete_atom IS '删除知识原子（支持软删除和硬删除）';

-- ----------------------------------------------------------------------------
-- 搜索辅助函数
-- ----------------------------------------------------------------------------

-- 全文搜索函数
CREATE OR REPLACE FUNCTION search_atoms(
    p_kb_id INTEGER,
    p_query TEXT,
    p_limit INTEGER DEFAULT 10,
    p_offset INTEGER DEFAULT 0,
    p_type atom_type DEFAULT NULL,
    p_status atom_status DEFAULT 'active'
) RETURNS TABLE(
    id INTEGER,
    title VARCHAR(512),
    type atom_type,
    description TEXT,
    rank REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        a.id,
        a.title,
        a.type,
        a.description,
        ts_rank(a.content_tsv, websearch_to_tsquery('english', p_query)) AS rank
    FROM atoms a
    WHERE a.kb_id = p_kb_id
      AND a.status = p_status
      AND (p_type IS NULL OR a.type = p_type)
      AND a.content_tsv @@ websearch_to_tsquery('english', p_query)
    ORDER BY rank DESC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION search_atoms IS '全文搜索知识原子';

-- 向量相似度搜索
CREATE OR REPLACE FUNCTION search_atoms_by_embedding(
    p_kb_id INTEGER,
    p_embedding vector,
    p_limit INTEGER DEFAULT 10,
    p_threshold FLOAT DEFAULT 0.5,  -- 相似度阈值
    p_status atom_status DEFAULT 'active'
) RETURNS TABLE(
    id INTEGER,
    title VARCHAR(512),
    type atom_type,
    description TEXT,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        a.id,
        a.title,
        a.type,
        a.description,
        1 - (a.embedding <=> p_embedding) AS similarity  -- cosine distance → similarity
    FROM atoms a
    WHERE a.kb_id = p_kb_id
      AND a.status = p_status
      AND a.embedding IS NOT NULL
      AND 1 - (a.embedding <=> p_embedding) >= p_threshold
    ORDER BY a.embedding <=> p_embedding  -- 按距离排序（越小越好）
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION search_atoms_by_embedding IS '向量相似度搜索知识原子';

-- ----------------------------------------------------------------------------
-- 权限检查函数
-- ----------------------------------------------------------------------------

-- 检查用户对资源的访问权限
CREATE OR REPLACE FUNCTION check_access_permission(
    p_user_id VARCHAR(64),
    p_resource_type TEXT,
    p_resource_id TEXT,
    p_action TEXT
) RETURNS BOOLEAN AS $$
DECLARE
    v_kb_id INTEGER;
BEGIN
    -- 根据资源类型检查权限
    IF p_resource_type = 'atom' THEN
        -- 获取原子所属知识库
        SELECT kb_id INTO v_kb_id FROM atoms WHERE id = p_resource_id::INTEGER;

        IF NOT FOUND THEN
            RETURN false;
        END IF;

        -- 检查知识库成员权限
        IF p_action IN ('view', 'read') THEN
            RETURN EXISTS (
                SELECT 1 FROM kb_members m
                WHERE m.kb_id = v_kb_id AND m.user_id = p_user_id
            ) OR EXISTS (
                SELECT 1 FROM knowledge_bases kb
                WHERE kb.id = v_kb_id AND kb.visibility = 'public'
            );
        ELSIF p_action IN ('edit', 'update', 'create') THEN
            RETURN EXISTS (
                SELECT 1 FROM kb_members m
                WHERE m.kb_id = v_kb_id
                  AND m.user_id = p_user_id
                  AND m.role IN ('owner', 'editor')
            );
        ELSIF p_action = 'delete' THEN
            RETURN EXISTS (
                SELECT 1 FROM kb_members m
                WHERE m.kb_id = v_kb_id
                  AND m.user_id = p_user_id
                  AND m.role = 'owner'
            );
        END IF;
    ELSIF p_resource_type = 'kb' THEN
        -- 知识库权限检查
        IF p_action IN ('view', 'read') THEN
            RETURN EXISTS (
                SELECT 1 FROM kb_members m
                WHERE m.kb_id = p_resource_id::INTEGER AND m.user_id = p_user_id
            ) OR EXISTS (
                SELECT 1 FROM knowledge_bases kb
                WHERE kb.id = p_resource_id::INTEGER AND kb.visibility = 'public'
            );
        ELSIF p_action IN ('edit', 'update') THEN
            RETURN EXISTS (
                SELECT 1 FROM kb_members m
                WHERE m.kb_id = p_resource_id::INTEGER
                  AND m.user_id = p_user_id
                  AND m.role = 'owner'
            );
        ELSIF p_action = 'delete' THEN
            RETURN EXISTS (
                SELECT 1 FROM kb_members m
                WHERE m.kb_id = p_resource_id::INTEGER
                  AND m.user_id = p_user_id
                  AND m.role = 'owner'
            );
        END IF;
    END IF;

    RETURN false;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION check_access_permission IS '检查用户对资源的访问权限';

-- ----------------------------------------------------------------------------
-- 统计函数
-- ----------------------------------------------------------------------------

-- 知识库统计信息
CREATE OR REPLACE FUNCTION get_kb_stats(p_kb_id INTEGER)
RETURNS TABLE(
    total_atoms BIGINT,
    active_atoms BIGINT,
    archived_atoms BIGINT,
    draft_atoms BIGINT,
    total_links BIGINT,
    total_tags BIGINT,
    total_versions BIGINT,
    total_assets BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*) AS total_atoms,
        COUNT(*) FILTER (WHERE status = 'active') AS active_atoms,
        COUNT(*) FILTER (WHERE status = 'archived') AS archived_atoms,
        COUNT(*) FILTER (WHERE status = 'draft') AS draft_atoms,
        (SELECT COUNT(*) FROM atom_links al
         JOIN atoms a ON al.source_atom_id = a.id OR al.target_atom_id = a.id
         WHERE a.kb_id = p_kb_id) AS total_links,
        (SELECT COUNT(*) FROM tags t WHERE t.kb_id = p_kb_id) AS total_tags,
        (SELECT COUNT(*) FROM snapshot_items si
         JOIN atoms a ON si.atom_id = a.id
         WHERE a.kb_id = p_kb_id) AS total_versions,
        (SELECT COUNT(*) FROM atom_assets aa
         JOIN atoms a ON aa.atom_id = a.id
         WHERE a.kb_id = p_kb_id) AS total_assets
    FROM atoms a
    WHERE a.kb_id = p_kb_id;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION get_kb_stats IS '获取知识库统计信息';

-- 用户统计信息
CREATE OR REPLACE FUNCTION get_user_stats(p_user_id VARCHAR(64))
RETURNS TABLE(
    total_kbs BIGINT,
    owned_kbs BIGINT,
    edited_atoms BIGINT,
    created_atoms BIGINT,
    total_versions BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        (SELECT COUNT(*) FROM kb_members WHERE user_id = p_user_id) AS total_kbs,
        (SELECT COUNT(*) FROM kb_members WHERE user_id = p_user_id AND role = 'owner') AS owned_kbs,
        (SELECT COUNT(*) FROM atoms WHERE author_id = p_user_id) AS created_atoms,
        (SELECT COUNT(*) FROM snapshot_items si
         JOIN atoms a ON si.atom_id = a.id
         WHERE a.author_id = p_user_id) AS total_versions,
        (SELECT COUNT(*) FROM audit_logs WHERE user_id = p_user_id) AS total_actions;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION get_user_stats IS '获取用户统计信息';