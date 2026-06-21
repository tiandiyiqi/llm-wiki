-- ============================================================================
-- llm-wiki PostgreSQL RLS (Row-Level Security) Policies
-- Version: 1.0
-- Created: 2026-06-21
-- Description: 行级安全策略，实现多租户数据隔离和权限控制
-- ============================================================================

-- ----------------------------------------------------------------------------
-- RLS 说明
-- ----------------------------------------------------------------------------
--
-- PostgreSQL RLS (Row-Level Security) 允许在数据库层面实现数据隔离。
--
-- 工作原理：
-- 1. 每个请求开始时，应用层调用 set_current_user_id() 设置用户上下文
-- 2. RLS 策略使用 current_user_id() 函数获取当前用户 ID
-- 3. 查询自动过滤，只返回用户有权访问的行
--
-- 连接池注意事项：
-- - set_config(..., false) 设置的是会话级参数
-- - 连接归还池后，参数自动清除
-- - 每个请求必须重新设置用户上下文
--
-- 管理员绕过：
-- - 表所有者默认绕过 RLS
-- - 可通过 ALTER TABLE ... FORCE ROW LEVEL SECURITY 强制应用
-- ----------------------------------------------------------------------------

-- ----------------------------------------------------------------------------
-- 知识库表 RLS 策略
-- ----------------------------------------------------------------------------

-- 启用 RLS
ALTER TABLE knowledge_bases ENABLE ROW LEVEL SECURITY;

-- 管理员也强制应用 RLS（可选，根据需求决定）
-- ALTER TABLE knowledge_bases FORCE ROW LEVEL SECURITY;

-- 知识库查询策略：用户可访问自己拥有、是成员、或公开的知识库
CREATE POLICY kb_select_policy ON knowledge_bases
    FOR SELECT
    USING (
        -- 所有者可访问
        owner_id = current_user_id() OR

        -- 成员可访问
        EXISTS (
            SELECT 1 FROM kb_members
            WHERE kb_id = id AND user_id = current_user_id()
        ) OR

        -- 公开知识库任何人可访问
        visibility = 'public' OR

        -- 团队知识库：同组织用户可访问
        (visibility = 'team' AND organization_id = current_user_organization_id()) OR

        -- 系统用户绕过（用于系统操作）
        current_user_id() = 'system' OR

        -- 管理员可访问所有
        EXISTS (
            SELECT 1 FROM users
            WHERE id = current_user_id() AND global_role = 'admin'
        )
    );

COMMENT ON POLICY kb_select_policy ON knowledge_bases IS
    '知识库查询策略：所有者、成员、公开、团队共享、管理员可访问';

-- 知识库插入策略：用户可创建知识库（需验证组织权限）
CREATE POLICY kb_insert_policy ON knowledge_bases
    FOR INSERT
    WITH CHECK (
        -- 创建者必须是所有者
        owner_id = current_user_id() OR

        -- 系统用户绕过
        current_user_id() = 'system' OR

        -- 管理员可创建
        EXISTS (
            SELECT 1 FROM users
            WHERE id = current_user_id() AND global_role = 'admin'
        )
    );

COMMENT ON POLICY kb_insert_policy ON knowledge_bases IS
    '知识库插入策略：所有者、系统用户、管理员可创建';

-- 知识库更新策略：仅所有者和管理员可修改
CREATE POLICY kb_update_policy ON knowledge_bases
    FOR UPDATE
    USING (
        -- 所有者可修改
        owner_id = current_user_id() OR

        -- 系统用户绕过
        current_user_id() = 'system' OR

        -- 管理员可修改
        EXISTS (
            SELECT 1 FROM users
            WHERE id = current_user_id() AND global_role = 'admin'
        )
    )
    WITH CHECK (
        -- 更新后仍需满足访问条件
        owner_id = current_user_id() OR
        current_user_id() = 'system' OR
        EXISTS (
            SELECT 1 FROM users
            WHERE id = current_user_id() AND global_role = 'admin'
        )
    );

COMMENT ON POLICY kb_update_policy ON knowledge_bases IS
    '知识库更新策略：仅所有者和管理员可修改';

-- 知识库删除策略：仅所有者和管理员可删除
CREATE POLICY kb_delete_policy ON knowledge_bases
    FOR DELETE
    USING (
        -- 所有者可删除
        owner_id = current_user_id() OR

        -- 系统用户绕过
        current_user_id() = 'system' OR

        -- 管理员可删除
        EXISTS (
            SELECT 1 FROM users
            WHERE id = current_user_id() AND global_role = 'admin'
        )
    );

COMMENT ON POLICY kb_delete_policy ON knowledge_bases IS
    '知识库删除策略：仅所有者和管理员可删除';

-- ----------------------------------------------------------------------------
-- 知识原子表 RLS 策略
-- ----------------------------------------------------------------------------

-- 启用 RLS
ALTER TABLE atoms ENABLE ROW LEVEL SECURITY;

-- 知识原子查询策略：基于知识库权限
CREATE POLICY atom_select_policy ON atoms
    FOR SELECT
    USING (
        -- 系统用户绕过
        current_user_id() = 'system' OR

        -- 管理员可访问所有
        EXISTS (
            SELECT 1 FROM users
            WHERE id = current_user_id() AND global_role = 'admin'
        ) OR

        -- 知识库成员可访问
        EXISTS (
            SELECT 1 FROM kb_members m
            WHERE m.kb_id = atoms.kb_id AND m.user_id = current_user_id()
        ) OR

        -- 公开知识库的原子任何人可访问
        EXISTS (
            SELECT 1 FROM knowledge_bases kb
            WHERE kb.id = atoms.kb_id AND kb.visibility = 'public'
        ) OR

        -- 团队知识库：同组织用户可访问
        EXISTS (
            SELECT 1 FROM knowledge_bases kb
            WHERE kb.id = atoms.kb_id
              AND kb.visibility = 'team'
              AND kb.organization_id = current_user_organization_id()
        )
    );

COMMENT ON POLICY atom_select_policy ON atoms IS
    '知识原子查询策略：基于知识库成员身份或公开可见性';

-- 知识原子插入策略：知识库编辑者及以上角色可创建
CREATE POLICY atom_insert_policy ON atoms
    FOR INSERT
    WITH CHECK (
        -- 系统用户绕过
        current_user_id() = 'system' OR

        -- 管理员可创建
        EXISTS (
            SELECT 1 FROM users
            WHERE id = current_user_id() AND global_role = 'admin'
        ) OR

        -- 知识库编辑者及以上可创建
        EXISTS (
            SELECT 1 FROM kb_members m
            WHERE m.kb_id = atoms.kb_id
              AND m.user_id = current_user_id()
              AND m.role IN ('owner', 'editor')
        )
    );

COMMENT ON POLICY atom_insert_policy ON atoms IS
    '知识原子插入策略：编辑者及以上角色可创建';

-- 知识原子更新策略：知识库编辑者及以上角色可修改（需检查锁定状态）
CREATE POLICY atom_update_policy ON atoms
    FOR UPDATE
    USING (
        -- 系统用户绕过
        current_user_id() = 'system' OR

        -- 管理员可修改
        EXISTS (
            SELECT 1 FROM users
            WHERE id = current_user_id() AND global_role = 'admin'
        ) OR

        -- 知识库编辑者及以上可修改（非锁定状态）
        (NOT is_locked AND EXISTS (
            SELECT 1 FROM kb_members m
            WHERE m.kb_id = atoms.kb_id
              AND m.user_id = current_user_id()
              AND m.role IN ('owner', 'editor')
        ))
    )
    WITH CHECK (
        -- 更新后仍需满足权限条件
        current_user_id() = 'system' OR
        EXISTS (
            SELECT 1 FROM users
            WHERE id = current_user_id() AND global_role = 'admin'
        ) OR
        EXISTS (
            SELECT 1 FROM kb_members m
            WHERE m.kb_id = atoms.kb_id
              AND m.user_id = current_user_id()
              AND m.role IN ('owner', 'editor')
        )
    );

COMMENT ON POLICY atom_update_policy ON atoms IS
    '知识原子更新策略：编辑者及以上角色可修改（非锁定）';

-- 知识原子删除策略：仅所有者可删除
CREATE POLICY atom_delete_policy ON atoms
    FOR DELETE
    USING (
        -- 系统用户绕过
        current_user_id() = 'system' OR

        -- 管理员可删除
        EXISTS (
            SELECT 1 FROM users
            WHERE id = current_user_id() AND global_role = 'admin'
        ) OR

        -- 知识库所有者可删除
        EXISTS (
            SELECT 1 FROM kb_members m
            WHERE m.kb_id = atoms.kb_id
              AND m.user_id = current_user_id()
              AND m.role = 'owner'
        )
    );

COMMENT ON POLICY atom_delete_policy ON atoms IS
    '知识原子删除策略：仅所有者和管理员可删除';

-- ----------------------------------------------------------------------------
-- 知识库成员表 RLS 策略
-- ----------------------------------------------------------------------------

-- 启用 RLS
ALTER TABLE kb_members ENABLE ROW LEVEL SECURITY;

-- 成员查询策略：知识库成员可查看其他成员
CREATE POLICY kb_members_select_policy ON kb_members
    FOR SELECT
    USING (
        -- 系统用户绕过
        current_user_id() = 'system' OR

        -- 管理员可访问
        EXISTS (
            SELECT 1 FROM users
            WHERE id = current_user_id() AND global_role = 'admin'
        ) OR

        -- 自己是成员的知识库
        EXISTS (
            SELECT 1 FROM kb_members m
            WHERE m.kb_id = kb_members.kb_id AND m.user_id = current_user_id()
        ) OR

        -- 公开知识库的成员信息可查看
        EXISTS (
            SELECT 1 FROM knowledge_bases kb
            WHERE kb.id = kb_members.kb_id AND kb.visibility = 'public'
        )
    );

COMMENT ON POLICY kb_members_select_policy ON kb_members IS
    '成员查询策略：知识库成员可查看其他成员';

-- 成员插入策略：仅所有者可添加成员
CREATE POLICY kb_members_insert_policy ON kb_members
    FOR INSERT
    WITH CHECK (
        -- 系统用户绕过
        current_user_id() = 'system' OR

        -- 管理员可添加
        EXISTS (
            SELECT 1 FROM users
            WHERE id = current_user_id() AND global_role = 'admin'
        ) OR

        -- 知识库所有者可添加成员
        EXISTS (
            SELECT 1 FROM kb_members m
            WHERE m.kb_id = kb_members.kb_id
              AND m.user_id = current_user_id()
              AND m.role = 'owner'
        )
    );

COMMENT ON POLICY kb_members_insert_policy ON kb_members IS
    '成员插入策略：仅所有者和管理员可添加成员';

-- 成员更新策略：仅所有者可修改成员角色
CREATE POLICY kb_members_update_policy ON kb_members
    FOR UPDATE
    USING (
        -- 系统用户绕过
        current_user_id() = 'system' OR

        -- 管理员可修改
        EXISTS (
            SELECT 1 FROM users
            WHERE id = current_user_id() AND global_role = 'admin'
        ) OR

        -- 知识库所有者可修改
        EXISTS (
            SELECT 1 FROM kb_members m
            WHERE m.kb_id = kb_members.kb_id
              AND m.user_id = current_user_id()
              AND m.role = 'owner'
        )
    )
    WITH CHECK (
        -- 不能将最后一个所有者降级
        -- 注：这个检查需要在 USING 中也加上，防止绕过
        NOT (
            kb_members.role != 'owner' AND
            NOT EXISTS (
                SELECT 1 FROM kb_members m
                WHERE m.kb_id = kb_members.kb_id
                  AND m.role = 'owner'
                  AND m.user_id != kb_members.user_id
            )
        ) AND
        (
            current_user_id() = 'system' OR
            EXISTS (
                SELECT 1 FROM users
                WHERE id = current_user_id() AND global_role = 'admin'
            ) OR
            EXISTS (
                SELECT 1 FROM kb_members m
                WHERE m.kb_id = kb_members.kb_id
                  AND m.user_id = current_user_id()
                  AND m.role = 'owner'
            )
        )
    );

COMMENT ON POLICY kb_members_update_policy ON kb_members IS
    '成员更新策略：仅所有者和管理员可修改成员角色';

-- 成员删除策略：仅所有者可移除成员（不能移除最后一个所有者）
CREATE POLICY kb_members_delete_policy ON kb_members
    FOR DELETE
    USING (
        -- 系统用户绕过
        current_user_id() = 'system' OR

        -- 管理员可删除
        EXISTS (
            SELECT 1 FROM users
            WHERE id = current_user_id() AND global_role = 'admin'
        ) OR

        -- 知识库所有者可删除成员
        EXISTS (
            SELECT 1 FROM kb_members m
            WHERE m.kb_id = kb_members.kb_id
              AND m.user_id = current_user_id()
              AND m.role = 'owner'
        )
    )
    -- 不能删除最后一个所有者（通过触发器或应用层检查）
    ;

COMMENT ON POLICY kb_members_delete_policy ON kb_members IS
    '成员删除策略：仅所有者和管理员可移除成员';

-- ----------------------------------------------------------------------------
-- 知识原子链接表 RLS 策略
-- ----------------------------------------------------------------------------

-- 启用 RLS（链接的权限继承自原子）
ALTER TABLE atom_links ENABLE ROW LEVEL SECURITY;

-- 链接查询策略：可访问源原子和目标原子时可查看链接
CREATE POLICY atom_links_select_policy ON atom_links
    FOR SELECT
    USING (
        -- 系统用户绕过
        current_user_id() = 'system' OR

        -- 管理员可访问
        EXISTS (
            SELECT 1 FROM users
            WHERE id = current_user_id() AND global_role = 'admin'
        ) OR

        -- 可访问源原子
        EXISTS (
            SELECT 1 FROM atoms a
            WHERE a.id = atom_links.source_atom_id
              AND (
                EXISTS (
                    SELECT 1 FROM kb_members m
                    WHERE m.kb_id = a.kb_id AND m.user_id = current_user_id()
                ) OR
                EXISTS (
                    SELECT 1 FROM knowledge_bases kb
                    WHERE kb.id = a.kb_id AND kb.visibility = 'public'
                )
              )
        )
    );

COMMENT ON POLICY atom_links_select_policy ON atom_links IS
    '链接查询策略：可访问源原子时可查看链接';

-- 链接插入策略：对两个原子都有编辑权限时可创建链接
CREATE POLICY atom_links_insert_policy ON atom_links
    FOR INSERT
    WITH CHECK (
        -- 系统用户绕过
        current_user_id() = 'system' OR

        -- 管理员可创建
        EXISTS (
            SELECT 1 FROM users
            WHERE id = current_user_id() AND global_role = 'admin'
        ) OR

        -- 对源原子有编辑权限
        EXISTS (
            SELECT 1 FROM atoms a
            JOIN kb_members m ON m.kb_id = a.kb_id
            WHERE a.id = atom_links.source_atom_id
              AND m.user_id = current_user_id()
              AND m.role IN ('owner', 'editor')
        )
    );

COMMENT ON POLICY atom_links_insert_policy ON atom_links IS
    '链接插入策略：对源原子有编辑权限时可创建链接';

-- 链接删除策略：对源原子有编辑权限时可删除链接
CREATE POLICY atom_links_delete_policy ON atom_links
    FOR DELETE
    USING (
        -- 系统用户绕过
        current_user_id() = 'system' OR

        -- 管理员可删除
        EXISTS (
            SELECT 1 FROM users
            WHERE id = current_user_id() AND global_role = 'admin'
        ) OR

        -- 对源原子有编辑权限
        EXISTS (
            SELECT 1 FROM atoms a
            JOIN kb_members m ON m.kb_id = a.kb_id
            WHERE a.id = atom_links.source_atom_id
              AND m.user_id = current_user_id()
              AND m.role IN ('owner', 'editor')
        )
    );

COMMENT ON POLICY atom_links_delete_policy ON atom_links IS
    '链接删除策略：对源原子有编辑权限时可删除链接';

-- ----------------------------------------------------------------------------
-- 标签表 RLS 策略
-- ----------------------------------------------------------------------------

-- 启用 RLS
ALTER TABLE tags ENABLE ROW LEVEL SECURITY;

-- 标签查询策略：知识库成员或公开知识库可查看标签
CREATE POLICY tags_select_policy ON tags
    FOR SELECT
    USING (
        -- 系统用户绕过
        current_user_id() = 'system' OR

        -- 管理员可访问
        EXISTS (
            SELECT 1 FROM users
            WHERE id = current_user_id() AND global_role = 'admin'
        ) OR

        -- kb_id 为空（全局标签）
        kb_id IS NULL OR

        -- 知识库成员可访问
        EXISTS (
            SELECT 1 FROM kb_members m
            WHERE m.kb_id = tags.kb_id AND m.user_id = current_user_id()
        ) OR

        -- 公开知识库的标签可查看
        EXISTS (
            SELECT 1 FROM knowledge_bases kb
            WHERE kb.id = tags.kb_id AND kb.visibility = 'public'
        )
    );

COMMENT ON POLICY tags_select_policy ON tags IS
    '标签查询策略：知识库成员或公开知识库可查看标签';

-- 标签插入策略：编辑者及以上可创建标签
CREATE POLICY tags_insert_policy ON tags
    FOR INSERT
    WITH CHECK (
        -- 系统用户绕过
        current_user_id() = 'system' OR

        -- 管理员可创建
        EXISTS (
            SELECT 1 FROM users
            WHERE id = current_user_id() AND global_role = 'admin'
        ) OR

        -- 知识库编辑者及以上可创建
        (kb_id IS NOT NULL AND EXISTS (
            SELECT 1 FROM kb_members m
            WHERE m.kb_id = tags.kb_id
              AND m.user_id = current_user_id()
              AND m.role IN ('owner', 'editor')
        ))
    );

COMMENT ON POLICY tags_insert_policy ON tags IS
    '标签插入策略：编辑者及以上可创建标签';

-- 标签更新策略：编辑者及以上可修改标签
CREATE POLICY tags_update_policy ON tags
    FOR UPDATE
    USING (
        -- 系统用户绕过
        current_user_id() = 'system' OR

        -- 管理员可修改
        EXISTS (
            SELECT 1 FROM users
            WHERE id = current_user_id() AND global_role = 'admin'
        ) OR

        -- 知识库编辑者及以上可修改
        (kb_id IS NOT NULL AND EXISTS (
            SELECT 1 FROM kb_members m
            WHERE m.kb_id = tags.kb_id
              AND m.user_id = current_user_id()
              AND m.role IN ('owner', 'editor')
        ))
    );

COMMENT ON POLICY tags_update_policy ON tags IS
    '标签更新策略：编辑者及以上可修改标签';

-- 标签删除策略：仅所有者可删除标签
CREATE POLICY tags_delete_policy ON tags
    FOR DELETE
    USING (
        -- 系统用户绕过
        current_user_id() = 'system' OR

        -- 管理员可删除
        EXISTS (
            SELECT 1 FROM users
            WHERE id = current_user_id() AND global_role = 'admin'
        ) OR

        -- 知识库所有者可删除
        (kb_id IS NOT NULL AND EXISTS (
            SELECT 1 FROM kb_members m
            WHERE m.kb_id = tags.kb_id
              AND m.user_id = current_user_id()
              AND m.role = 'owner'
        ))
    );

COMMENT ON POLICY tags_delete_policy ON tags IS
    '标签删除策略：仅所有者和管理员可删除标签';

-- ----------------------------------------------------------------------------
-- 原子标签关联表 RLS 策略
-- ----------------------------------------------------------------------------

-- 启用 RLS
ALTER TABLE atom_tags ENABLE ROW LEVEL SECURITY;

-- 原子标签查询策略：继承原子权限
CREATE POLICY atom_tags_select_policy ON atom_tags
    FOR SELECT
    USING (
        -- 系统用户绕过
        current_user_id() = 'system' OR

        -- 管理员可访问
        EXISTS (
            SELECT 1 FROM users
            WHERE id = current_user_id() AND global_role = 'admin'
        ) OR

        -- 可访问原子时可查看关联
        EXISTS (
            SELECT 1 FROM atoms a
            WHERE a.id = atom_tags.atom_id
              AND (
                EXISTS (
                    SELECT 1 FROM kb_members m
                    WHERE m.kb_id = a.kb_id AND m.user_id = current_user_id()
                ) OR
                EXISTS (
                    SELECT 1 FROM knowledge_bases kb
                    WHERE kb.id = a.kb_id AND kb.visibility = 'public'
                )
              )
        )
    );

COMMENT ON POLICY atom_tags_select_policy ON atom_tags IS
    '原子标签查询策略：继承原子权限';

-- 原子标签插入策略：对原子有编辑权限时可关联标签
CREATE POLICY atom_tags_insert_policy ON atom_tags
    FOR INSERT
    WITH CHECK (
        -- 系统用户绕过
        current_user_id() = 'system' OR

        -- 管理员可创建
        EXISTS (
            SELECT 1 FROM users
            WHERE id = current_user_id() AND global_role = 'admin'
        ) OR

        -- 对原子有编辑权限
        EXISTS (
            SELECT 1 FROM atoms a
            JOIN kb_members m ON m.kb_id = a.kb_id
            WHERE a.id = atom_tags.atom_id
              AND m.user_id = current_user_id()
              AND m.role IN ('owner', 'editor')
        )
    );

COMMENT ON POLICY atom_tags_insert_policy ON atom_tags IS
    '原子标签插入策略：对原子有编辑权限时可关联标签';

-- 原子标签删除策略：对原子有编辑权限时可移除关联
CREATE POLICY atom_tags_delete_policy ON atom_tags
    FOR DELETE
    USING (
        -- 系统用户绕过
        current_user_id() = 'system' OR

        -- 管理员可删除
        EXISTS (
            SELECT 1 FROM users
            WHERE id = current_user_id() AND global_role = 'admin'
        ) OR

        -- 对原子有编辑权限
        EXISTS (
            SELECT 1 FROM atoms a
            JOIN kb_members m ON m.kb_id = a.kb_id
            WHERE a.id = atom_tags.atom_id
              AND m.user_id = current_user_id()
              AND m.role IN ('owner', 'editor')
        )
    );

COMMENT ON POLICY atom_tags_delete_policy ON atom_tags IS
    '原子标签删除策略：对原子有编辑权限时可移除关联';

-- ----------------------------------------------------------------------------
-- 版本快照表 RLS 策略
-- ----------------------------------------------------------------------------

-- 启用 RLS
ALTER TABLE snapshots ENABLE ROW LEVEL SECURITY;

-- 快照查询策略：知识库成员可查看
CREATE POLICY snapshots_select_policy ON snapshots
    FOR SELECT
    USING (
        -- 系统用户绕过
        current_user_id() = 'system' OR

        -- 管理员可访问
        EXISTS (
            SELECT 1 FROM users
            WHERE id = current_user_id() AND global_role = 'admin'
        ) OR

        -- 知识库成员可查看
        EXISTS (
            SELECT 1 FROM kb_members m
            WHERE m.kb_id = snapshots.kb_id AND m.user_id = current_user_id()
        ) OR

        -- 公开知识库的快照可查看
        EXISTS (
            SELECT 1 FROM knowledge_bases kb
            WHERE kb.id = snapshots.kb_id AND kb.visibility = 'public'
        )
    );

COMMENT ON POLICY snapshots_select_policy ON snapshots IS
    '快照查询策略：知识库成员可查看';

-- 快照插入策略：所有者可创建快照
CREATE POLICY snapshots_insert_policy ON snapshots
    FOR INSERT
    WITH CHECK (
        -- 系统用户绕过
        current_user_id() = 'system' OR

        -- 管理员可创建
        EXISTS (
            SELECT 1 FROM users
            WHERE id = current_user_id() AND global_role = 'admin'
        ) OR

        -- 知识库所有者可创建快照
        EXISTS (
            SELECT 1 FROM kb_members m
            WHERE m.kb_id = snapshots.kb_id
              AND m.user_id = current_user_id()
              AND m.role = 'owner'
        )
    );

COMMENT ON POLICY snapshots_insert_policy ON snapshots IS
    '快照插入策略：所有者可创建快照';

-- 快照删除策略：仅所有者可删除快照
CREATE POLICY snapshots_delete_policy ON snapshots
    FOR DELETE
    USING (
        -- 系统用户绕过
        current_user_id() = 'system' OR

        -- 管理员可删除
        EXISTS (
            SELECT 1 FROM users
            WHERE id = current_user_id() AND global_role = 'admin'
        ) OR

        -- 知识库所有者可删除快照
        EXISTS (
            SELECT 1 FROM kb_members m
            WHERE m.kb_id = snapshots.kb_id
              AND m.user_id = current_user_id()
              AND m.role = 'owner'
        )
    );

COMMENT ON POLICY snapshots_delete_policy ON snapshots IS
    '快照删除策略：仅所有者可删除快照';

-- ----------------------------------------------------------------------------
-- 快照项表 RLS 策略
-- ----------------------------------------------------------------------------

-- 启用 RLS（继承快照权限）
ALTER TABLE snapshot_items ENABLE ROW LEVEL SECURITY;

-- 快照项查询策略：继承快照权限
CREATE POLICY snapshot_items_select_policy ON snapshot_items
    FOR SELECT
    USING (
        -- 系统用户绕过
        current_user_id() = 'system' OR

        -- 管理员可访问
        EXISTS (
            SELECT 1 FROM users
            WHERE id = current_user_id() AND global_role = 'admin'
        ) OR

        -- 通过快照检查权限
        EXISTS (
            SELECT 1 FROM snapshots s
            JOIN kb_members m ON m.kb_id = s.kb_id
            WHERE s.id = snapshot_items.snapshot_id
              AND m.user_id = current_user_id()
        ) OR

        -- 公开知识库的快照项可查看
        EXISTS (
            SELECT 1 FROM snapshots s
            JOIN knowledge_bases kb ON kb.id = s.kb_id
            WHERE s.id = snapshot_items.snapshot_id AND kb.visibility = 'public'
        )
    );

COMMENT ON POLICY snapshot_items_select_policy ON snapshot_items IS
    '快照项查询策略：继承快照权限';

-- ----------------------------------------------------------------------------
-- 资产表 RLS 策略
-- ----------------------------------------------------------------------------

-- 启用 RLS
ALTER TABLE atom_assets ENABLE ROW LEVEL SECURITY;

-- 资产查询策略：继承原子权限
CREATE POLICY atom_assets_select_policy ON atom_assets
    FOR SELECT
    USING (
        -- 系统用户绕过
        current_user_id() = 'system' OR

        -- 管理员可访问
        EXISTS (
            SELECT 1 FROM users
            WHERE id = current_user_id() AND global_role = 'admin'
        ) OR

        -- 可访问原子时可查看资产
        EXISTS (
            SELECT 1 FROM atoms a
            WHERE a.id = atom_assets.atom_id
              AND (
                EXISTS (
                    SELECT 1 FROM kb_members m
                    WHERE m.kb_id = a.kb_id AND m.user_id = current_user_id()
                ) OR
                EXISTS (
                    SELECT 1 FROM knowledge_bases kb
                    WHERE kb.id = a.kb_id AND kb.visibility = 'public'
                )
              )
        )
    );

COMMENT ON POLICY atom_assets_select_policy ON atom_assets IS
    '资产查询策略：继承原子权限';

-- 资产插入策略：对原子有编辑权限时可上传资产
CREATE POLICY atom_assets_insert_policy ON atom_assets
    FOR INSERT
    WITH CHECK (
        -- 系统用户绕过
        current_user_id() = 'system' OR

        -- 管理员可上传
        EXISTS (
            SELECT 1 FROM users
            WHERE id = current_user_id() AND global_role = 'admin'
        ) OR

        -- 对原子有编辑权限
        EXISTS (
            SELECT 1 FROM atoms a
            JOIN kb_members m ON m.kb_id = a.kb_id
            WHERE a.id = atom_assets.atom_id
              AND m.user_id = current_user_id()
              AND m.role IN ('owner', 'editor')
        )
    );

COMMENT ON POLICY atom_assets_insert_policy ON atom_assets IS
    '资产插入策略：对原子有编辑权限时可上传资产';

-- 资产删除策略：对原子有编辑权限时可删除资产
CREATE POLICY atom_assets_delete_policy ON atom_assets
    FOR DELETE
    USING (
        -- 系统用户绕过
        current_user_id() = 'system' OR

        -- 管理员可删除
        EXISTS (
            SELECT 1 FROM users
            WHERE id = current_user_id() AND global_role = 'admin'
        ) OR

        -- 对原子有编辑权限
        EXISTS (
            SELECT 1 FROM atoms a
            JOIN kb_members m ON m.kb_id = a.kb_id
            WHERE a.id = atom_assets.atom_id
              AND m.user_id = current_user_id()
              AND m.role IN ('owner', 'editor')
        )
    );

COMMENT ON POLICY atom_assets_delete_policy ON atom_assets IS
    '资产删除策略：对原子有编辑权限时可删除资产';

-- ----------------------------------------------------------------------------
-- 审计日志表 RLS 策略
-- ----------------------------------------------------------------------------

-- 启用 RLS（审计日志是敏感数据，限制访问）
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- 审计日志查询策略：仅管理员可查看所有，用户可查看自己的操作记录
CREATE POLICY audit_logs_select_policy ON audit_logs
    FOR SELECT
    USING (
        -- 系统用户绕过
        current_user_id() = 'system' OR

        -- 管理员可查看所有
        EXISTS (
            SELECT 1 FROM users
            WHERE id = current_user_id() AND global_role = 'admin'
        ) OR

        -- 用户可查看自己的操作记录
        user_id = current_user_id()
    );

COMMENT ON POLICY audit_logs_select_policy ON audit_logs IS
    '审计日志查询策略：仅管理员可查看所有，用户可查看自己的操作记录';

-- 审计日志仅允许 INSERT，禁止 UPDATE 和 DELETE（通过函数插入）
-- 注意：已通过 REVOKE UPDATE, DELETE 权限实现，这里不需要 RLS

-- ----------------------------------------------------------------------------
-- 用户表 RLS 策略
-- ----------------------------------------------------------------------------

-- 启用 RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- 用户查询策略：用户可查看自己的信息，管理员可查看所有
CREATE POLICY users_select_policy ON users
    FOR SELECT
    USING (
        -- 系统用户绕过
        current_user_id() = 'system' OR

        -- 管理员可查看所有
        EXISTS (
            SELECT 1 FROM users u
            WHERE u.id = current_user_id() AND u.global_role = 'admin'
        ) OR

        -- 用户可查看自己的信息
        id = current_user_id() OR

        -- 公开信息：同组织用户可查看基本信息
        (organization_id = current_user_organization_id())
    );

COMMENT ON POLICY users_select_policy ON users IS
    '用户查询策略：用户可查看自己的信息，同组织用户可查看基本信息';

-- 用户更新策略：用户可修改自己的信息，管理员可修改所有
CREATE POLICY users_update_policy ON users
    FOR UPDATE
    USING (
        -- 系统用户绕过
        current_user_id() = 'system' OR

        -- 管理员可修改
        EXISTS (
            SELECT 1 FROM users u
            WHERE u.id = current_user_id() AND u.global_role = 'admin'
        ) OR

        -- 用户可修改自己的信息
        id = current_user_id()
    )
    WITH CHECK (
        -- 更新后不能修改 global_role（除非是管理员）
        (
            EXISTS (
                SELECT 1 FROM users u
                WHERE u.id = current_user_id() AND u.global_role = 'admin'
            )
        ) OR (
            global_role = (SELECT global_role FROM users WHERE id = current_user_id())
        )
    );

COMMENT ON POLICY users_update_policy ON users IS
    '用户更新策略：用户可修改自己的信息，管理员可修改所有';

-- ----------------------------------------------------------------------------
-- RLS 测试函数
-- ----------------------------------------------------------------------------

-- 测试 RLS 策略是否正确应用
CREATE OR REPLACE FUNCTION test_rls_policy(
    p_user_id VARCHAR(64),
    p_kb_id INTEGER,
    p_expected_atoms_count INTEGER
) RETURNS BOOLEAN AS $$
DECLARE
    v_actual_count INTEGER;
BEGIN
    -- 设置用户上下文
    PERFORM set_current_user_id(p_user_id);

    -- 查询原子数量
    SELECT COUNT(*) INTO v_actual_count FROM atoms WHERE kb_id = p_kb_id;

    -- 检查结果
    IF v_actual_count != p_expected_atoms_count THEN
        RAISE NOTICE 'RLS test failed: expected % atoms, got %',
            p_expected_atoms_count, v_actual_count;
        RETURN false;
    END IF;

    RETURN true;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION test_rls_policy IS '测试 RLS 策略是否正确应用';

-- ----------------------------------------------------------------------------
-- 清除用户上下文（用于连接归还池前）
-- ----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION clear_current_user_id()
RETURNS VOID AS $$
BEGIN
    PERFORM set_config('app.current_user_id', '', false);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION clear_current_user_id IS '清除用户上下文（用于连接归还池前）';

-- ----------------------------------------------------------------------------
-- RLS 禁用说明（仅用于数据迁移等特殊场景）
-- ----------------------------------------------------------------------------
--
-- 临时禁用 RLS（仅超级用户可执行）：
-- ALTER TABLE atoms DISABLE ROW LEVEL SECURITY;
--
-- 重新启用：
-- ALTER TABLE atoms ENABLE ROW LEVEL SECURITY;
--
-- 注意：禁用 RLS 会暴露所有数据，仅用于：
-- 1. 数据迁移（导入导出）
-- 2. 系统维护
-- 3. 管理员批量操作
--
-- 操作完成后必须重新启用！
-- ----------------------------------------------------------------------------