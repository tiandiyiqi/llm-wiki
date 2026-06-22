"""图像上传 API

提供图像上传、获取、删除、列表的 RESTful 接口。
参考 lib/api/kb_management.py 的风格。

端点：
- POST /api/images — 上传图像
- GET /api/images — 列出图像
- GET /api/images/{id} — 获取图像详情
- DELETE /api/images/{id} — 删除图像
- GET /api/images/{id}/variants — 获取变体
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# 允许的图像 MIME 类型
ALLOWED_MIME_TYPES: Set[str] = {
    'image/jpeg',
    'image/png',
    'image/webp',
    'image/gif',
}

# 默认最大文件大小：10MB
DEFAULT_MAX_FILE_SIZE = 10 * 1024 * 1024


@dataclass(frozen=True)
class CreateImageRequest:
    """创建图像请求（不可变）"""
    atom_id: int
    image_data: bytes
    filename: str
    mime_type: str
    user_id: Optional[str] = None
    storage_provider: Optional[str] = None


class ImageAPI:
    """图像管理 API

    提供 RESTful 接口进行图像的 CRUD 操作。
    集成权限中间件和文件大小限制。
    """

    def __init__(
        self,
        storage_service: Any,
        rbac: Any,
        max_file_size: int = DEFAULT_MAX_FILE_SIZE,
    ):
        """初始化图像 API

        Args:
            storage_service: ImageStorageService 实例
            rbac: RBAC 权限管理器
            max_file_size: 最大文件大小（字节）
        """
        self.storage_service = storage_service
        self.rbac = rbac
        self.max_file_size = max_file_size

    async def upload_image(
        self,
        request: CreateImageRequest,
    ) -> Dict[str, Any]:
        """上传图像

        Args:
            request: 创建图像请求

        Returns:
            上传结果字典
        """
        try:
            # 权限校验
            if request.user_id:
                has_perm = await self.rbac.check_permission(
                    request.user_id,
                    request.atom_id,
                    'atom:update',
                )
                if not has_perm:
                    return {
                        'success': False,
                        'error': 'Permission denied',
                        'code': 403,
                    }

            # 格式校验
            if request.mime_type not in ALLOWED_MIME_TYPES:
                return {
                    'success': False,
                    'error': f'Unsupported image format: {request.mime_type}',
                    'code': 400,
                }

            # 大小校验
            if len(request.image_data) > self.max_file_size:
                return {
                    'success': False,
                    'error': (
                        f'File size {len(request.image_data)} exceeds '
                        f'limit {self.max_file_size}'
                    ),
                    'code': 400,
                }

            # 文件名校验
            if not request.filename or len(request.filename) > 255:
                return {
                    'success': False,
                    'error': 'Invalid filename',
                    'code': 400,
                }

            # 调用存储服务
            result = await self.storage_service.upload_image(
                atom_id=request.atom_id,
                image_data=request.image_data,
                filename=request.filename,
                mime_type=request.mime_type,
                user_id=request.user_id or 'anonymous',
                storage_provider=request.storage_provider,
            )

            logger.info(
                f"Image upload: atom={request.atom_id}, "
                f"file={request.filename}, "
                f"success={result.get('success', False)}"
            )

            return result

        except Exception as e:
            logger.error(f"Failed to upload image: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500,
            }

    async def get_image(
        self,
        user_id: str,
        asset_id: int,
    ) -> Dict[str, Any]:
        """获取图像详情

        Args:
            user_id: 用户 ID
            asset_id: 资产 ID

        Returns:
            图像详情字典
        """
        try:
            # 权限校验
            has_perm = await self.rbac.check_permission(
                user_id, 0, 'atom:read',
            )
            if not has_perm:
                return {
                    'success': False,
                    'error': 'Permission denied',
                    'code': 403,
                }

            return await self.storage_service.get_image(asset_id)

        except Exception as e:
            logger.error(f"Failed to get image {asset_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500,
            }

    async def list_images(
        self,
        user_id: str,
        atom_id: int,
        variant_type: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """列出图像

        Args:
            user_id: 用户 ID
            atom_id: 知识原子 ID
            variant_type: 变体类型过滤
            page: 页码
            limit: 每页数量

        Returns:
            图像列表字典
        """
        try:
            # 权限校验
            has_perm = await self.rbac.check_permission(
                user_id, atom_id, 'atom:read',
            )
            if not has_perm:
                return {
                    'success': False,
                    'error': 'Permission denied',
                    'code': 403,
                }

            return await self.storage_service.list_images(
                atom_id=atom_id,
                variant_type=variant_type,
                page=page,
                limit=limit,
            )

        except Exception as e:
            logger.error(f"Failed to list images for atom {atom_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500,
            }

    async def delete_image(
        self,
        user_id: str,
        asset_id: int,
    ) -> Dict[str, Any]:
        """删除图像

        Args:
            user_id: 用户 ID
            asset_id: 资产 ID

        Returns:
            删除结果字典
        """
        try:
            # 权限校验
            has_perm = await self.rbac.check_permission(
                user_id, 0, 'atom:update',
            )
            if not has_perm:
                return {
                    'success': False,
                    'error': 'Permission denied',
                    'code': 403,
                }

            return await self.storage_service.delete_image(
                asset_id=asset_id,
                user_id=user_id,
            )

        except Exception as e:
            logger.error(f"Failed to delete image {asset_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500,
            }

    async def get_variants(
        self,
        user_id: str,
        asset_id: int,
    ) -> Dict[str, Any]:
        """获取图像变体

        Args:
            user_id: 用户 ID
            asset_id: 原始图像资产 ID

        Returns:
            变体列表字典
        """
        try:
            # 权限校验
            has_perm = await self.rbac.check_permission(
                user_id, 0, 'atom:read',
            )
            if not has_perm:
                return {
                    'success': False,
                    'error': 'Permission denied',
                    'code': 403,
                }

            return await self.storage_service.get_variants(
                original_asset_id=asset_id,
            )

        except Exception as e:
            logger.error(f"Failed to get variants for asset {asset_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500,
            }
