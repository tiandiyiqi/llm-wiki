"""OCR 任务队列测试

测试 OCR 任务队列功能：
- 任务提交
- 同步执行模式
- 重试策略
- 死信处理
- 降级行为（无 Celery/Redis）
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from lib.ocr.task_queue import (
    CELERY_AVAILABLE,
    DEFAULT_MAX_RETRIES,
    OCRTaskConfig,
    OCRTaskQueue,
    OCRTaskResult,
    REDIS_AVAILABLE,
    RETRY_DELAYS,
    _generate_task_id,
    create_celery_app,
)


class TestAvailabilityFlags(unittest.TestCase):
    """可用性标志测试"""

    def test_celery_flag_is_boolean(self):
        """CELERY_AVAILABLE 应为布尔值"""
        self.assertIsInstance(CELERY_AVAILABLE, bool)

    def test_redis_flag_is_boolean(self):
        """REDIS_AVAILABLE 应为布尔值"""
        self.assertIsInstance(REDIS_AVAILABLE, bool)


class TestOCRTaskConfig(unittest.TestCase):
    """OCR 任务配置测试"""

    def test_default_config(self):
        """默认配置值"""
        config = OCRTaskConfig()
        self.assertEqual(config.language, 'chi_sim+eng')
        self.assertEqual(config.max_retries, DEFAULT_MAX_RETRIES)
        self.assertEqual(config.page_timeout, 60)
        self.assertEqual(config.document_timeout, 600)
        self.assertTrue(config.preprocess)

    def test_custom_config(self):
        """自定义配置"""
        config = OCRTaskConfig(
            language='eng',
            max_retries=5,
            page_timeout=30,
            document_timeout=300,
            preprocess=False,
        )
        self.assertEqual(config.language, 'eng')
        self.assertEqual(config.max_retries, 5)
        self.assertFalse(config.preprocess)

    def test_config_is_frozen(self):
        """配置不可变"""
        config = OCRTaskConfig()
        with self.assertRaises(AttributeError):
            config.language = 'fra'  # type: ignore[misc]


class TestOCRTaskResult(unittest.TestCase):
    """OCR 任务结果测试"""

    def test_result_creation(self):
        """创建任务结果"""
        result = OCRTaskResult(
            task_id='test-1',
            asset_id=42,
            status='completed',
            result_text='Hello',
        )
        self.assertEqual(result.task_id, 'test-1')
        self.assertEqual(result.asset_id, 42)
        self.assertEqual(result.status, 'completed')
        self.assertEqual(result.result_text, 'Hello')

    def test_result_is_frozen(self):
        """结果不可变"""
        result = OCRTaskResult(
            task_id='test-1',
            asset_id=42,
            status='pending',
        )
        with self.assertRaises(AttributeError):
            result.status = 'completed'  # type: ignore[misc]


class TestTaskQueueSync(unittest.TestCase):
    """同步模式任务队列测试"""

    def setUp(self):
        """设置测试"""
        self.queue = OCRTaskQueue(db=None)

    def test_is_async_without_celery(self):
        """无 Celery 时为同步模式"""
        queue = OCRTaskQueue(celery_app=None)
        self.assertFalse(queue.is_async)

    def test_is_async_with_celery(self):
        """有 Celery 时为异步模式"""
        mock_celery = MagicMock()
        with patch('lib.ocr.task_queue.CELERY_AVAILABLE', True):
            queue = OCRTaskQueue(celery_app=mock_celery)
            self.assertTrue(queue.is_async)

    def test_is_redis_available_without_redis(self):
        """无 Redis 时 Redis 不可用"""
        queue = OCRTaskQueue(redis_client=None)
        self.assertFalse(queue.is_redis_available)

    @patch('lib.ocr.task_queue.PADDLEOCR_AVAILABLE', False)
    def test_sync_execution_without_paddle(self):
        """无 PaddleOCR 时同步执行返回失败"""
        queue = OCRTaskQueue(db=None)
        result = asyncio.run(
            queue.submit_task(
                asset_id=1,
                image_data=b'fake',
            )
        )
        self.assertEqual(result.status, 'failed')
        self.assertIn('PaddleOCR', result.error_message or '')


class TestGenerateTaskId(unittest.TestCase):
    """任务 ID 生成测试"""

    def test_task_id_format(self):
        """任务 ID 格式正确"""
        task_id = _generate_task_id(42)
        self.assertTrue(task_id.startswith('ocr-42-'))

    def test_task_id_uniqueness(self):
        """任务 ID 唯一性"""
        id1 = _generate_task_id(1)
        id2 = _generate_task_id(1)
        self.assertNotEqual(id1, id2)


class TestCreateCeleryApp(unittest.TestCase):
    """Celery 应用创建测试"""

    @patch('lib.ocr.task_queue.CELERY_AVAILABLE', False)
    def test_create_without_celery(self):
        """无 Celery 时返回 None"""
        result = create_celery_app()
        self.assertIsNone(result)

    @patch('lib.ocr.task_queue.CELERY_AVAILABLE', True)
    def test_create_with_celery(self):
        """有 Celery 时返回应用实例"""
        mock_app = MagicMock()
        with patch('lib.ocr.task_queue.Celery', return_value=mock_app):
            result = create_celery_app()
            self.assertIsNotNone(result)


class TestRetryDelays(unittest.TestCase):
    """重试延迟测试"""

    def test_retry_delays_count(self):
        """重试延迟数量等于默认最大重试次数"""
        self.assertEqual(len(RETRY_DELAYS), DEFAULT_MAX_RETRIES)

    def test_retry_delays_exponential(self):
        """重试延迟呈指数增长"""
        for i in range(1, len(RETRY_DELAYS)):
            self.assertGreater(RETRY_DELAYS[i], RETRY_DELAYS[i - 1])


class TestOCRTaskQueueWithDB(unittest.TestCase):
    """带数据库的 OCR 任务队列测试"""

    def setUp(self):
        """设置 mock 数据库"""
        self.mock_db = AsyncMock()
        self.mock_db.execute = AsyncMock(return_value=[])
        self.mock_db.fetch_one = AsyncMock(return_value=None)
        self.queue = OCRTaskQueue(db=self.mock_db)

    def test_get_task_status_no_db(self):
        """无数据库时获取状态返回 None"""
        queue = OCRTaskQueue(db=None)
        result = asyncio.run(
            queue.get_task_status('1')
        )
        self.assertIsNone(result)

    def test_get_task_status_with_db(self):
        """有数据库时获取状态"""
        self.mock_db.fetch_one.return_value = {
            'id': 1,
            'asset_id': 42,
            'status': 'completed',
            'result_text': 'Hello',
            'result_json': None,
            'error_message': None,
            'retry_count': 0,
        }

        result = asyncio.run(
            self.queue.get_task_status('1')
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.status, 'completed')

    def test_retry_dead_letter(self):
        """重试死信任务"""
        result = asyncio.run(
            self.queue.retry_dead_letter('1')
        )
        self.assertEqual(result.status, 'pending')


if __name__ == '__main__':
    unittest.main()
