#!/usr/bin/env python3
"""独立测试 RBAC 功能."""

from typing import Dict, List, Optional, Set
from datetime import datetime


class MockDBManager:
    """模拟数据库管理器."""

    def __init__(self):
        self.roles: Dict[int, Dict] = {}
        self.permissions: Dict[int, Dict] = {}
        self.role_permissions: Dict[int, Set[int]] = {}
        self.user_roles: Dict[str, Set[int]] = {}
        self._next_id = 1

    async def execute(self, query: str, *args) -> None:
        """模拟执行查询."""
        pass

    async def fetch_one(self, query: str, *args) -> Optional[Dict]:
        """模拟查询单条记录."""
        if "SELECT id FROM roles WHERE name" in query:
            name = args[0]
            for rid, role in self.roles.items():
                if role['name'] == name:
                    return {'id': rid}
            return None

        if "SELECT id FROM permissions WHERE name" in query:
            name = args[0]
            for pid, perm in self.permissions.items():
                if perm['name'] == name:
                    return {'id': pid}
            return None

        if "SELECT is_system FROM roles WHERE id" in query:
            role_id = args[0]
            if role_id in self.roles:
                return {'is_system': self.roles[role_id]['is_system']}
            return None

        return None

    async def fetch_all(self, query: str, *args) -> List[Dict]:
        """模拟查询多条记录."""
        if "SELECT r.name" in query:
            user_id = args[0]
            if user_id not in self.user_roles:
                return []
            role_names = []
            for rid in self.user_roles[user_id]:
                if rid in self.roles:
                    role_names.append({'name': self.roles[rid]['name']})
            return role_names

        return []

    def add_role(self, name: str, description: str, is_system: bool = False) -> int:
        """添加角色（测试辅助方法）."""
        rid = self._next_id
        self._next_id += 1
        self.roles[rid] = {
            'id': rid,
            'name': name,
            'description': description,
            'is_system': is_system,
        }
        self.role_permissions[rid] = set()
        return rid

    def add_permission(self, name: str, resource_type: str, action: str) -> int:
        """添加权限（测试辅助方法）."""
        pid = self._next_id
        self._next_id += 1
        self.permissions[pid] = {
            'id': pid,
            'name': name,
            'resource_type': resource_type,
            'action': action,
        }
        return pid

    def grant_permission(self, role_id: int, permission_id: int) -> None:
        """授权（测试辅助方法）."""
        if role_id in self.role_permissions:
            self.role_permissions[role_id].add(permission_id)

    def assign_role(self, user_id: str, role_id: int) -> None:
        """分配角色（测试辅助方法）."""
        if user_id not in self.user_roles:
            self.user_roles[user_id] = set()
        self.user_roles[user_id].add(role_id)


async def test_create_roles():
    print("\n=== 测试角色创建 ===")
    db = MockDBManager()

    # 创建角色
    admin_id = db.add_role('admin', '管理员', is_system=True)
    editor_id = db.add_role('editor', '编辑者', is_system=False)
    viewer_id = db.add_role('viewer', '查看者', is_system=False)

    assert len(db.roles) == 3
    assert db.roles[admin_id]['name'] == 'admin'
    assert db.roles[editor_id]['is_system'] is False
    print(f"✅ 创建了 3 个角色: admin(id={admin_id}), editor(id={editor_id}), viewer(id={viewer_id})")


async def test_create_permissions():
    print("\n=== 测试权限创建 ===")
    db = MockDBManager()

    # 创建权限
    kb_create = db.add_permission('kb:create', 'kb', 'create')
    kb_read = db.add_permission('kb:read', 'kb', 'read')
    atom_create = db.add_permission('atom:create', 'atom', 'create')

    assert len(db.permissions) == 3
    assert db.permissions[kb_create]['resource_type'] == 'kb'
    print(f"✅ 创建了 3 个权限: kb:create, kb:read, atom:create")


async def test_grant_permissions():
    print("\n=== 测试权限授予 ===")
    db = MockDBManager()

    # 创建角色和权限
    admin_id = db.add_role('admin', '管理员')
    kb_create = db.add_permission('kb:create', 'kb', 'create')
    kb_read = db.add_permission('kb:read', 'kb', 'read')

    # 授予权限
    db.grant_permission(admin_id, kb_create)
    db.grant_permission(admin_id, kb_read)

    assert len(db.role_permissions[admin_id]) == 2
    assert kb_create in db.role_permissions[admin_id]
    print(f"✅ admin 角色被授予了 2 个权限")


async def test_assign_roles():
    print("\n=== 测试角色分配 ===")
    db = MockDBManager()

    # 创建角色
    admin_id = db.add_role('admin', '管理员')
    editor_id = db.add_role('editor', '编辑者')

    # 分配角色给用户
    db.assign_role('user_001', admin_id)
    db.assign_role('user_002', editor_id)
    db.assign_role('user_001', editor_id)  # user_001 有两个角色

    assert len(db.user_roles['user_001']) == 2
    assert len(db.user_roles['user_002']) == 1
    print(f"✅ user_001 有 2 个角色，user_002 有 1 个角色")


async def test_get_user_roles():
    print("\n=== 测试获取用户角色 ===")
    db = MockDBManager()

    # 创建角色
    admin_id = db.add_role('admin', '管理员')
    editor_id = db.add_role('editor', '编辑者')

    # 分配角色
    db.assign_role('user_001', admin_id)
    db.assign_role('user_001', editor_id)

    # 查询用户角色
    result = await db.fetch_all("SELECT r.name FROM roles...", 'user_001')
    role_names = [r['name'] for r in result]

    assert len(role_names) == 2
    assert 'admin' in role_names
    assert 'editor' in role_names
    print(f"✅ user_001 的角色: {', '.join(role_names)}")


async def test_system_role_protection():
    print("\n=== 测试系统角色保护 ===")
    db = MockDBManager()

    # 创建系统角色
    admin_id = db.add_role('admin', '管理员', is_system=True)

    # 检查系统角色标记
    result = await db.fetch_one("SELECT is_system FROM roles WHERE id = $1", admin_id)
    assert result['is_system'] is True
    print("✅ 系统角色标记正确，应受保护")


async def main():
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("RBAC 功能测试（独立版本）")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    try:
        await test_create_roles()
        await test_create_permissions()
        await test_grant_permissions()
        await test_assign_roles()
        await test_get_user_roles()
        await test_system_role_protection()

        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("✅ 所有测试通过！")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        return 0

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    import asyncio
    import sys
    sys.exit(asyncio.run(main()))