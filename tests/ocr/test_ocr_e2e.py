"""OCR 基础设施端到端集成验证

验证 OCR 模块各组件之间的集成：
- PaddleOCRService + OCRTaskQueue + OCRResultStore
- 降级模式下的完整流程
- 错误处理链路
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from lib.ocr.paddle_ocr import (
    OCRError,
    OCRPageResult,
    PaddleOCRNotAvailableError,
    PaddleOCRService,
    PADDLEOCR_AVAILABLE,
)
from lib.ocr.task_queue import (
    CELERY_AVAILABLE,
    OCRTaskConfig,
    OCRTaskQueue,
    OCRTaskResult,
    REDIS_AVAILABLE,
)
from lib.ocr.result_store import OCRResultStore, OCRStorageResult


class TestOCRIntegrationNoPaddle(unittest.TestCase):
    """无 PaddleOCR 的集成测试"""

    def setUp(self):
        """每个测试前重置单例"""
        PaddleOCRService.reset_instance()

    def tearDown(self):
        """每个测试后重置单例"""
        PaddleOCRService.reset_instance()

    @patch('lib.ocr.paddle_ocr.PADDLEOCR_AVAILABLE', False)
    @patch('lib.ocr.task_queue.PADDLEOCR_AVAILABLE', False)
    def test_full_pipeline_without_paddle(self):
        """无 PaddleOCR 时完整流程降级"""
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=[])

        queue = OCRTaskQueue(db=mock_db)
        result = asyncio.run(
            queue.submit_task(
                asset_id=1,
                image_data=b'fake_image',
            )
        )

        self.assertEqual(result.status, 'failed')
        self.assertIn('PaddleOCR', result.error_message or '')


class TestOCRIntegrationSyncMode(unittest.TestCase):
    """同步模式集成测试"""

    def setUp(self):
        """设置"""
        PaddleOCRService.reset_instance()

    def tearDown(self):
        """清理"""
        PaddleOCRService.reset_instance()

    @patch('lib.ocr.task_queue.CELERY_AVAILABLE', False)
    def test_queue_sync_mode(self):
        """无 Celery 时降级为同步模式"""
        queue = OCRTaskQueue(db=None)
        self.assertFalse(queue.is_async)

    def test_queue_config_propagation(self):
        """配置正确传播"""
        config = OCRTaskConfig(
            language='eng',
            max_retries=5,
            preprocess=False,
        )
        queue = OCRTaskQueue(db=None, config=config)
        self.assertEqual(queue._config.language, 'eng')
        self.assertEqual(queue._config.max_retries, 5)


class TestOCRIntegrationResultStore(unittest.TestCase):
    """OCR 结果存储集成测试"""

    def test_store_then_get(self):
        """存储后获取"""
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=[{'id': 1}])
        mock_db.fetch_one = AsyncMock(return_value={
            'id': 1,
            'asset_id': 42,
            'status': 'completed',
            'result_text': 'OCR Result Text',
            'result_json': None,
            'error_message': None,
            'retry_count': 0,
        })

        store = OCRResultStore(db=mock_db)

        # 存储
        store_result = asyncio.run(
            store.store_result(
                task_id=1,
                asset_id=42,
                result_text='OCR Result Text',
            )
        )
        self.assertTrue(store_result.text_stored)

        # 获取
        get_result = asyncio.run(
            store.get_result(task_id=1)
        )
        self.assertIsNotNone(get_result)
        self.assertEqual(get_result['text'], 'OCR Result Text')


class TestOCRErrorHandling(unittest.TestCase):
    """OCR 错误处理集成测试"""

    def setUp(self):
        """每个测试前重置单例"""
        PaddleOCRService.reset_instance()

    def tearDown(self):
        """每个测试后重置单例"""
        PaddleOCRService.reset_instance()

    def test_error_chain(self):
        """错误类型链正确"""
        from lib.ocr.paddle_ocr import (
            OCRError,
            OCRTimeoutError,
            PaddleOCRNotAvailableError,
        )

        self.assertTrue(issubclass(PaddleOCRNotAvailableError, OCRError))
        self.assertTrue(issubclass(OCRTimeoutError, OCRError))

    def test_timeout_in_queue(self):
        """队列中超时处理"""
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=[])
        config = OCRTaskConfig(max_retries=0)

        queue = OCRTaskQueue(db=mock_db, config=config)
        # 即使 PaddleOCR 不可用，也不应该抛出未捕获的异常
        result = asyncio.run(
            queue.submit_task(
                asset_id=1,
                image_data=b'fake',
            )
        )
        self.assertIn(result.status, ['failed', 'dead_letter'])


class TestAvailabilityIntegration(unittest.TestCase):
    """可用性标志集成测试"""

    def test_all_flags_are_boolean(self):
        """所有可用性标志为布尔值"""
        self.assertIsInstance(PADDLEOCR_AVAILABLE, bool)
        self.assertIsInstance(CELERY_AVAILABLE, bool)
        self.assertIsInstance(REDIS_AVAILABLE, bool)

    def test_graceful_degradation(self):
        """优雅降级：所有服务不可用时系统不崩溃"""
        queue = OCRTaskQueue(db=None)
        store = OCRResultStore(db=None)

        # 这些操作不应该抛出异常
        result = asyncio.run(
            queue.submit_task(asset_id=1, image_data=b'fake')
        )
        self.assertIsNotNone(result)

        get_result = asyncio.run(
            store.get_result(task_id=1)
        )
        self.assertIsNone(get_result)

        list_result = asyncio.run(
            store.get_results_by_asset(asset_id=1)
        )
        self.assertEqual(list_result, [])


if __name__ == '__main__':
    unittest.main()
