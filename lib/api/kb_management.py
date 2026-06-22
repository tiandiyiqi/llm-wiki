"""知识库管理 API

提供知识库的 CRUD 操作接口，支持：
- 创建知识库
- 获取知识库列表
- 更新知识库
- 删除知识库
- 查询知识库详情
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass

from ..core.storage_interface import StorageInterface
from ..core.hierarchy import HierarchyManager, KBLevel
from ..auth.rbac import RBACManager, Permission

logger = logging.getLogger(__name__)


@dataclass
class CreateKBRequest:
    """创建知识库请求"""
    name: str
    description: Optional[str] = None
    scope: str = "personal"  # personal/department/project/company
    organization_id: Optional[int] = None
    department_id: Optional[int] = None
    project_id: Optional[int] = None
    tags: Optional[List[str]] = None
    is_public: bool = False


@dataclass
class UpdateKBRequest:
    """更新知识库请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    is_public: Optional[bool] = None


@dataclass
class KBResponse:
    """知识库响应"""
    id: int
    name: str
    description: Optional[str]
    scope: str
    organization_id: Optional[int]
    department_id: Optional[int]
    project_id: Optional[int]
    tags: List[str]
    is_public: bool
    created_at: datetime
    updated_at: datetime
    atom_count: int = 0
    member_count: int = 0


class KBManagementAPI:
    """知识库管理 API

    提供 RESTful 接口进行知识库的 CRUD 操作。
    """

    def __init__(
        self,
        storage: StorageInterface,
        hierarchy: HierarchyManager,
        rbac: RBACManager
    ):
        """初始化知识库管理 API

        Args:
            storage: 存储接口
            hierarchy: 层级管理器
            rbac: RBAC 权限管理器
        """
        self.storage = storage
        self.hierarchy = hierarchy
        self.rbac = rbac

    async def initialize(self) -> None:
        """初始化 API"""
        logger.info("KBManagementAPI initialized")

    async def create_kb(
        self,
        user_id: str,
        request: CreateKBRequest
    ) -> Dict[str, Any]:
        """创建知识库

        Args:
            user_id: 用户 ID
            request: 创建请求

        Returns:
            创建结果，包含 kb_id
        """
        try:
            # 检查权限
            if not await self.rbac.check_permission(
                user_id, 0, Permission.KB_CREATE
            ):
                return {
                    'success': False,
                    'error': 'Permission denied',
                    'code': 403
                }

            # 验证 scope
            valid_scopes = ['personal', 'department', 'project', 'company']
            if request.scope not in valid_scopes:
                return {
                    'success': False,
                    'error': f'Invalid scope: {request.scope}',
                    'code': 400
                }

            # 验证层级关联
            if request.scope == 'department' and not request.department_id:
                return {
                    'success': False,
                    'error': 'Department KB must have department_id',
                    'code': 400
                }

            if request.scope == 'project' and not request.project_id:
                return {
                    'success': False,
                    'error': 'Project KB must have project_id',
                    'code': 400
                }

            if request.scope == 'company' and not request.organization_id:
                return {
                    'success': False,
                    'error': 'Company KB must have organization_id',
                    'code': 400
                }

            # 准备数据
            kb_data = {
                'name': request.name,
                'description': request.description or '',
                'type': request.scope,
                'organization_id': request.organization_id,
                'department_id': request.department_id,
                'project_id': request.project_id,
                'tags': request.tags or [],
                'is_public': request.is_public,
                'created_by': user_id,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }

            # 创建知识库
            kb_id = await self.storage.create_kb(kb_data)

            # 自动将创建者设为 owner
            await self.rbac.assign_role(user_id, kb_id, 'owner')

            # 刷新层级缓存
            await self.hierarchy.refresh_cache()

            logger.info(f"Created KB {kb_id} by user {user_id}")

            return {
                'success': True,
                'data': {
                    'kb_id': kb_id,
                    'name': request.name,
                    'scope': request.scope
                },
                'code': 201
            }

        except Exception as e:
            logger.error(f"Failed to create KB: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500
            }

    async def get_kb(
        self,
        user_id: str,
        kb_id: int
    ) -> Dict[str, Any]:
        """获取知识库详情

        Args:
            user_id: 用户 ID
            kb_id: 知识库 ID

        Returns:
            知识库详情
        """
        try:
            # 检查权限
            if not await self.rbac.check_permission(
                user_id, kb_id, Permission.KB_READ
            ):
                return {
                    'success': False,
                    'error': 'Permission denied',
                    'code': 403
                }

            # 获取知识库信息
            kb_info = await self.storage.get_kb(kb_id)

            if not kb_info:
                return {
                    'success': False,
                    'error': 'Knowledge base not found',
                    'code': 404
                }

            # 获取统计信息
            stats = await self.storage.get_stats(kb_id)

            # 构建响应
            response = KBResponse(
                id=kb_info['id'],
                name=kb_info['name'],
                description=kb_info.get('description'),
                scope=kb_info.get('type', 'personal'),
                organization_id=kb_info.get('organization_id'),
                department_id=kb_info.get('department_id'),
                project_id=kb_info.get('project_id'),
                tags=kb_info.get('tags', []),
                is_public=kb_info.get('is_public', False),
                created_at=kb_info.get('created_at'),
                updated_at=kb_info.get('updated_at'),
                atom_count=stats.get('atom_count', 0),
                member_count=stats.get('member_count', 0)
            )

            return {
                'success': True,
                'data': response.__dict__,
                'code': 200
            }

        except Exception as e:
            logger.error(f"Failed to get KB {kb_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500
            }

    async def list_kbs(
        self,
        user_id: str,
        scope: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """获取知识库列表

        Args:
            user_id: 用户 ID
            scope: 范围过滤（可选）
            page: 页码
            limit: 每页数量

        Returns:
            知识库列表
        """
        try:
            # 获取用户有权限的知识库列表
            kbs = await self.storage.list_kbs(user_id=user_id, scope=scope)

            # 分页
            total = len(kbs)
            start = (page - 1) * limit
            end = start + limit
            paginated_kbs = kbs[start:end]

            # 为每个知识库获取额外信息
            kb_list = []
            for kb in paginated_kbs:
                kb_id = kb['id']
                stats = await self.storage.get_stats(kb_id)

                kb_list.append({
                    'id': kb_id,
                    'name': kb['name'],
                    'description': kb.get('description'),
                    'scope': kb.get('type', 'personal'),
                    'is_public': kb.get('is_public', False),
                    'atom_count': stats.get('atom_count', 0),
                    'created_at': kb.get('created_at')
                })

            return {
                'success': True,
                'data': {
                    'kbs': kb_list,
                    'total': total,
                    'page': page,
                    'limit': limit,
                    'pages': (total + limit - 1) // limit
                },
                'code': 200
            }

        except Exception as e:
            logger.error(f"Failed to list KBs: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500
            }

    async def update_kb(
        self,
        user_id: str,
        kb_id: int,
        request: UpdateKBRequest
    ) -> Dict[str, Any]:
        """更新知识库

        Args:
            user_id: 用户 ID
            kb_id: 知识库 ID
            request: 更新请求

        Returns:
            更新结果
        """
        try:
            # 检查权限
            if not await self.rbac.check_permission(
                user_id, kb_id, Permission.KB_UPDATE
            ):
                return {
                    'success': False,
                    'error': 'Permission denied',
                    'code': 403
                }

            # 检查知识库是否存在
            kb_info = await self.storage.get_kb(kb_id)
            if not kb_info:
                return {
                    'success': False,
                    'error': 'Knowledge base not found',
                    'code': 404
                }

            # 准备更新数据
            update_data = {
                'updated_at': datetime.now().isoformat()
            }

            if request.name is not None:
                update_data['name'] = request.name

            if request.description is not None:
                update_data['description'] = request.description

            if request.tags is not None:
                update_data['tags'] = request.tags

            if request.is_public is not None:
                update_data['is_public'] = request.is_public

            # 执行更新
            success = await self.storage.update_kb(kb_id, update_data)

            if not success:
                return {
                    'success': False,
                    'error': 'Failed to update knowledge base',
                    'code': 500
                }

            logger.info(f"Updated KB {kb_id} by user {user_id}")

            return {
                'success': True,
                'data': {
                    'kb_id': kb_id,
                    'updated_fields': list(update_data.keys())
                },
                'code': 200
            }

        except Exception as e:
            logger.error(f"Failed to update KB {kb_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500
            }

    async def delete_kb(
        self,
        user_id: str,
        kb_id: int
    ) -> Dict[str, Any]:
        """删除知识库

        Args:
            user_id: 用户 ID
            kb_id: 知识库 ID

        Returns:
            删除结果
        """
        try:
            # 检查权限
            if not await self.rbac.check_permission(
                user_id, kb_id, Permission.KB_DELETE
            ):
                return {
                    'success': False,
                    'error': 'Permission denied',
                    'code': 403
                }

            # 检查知识库是否存在
            kb_info = await self.storage.get_kb(kb_id)
            if not kb_info:
                return {
                    'success': False,
                    'error': 'Knowledge base not found',
                    'code': 404
                }

            # 检查是否有子知识库
            children = await self.hierarchy.get_child_kbs(kb_id)
            if children:
                return {
                    'success': False,
                    'error': 'Cannot delete KB with children',
                    'code': 400,
                    'data': {'children': children}
                }

            # 执行删除
            success = await self.storage.delete_kb(kb_id)

            if not success:
                return {
                    'success': False,
                    'error': 'Failed to delete knowledge base',
                    'code': 500
                }

            # 刷新层级缓存
            await self.hierarchy.refresh_cache()

            logger.info(f"Deleted KB {kb_id} by user {user_id}")

            return {
                'success': True,
                'data': {
                    'kb_id': kb_id,
                    'deleted': True
                },
                'code': 200
            }

        except Exception as e:
            logger.error(f"Failed to delete KB {kb_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500
            }

    async def search_kbs(
        self,
        user_id: str,
        query: str,
        scope: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """搜索知识库

        Args:
            user_id: 用户 ID
            query: 搜索关键词
            scope: 范围过滤（可选）
            page: 页码
            limit: 每页数量

        Returns:
            搜索结果
        """
        try:
            # 获取用户有权限的知识库列表
            kbs = await self.storage.list_kbs(user_id=user_id, scope=scope)

            # 搜索匹配
            matching_kbs = []
            for kb in kbs:
                # 在名称和描述中搜索
                if query.lower() in kb['name'].lower():
                    matching_kbs.append(kb)
                    continue

                description = kb.get('description', '')
                if description and query.lower() in description.lower():
                    matching_kbs.append(kb)
                    continue

                # 在标签中搜索
                tags = kb.get('tags', [])
                if tags and any(query.lower() in tag.lower() for tag in tags):
                    matching_kbs.append(kb)
                    continue

            # 分页
            total = len(matching_kbs)
            start = (page - 1) * limit
            end = start + limit
            paginated = matching_kbs[start:end]

            return {
                'success': True,
                'data': {
                    'kbs': paginated,
                    'total': total,
                    'page': page,
                    'limit': limit,
                    'query': query
                },
                'code': 200
            }

        except Exception as e:
            logger.error(f"Failed to search KBs: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500
            }

    async def get_kb_hierarchy(
        self,
        user_id: str,
        kb_id: int
    ) -> Dict[str, Any]:
        """获取知识库层级关系

        Args:
            user_id: 用户 ID
            kb_id: 知识库 ID

        Returns:
            层级关系（父知识库、子知识库）
        """
        try:
            # 检查权限
            if not await self.rbac.check_permission(
                user_id, kb_id, Permission.KB_READ
            ):
                return {
                    'success': False,
                    'error': 'Permission denied',
                    'code': 403
                }

            # 获取父知识库
            parent_id = await self.hierarchy.get_parent_kb(kb_id)

            # 获取子知识库
            children_ids = await self.hierarchy.get_child_kbs(kb_id)

            # 获取祖先知识库
            ancestors = await self.hierarchy.get_all_ancestors(kb_id)

            # 获取后代知识库
            descendants = await self.hierarchy.get_all_descendants(kb_id)

            return {
                'success': True,
                'data': {
                    'kb_id': kb_id,
                    'parent_id': parent_id,
                    'children': children_ids,
                    'ancestors': ancestors,
                    'descendants': descendants
                },
                'code': 200
            }

        except Exception as e:
            logger.error(f"Failed to get KB hierarchy: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500
            }

    async def close(self) -> None:
        """关闭 API"""
        logger.info("KBManagementAPI closed")