"""图像 API 集成测试

测试图像上传 API 端点：
- POST /api/images — 上传图像
- GET /api/images — 列出图像
- GET /api/images/{id} — 获取图像详情
- DELETE /api/images/{id} — 删除图像
- 权限校验
- 文件大小限制
"""

import asyncio
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock

# 直接导入模块
_api_path = str(Path(__file__).parent.parent.parent / 'lib' / 'api')
if _api_path not in sys.path:
    sys.path.insert(0, _api_path)

from image_api import ImageAPI, CreateImageRequest


class TestCreateImageRequest(unittest.TestCase):
    """CreateImageRequest 数据类测试"""

    def test_create_request_required_fields(self):
        """创建请求应包含必要字段"""
        req = CreateImageRequest(
            atom_id=1,
            image_data=b'png_data',
            filename='test.png',
            mime_type='image/png',
        )
        self.assertEqual(req.atom_id, 1)
        self.assertEqual(req.filename, 'test.png')
        self.assertEqual(req.mime_type, 'image/png')

    def test_create_request_default_user(self):
        """创建请求默认用户为 None"""
        req = CreateImageRequest(
            atom_id=1,
            image_data=b'png_data',
            filename='test.png',
            mime_type='image/png',
        )
        self.assertIsNone(req.user_id)

    def test_create_request_with_user(self):
        """创建请求可指定用户"""
        req = CreateImageRequest(
            atom_id=1,
            image_data=b'png_data',
            filename='test.png',
            mime_type='image/png',
            user_id='user123',
        )
        self.assertEqual(req.user_id, 'user123')


class TestImageAPI(unittest.TestCase):
    """ImageAPI 端点测试"""

    def _create_api(self) -> ImageAPI:
        """创建测试用 API 实例"""
        mock_storage_service = AsyncMock()
        mock_rbac = AsyncMock()
        return ImageAPI(
            storage_service=mock_storage_service,
            rbac=mock_rbac,
            max_file_size=10 * 1024 * 1024,
        )

    def _run(self, coro):
        """运行协程"""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def test_api_initialization(self):
        """API 应正确初始化"""
        api = self._create_api()
        self.assertIsNotNone(api)
        self.assertEqual(api.max_file_size, 10 * 1024 * 1024)

    def test_upload_without_permission(self):
        """无权限用户上传应被拒绝"""
        api = self._create_api()
        api.rbac.check_permission.return_value = False

        req = CreateImageRequest(
            atom_id=1,
            image_data=b'data',
            filename='test.png',
            mime_type='image/png',
            user_id='user1',
        )
        result = self._run(api.upload_image(req))
        self.assertFalse(result['success'])
        self.assertEqual(result['code'], 403)

    def test_upload_with_permission(self):
        """有权限用户应能上传"""
        api = self._create_api()
        api.rbac.check_permission.return_value = True
        api.storage_service.upload_image.return_value = {
            'success': True,
            'data': {
                'asset_id': 1,
                'filename': 'test.png',
                'storage_type': 'inline',
                'width': 100,
                'height': 80,
                'size': 1024,
                'checksum': 'abc',
            },
            'code': 201,
        }

        req = CreateImageRequest(
            atom_id=1,
            image_data=b'data',
            filename='test.png',
            mime_type='image/png',
            user_id='user1',
        )
        result = self._run(api.upload_image(req))
        self.assertTrue(result['success'])
        self.assertEqual(result['code'], 201)

    def test_upload_oversized_file(self):
        """超大文件应被拒绝"""
        api = self._create_api()
        api.rbac.check_permission.return_value = True

        req = CreateImageRequest(
            atom_id=1,
            image_data=b'x' * (20 * 1024 * 1024),  # 20MB
            filename='big.png',
            mime_type='image/png',
            user_id='user1',
        )
        result = self._run(api.upload_image(req))
        self.assertFalse(result['success'])
        self.assertEqual(result['code'], 400)

    def test_upload_invalid_format(self):
        """无效格式应被拒绝"""
        api = self._create_api()
        api.rbac.check_permission.return_value = True

        req = CreateImageRequest(
            atom_id=1,
            image_data=b'<svg></svg>',
            filename='test.svg',
            mime_type='image/svg+xml',
            user_id='user1',
        )
        result = self._run(api.upload_image(req))
        self.assertFalse(result['success'])
        self.assertEqual(result['code'], 400)

    def test_get_image_success(self):
        """获取图像应返回详情"""
        api = self._create_api()
        api.rbac.check_permission.return_value = True
        api.storage_service.get_image.return_value = {
            'success': True,
            'data': {
                'id': 1,
                'filename': 'test.png',
                'mime_type': 'image/png',
                'size': 1024,
                'width': 100,
                'height': 80,
                'variant_type': 'original',
            },
            'code': 200,
        }

        result = self._run(api.get_image(user_id='user1', asset_id=1))
        self.assertTrue(result['success'])

    def test_get_image_no_permission(self):
        """无权限获取图像应被拒绝"""
        api = self._create_api()
        api.rbac.check_permission.return_value = False

        result = self._run(api.get_image(user_id='user1', asset_id=1))
        self.assertFalse(result['success'])
        self.assertEqual(result['code'], 403)

    def test_list_images(self):
        """列出图像应返回分页结果"""
        api = self._create_api()
        api.rbac.check_permission.return_value = True
        api.storage_service.list_images.return_value = {
            'success': True,
            'data': {
                'images': [
                    {'id': 1, 'filename': 'a.png'},
                    {'id': 2, 'filename': 'b.png'},
                ],
                'total': 2,
                'page': 1,
                'limit': 20,
                'pages': 1,
            },
            'code': 200,
        }

        result = self._run(
            api.list_images(user_id='user1', atom_id=1, page=1, limit=20)
        )
        self.assertTrue(result['success'])
        self.assertEqual(result['data']['total'], 2)

    def test_delete_image_success(self):
        """删除图像应成功"""
        api = self._create_api()
        api.rbac.check_permission.return_value = True
        api.storage_service.delete_image.return_value = {
            'success': True,
            'data': {'asset_id': 1, 'deleted': True},
            'code': 200,
        }

        result = self._run(api.delete_image(user_id='user1', asset_id=1))
        self.assertTrue(result['success'])

    def test_delete_image_no_permission(self):
        """无权限删除应被拒绝"""
        api = self._create_api()
        api.rbac.check_permission.return_value = False

        result = self._run(api.delete_image(user_id='user1', asset_id=1))
        self.assertFalse(result['success'])
        self.assertEqual(result['code'], 403)

    def test_get_variants(self):
        """获取变体应成功"""
        api = self._create_api()
        api.rbac.check_permission.return_value = True
        api.storage_service.get_variants.return_value = {
            'success': True,
            'data': {
                'variants': [
                    {'id': 1, 'variant_type': 'original'},
                    {'id': 2, 'variant_type': 'thumbnail'},
                ],
            },
            'code': 200,
        }

        result = self._run(api.get_variants(user_id='user1', asset_id=1))
        self.assertTrue(result['success'])
        self.assertEqual(len(result['data']['variants']), 2)

    def test_upload_without_user_id(self):
        """无用户 ID 时跳过权限校验直接上传"""
        api = self._create_api()
        api.storage_service.upload_image.return_value = {
            'success': True,
            'data': {
                'asset_id': 1,
                'filename': 'test.png',
                'storage_type': 'inline',
                'width': 100,
                'height': 80,
                'size': 100,
                'checksum': 'abc',
            },
            'code': 201,
        }

        req = CreateImageRequest(
            atom_id=1,
            image_data=b'data',
            filename='test.png',
            mime_type='image/png',
        )
        result = self._run(api.upload_image(req))
        self.assertTrue(result['success'])
        # 不应调用权限检查
        api.rbac.check_permission.assert_not_called()

    def test_upload_invalid_filename(self):
        """无效文件名应被拒绝"""
        api = self._create_api()
        api.rbac.check_permission.return_value = True

        req = CreateImageRequest(
            atom_id=1,
            image_data=b'data',
            filename='',
            mime_type='image/png',
            user_id='user1',
        )
        result = self._run(api.upload_image(req))
        self.assertFalse(result['success'])
        self.assertEqual(result['code'], 400)


if __name__ == '__main__':
    unittest.main()
