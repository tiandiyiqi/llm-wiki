"""ImageStorageService 测试

测试图像存储服务的核心功能：
- 格式验证（JPEG/PNG/WebP/GIF）
- 元数据提取
- 存储路径生成
- checksum 计算
- 上传/获取/删除/列表操作
- 变体查询
"""

import hashlib
import io
import sys
import unittest
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# 直接导入 media 模块，避免触发 lib/__init__.py 的重导入
_media_path = str(Path(__file__).parent.parent.parent / 'lib' / 'media')
if _media_path not in sys.path:
    sys.path.insert(0, _media_path)

from image_storage import (
    ALLOWED_MIME_TYPES,
    ImageMetadata,
    ImageStorageService,
    validate_image_format,
    compute_checksum,
    generate_storage_path,
    extract_metadata,
)


@dataclass
class MockAssetRecord:
    """模拟数据库资产记录"""
    id: int
    atom_id: int
    filename: str
    original_filename: Optional[str]
    mime_type: str
    size: int
    storage_type: str
    data: Optional[bytes] = None
    storage_path: Optional[str] = None
    storage_provider: Optional[str] = None
    checksum: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    variant_type: str = 'original'
    variant_of_id: Optional[int] = None
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None


class TestValidateImageFormat(unittest.TestCase):
    """图像格式验证测试"""

    def test_jpeg_is_allowed(self):
        """JPEG 格式应被允许"""
        self.assertIn('image/jpeg', ALLOWED_MIME_TYPES)
        result = validate_image_format('image/jpeg')
        self.assertTrue(result)

    def test_png_is_allowed(self):
        """PNG 格式应被允许"""
        self.assertIn('image/png', ALLOWED_MIME_TYPES)
        result = validate_image_format('image/png')
        self.assertTrue(result)

    def test_webp_is_allowed(self):
        """WebP 格式应被允许"""
        self.assertIn('image/webp', ALLOWED_MIME_TYPES)
        result = validate_image_format('image/webp')
        self.assertTrue(result)

    def test_gif_is_allowed(self):
        """GIF 格式应被允许"""
        self.assertIn('image/gif', ALLOWED_MIME_TYPES)
        result = validate_image_format('image/gif')
        self.assertTrue(result)

    def test_svg_is_not_allowed(self):
        """SVG 格式不应被允许"""
        result = validate_image_format('image/svg+xml')
        self.assertFalse(result)

    def test_bmp_is_not_allowed(self):
        """BMP 格式不应被允许"""
        result = validate_image_format('image/bmp')
        self.assertFalse(result)

    def test_empty_mime_type_rejected(self):
        """空 MIME 类型应被拒绝"""
        result = validate_image_format('')
        self.assertFalse(result)

    def test_none_mime_type_rejected(self):
        """None MIME 类型应被拒绝"""
        result = validate_image_format(None)
        self.assertFalse(result)


class TestComputeChecksum(unittest.TestCase):
    """Checksum 计算测试"""

    def test_sha256_checksum(self):
        """验证 SHA256 checksum 计算"""
        data = b'hello world'
        expected = hashlib.sha256(data).hexdigest()
        result = compute_checksum(data)
        self.assertEqual(result, expected)

    def test_empty_data_checksum(self):
        """空数据的 checksum"""
        data = b''
        expected = hashlib.sha256(data).hexdigest()
        result = compute_checksum(data)
        self.assertEqual(result, expected)

    def test_binary_data_checksum(self):
        """二进制数据的 checksum"""
        data = bytes(range(256))
        expected = hashlib.sha256(data).hexdigest()
        result = compute_checksum(data)
        self.assertEqual(result, expected)

    def test_checksum_deterministic(self):
        """checksum 计算应是确定性的"""
        data = b'test data for determinism'
        result1 = compute_checksum(data)
        result2 = compute_checksum(data)
        self.assertEqual(result1, result2)

    def test_different_data_different_checksum(self):
        """不同数据应产生不同 checksum"""
        result1 = compute_checksum(b'data1')
        result2 = compute_checksum(b'data2')
        self.assertNotEqual(result1, result2)


class TestGenerateStoragePath(unittest.TestCase):
    """存储路径生成测试"""

    def test_path_contains_atom_id(self):
        """路径应包含 atom_id"""
        path = generate_storage_path(atom_id=42, filename='photo.jpg')
        self.assertIn('42', path)

    def test_path_contains_filename_base(self):
        """路径应包含文件名基础部分"""
        path = generate_storage_path(atom_id=1, filename='photo.jpg')
        # 文件名会添加唯一 ID 后缀，但基础名应保留
        self.assertIn('photo', path)
        self.assertTrue(path.endswith('.jpg'))

    def test_path_has_date_prefix(self):
        """路径应有日期前缀"""
        path = generate_storage_path(atom_id=1, filename='photo.jpg')
        parts = path.split('/')
        self.assertGreaterEqual(len(parts), 3)

    def test_different_atom_ids_different_paths(self):
        """不同 atom_id 应产生不同路径"""
        path1 = generate_storage_path(atom_id=1, filename='photo.jpg')
        path2 = generate_storage_path(atom_id=2, filename='photo.jpg')
        self.assertNotEqual(path1, path2)

    def test_path_for_variant(self):
        """变体路径应包含变体类型"""
        path = generate_storage_path(
            atom_id=1,
            filename='photo.jpg',
            variant_type='thumbnail',
        )
        self.assertIn('thumbnail', path)


class TestExtractMetadata(unittest.TestCase):
    """元数据提取测试"""

    @patch('image_storage.PILImage')
    @patch('image_storage.PILLOW_AVAILABLE', True)
    def test_extract_metadata_from_valid_image(self, mock_pil):
        """从有效图像提取元数据"""
        mock_img = MagicMock()
        mock_img.size = (100, 80)
        mock_pil.open.return_value = mock_img

        image_bytes = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        metadata = extract_metadata(image_bytes, 'image/png')
        self.assertIsInstance(metadata, ImageMetadata)
        self.assertEqual(metadata.width, 100)
        self.assertEqual(metadata.height, 80)
        self.assertEqual(metadata.mime_type, 'image/png')
        self.assertEqual(metadata.size, len(image_bytes))

    @patch('image_storage.PILImage')
    @patch('image_storage.PILLOW_AVAILABLE', True)
    def test_extract_metadata_from_jpeg(self, mock_pil):
        """从 JPEG 图像提取元数据"""
        mock_img = MagicMock()
        mock_img.size = (200, 150)
        mock_pil.open.return_value = mock_img

        image_bytes = b'\xff\xd8\xff' + b'\x00' * 100
        metadata = extract_metadata(image_bytes, 'image/jpeg')
        self.assertEqual(metadata.width, 200)
        self.assertEqual(metadata.height, 150)

    def test_extract_metadata_invalid_data(self):
        """无效图像数据应返回默认元数据"""
        metadata = extract_metadata(b'not an image', 'image/png')
        self.assertIsInstance(metadata, ImageMetadata)
        self.assertIsNone(metadata.width)
        self.assertIsNone(metadata.height)

    def test_extract_metadata_includes_checksum(self):
        """元数据应包含 checksum"""
        image_bytes = b'\x89PNG\r\n\x1a\n' + b'\x00' * 50
        metadata = extract_metadata(image_bytes, 'image/png')
        self.assertIsNotNone(metadata.checksum)
        self.assertEqual(
            metadata.checksum,
            hashlib.sha256(image_bytes).hexdigest(),
        )


class TestImageStorageService(unittest.TestCase):
    """ImageStorageService 集成测试"""

    def _create_service(self) -> ImageStorageService:
        """创建测试用服务实例"""
        mock_db = AsyncMock()
        mock_storage = AsyncMock()
        return ImageStorageService(
            db=mock_db,
            external_storage=mock_storage,
            max_file_size=10 * 1024 * 1024,
        )

    def test_service_initialization(self):
        """服务应正确初始化"""
        service = self._create_service()
        self.assertIsNotNone(service)
        self.assertEqual(service.max_file_size, 10 * 1024 * 1024)

    def test_service_default_max_file_size(self):
        """默认最大文件大小应为 10MB"""
        mock_db = AsyncMock()
        mock_storage = AsyncMock()
        service = ImageStorageService(db=mock_db, external_storage=mock_storage)
        self.assertEqual(service.max_file_size, 10 * 1024 * 1024)

    @patch('image_storage.extract_metadata')
    def test_upload_image_validates_format(self, mock_extract):
        """上传图像应验证格式"""
        service = self._create_service()
        mock_extract.return_value = ImageMetadata(
            width=100, height=80, mime_type='image/svg+xml',
            size=100, checksum='abc',
        )

        import asyncio
        result = asyncio.run(
            service.upload_image(
                atom_id=1,
                image_data=b'<svg></svg>',
                filename='test.svg',
                mime_type='image/svg+xml',
                user_id='user1',
            )
        )
        self.assertFalse(result['success'])
        self.assertIn('Unsupported', result['error'])

    @patch('image_storage.extract_metadata')
    def test_upload_image_validates_size(self, mock_extract):
        """上传图像应验证文件大小"""
        service = self._create_service()
        service.max_file_size = 100

        mock_extract.return_value = ImageMetadata(
            width=100, height=80, mime_type='image/png',
            size=200, checksum='abc',
        )

        import asyncio
        result = asyncio.run(
            service.upload_image(
                atom_id=1,
                image_data=b'x' * 200,
                filename='test.png',
                mime_type='image/png',
                user_id='user1',
            )
        )
        self.assertFalse(result['success'])
        self.assertIn('size', result['error'].lower())

    @patch('image_storage.extract_metadata')
    @patch.object(ImageStorageService, '_generate_variants', new_callable=AsyncMock)
    def test_upload_image_inline_storage(self, mock_variants, mock_extract):
        """小文件应使用 inline 存储"""
        service = self._create_service()
        image_data = b'x' * 100  # 小于 inline 阈值

        mock_extract.return_value = ImageMetadata(
            width=50, height=50, mime_type='image/png',
            size=len(image_data),
            checksum=hashlib.sha256(image_data).hexdigest(),
        )
        service.db.execute.return_value = [{'id': 1}]

        import asyncio
        result = asyncio.run(
            service.upload_image(
                atom_id=1,
                image_data=image_data,
                filename='test.png',
                mime_type='image/png',
                user_id='user1',
            )
        )
        self.assertTrue(result['success'])
        self.assertEqual(result['data']['storage_type'], 'inline')

    @patch('image_storage.extract_metadata')
    @patch.object(ImageStorageService, '_generate_variants', new_callable=AsyncMock)
    def test_upload_image_external_storage(self, mock_variants, mock_extract):
        """大文件应使用 external 存储"""
        service = self._create_service()
        large_data = b'x' * (2 * 1024 * 1024)  # 2MB

        mock_extract.return_value = ImageMetadata(
            width=1000, height=800, mime_type='image/png',
            size=len(large_data),
            checksum=hashlib.sha256(large_data).hexdigest(),
        )
        service.db.execute.return_value = [{'id': 2}]
        service.external_storage.store.return_value = 'assets/1/2026/06/test.png'

        import asyncio
        result = asyncio.run(
            service.upload_image(
                atom_id=1,
                image_data=large_data,
                filename='test.png',
                mime_type='image/png',
                user_id='user1',
            )
        )
        self.assertTrue(result['success'])
        self.assertEqual(result['data']['storage_type'], 'external')

    def test_get_image_not_found(self):
        """获取不存在的图像应返回 404"""
        service = self._create_service()
        service.db.fetch_one.return_value = None

        import asyncio
        result = asyncio.run(
            service.get_image(asset_id=999)
        )
        self.assertFalse(result['success'])
        self.assertEqual(result['code'], 404)

    def test_get_image_found(self):
        """获取存在的图像应返回数据"""
        service = self._create_service()
        record = {
            'id': 1,
            'atom_id': 10,
            'filename': 'test.png',
            'original_filename': 'photo.png',
            'mime_type': 'image/png',
            'size': 1024,
            'storage_type': 'inline',
            'data': b'png_data',
            'storage_path': None,
            'storage_provider': None,
            'checksum': 'abc123',
            'width': 100,
            'height': 80,
            'variant_type': 'original',
            'variant_of_id': None,
            'created_at': datetime.now(),
            'created_by': 'user1',
        }
        service.db.fetch_one.return_value = record

        import asyncio
        result = asyncio.run(
            service.get_image(asset_id=1)
        )
        self.assertTrue(result['success'])
        self.assertEqual(result['data']['filename'], 'test.png')

    def test_delete_image_success(self):
        """删除图像应成功"""
        service = self._create_service()
        service.db.fetch_one.return_value = {
            'id': 1,
            'storage_type': 'inline',
            'storage_path': None,
        }
        service.db.execute.return_value = [{'id': 1}]

        import asyncio
        result = asyncio.run(
            service.delete_image(asset_id=1, user_id='user1')
        )
        self.assertTrue(result['success'])

    def test_delete_image_not_found(self):
        """删除不存在的图像应返回 404"""
        service = self._create_service()
        service.db.fetch_one.return_value = None

        import asyncio
        result = asyncio.run(
            service.delete_image(asset_id=999, user_id='user1')
        )
        self.assertFalse(result['success'])
        self.assertEqual(result['code'], 404)

    def test_list_images(self):
        """列出图像应返回分页结果"""
        service = self._create_service()
        service.db.fetch_all.return_value = [
            {'id': 1, 'filename': 'a.png', 'variant_type': 'original'},
            {'id': 2, 'filename': 'b.png', 'variant_type': 'original'},
        ]
        service.db.fetch_val.return_value = 2

        import asyncio
        result = asyncio.run(
            service.list_images(atom_id=1, page=1, limit=20)
        )
        self.assertTrue(result['success'])
        self.assertEqual(result['data']['total'], 2)

    def test_get_variants(self):
        """获取变体应返回所有变体"""
        service = self._create_service()
        service.db.fetch_all.return_value = [
            {'id': 1, 'variant_type': 'original', 'filename': 'photo.png'},
            {'id': 2, 'variant_type': 'thumbnail', 'filename': 'photo_thumb.png'},
            {'id': 3, 'variant_type': 'medium', 'filename': 'photo_med.png'},
        ]

        import asyncio
        result = asyncio.run(
            service.get_variants(original_asset_id=1)
        )
        self.assertTrue(result['success'])
        self.assertEqual(len(result['data']['variants']), 3)


if __name__ == '__main__':
    unittest.main()
