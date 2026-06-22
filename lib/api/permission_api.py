"""权限管理 API

提供权限管理接口，支持：
- 检查权限
- 分配角色
- 撤销角色
- 查询用户权限
"""

import logging
from typing import Any, Dict, List, Optional, Set
from datetime import datetime
from dataclasses import dataclass

from ..core.storage_interface import StorageInterface
from ..auth.rbac import RBACManager, Permission, Role, ROLE_DEFINITIONS

logger = logging.getLogger(__name__)


@dataclass
class CheckPermissionRequest:
    """检查权限请求"""
    kb_id: int
    permission: str


@dataclass
class AssignRoleRequest:
    """分配角色请求"""
    user_id: str
    kb_id: int
    role: str


@dataclass
class RevokeRoleRequest:
    """撤销角色请求"""
    user_id: str
    kb_id: int
    role: str


@dataclass
class PermissionInfo:
    """权限信息"""
    name: str
    value: str
    description: str


@dataclass
class RoleInfo:
    """角色信息"""
    name: str
    permissions: List[str]
    description: str


class PermissionAPI:
    """权限管理 API

    提供权限查询和管理的 RESTful 接口。
    """

    def __init__(
        self,
        storage: StorageInterface,
        rbac: RBACManager
    ):
        """初始化权限管理 API

        Args:
            storage: 存储接口
            rbac: RBAC 权限管理器
        """
        self.storage = storage
        self.rbac = rbac

    async def initialize(self) -> None:
        """初始化 API"""
        logger.info("PermissionAPI initialized")

    async def check_permission(
        self,
        user_id: str,
        request: CheckPermissionRequest
    ) -> Dict[str, Any]:
        """检查用户是否有指定权限

        Args:
            user_id: 用户 ID
            request: 检查权限请求

        Returns:
            权限检查结果
        """
        try:
            # 验证权限名称
            try:
                permission = Permission(request.permission)
            except ValueError:
                return {
                    'success': False,
                    'error': f'Invalid permission: {request.permission}',
                    'code': 400,
                    'data': {
                        'valid_permissions': [p.value for p in Permission]
                    }
                }

            # 检查权限
            has_permission = await self.rbac.check_permission(
                user_id,
                request.kb_id,
                permission
            )

            # 获取用户角色
            roles = await self.rbac.get_user_roles(user_id, request.kb_id)

            return {
                'success': True,
                'data': {
                    'user_id': user_id,
                    'kb_id': request.kb_id,
                    'permission': request.permission,
                    'has_permission': has_permission,
                    'roles': list(roles)
                },
                'code': 200
            }

        except Exception as e:
            logger.error(f"Failed to check permission: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500
            }

    async def assign_role(
        self,
        operator_id: str,
        request: AssignRoleRequest
    ) -> Dict[str, Any]:
        """为用户分配角色

        Args:
            operator_id: 操作者 ID
            request: 分配角色请求

        Returns:
            分配结果
        """
        try:
            # 检查操作者权限（需要有 MEMBER_MANAGE 或 ADMIN 权限）
            if not await self.rbac.check_permission(
                operator_id, request.kb_id, Permission.MEMBER_MANAGE
            ):
                # 检查是否有 ADMIN 权限
                if not await self.rbac.check_permission(
                    operator_id, request.kb_id, Permission.ADMIN
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
                    'error': f'Invalid role: {request.role}',
                    'code': 400,
                    'data': {'valid_roles': valid_roles}
                }

            # 不允许非 owner 分配 owner 角色
            if request.role == Role.OWNER.value:
                operator_roles = await self.rbac.get_user_roles(operator_id, request.kb_id)
                if Role.OWNER.value not in operator_roles:
                    return {
                        'success': False,
                        'error': 'Only owner can assign owner role',
                        'code': 403
                    }

            # 分配角色
            success = await self.rbac.assign_role(
                request.user_id,
                request.kb_id,
                request.role
            )

            if not success:
                return {
                    'success': False,
                    'error': 'Failed to assign role',
                    'code': 500
                }

            # 记录日志
            logger.info(
                f"Assigned role {request.role} to user {request.user_id} "
                f"in KB {request.kb_id} by {operator_id}"
            )

            return {
                'success': True,
                'data': {
                    'user_id': request.user_id,
                    'kb_id': request.kb_id,
                    'role': request.role
                },
                'code': 201
            }

        except Exception as e:
            logger.error(f"Failed to assign role: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500
            }

    async def revoke_role(
        self,
        operator_id: str,
        request: RevokeRoleRequest
    ) -> Dict[str, Any]:
        """撤销用户角色

        Args:
            operator_id: 操作者 ID
            request: 撤销角色请求

        Returns:
            撤销结果
        """
        try:
            # 检查操作者权限
            if not await self.rbac.check_permission(
                operator_id, request.kb_id, Permission.MEMBER_MANAGE
            ):
                if not await self.rbac.check_permission(
                    operator_id, request.kb_id, Permission.ADMIN
                ):
                    return {
                        'success': False,
                        'error': 'Permission denied',
                        'code': 403
                    }

            # 检查目标用户是否有该角色
            existing_roles = await self.rbac.get_user_roles(
                request.user_id, request.kb_id
            )

            if request.role not in existing_roles:
                return {
                    'success': False,
                    'error': f'User does not have role: {request.role}',
                    'code': 404,
                    'data': {'current_roles': list(existing_roles)}
                }

            # 不允许撤销最后一个 owner
            if request.role == Role.OWNER.value:
                # 检查是否还有其他 owner
                # 这里简化处理，实际应该查询数据库
                logger.warning("Attempting to revoke owner role")

            # 撤销角色
            success = await self.rbac.revoke_role(
                request.user_id,
                request.kb_id,
                request.role
            )

            if not success:
                return {
                    'success': False,
                    'error': 'Failed to revoke role',
                    'code': 500
                }

            logger.info(
                f"Revoked role {request.role} from user {request.user_id} "
                f"in KB {request.kb_id} by {operator_id}"
            )

            return {
                'success': True,
                'data': {
                    'user_id': request.user_id,
                    'kb_id': request.kb_id,
                    'revoked_role': request.role
                },
                'code': 200
            }

        except Exception as e:
            logger.error(f"Failed to revoke role: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500
            }

    async def get_user_permissions(
        self,
        user_id: str,
        kb_id: int
    ) -> Dict[str, Any]:
        """查询用户在知识库中的所有权限

        Args:
            user_id: 用户 ID
            kb_id: 知识库 ID

        Returns:
            用户权限列表
        """
        try:
            # 获取用户角色
            roles = await self.rbac.get_user_roles(user_id, kb_id)

            # 获取用户权限
            permissions = await self.rbac.get_user_permissions(user_id, kb_id)

            # 构建响应
            return {
                'success': True,
                'data': {
                    'user_id': user_id,
                    'kb_id': kb_id,
                    'roles': list(roles),
                    'permissions': [p.value for p in permissions]
                },
                'code': 200
            }

        except Exception as e:
            logger.error(f"Failed to get user permissions: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500
            }

    async def get_user_roles(
        self,
        user_id: str,
        kb_id: int
    ) -> Dict[str, Any]:
        """查询用户在知识库中的角色

        Args:
            user_id: 用户 ID
            kb_id: 知识库 ID

        Returns:
            用户角色列表
        """
        try:
            roles = await self.rbac.get_user_roles(user_id, kb_id)

            return {
                'success': True,
                'data': {
                    'user_id': user_id,
                    'kb_id': kb_id,
                    'roles': list(roles)
                },
                'code': 200
            }

        except Exception as e:
            logger.error(f"Failed to get user roles: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500
            }

    async def list_roles(self) -> Dict[str, Any]:
        """列出所有可用角色

        Returns:
            角色列表及其权限
        """
        try:
            roles = []
            for role_name, role_def in ROLE_DEFINITIONS.items():
                role_info = RoleInfo(
                    name=role_name,
                    permissions=[p.value for p in role_def.permissions],
                    description=role_def.description
                )
                roles.append(role_info.__dict__)

            return {
                'success': True,
                'data': {
                    'roles': roles,
                    'total': len(roles)
                },
                'code': 200
            }

        except Exception as e:
            logger.error(f"Failed to list roles: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500
            }

    async def list_permissions(self) -> Dict[str, Any]:
        """列出所有可用权限

        Returns:
            权限列表
        """
        try:
            permissions = []
            for perm in Permission:
                permissions.append(PermissionInfo(
                    name=perm.name,
                    value=perm.value,
                    description=self._get_permission_description(perm)
                ).__dict__)

            return {
                'success': True,
                'data': {
                    'permissions': permissions,
                    'total': len(permissions)
                },
                'code': 200
            }

        except Exception as e:
            logger.error(f"Failed to list permissions: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500
            }

    async def get_role_permissions(
        self,
        role_name: str
    ) -> Dict[str, Any]:
        """获取角色的所有权限

        Args:
            role_name: 角色名称

        Returns:
            角色的权限列表
        """
        try:
            if role_name not in ROLE_DEFINITIONS:
                return {
                    'success': False,
                    'error': f'Role not found: {role_name}',
                    'code': 404,
                    'data': {
                        'valid_roles': list(ROLE_DEFINITIONS.keys())
                    }
                }

            permissions = self.rbac.get_role_permissions(role_name)

            return {
                'success': True,
                'data': {
                    'role': role_name,
                    'permissions': [p.value for p in permissions],
                    'description': ROLE_DEFINITIONS[role_name].description
                },
                'code': 200
            }

        except Exception as e:
            logger.error(f"Failed to get role permissions: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500
            }

    async def check_multiple_permissions(
        self,
        user_id: str,
        kb_id: int,
        permissions: List[str]
    ) -> Dict[str, Any]:
        """批量检查多个权限

        Args:
            user_id: 用户 ID
            kb_id: 知识库 ID
            permissions: 权限列表

        Returns:
            每个权限的检查结果
        """
        try:
            results = {}

            for perm_str in permissions:
                try:
                    permission = Permission(perm_str)
                    has_perm = await self.rbac.check_permission(
                        user_id, kb_id, permission
                    )
                    results[perm_str] = has_perm
                except ValueError:
                    results[perm_str] = False

            return {
                'success': True,
                'data': {
                    'user_id': user_id,
                    'kb_id': kb_id,
                    'results': results
                },
                'code': 200
            }

        except Exception as e:
            logger.error(f"Failed to check multiple permissions: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500
            }

    async def get_accessible_kbs(
        self,
        user_id: str,
        permission: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取用户可访问的知识库列表

        Args:
            user_id: 用户 ID
            permission: 所需权限（可选）

        Returns:
            可访问的知识库列表
        """
        try:
            # 获取所有知识库
            all_kbs = await self.storage.list_kbs()

            # 过滤出用户有权限的知识库
            accessible_kbs = []

            for kb in all_kbs:
                kb_id = kb['id']

                # 如果指定了权限，检查该权限
                if permission:
                    try:
                        perm = Permission(permission)
                        has_perm = await self.rbac.check_permission(
                            user_id, kb_id, perm
                        )
                        if has_perm:
                            accessible_kbs.append(kb)
                    except ValueError:
                        continue
                else:
                    # 检查是否有任何权限
                    roles = await self.rbac.get_user_roles(user_id, kb_id)
                    if roles:
                        accessible_kbs.append(kb)

            return {
                'success': True,
                'data': {
                    'user_id': user_id,
                    'permission_filter': permission,
                    'kbs': accessible_kbs,
                    'total': len(accessible_kbs)
                },
                'code': 200
            }

        except Exception as e:
            logger.error(f"Failed to get accessible KBs: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500
            }

    async def create_custom_role(
        self,
        operator_id: str,
        role_name: str,
        permissions: List[str],
        description: str,
        inherits_from: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建自定义角色

        Args:
            operator_id: 操作者 ID
            role_name: 角色名称
            permissions: 权限列表
            description: 描述
            inherits_from: 继承自哪个角色

        Returns:
            创建结果
        """
        try:
            # 检查操作者是否有 ADMIN 权限
            # 这里需要系统级权限检查，暂时简化处理
            logger.warning(
                f"User {operator_id} attempting to create custom role {role_name}"
            )

            # 验证权限名称
            perm_set = set()
            invalid_perms = []

            for perm_str in permissions:
                try:
                    perm_set.add(Permission(perm_str))
                except ValueError:
                    invalid_perms.append(perm_str)

            if invalid_perms:
                return {
                    'success': False,
                    'error': f'Invalid permissions: {invalid_perms}',
                    'code': 400
                }

            # 创建角色
            success = await self.rbac.create_custom_role(
                role_name=role_name,
                permissions=perm_set,
                description=description,
                inherits_from=inherits_from
            )

            if not success:
                return {
                    'success': False,
                    'error': 'Failed to create custom role',
                    'code': 500
                }

            logger.info(f"Created custom role {role_name} by {operator_id}")

            return {
                'success': True,
                'data': {
                    'role_name': role_name,
                    'permissions': permissions,
                    'description': description
                },
                'code': 201
            }

        except Exception as e:
            logger.error(f"Failed to create custom role: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500
            }

    async def delete_custom_role(
        self,
        operator_id: str,
        role_name: str
    ) -> Dict[str, Any]:
        """删除自定义角色

        Args:
            operator_id: 操作者 ID
            role_name: 角色名称

        Returns:
            删除结果
        """
        try:
            # 检查是否是预定义角色
            if role_name in [r.value for r in Role]:
                return {
                    'success': False,
                    'error': 'Cannot delete predefined role',
                    'code': 400
                }

            # 删除角色
            success = await self.rbac.delete_custom_role(role_name)

            if not success:
                return {
                    'success': False,
                    'error': 'Role not found',
                    'code': 404
                }

            logger.info(f"Deleted custom role {role_name} by {operator_id}")

            return {
                'success': True,
                'data': {
                    'role_name': role_name,
                    'deleted': True
                },
                'code': 200
            }

        except Exception as e:
            logger.error(f"Failed to delete custom role: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500
            }

    def _get_permission_description(self, permission: Permission) -> str:
        """获取权限描述

        Args:
            permission: 权限枚举

        Returns:
            权限描述
        """
        descriptions = {
            Permission.KB_CREATE: "创建知识库",
            Permission.KB_READ: "读取知识库",
            Permission.KB_UPDATE: "更新知识库",
            Permission.KB_DELETE: "删除知识库",
            Permission.KB_MANAGE: "管理知识库成员",
            Permission.ATOM_CREATE: "创建知识原子",
            Permission.ATOM_READ: "读取知识原子",
            Permission.ATOM_UPDATE: "更新知识原子",
            Permission.ATOM_DELETE: "删除知识原子",
            Permission.MEMBER_MANAGE: "管理成员",
            Permission.ADMIN: "管理员权限"
        }
        return descriptions.get(permission, "")

    async def close(self) -> None:
        """关闭 API"""
        logger.info("PermissionAPI closed")