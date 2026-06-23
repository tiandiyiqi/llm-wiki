"""OCR 结果存储测试

测试 OCR 结果存储模块：
- 文本存储
- JSON 内联存储
- JSON 外部存储
- 结果获取
- 结果删除
"""

import asyncio
import json
import unittest
from unittest.mock import AsyncMock, MagicMock

from lib.ocr.result_store import (
    INLINE_JSON_THRESHOLD,
    OCRResultStore,
    OCRStorageResult,
    _generate_json_storage_path,
)


class TestOCRStorageResult(unittest.TestCase):
    """存储结果数据类测试"""

    def test_result_creation(self):
        """创建存储结果"""
        result = OCRStorageResult(
            task_id=1,
            asset_id=42,
            text_stored=True,
            json_stored=True,
            json_storage_type='inline',
        )
        self.assertEqual(result.task_id, 1)
        self.assertTrue(result.text_stored)
        self.assertTrue(result.json_stored)

    def test_result_is_frozen(self):
        """结果不可变"""
        result = OCRStorageResult(
            task_id=1,
            asset_id=42,
            text_stored=True,
            json_stored=False,
            json_storage_type='inline',
        )
        with self.assertRaises(AttributeError):
            result.text_stored = False  # type: ignore[misc]

    def test_result_with_error(self):
        """带错误的存储结果"""
        result = OCRStorageResult(
            task_id=1,
            asset_id=42,
            text_stored=False,
            json_stored=False,
            json_storage_type='inline',
            error='Database unavailable',
        )
        self.assertEqual(result.error, 'Database unavailable')


class TestOCRResultStoreNoDB(unittest.TestCase):
    """无数据库的存储测试"""

    def setUp(self):
        """设置测试"""
        self.store = OCRResultStore(db=None)

    def test_store_without_db(self):
        """无数据库时存储返回失败"""
        result = asyncio.run(
            self.store.store_result(
                task_id=1,
                asset_id=42,
                result_text='Hello',
            )
        )
        self.assertFalse(result.text_stored)

    def test_get_without_db(self):
        """无数据库时获取返回 None"""
        result = asyncio.run(
            self.store.get_result(task_id=1)
        )
        self.assertIsNone(result)

    def test_get_by_asset_without_db(self):
        """无数据库时按资产获取返回空列表"""
        result = asyncio.run(
            self.store.get_results_by_asset(asset_id=42)
        )
        self.assertEqual(result, [])

    def test_delete_without_db(self):
        """无数据库时删除返回 False"""
        result = asyncio.run(
            self.store.delete_result(task_id=1)
        )
        self.assertFalse(result)


class TestOCRResultStoreWithDB(unittest.TestCase):
    """带数据库的存储测试"""

    def setUp(self):
        """设置测试"""
        self.mock_db = AsyncMock()
        self.mock_db.execute = AsyncMock(return_value=[])
        self.mock_db.fetch_one = AsyncMock(return_value=None)
        self.mock_db.fetch_all = AsyncMock(return_value=[])
        self.store = OCRResultStore(db=self.mock_db)

    def test_store_text_success(self):
        """文本存储成功"""
        self.mock_db.execute.return_value = [{'id': 1}]

        result = asyncio.run(
            self.store.store_result(
                task_id=1,
                asset_id=42,
                result_text='Hello World',
            )
        )
        self.assertTrue(result.text_stored)

    def test_store_text_and_json_inline(self):
        """文本和 JSON 内联存储"""
        self.mock_db.execute.return_value = [{'id': 1}]

        result = asyncio.run(
            self.store.store_result(
                task_id=1,
                asset_id=42,
                result_text='Hello',
                result_json={'boxes': [{'text': 'Hello', 'confidence': 0.9}]},
            )
        )
        self.assertTrue(result.text_stored)
        self.assertTrue(result.json_stored)
        self.assertEqual(result.json_storage_type, 'inline')

    def test_store_json_external(self):
        """JSON 外部存储"""
        mock_storage = AsyncMock()
        mock_storage.store = AsyncMock(return_value=None)
        self.store = OCRResultStore(
            db=self.mock_db,
            external_storage=mock_storage,
        )
        self.mock_db.execute.return_value = [{'id': 1}]

        # 创建大于阈值的数据
        large_json = {'data': 'x' * (INLINE_JSON_THRESHOLD + 1)}
        result = asyncio.run(
            self.store.store_result(
                task_id=1,
                asset_id=42,
                result_text='Hello',
                result_json=large_json,
            )
        )
        self.assertTrue(result.json_stored)
        self.assertEqual(result.json_storage_type, 'external')

    def test_get_result(self):
        """获取结果"""
        self.mock_db.fetch_one.return_value = {
            'id': 1,
            'asset_id': 42,
            'status': 'completed',
            'result_text': 'Hello World',
            'result_json': {'boxes': []},
            'error_message': None,
            'retry_count': 0,
        }

        result = asyncio.run(
            self.store.get_result(task_id=1)
        )
        self.assertIsNotNone(result)
        self.assertEqual(result['text'], 'Hello World')

    def test_get_result_not_found(self):
        """获取不存在的结果"""
        self.mock_db.fetch_one.return_value = None

        result = asyncio.run(
            self.store.get_result(task_id=999)
        )
        self.assertIsNone(result)

    def test_get_results_by_asset(self):
        """按资产获取结果列表"""
        self.mock_db.fetch_all.return_value = [
            {
                'id': 1,
                'asset_id': 42,
                'status': 'completed',
                'result_text': 'Text 1',
                'created_at': '2026-01-01',
            },
            {
                'id': 2,
                'asset_id': 42,
                'status': 'completed',
                'result_text': 'Text 2',
                'created_at': '2026-01-02',
            },
        ]

        results = asyncio.run(
            self.store.get_results_by_asset(asset_id=42)
        )
        self.assertEqual(len(results), 2)

    def test_delete_result(self):
        """删除结果"""
        self.mock_db.fetch_one.return_value = {
            'result_json': {'storage_type': 'inline'},
        }

        result = asyncio.run(
            self.store.delete_result(task_id=1)
        )
        self.assertTrue(result)

    def test_delete_result_with_external_storage(self):
        """删除含外部存储的结果"""
        mock_storage = AsyncMock()
        mock_storage.delete = AsyncMock(return_value=None)
        self.store = OCRResultStore(
            db=self.mock_db,
            external_storage=mock_storage,
        )
        self.mock_db.fetch_one.return_value = {
            'result_json': {
                'storage_type': 'external',
                'storage_path': 'ocr_results/42/2026/01/1_abc.json',
            },
        }

        result = asyncio.run(
            self.store.delete_result(task_id=1)
        )
        self.assertTrue(result)
        mock_storage.delete.assert_called_once()


class TestGenerateJsonStoragePath(unittest.TestCase):
    """JSON 存储路径生成测试"""

    def test_path_format(self):
        """路径格式正确"""
        path = _generate_json_storage_path(asset_id=42, task_id=1)
        self.assertTrue(path.startswith('ocr_results/42/'))
        self.assertTrue(path.endswith('.json'))

    def test_path_contains_year_month(self):
        """路径包含年月"""
        path = _generate_json_storage_path(asset_id=42, task_id=1)
        # 应包含 2026/ 格式的年月
        import re
        self.assertIsNotNone(re.search(r'\d{4}/\d{2}', path))


if __name__ == '__main__':
    unittest.main()
