"""成员管理 API

提供知识库成员的管理接口，支持：
- 添加成员
- 移除成员
- 更新成员角色
- 查询成员列表
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass

from ..core.storage_interface import StorageInterface
from ..auth.rbac import RBACManager, Permission, Role

logger = logging.getLogger(__name__)


@dataclass
class AddMemberRequest:
    """添加成员请求"""
    user_id: str
    role: str = "reader"  # owner/editor/reader


@dataclass
class UpdateMemberRoleRequest:
    """更新成员角色请求"""
    role: str  # owner/editor/reader


@dataclass
class MemberResponse:
    """成员响应"""
    user_id: str
    username: Optional[str]
    role: str
    added_at: datetime
    added_by: Optional[str]


class MemberAPI:
    """成员管理 API

    提供知识库成员的管理接口。
    """

    def __init__(
        self,
        storage: StorageInterface,
        rbac: RBACManager
    ):
        """初始化成员管理 API

        Args:
            storage: 存储接口
            rbac: RBAC 权限管理器
        """
        self.storage = storage
        self.rbac = rbac

    async def initialize(self) -> None:
        """初始化 API"""
        logger.info("MemberAPI initialized")

    async def add_member(
        self,
        operator_id: str,
        kb_id: int,
        request: AddMemberRequest
    ) -> Dict[str, Any]:
        """添加成员到知识库

        Args:
            operator_id: 操作者 ID
            kb_id: 知识库 ID
            request: 添加成员请求

        Returns:
            添加结果
        """
        try:
            # 检查操作者权限
            if not await self.rbac.check_permission(
                operator_id, kb_id, Permission.MEMBER_MANAGE
            ):
                return {
                    'success': False,
                    'error': 'Permission denied',
                    'code': 403
                }

            # 验证角色
            valid_roles = [Role.OWNER.value, Role.EDITOR.value, Role.READER.value]
            if request.role not in valid_roles:
                return {
                    'success': False,
                    'error': f'Invalid role: {request.role}. Must be one of {valid_roles}',
                    'code': 400
                }

            # 检查知识库是否存在
            kb_info = await self.storage.get_kb(kb_id)
            if not kb_info:
                return {
                    'success': False,
                    'error': 'Knowledge base not found',
                    'code': 404
                }

            # 检查成员是否已存在
            existing_roles = await self.rbac.get_user_roles(request.user_id, kb_id)
            if existing_roles:
                return {
                    'success': False,
                    'error': 'User is already a member',
                    'code': 400,
                    'data': {'current_roles': list(existing_roles)}
                }

            # 添加成员（分配角色）
            success = await self.rbac.assign_role(
                request.user_id,
                kb_id,
                request.role
            )

            if not success:
                return {
                    'success': False,
                    'error': 'Failed to add member',
                    'code': 500
                }

            # 记录操作日志
            await self._log_member_operation(
                kb_id=kb_id,
                operator_id=operator_id,
                target_user_id=request.user_id,
                operation='add_member',
                details={'role': request.role}
            )

            logger.info(
                f"Added member {request.user_id} with role {request.role} "
                f"to KB {kb_id} by {operator_id}"
            )

            return {
                'success': True,
                'data': {
                    'kb_id': kb_id,
                    'user_id': request.user_id,
                    'role': request.role
                },
                'code': 201
            }

        except Exception as e:
            logger.error(f"Failed to add member: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500
            }

    async def remove_member(
        self,
        operator_id: str,
        kb_id: int,
        user_id: str
    ) -> Dict[str, Any]:
        """从知识库移除成员

        Args:
            operator_id: 操作者 ID
            kb_id: 知识库 ID
            user_id: 要移除的用户 ID

        Returns:
            移除结果
        """
        try:
            # 检查操作者权限
            if not await self.rbac.check_permission(
                operator_id, kb_id, Permission.MEMBER_MANAGE
            ):
                return {
                    'success': False,
                    'error': 'Permission denied',
                    'code': 403
                }

            # 检查成员是否存在
            existing_roles = await self.rbac.get_user_roles(user_id, kb_id)
            if not existing_roles:
                return {
                    'success': False,
                    'error': 'User is not a member of this knowledge base',
                    'code': 404
                }

            # 不允许移除最后一个 owner
            if Role.OWNER.value in existing_roles:
                # 检查是否还有其他 owner
                all_members = await self._get_all_members(kb_id)
                owner_count = sum(
                    1 for m in all_members
                    if Role.OWNER.value in await self.rbac.get_user_roles(m['user_id'], kb_id)
                )

                if owner_count <= 1:
                    return {
                        'success': False,
                        'error': 'Cannot remove the last owner',
                        'code': 400
                    }

            # 撤销所有角色
            for role in existing_roles:
                await self.rbac.revoke_role(user_id, kb_id, role)

            # 记录操作日志
            await self._log_member_operation(
                kb_id=kb_id,
                operator_id=operator_id,
                target_user_id=user_id,
                operation='remove_member',
                details={'removed_roles': list(existing_roles)}
            )

            logger.info(f"Removed member {user_id} from KB {kb_id} by {operator_id}")

            return {
                'success': True,
                'data': {
                    'kb_id': kb_id,
                    'user_id': user_id,
                    'removed': True
                },
                'code': 200
            }

        except Exception as e:
            logger.error(f"Failed to remove member: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500
            }

    async def update_member_role(
        self,
        operator_id: str,
        kb_id: int,
        user_id: str,
        request: UpdateMemberRoleRequest
    ) -> Dict[str, Any]:
        """更新成员角色

        Args:
            operator_id: 操作者 ID
            kb_id: 知识库 ID
            user_id: 用户 ID
            request: 更新角色请求

        Returns:
            更新结果
        """
        try:
            # 检查操作者权限
            if not await self.rbac.check_permission(
                operator_id, kb_id, Permission.MEMBER_MANAGE
            ):
                return {
                    'success': False,
                    'error': 'Permission denied',
                    'code': 403
                }

            # 验证角色
            valid_roles = [Role.OWNER.value, Role.EDITOR.value, Role.READER.value]
            if request.role not in valid_roles:
                return {
                    'success': False,
                    'error': f'Invalid role: {request.role}. Must be one of {valid_roles}',
                    'code': 400
                }

            # 检查成员是否存在
            existing_roles = await self.rbac.get_user_roles(user_id, kb_id)
            if not existing_roles:
                return {
                    'success': False,
                    'error': 'User is not a member of this knowledge base',
                    'code': 404
                }

            # 如果要降级 owner，检查是否是最后一个
            if Role.OWNER.value in existing_roles and request.role != Role.OWNER.value:
                all_members = await self._get_all_members(kb_id)
                owner_count = sum(
                    1 for m in all_members
                    if Role.OWNER.value in await self.rbac.get_user_roles(m['user_id'], kb_id)
                )

                if owner_count <= 1:
                    return {
                        'success': False,
                        'error': 'Cannot downgrade the last owner',
                        'code': 400
                    }

            # 撤销旧角色并分配新角色
            old_roles = list(existing_roles)
            for role in old_roles:
                await self.rbac.revoke_role(user_id, kb_id, role)

            await self.rbac.assign_role(user_id, kb_id, request.role)

            # 记录操作日志
            await self._log_member_operation(
                kb_id=kb_id,
                operator_id=operator_id,
                target_user_id=user_id,
                operation='update_role',
                details={
                    'old_roles': old_roles,
                    'new_role': request.role
                }
            )

            logger.info(
                f"Updated member {user_id} role to {request.role} "
                f"in KB {kb_id} by {operator_id}"
            )

            return {
                'success': True,
                'data': {
                    'kb_id': kb_id,
                    'user_id': user_id,
                    'old_roles': old_roles,
                    'new_role': request.role
                },
                'code': 200
            }

        except Exception as e:
            logger.error(f"Failed to update member role: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500
            }

    async def list_members(
        self,
        user_id: str,
        kb_id: int,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """查询知识库成员列表

        Args:
            user_id: 用户 ID
            kb_id: 知识库 ID
            page: 页码
            limit: 每页数量

        Returns:
            成员列表
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

            # 获取所有成员
            members = await self._get_all_members(kb_id)

            # 按角色排序（owner > editor > reader）
            role_order = {
                Role.OWNER.value: 0,
                Role.EDITOR.value: 1,
                Role.READER.value: 2
            }

            async def get_primary_role(member: Dict) -> int:
                roles = await self.rbac.get_user_roles(member['user_id'], kb_id)
                if Role.OWNER.value in roles:
                    return 0
                elif Role.EDITOR.value in roles:
                    return 1
                else:
                    return 2

            # 由于需要异步排序，我们创建一个新列表
            sorted_members = []
            for member in members:
                roles = await self.rbac.get_user_roles(member['user_id'], kb_id)
                if Role.OWNER.value in roles:
                    priority = 0
                    primary_role = Role.OWNER.value
                elif Role.EDITOR.value in roles:
                    priority = 1
                    primary_role = Role.EDITOR.value
                else:
                    priority = 2
                    primary_role = Role.READER.value

                sorted_members.append({
                    **member,
                    'priority': priority,
                    'primary_role': primary_role,
                    'roles': list(roles)
                })

            sorted_members.sort(key=lambda m: m['priority'])

            # 分页
            total = len(sorted_members)
            start = (page - 1) * limit
            end = start + limit
            paginated = sorted_members[start:end]

            # 移除临时字段
            for member in paginated:
                del member['priority']

            return {
                'success': True,
                'data': {
                    'members': paginated,
                    'total': total,
                    'page': page,
                    'limit': limit,
                    'pages': (total + limit - 1) // limit
                },
                'code': 200
            }

        except Exception as e:
            logger.error(f"Failed to list members: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500
            }

    async def get_member_info(
        self,
        user_id: str,
        kb_id: int,
        target_user_id: str
    ) -> Dict[str, Any]:
        """获取成员详情

        Args:
            user_id: 请求者 ID
            kb_id: 知识库 ID
            target_user_id: 目标用户 ID

        Returns:
            成员详情
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

            # 获取成员角色
            roles = await self.rbac.get_user_roles(target_user_id, kb_id)
            if not roles:
                return {
                    'success': False,
                    'error': 'User is not a member of this knowledge base',
                    'code': 404
                }

            # 获取成员权限
            permissions = await self.rbac.get_user_permissions(target_user_id, kb_id)

            # 构建响应
            return {
                'success': True,
                'data': {
                    'user_id': target_user_id,
                    'kb_id': kb_id,
                    'roles': list(roles),
                    'permissions': [p.value for p in permissions]
                },
                'code': 200
            }

        except Exception as e:
            logger.error(f"Failed to get member info: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500
            }

    async def transfer_ownership(
        self,
        operator_id: str,
        kb_id: int,
        new_owner_id: str
    ) -> Dict[str, Any]:
        """转移知识库所有权

        Args:
            operator_id: 操作者 ID
            kb_id: 知识库 ID
            new_owner_id: 新所有者 ID

        Returns:
            转移结果
        """
        try:
            # 检查操作者是否是 owner
            operator_roles = await self.rbac.get_user_roles(operator_id, kb_id)
            if Role.OWNER.value not in operator_roles:
                return {
                    'success': False,
                    'error': 'Only owner can transfer ownership',
                    'code': 403
                }

            # 检查新所有者是否已是成员
            new_owner_roles = await self.rbac.get_user_roles(new_owner_id, kb_id)
            if not new_owner_roles:
                return {
                    'success': False,
                    'error': 'New owner must be an existing member',
                    'code': 400
                }

            # 将原 owner 降级为 editor
            await self.rbac.revoke_role(operator_id, kb_id, Role.OWNER.value)
            await self.rbac.assign_role(operator_id, kb_id, Role.EDITOR.value)

            # 撤销新 owner 的旧角色
            for role in new_owner_roles:
                await self.rbac.revoke_role(new_owner_id, kb_id, role)

            # 分配 owner 角色
            await self.rbac.assign_role(new_owner_id, kb_id, Role.OWNER.value)

            # 记录操作日志
            await self._log_member_operation(
                kb_id=kb_id,
                operator_id=operator_id,
                target_user_id=new_owner_id,
                operation='transfer_ownership',
                details={}
            )

            logger.info(
                f"Transferred ownership of KB {kb_id} "
                f"from {operator_id} to {new_owner_id}"
            )

            return {
                'success': True,
                'data': {
                    'kb_id': kb_id,
                    'old_owner': operator_id,
                    'new_owner': new_owner_id
                },
                'code': 200
            }

        except Exception as e:
            logger.error(f"Failed to transfer ownership: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500
            }

    async def _get_all_members(self, kb_id: int) -> List[Dict]:
        """获取知识库的所有成员（内部方法）

        Args:
            kb_id: 知识库 ID

        Returns:
            成员列表
        """
        # 这里应该从存储层获取成员列表
        # 由于 RBACManager 存储在内存中，我们需要从存储层获取
        # 这里是一个简化的实现
        query = """
            SELECT user_id, role, added_at, added_by
            FROM kb_members
            WHERE kb_id = $1
        """

        try:
            results = await self.storage.db_manager.fetch_all(query, kb_id)
            members = []
            for row in results:
                members.append({
                    'user_id': row['user_id'],
                    'role': row['role'],
                    'added_at': row['added_at'],
                    'added_by': row['added_by']
                })
            return members
        except Exception:
            # 如果表不存在或查询失败，返回空列表
            return []

    async def _log_member_operation(
        self,
        kb_id: int,
        operator_id: str,
        target_user_id: str,
        operation: str,
        details: Dict
    ) -> None:
        """记录成员操作日志

        Args:
            kb_id: 知识库 ID
            operator_id: 操作者 ID
            target_user_id: 目标用户 ID
            operation: 操作类型
            details: 操作详情
        """
        try:
            log_data = {
                'kb_id': kb_id,
                'operator_id': operator_id,
                'target_user_id': target_user_id,
                'operation': operation,
                'details': details,
                'timestamp': datetime.now().isoformat()
            }

            # 存储日志（简化实现）
            logger.info(f"Member operation: {log_data}")

        except Exception as e:
            logger.error(f"Failed to log member operation: {e}")

    async def close(self) -> None:
        """关闭 API"""
        logger.info("MemberAPI closed")