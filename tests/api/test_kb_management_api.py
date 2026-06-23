"""知识库管理 API 测试

测试 KBManagementAPI 的 CRUD 操作、权限检查和输入验证。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 尝试导入，失败则跳过整个模块
try:
    from lib.api.kb_management import KBManagementAPI, CreateKBRequest, UpdateKBRequest
    from lib.core.storage_interface import StorageInterface
    from lib.core.hierarchy import HierarchyManager
    from lib.auth.rbac import RBACManager, Permission

    _IMPORT_OK = True
except ImportError as _e:
    _IMPORT_OK = False
    _IMPORT_ERROR = str(_e)


@pytest.fixture
def mock_storage():
    """Mock StorageInterface"""
    storage = AsyncMock(spec=StorageInterface)
    storage.create_kb = AsyncMock(return_value=1)
    storage.get_kb = AsyncMock(return_value=None)
    storage.update_kb = AsyncMock(return_value=True)
    storage.delete_kb = AsyncMock(return_value=True)
    storage.list_kbs = AsyncMock(return_value=[])
    storage.get_stats = AsyncMock(return_value={'atom_count': 0, 'member_count': 0})
    return storage


@pytest.fixture
def mock_hierarchy():
    """Mock HierarchyManager"""
    hierarchy = AsyncMock(spec=HierarchyManager)
    hierarchy.refresh_cache = AsyncMock()
    hierarchy.get_parent_kb = AsyncMock(return_value=None)
    hierarchy.get_child_kbs = AsyncMock(return_value=[])
    hierarchy.get_all_ancestors = AsyncMock(return_value=[])
    hierarchy.get_all_descendants = AsyncMock(return_value=[])
    return hierarchy


@pytest.fixture
def mock_rbac():
    """Mock RBACManager"""
    rbac = AsyncMock(spec=RBACManager)
    rbac.check_permission = AsyncMock(return_value=True)
    rbac.assign_role = AsyncMock(return_value=True)
    rbac.revoke_role = AsyncMock(return_value=True)
    rbac.get_user_roles = AsyncMock(return_value=set())
    return rbac


@pytest.fixture
def kb_api(mock_storage, mock_hierarchy, mock_rbac):
    """创建 KBManagementAPI 实例"""
    return KBManagementAPI(
        storage=mock_storage,
        hierarchy=mock_hierarchy,
        rbac=mock_rbac,
    )


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestKBCreate:
    """知识库创建测试"""

    @pytest.mark.asyncio
    async def test_create_kb_success(self, kb_api, mock_rbac, mock_storage):
        """成功创建知识库"""
        request = CreateKBRequest(
            name="测试知识库",
            description="描述",
            scope="personal",
        )
        result = await kb_api.create_kb("user1", request)

        assert result['success'] is True
        assert result['code'] == 201
        assert result['data']['kb_id'] == 1
        assert result['data']['name'] == "测试知识库"
        mock_storage.create_kb.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_kb_permission_denied(self, kb_api, mock_rbac):
        """无权限创建知识库"""
        mock_rbac.check_permission = AsyncMock(return_value=False)
        request = CreateKBRequest(name="测试", scope="personal")
        result = await kb_api.create_kb("user1", request)

        assert result['success'] is False
        assert result['code'] == 403
        assert 'Permission denied' in result['error']

    @pytest.mark.asyncio
    async def test_create_kb_invalid_scope(self, kb_api):
        """无效的 scope 参数"""
        request = CreateKBRequest(name="测试", scope="invalid_scope")
        result = await kb_api.create_kb("user1", request)

        assert result['success'] is False
        assert result['code'] == 400
        assert 'Invalid scope' in result['error']

    @pytest.mark.asyncio
    async def test_create_kb_department_without_id(self, kb_api):
        """部门知识库缺少 department_id"""
        request = CreateKBRequest(name="测试", scope="department")
        result = await kb_api.create_kb("user1", request)

        assert result['success'] is False
        assert result['code'] == 400
        assert 'department_id' in result['error']

    @pytest.mark.asyncio
    async def test_create_kb_project_without_id(self, kb_api):
        """项目知识库缺少 project_id"""
        request = CreateKBRequest(name="测试", scope="project")
        result = await kb_api.create_kb("user1", request)

        assert result['success'] is False
        assert result['code'] == 400
        assert 'project_id' in result['error']

    @pytest.mark.asyncio
    async def test_create_kb_company_without_org_id(self, kb_api):
        """公司知识库缺少 organization_id"""
        request = CreateKBRequest(name="测试", scope="company")
        result = await kb_api.create_kb("user1", request)

        assert result['success'] is False
        assert result['code'] == 400
        assert 'organization_id' in result['error']

    @pytest.mark.asyncio
    async def test_create_kb_auto_assign_owner(self, kb_api, mock_rbac):
        """创建知识库后自动将创建者设为 owner"""
        request = CreateKBRequest(name="测试", scope="personal")
        await kb_api.create_kb("user1", request)

        mock_rbac.assign_role.assert_called_once_with("user1", 1, 'owner')


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestKBGet:
    """知识库查询测试"""

    @pytest.mark.asyncio
    async def test_get_kb_success(self, kb_api, mock_storage, mock_rbac):
        """成功获取知识库详情"""
        mock_storage.get_kb = AsyncMock(return_value={
            'id': 1,
            'name': '测试知识库',
            'description': '描述',
            'type': 'personal',
            'tags': [],
            'is_public': False,
            'created_at': '2026-01-01T00:00:00',
            'updated_at': '2026-06-01T00:00:00',
        })
        result = await kb_api.get_kb("user1", 1)

        assert result['success'] is True
        assert result['code'] == 200
        assert result['data']['name'] == '测试知识库'

    @pytest.mark.asyncio
    async def test_get_kb_not_found(self, kb_api, mock_storage, mock_rbac):
        """知识库不存在"""
        mock_storage.get_kb = AsyncMock(return_value=None)
        result = await kb_api.get_kb("user1", 999)

        assert result['success'] is False
        assert result['code'] == 404

    @pytest.mark.asyncio
    async def test_get_kb_permission_denied(self, kb_api, mock_rbac):
        """无权限查看知识库"""
        mock_rbac.check_permission = AsyncMock(return_value=False)
        result = await kb_api.get_kb("user1", 1)

        assert result['success'] is False
        assert result['code'] == 403


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestKBList:
    """知识库列表测试"""

    @pytest.mark.asyncio
    async def test_list_kbs_success(self, kb_api, mock_storage):
        """成功获取知识库列表"""
        mock_storage.list_kbs = AsyncMock(return_value=[
            {'id': 1, 'name': 'KB1', 'description': '', 'type': 'personal', 'is_public': False, 'created_at': '2026-01-01'},
            {'id': 2, 'name': 'KB2', 'description': '', 'type': 'project', 'is_public': True, 'created_at': '2026-02-01'},
        ])
        result = await kb_api.list_kbs("user1")

        assert result['success'] is True
        assert result['code'] == 200
        assert result['data']['total'] == 2

    @pytest.mark.asyncio
    async def test_list_kbs_pagination(self, kb_api, mock_storage):
        """知识库列表分页"""
        kbs = [{'id': i, 'name': f'KB{i}', 'description': '', 'type': 'personal', 'is_public': False, 'created_at': '2026-01-01'} for i in range(1, 26)]
        mock_storage.list_kbs = AsyncMock(return_value=kbs)
        result = await kb_api.list_kbs("user1", page=2, limit=10)

        assert result['success'] is True
        assert result['data']['page'] == 2
        assert result['data']['pages'] == 3
        assert len(result['data']['kbs']) == 10


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestKBUpdate:
    """知识库更新测试"""

    @pytest.mark.asyncio
    async def test_update_kb_success(self, kb_api, mock_storage, mock_rbac):
        """成功更新知识库"""
        mock_storage.get_kb = AsyncMock(return_value={'id': 1, 'name': '旧名称'})
        request = UpdateKBRequest(name="新名称", description="新描述")
        result = await kb_api.update_kb("user1", 1, request)

        assert result['success'] is True
        assert result['code'] == 200
        assert 'name' in result['data']['updated_fields']

    @pytest.mark.asyncio
    async def test_update_kb_not_found(self, kb_api, mock_storage, mock_rbac):
        """更新不存在的知识库"""
        mock_storage.get_kb = AsyncMock(return_value=None)
        request = UpdateKBRequest(name="新名称")
        result = await kb_api.update_kb("user1", 999, request)

        assert result['success'] is False
        assert result['code'] == 404

    @pytest.mark.asyncio
    async def test_update_kb_permission_denied(self, kb_api, mock_rbac):
        """无权限更新知识库"""
        mock_rbac.check_permission = AsyncMock(return_value=False)
        request = UpdateKBRequest(name="新名称")
        result = await kb_api.update_kb("user1", 1, request)

        assert result['success'] is False
        assert result['code'] == 403


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestKBDelete:
    """知识库删除测试"""

    @pytest.mark.asyncio
    async def test_delete_kb_success(self, kb_api, mock_storage, mock_hierarchy, mock_rbac):
        """成功删除知识库"""
        mock_storage.get_kb = AsyncMock(return_value={'id': 1, 'name': '测试'})
        mock_hierarchy.get_child_kbs = AsyncMock(return_value=[])
        result = await kb_api.delete_kb("user1", 1)

        assert result['success'] is True
        assert result['code'] == 200
        assert result['data']['deleted'] is True

    @pytest.mark.asyncio
    async def test_delete_kb_with_children(self, kb_api, mock_storage, mock_hierarchy, mock_rbac):
        """有子知识库时不能删除"""
        mock_storage.get_kb = AsyncMock(return_value={'id': 1, 'name': '测试'})
        mock_hierarchy.get_child_kbs = AsyncMock(return_value=[2, 3])
        result = await kb_api.delete_kb("user1", 1)

        assert result['success'] is False
        assert result['code'] == 400
        assert 'children' in result['error'].lower() or 'Cannot delete' in result['error']

    @pytest.mark.asyncio
    async def test_delete_kb_not_found(self, kb_api, mock_storage, mock_rbac):
        """删除不存在的知识库"""
        mock_storage.get_kb = AsyncMock(return_value=None)
        result = await kb_api.delete_kb("user1", 999)

        assert result['success'] is False
        assert result['code'] == 404


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestKBSearch:
    """知识库搜索测试"""

    @pytest.mark.asyncio
    async def test_search_kbs_by_name(self, kb_api, mock_storage):
        """按名称搜索知识库"""
        mock_storage.list_kbs = AsyncMock(return_value=[
            {'id': 1, 'name': 'Python入门', 'description': '', 'tags': []},
            {'id': 2, 'name': 'Java入门', 'description': '', 'tags': []},
        ])
        result = await kb_api.search_kbs("user1", "Python")

        assert result['success'] is True
        assert result['data']['total'] == 1
        assert result['data']['kbs'][0]['name'] == 'Python入门'

    @pytest.mark.asyncio
    async def test_search_kbs_by_tag(self, kb_api, mock_storage):
        """按标签搜索知识库"""
        mock_storage.list_kbs = AsyncMock(return_value=[
            {'id': 1, 'name': 'KB1', 'description': '', 'tags': ['python', 'tutorial']},
            {'id': 2, 'name': 'KB2', 'description': '', 'tags': ['java']},
        ])
        result = await kb_api.search_kbs("user1", "python")

        assert result['success'] is True
        assert result['data']['total'] == 1


@pytest.mark.skipif(not _IMPORT_OK, reason=f"导入失败: {_IMPORT_ERROR if not _IMPORT_OK else ''}")
class TestKBHierarchy:
    """知识库层级关系测试"""

    @pytest.mark.asyncio
    async def test_get_kb_hierarchy_success(self, kb_api, mock_hierarchy, mock_rbac):
        """成功获取层级关系"""
        mock_hierarchy.get_parent_kb = AsyncMock(return_value=None)
        mock_hierarchy.get_child_kbs = AsyncMock(return_value=[2, 3])
        mock_hierarchy.get_all_ancestors = AsyncMock(return_value=[])
        mock_hierarchy.get_all_descendants = AsyncMock(return_value=[2, 3])
        result = await kb_api.get_kb_hierarchy("user1", 1)

        assert result['success'] is True
        assert result['data']['children'] == [2, 3]

    @pytest.mark.asyncio
    async def test_get_kb_hierarchy_permission_denied(self, kb_api, mock_rbac):
        """无权限查看层级关系"""
        mock_rbac.check_permission = AsyncMock(return_value=False)
        result = await kb_api.get_kb_hierarchy("user1", 1)

        assert result['success'] is False
        assert result['code'] == 403
