"""PaddleOCR 集成测试

测试 PaddleOCR 核心模块功能：
- Mock PaddleOCR 调用
- 无 PaddleOCR 时测试降级行为
- 图像预处理
- 结果后处理
"""

import unittest
from unittest.mock import MagicMock, patch

from lib.ocr.paddle_ocr import (
    DEFAULT_LANGUAGE,
    OCRError,
    OCRPageResult,
    OCRTimeoutError,
    PaddleOCRNotAvailableError,
    PaddleOCRService,
    PADDLEOCR_AVAILABLE,
    clean_ocr_text,
    _merge_paragraphs,
)


class TestPaddleOCRAvailability(unittest.TestCase):
    """PaddleOCR 可用性测试"""

    def test_availability_flag_is_boolean(self):
        """PADDLEOCR_AVAILABLE 应为布尔值"""
        self.assertIsInstance(PADDLEOCR_AVAILABLE, bool)

    def test_service_creation_without_paddle(self):
        """无 PaddleOCR 时也能创建服务实例"""
        service = PaddleOCRService.__new__(PaddleOCRService)
        service._initialized = False
        service._language = DEFAULT_LANGUAGE
        service._use_gpu = False
        service._kwargs = {}
        service._engine = None
        service._initialized = True

        self.assertIsNotNone(service)

    def test_is_available_property(self):
        """is_available 属性返回布尔值"""
        service = PaddleOCRService()
        self.assertIsInstance(service.is_available, bool)


class TestPaddleOCRNotAvailable(unittest.TestCase):
    """PaddleOCR 不可用时的降级行为测试"""

    def setUp(self):
        """每个测试前重置单例"""
        PaddleOCRService.reset_instance()

    def tearDown(self):
        """每个测试后重置单例"""
        PaddleOCRService.reset_instance()

    @patch('lib.ocr.paddle_ocr.PADDLEOCR_AVAILABLE', False)
    def test_ensure_engine_raises_error(self):
        """无 PaddleOCR 时调用 _ensure_engine 抛出异常"""
        service = PaddleOCRService()
        service._engine = None

        with self.assertRaises(PaddleOCRNotAvailableError):
            service._ensure_engine()

    @patch('lib.ocr.paddle_ocr.PADDLEOCR_AVAILABLE', False)
    def test_recognize_image_raises_error(self):
        """无 PaddleOCR 时调用 recognize_image 抛出异常"""
        service = PaddleOCRService()
        service._engine = None

        with self.assertRaises(PaddleOCRNotAvailableError):
            service.recognize_image(b'fake_image_data')


class TestOCRResultParsing(unittest.TestCase):
    """OCR 结果解析测试"""

    def setUp(self):
        """每个测试前重置单例"""
        PaddleOCRService.reset_instance()

    def tearDown(self):
        """每个测试后重置单例"""
        PaddleOCRService.reset_instance()

    def test_parse_empty_result(self):
        """解析空结果"""
        service = PaddleOCRService()
        result = service._parse_ocr_result(None, 100.0)
        self.assertEqual(result.text, '')
        self.assertEqual(len(result.boxes), 0)

    def test_parse_empty_list_result(self):
        """解析空列表结果"""
        service = PaddleOCRService()
        result = service._parse_ocr_result([None], 100.0)
        self.assertEqual(result.text, '')

    def test_parse_normal_result(self):
        """解析正常 OCR 结果"""
        service = PaddleOCRService()

        # 模拟 PaddleOCR 输出格式
        mock_result = [[
            [
                [[10, 20], [100, 20], [100, 40], [10, 40]],
                ['Hello World', 0.98],
            ],
            [
                [[10, 50], [200, 50], [200, 70], [10, 70]],
                ['Test Line', 0.95],
            ],
        ]]

        result = service._parse_ocr_result(mock_result, 200.0)

        self.assertIn('Hello World', result.text)
        self.assertIn('Test Line', result.text)
        self.assertEqual(len(result.boxes), 2)
        self.assertAlmostEqual(result.processing_time_ms, 200.0)
        self.assertEqual(result.page_number, 1)

    def test_parse_result_with_low_confidence(self):
        """解析低置信度结果"""
        service = PaddleOCRService()

        mock_result = [[
            [
                [[10, 20], [100, 20], [100, 40], [10, 40]],
                ['Uncertain', 0.3],
            ],
        ]]

        result = service._parse_ocr_result(mock_result, 50.0)
        self.assertEqual(len(result.boxes), 1)
        self.assertAlmostEqual(result.boxes[0].confidence, 0.3)

    def test_parse_result_with_invalid_line(self):
        """解析包含无效行的结果"""
        service = PaddleOCRService()

        mock_result = [[
            None,
            [
                [[10, 20], [100, 20], [100, 40], [10, 40]],
                ['Valid', 0.9],
            ],
        ]]

        result = service._parse_ocr_result(mock_result, 50.0)
        self.assertIn('Valid', result.text)


class TestMergeParagraphs(unittest.TestCase):
    """段落合并测试"""

    def test_empty_lines(self):
        """空行列表"""
        self.assertEqual(_merge_paragraphs([]), '')

    def test_single_line(self):
        """单行文本"""
        self.assertEqual(_merge_paragraphs(['Hello']), 'Hello')

    def test_multiple_lines_no_breaks(self):
        """多行无空行"""
        result = _merge_paragraphs(['Line 1', 'Line 2', 'Line 3'])
        self.assertEqual(result, 'Line 1 Line 2 Line 3')

    def test_paragraph_breaks(self):
        """带空行的段落"""
        result = _merge_paragraphs(['Para 1', '', 'Para 2'])
        self.assertEqual(result, 'Para 1\n\nPara 2')

    def test_multiple_empty_lines(self):
        """多个连续空行"""
        result = _merge_paragraphs(['Para 1', '', '', 'Para 2'])
        self.assertEqual(result, 'Para 1\n\nPara 2')

    def test_trailing_empty_lines(self):
        """末尾空行"""
        result = _merge_paragraphs(['Text', ''])
        self.assertEqual(result, 'Text')


class TestCleanOCRText(unittest.TestCase):
    """OCR 文本清理测试"""

    def test_empty_text(self):
        """空文本"""
        self.assertEqual(clean_ocr_text(''), '')

    def test_whitespace_cleanup(self):
        """多余空白清理"""
        result = clean_ocr_text('  Hello   World  ')
        self.assertNotIn('  ', result)

    def test_newline_normalization(self):
        """换行规范化"""
        result = clean_ocr_text('Line1\n\n\n\nLine2')
        self.assertNotIn('\n\n\n', result)

    def test_preserves_content(self):
        """保留有效内容"""
        result = clean_ocr_text('Hello World')
        self.assertIn('Hello', result)
        self.assertIn('World', result)


class TestOCRErrorTypes(unittest.TestCase):
    """OCR 错误类型测试"""

    def test_ocr_error(self):
        """OCRError 基类"""
        error = OCRError('test error')
        self.assertEqual(str(error), 'test error')
        self.assertIsInstance(error, Exception)

    def test_paddle_not_available_error(self):
        """PaddleOCRNotAvailableError"""
        error = PaddleOCRNotAvailableError()
        self.assertIn('PaddleOCR', str(error))
        self.assertIsInstance(error, OCRError)

    def test_timeout_error(self):
        """OCRTimeoutError"""
        error = OCRTimeoutError(timeout=60)
        self.assertIn('60', str(error))
        self.assertIsInstance(error, OCRError)


class TestPreprocessing(unittest.TestCase):
    """图像预处理测试"""

    def setUp(self):
        """每个测试前重置单例"""
        PaddleOCRService.reset_instance()

    def tearDown(self):
        """每个测试后重置单例"""
        PaddleOCRService.reset_instance()

    def test_preprocess_without_pillow(self):
        """无 Pillow 时跳过预处理"""
        service = PaddleOCRService()
        with patch('lib.ocr.paddle_ocr.PILLOW_AVAILABLE', False):
            data = b'fake_image_data'
            result = service.preprocess_image(data)
            self.assertEqual(result, data)

    def test_unknown_operation(self):
        """未知预处理操作不报错"""
        service = PaddleOCRService()
        # 如果 Pillow 不可用，直接返回原数据
        if not service.is_available:
            result = service.preprocess_image(b'data', ['unknown_op'])
            self.assertEqual(result, b'data')


class TestSingletonPattern(unittest.TestCase):
    """单例模式测试"""

    def setUp(self):
        """每个测试前重置单例"""
        PaddleOCRService.reset_instance()

    def tearDown(self):
        """每个测试后重置单例"""
        PaddleOCRService.reset_instance()

    def test_singleton_returns_same_instance(self):
        """多次创建返回同一实例"""
        service1 = PaddleOCRService()
        service2 = PaddleOCRService()
        self.assertIs(service1, service2)

    def test_reset_creates_new_instance(self):
        """重置后创建新实例"""
        service1 = PaddleOCRService()
        PaddleOCRService.reset_instance()
        service2 = PaddleOCRService()
        self.assertIsNot(service1, service2)


if __name__ == '__main__':
    unittest.main()
