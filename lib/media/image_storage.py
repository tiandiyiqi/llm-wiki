"""图像存储服务

提供图像上传、获取、删除、列表和变体查询功能。
支持 inline（内联）和 external（外部）双模式存储。
"""

import hashlib
import io
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

try:
    from PIL import Image as PILImage
    PILLOW_AVAILABLE = True
except ImportError:
    PILImage = None
    PILLOW_AVAILABLE = False

logger = logging.getLogger(__name__)

# 允许的图像 MIME 类型
ALLOWED_MIME_TYPES: Set[str] = {
    'image/jpeg',
    'image/png',
    'image/webp',
    'image/gif',
}

# 内联存储阈值：1MB
INLINE_STORAGE_THRESHOLD = 1 * 1024 * 1024

# 默认最大文件大小：10MB
DEFAULT_MAX_FILE_SIZE = 10 * 1024 * 1024


@dataclass(frozen=True)
class ImageMetadata:
    """图像元数据（不可变）"""
    width: Optional[int] = None
    height: Optional[int] = None
    mime_type: str = ''
    size: int = 0
    checksum: Optional[str] = None


def validate_image_format(mime_type: Optional[str]) -> bool:
    """验证图像格式是否被允许

    Args:
        mime_type: MIME 类型字符串

    Returns:
        是否为允许的图像格式
    """
    if not mime_type:
        return False
    return mime_type in ALLOWED_MIME_TYPES


def compute_checksum(data: bytes) -> str:
    """计算 SHA256 checksum

    Args:
        data: 二进制数据

    Returns:
        SHA256 十六进制字符串
    """
    return hashlib.sha256(data).hexdigest()


def generate_storage_path(
    atom_id: int,
    filename: str,
    variant_type: str = 'original',
) -> str:
    """生成存储路径

    格式: assets/{atom_id}/{date_prefix}/{variant_type}/{filename}

    Args:
        atom_id: 知识原子 ID
        filename: 文件名
        variant_type: 变体类型

    Returns:
        存储路径字符串
    """
    now = datetime.now()
    date_prefix = now.strftime('%Y/%m')
    unique_id = uuid.uuid4().hex[:8]
    name_parts = filename.rsplit('.', 1)
    if len(name_parts) == 2:
        safe_name = f"{name_parts[0]}_{unique_id}.{name_parts[1]}"
    else:
        safe_name = f"{filename}_{unique_id}"

    if variant_type == 'original':
        return f"assets/{atom_id}/{date_prefix}/{safe_name}"
    return f"assets/{atom_id}/{date_prefix}/{variant_type}/{safe_name}"


def extract_metadata(
    image_data: bytes,
    mime_type: str,
) -> ImageMetadata:
    """提取图像元数据

    Args:
        image_data: 图像二进制数据
        mime_type: MIME 类型

    Returns:
        图像元数据对象
    """
    checksum = compute_checksum(image_data)

    if PILLOW_AVAILABLE and PILImage is not None:
        try:
            img = PILImage.open(io.BytesIO(image_data))
            width, height = img.size

            return ImageMetadata(
                width=width,
                height=height,
                mime_type=mime_type,
                size=len(image_data),
                checksum=checksum,
            )
        except Exception:
            logger.warning("Failed to extract image metadata, using defaults")

    return ImageMetadata(
        width=None,
        height=None,
        mime_type=mime_type,
        size=len(image_data),
        checksum=checksum,
    )


class ImageStorageService:
    """图像存储服务

    提供图像的 CRUD 操作，支持 inline/external 双模式存储。
    自动提取元数据并集成缩略图生成。
    """

    def __init__(
        self,
        db: Any,
        external_storage: Any = None,
        max_file_size: int = DEFAULT_MAX_FILE_SIZE,
        inline_threshold: int = INLINE_STORAGE_THRESHOLD,
    ):
        """初始化图像存储服务

        Args:
            db: 数据库管理器（需提供 execute/fetch_one/fetch_all/fetch_val）
            external_storage: 外部存储提供者（需提供 store/delete/read）
            max_file_size: 最大文件大小（字节）
            inline_threshold: 内联存储阈值（字节）
        """
        self.db = db
        self.external_storage = external_storage
        self.max_file_size = max_file_size
        self.inline_threshold = inline_threshold

    async def upload_image(
        self,
        atom_id: int,
        image_data: bytes,
        filename: str,
        mime_type: str,
        user_id: str,
        storage_provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """上传图像

        Args:
            atom_id: 知识原子 ID
            image_data: 图像二进制数据
            filename: 文件名
            mime_type: MIME 类型
            user_id: 上传用户 ID
            storage_provider: 存储提供商（可选）

        Returns:
            上传结果字典
        """
        # 验证格式
        if not validate_image_format(mime_type):
            return {
                'success': False,
                'error': f'Unsupported image format: {mime_type}',
                'code': 400,
            }

        # 验证大小
        if len(image_data) > self.max_file_size:
            return {
                'success': False,
                'error': f'File size exceeds limit: {len(image_data)} > {self.max_file_size}',
                'code': 400,
            }

        # 提取元数据
        metadata = extract_metadata(image_data, mime_type)

        # 决定存储模式
        storage_type, stored_path, stored_data = await self._store_image(
            atom_id=atom_id,
            image_data=image_data,
            filename=filename,
            storage_provider=storage_provider,
        )

        # 写入数据库
        try:
            rows = await self.db.execute(
                '''
                INSERT INTO atom_assets (
                    atom_id, filename, original_filename, mime_type, size,
                    storage_type, data, storage_path, storage_provider,
                    checksum, width, height, variant_type, created_by
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                RETURNING id
                ''',
                atom_id, filename, filename, mime_type, metadata.size,
                storage_type, stored_data, stored_path,
                storage_provider if storage_type == 'external' else None,
                metadata.checksum, metadata.width, metadata.height,
                'original', user_id,
            )

            asset_id = rows[0]['id'] if rows else None

            # 生成缩略图变体
            await self._generate_variants(
                asset_id=asset_id,
                atom_id=atom_id,
                image_data=image_data,
                filename=filename,
                mime_type=mime_type,
                user_id=user_id,
                storage_provider=storage_provider,
            )

            logger.info(f"Uploaded image {asset_id} for atom {atom_id}")

            return {
                'success': True,
                'data': {
                    'asset_id': asset_id,
                    'filename': filename,
                    'storage_type': storage_type,
                    'width': metadata.width,
                    'height': metadata.height,
                    'size': metadata.size,
                    'checksum': metadata.checksum,
                },
                'code': 201,
            }

        except Exception as e:
            logger.error(f"Failed to store image in DB: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500,
            }

    async def _store_image(
        self,
        atom_id: int,
        image_data: bytes,
        filename: str,
        storage_provider: Optional[str] = None,
    ) -> tuple:
        """存储图像数据，返回 (storage_type, path, data)

        Args:
            atom_id: 知识原子 ID
            image_data: 图像数据
            filename: 文件名
            storage_provider: 存储提供商

        Returns:
            (storage_type, storage_path, data) 元组
        """
        if len(image_data) <= self.inline_threshold:
            return ('inline', None, image_data)

        # 外部存储
        if not self.external_storage:
            # 无外部存储，回退到 inline
            return ('inline', None, image_data)

        storage_path = generate_storage_path(atom_id, filename)
        await self.external_storage.store(storage_path, image_data)
        return ('external', storage_path, None)

    async def _generate_variants(
        self,
        asset_id: Optional[int],
        atom_id: int,
        image_data: bytes,
        filename: str,
        mime_type: str,
        user_id: str,
        storage_provider: Optional[str] = None,
    ) -> None:
        """生成并存储图像变体

        Args:
            asset_id: 原始图像资产 ID
            atom_id: 知识原子 ID
            image_data: 原始图像数据
            filename: 文件名
            mime_type: MIME 类型
            user_id: 用户 ID
            storage_provider: 存储提供商
        """
        if not asset_id:
            return

        try:
            from .thumbnail import ThumbnailGenerator

            generator = ThumbnailGenerator()
            variants = generator.generate_all(image_data, mime_type)

            for variant_type, variant_data in variants.items():
                variant_metadata = extract_metadata(variant_data, mime_type)
                variant_filename = _make_variant_filename(filename, variant_type)

                storage_type, stored_path, stored_data = await self._store_image(
                    atom_id=atom_id,
                    image_data=variant_data,
                    filename=variant_filename,
                    storage_provider=storage_provider,
                )

                await self.db.execute(
                    '''
                    INSERT INTO atom_assets (
                        atom_id, filename, original_filename, mime_type, size,
                        storage_type, data, storage_path, storage_provider,
                        checksum, width, height, variant_type, variant_of_id,
                        created_by
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                    ''',
                    atom_id, variant_filename, filename, mime_type,
                    variant_metadata.size,
                    storage_type, stored_data, stored_path,
                    storage_provider if storage_type == 'external' else None,
                    variant_metadata.checksum,
                    variant_metadata.width, variant_metadata.height,
                    variant_type, asset_id, user_id,
                )

        except Exception as e:
            logger.warning(f"Failed to generate variants for asset {asset_id}: {e}")

    async def get_image(self, asset_id: int) -> Dict[str, Any]:
        """获取图像信息

        Args:
            asset_id: 资产 ID

        Returns:
            图像信息字典
        """
        try:
            record = await self.db.fetch_one(
                'SELECT * FROM atom_assets WHERE id = $1',
                asset_id,
            )

            if not record:
                return {
                    'success': False,
                    'error': 'Image not found',
                    'code': 404,
                }

            return {
                'success': True,
                'data': _record_to_dict(record),
                'code': 200,
            }

        except Exception as e:
            logger.error(f"Failed to get image {asset_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500,
            }

    async def delete_image(
        self,
        asset_id: int,
        user_id: str,
    ) -> Dict[str, Any]:
        """删除图像

        Args:
            asset_id: 资产 ID
            user_id: 操作用户 ID

        Returns:
            删除结果字典
        """
        try:
            record = await self.db.fetch_one(
                'SELECT * FROM atom_assets WHERE id = $1',
                asset_id,
            )

            if not record:
                return {
                    'success': False,
                    'error': 'Image not found',
                    'code': 404,
                }

            # 删除外部存储文件
            if record.get('storage_type') == 'external' and self.external_storage:
                storage_path = record.get('storage_path')
                if storage_path:
                    await self.external_storage.delete(storage_path)

            # 删除数据库记录（变体也会级联删除 variant_of_id → SET NULL）
            await self.db.execute(
                'DELETE FROM atom_assets WHERE id = $1',
                asset_id,
            )

            logger.info(f"Deleted image {asset_id} by user {user_id}")

            return {
                'success': True,
                'data': {'asset_id': asset_id, 'deleted': True},
                'code': 200,
            }

        except Exception as e:
            logger.error(f"Failed to delete image {asset_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500,
            }

    async def list_images(
        self,
        atom_id: int,
        variant_type: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """列出图像

        Args:
            atom_id: 知识原子 ID
            variant_type: 变体类型过滤（可选）
            page: 页码
            limit: 每页数量

        Returns:
            图像列表字典
        """
        try:
            where_clause = 'WHERE atom_id = $1'
            params: list = [atom_id]

            if variant_type:
                where_clause += ' AND variant_type = $2'
                params.append(variant_type)

            # 获取总数
            count_sql = f'SELECT COUNT(*) as cnt FROM atom_assets {where_clause}'
            count_result = await self.db.fetch_val(count_sql, *params)
            total = count_result if isinstance(count_result, int) else 0

            # 分页查询
            offset = (page - 1) * limit
            list_sql = (
                f'SELECT * FROM atom_assets {where_clause} '
                f'ORDER BY created_at DESC LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}'
            )
            records = await self.db.fetch_all(
                list_sql, *params, limit, offset,
            )

            images = [_record_to_dict(r) for r in records]

            return {
                'success': True,
                'data': {
                    'images': images,
                    'total': total,
                    'page': page,
                    'limit': limit,
                    'pages': (total + limit - 1) // limit if limit > 0 else 0,
                },
                'code': 200,
            }

        except Exception as e:
            logger.error(f"Failed to list images for atom {atom_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500,
            }

    async def get_variants(
        self,
        original_asset_id: int,
    ) -> Dict[str, Any]:
        """获取图像的所有变体

        Args:
            original_asset_id: 原始图像资产 ID

        Returns:
            变体列表字典
        """
        try:
            records = await self.db.fetch_all(
                '''
                SELECT * FROM atom_assets
                WHERE id = $1 OR variant_of_id = $1
                ORDER BY
                    CASE variant_type
                        WHEN 'original' THEN 0
                        WHEN 'thumbnail' THEN 1
                        WHEN 'medium' THEN 2
                        WHEN 'large' THEN 3
                    END
                ''',
                original_asset_id,
            )

            variants = [_record_to_dict(r) for r in records]

            return {
                'success': True,
                'data': {'variants': variants},
                'code': 200,
            }

        except Exception as e:
            logger.error(f"Failed to get variants for asset {original_asset_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': 500,
            }


def _make_variant_filename(filename: str, variant_type: str) -> str:
    """生成变体文件名

    Args:
        filename: 原始文件名
        variant_type: 变体类型

    Returns:
        变体文件名
    """
    name_parts = filename.rsplit('.', 1)
    suffix = f"_{variant_type}"
    if len(name_parts) == 2:
        return f"{name_parts[0]}{suffix}.{name_parts[1]}"
    return f"{filename}{suffix}"


def _record_to_dict(record: Any) -> Dict[str, Any]:
    """将数据库记录转为字典

    Args:
        record: 数据库记录

    Returns:
        字典形式的数据
    """
    if isinstance(record, dict):
        result = dict(record)
    else:
        result = dict(record)

    # 处理不可序列化的字段
    if 'data' in result and isinstance(result['data'], bytes):
        result['data'] = f'<binary {len(result["data"])} bytes>'
    if 'created_at' in result and hasattr(result['created_at'], 'isoformat'):
        result['created_at'] = result['created_at'].isoformat()

    return result
