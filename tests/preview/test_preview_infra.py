"""预览基础设施测试

测试预览模块各组件：
- OfficeViewerService 功能
- PreviewCacheManager 功能
- 降级行为
"""

import asyncio
import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from lib.preview.office_viewer import (
    KKFILEVIEW_AVAILABLE,
    OFFICE_MIME_TYPES,
    OfficeViewerService,
    PreviewURL,
    _base64_encode_url,
    _get_format_from_mime,
)
from lib.preview.cache_manager import (
    CacheEntry,
    CacheStats,
    DEFAULT_CACHE_TTL,
    PreviewCacheManager,
    _get_extension_for_format,
    _sanitize_filename,
)


class TestKKFileViewAvailability(unittest.TestCase):
    """KKFileView 可用性测试"""

    def test_availability_flag_is_boolean(self):
        """KKFILEVIEW_AVAILABLE 应为布尔值"""
        self.assertIsInstance(KKFILEVIEW_AVAILABLE, bool)


class TestOfficeViewerService(unittest.TestCase):
    """Office 文档预览服务测试"""

    def setUp(self):
        """设置"""
        self.service = OfficeViewerService()

    def test_is_available(self):
        """is_available 返回布尔值"""
        self.assertIsInstance(self.service.is_available, bool)

    def test_get_preview_url_not_available(self):
        """KKFileView 不可用时返回降级 URL"""
        with patch('lib.preview.office_viewer.KKFILEVIEW_AVAILABLE', False):
            service = OfficeViewerService()
            result = service.get_preview_url(
                file_url='http://example.com/doc.docx',
                source_mime_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            )
            self.assertFalse(result.is_available)
            self.assertEqual(result.format, 'word')
            self.assertIsNotNone(result.error)

    def test_get_preview_url_pdf(self):
        """PDF 文件直接返回原始 URL"""
        with patch('lib.preview.office_viewer.KKFILEVIEW_AVAILABLE', True):
            service = OfficeViewerService()
            result = service.get_preview_url(
                file_url='http://example.com/doc.pdf',
                source_mime_type='application/pdf',
            )
            self.assertTrue(result.is_available)
            self.assertEqual(result.format, 'pdf')
            self.assertEqual(result.url, 'http://example.com/doc.pdf')

    def test_get_preview_url_word(self):
        """Word 文档返回 KKFileView 预览 URL"""
        with patch('lib.preview.office_viewer.KKFILEVIEW_AVAILABLE', True):
            service = OfficeViewerService()
            result = service.get_preview_url(
                file_url='http://example.com/doc.docx',
                source_mime_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            )
            self.assertTrue(result.is_available)
            self.assertEqual(result.format, 'word')
            self.assertIn('onlinePreview', result.url)

    def test_get_preview_url_excel(self):
        """Excel 文档返回 KKFileView 预览 URL"""
        with patch('lib.preview.office_viewer.KKFILEVIEW_AVAILABLE', True):
            service = OfficeViewerService()
            result = service.get_preview_url(
                file_url='http://example.com/sheet.xlsx',
                source_mime_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            )
            self.assertTrue(result.is_available)
            self.assertEqual(result.format, 'excel')

    def test_get_preview_url_ppt(self):
        """PPT 文档返回 KKFileView 预览 URL"""
        with patch('lib.preview.office_viewer.KKFILEVIEW_AVAILABLE', True):
            service = OfficeViewerService()
            result = service.get_preview_url(
                file_url='http://example.com/slides.pptx',
                source_mime_type='application/vnd.openxmlformats-officedocument.presentationml.presentation',
            )
            self.assertTrue(result.is_available)
            self.assertEqual(result.format, 'ppt')

    def test_get_preview_url_no_mime(self):
        """无 MIME 类型时格式为 other"""
        service = OfficeViewerService()
        result = service.get_preview_url(
            file_url='http://example.com/file.xyz',
        )
        self.assertEqual(result.format, 'other')

    def test_fallback_message_word(self):
        """Word 降级提示"""
        service = OfficeViewerService()
        msg = service._get_fallback_message(
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        self.assertIn('Word', msg)
        self.assertIn('KKFileView', msg)

    def test_fallback_message_unknown(self):
        """未知格式降级提示"""
        service = OfficeViewerService()
        msg = service._get_fallback_message('application/unknown')
        self.assertIn('不可用', msg)

    def test_supported_mime_types(self):
        """支持的 MIME 类型列表"""
        service = OfficeViewerService()
        types = service.get_supported_mime_types()
        self.assertIn('application/pdf', types)
        self.assertIn('application/msword', types)
        self.assertIn('application/vnd.ms-excel', types)

    def test_convert_document_not_available(self):
        """KKFileView 不可用时转换返回降级"""
        with patch('lib.preview.office_viewer.KKFILEVIEW_AVAILABLE', False):
            service = OfficeViewerService()
            result = asyncio.run(
                service.convert_document(
                    file_url='http://example.com/doc.docx',
                    source_mime_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                )
            )
            self.assertFalse(result['success'])
            self.assertIn('fallback', result)

    def test_health_check_no_httpx(self):
        """无 httpx 时健康检查返回不可用"""
        with patch('lib.preview.office_viewer.HTTPX_AVAILABLE', False):
            service = OfficeViewerService()
            result = asyncio.run(service.check_health())
            self.assertFalse(result['available'])


class TestPreviewURL(unittest.TestCase):
    """PreviewURL 数据类测试"""

    def test_creation(self):
        """创建 PreviewURL"""
        url = PreviewURL(
            url='http://example.com/preview',
            format='pdf',
            source_mime_type='application/pdf',
            is_available=True,
        )
        self.assertEqual(url.url, 'http://example.com/preview')
        self.assertTrue(url.is_available)

    def test_frozen(self):
        """PreviewURL 不可变"""
        url = PreviewURL(
            url='http://example.com/preview',
            format='pdf',
            source_mime_type='application/pdf',
        )
        with self.assertRaises(AttributeError):
            url.format = 'word'  # type: ignore[misc]


class TestBase64EncodeURL(unittest.TestCase):
    """Base64 编码测试"""

    def test_encode(self):
        """编码 URL"""
        encoded = _base64_encode_url('http://example.com/doc.docx')
        self.assertIsInstance(encoded, str)
        self.assertNotIn('http://', encoded)

    def test_round_trip(self):
        """编码后解码应一致"""
        import base64
        from urllib.parse import unquote

        original = 'http://example.com/doc.docx'
        encoded = _base64_encode_url(original)
        decoded = base64.b64decode(unquote(encoded)).decode('utf-8')
        self.assertEqual(decoded, original)


class TestGetFormatFromMime(unittest.TestCase):
    """MIME 类型格式映射测试"""

    def test_word_formats(self):
        """Word 格式"""
        self.assertEqual(_get_format_from_mime('application/msword'), 'word')
        self.assertEqual(
            _get_format_from_mime(
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            ),
            'word',
        )

    def test_excel_formats(self):
        """Excel 格式"""
        self.assertEqual(_get_format_from_mime('application/vnd.ms-excel'), 'excel')

    def test_pdf_format(self):
        """PDF 格式"""
        self.assertEqual(_get_format_from_mime('application/pdf'), 'pdf')

    def test_unknown_format(self):
        """未知格式"""
        self.assertEqual(_get_format_from_mime('application/unknown'), 'other')

    def test_empty_string(self):
        """空字符串"""
        self.assertEqual(_get_format_from_mime(''), 'other')


class TestPreviewCacheManager(unittest.TestCase):
    """预览缓存管理器测试"""

    def setUp(self):
        """设置测试"""
        self.temp_dir = tempfile.mkdtemp()
        self.cache = PreviewCacheManager(
            cache_dir=self.temp_dir,
            ttl=DEFAULT_CACHE_TTL,
        )

    def tearDown(self):
        """清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generate_cache_key(self):
        """生成缓存键"""
        key = self.cache.generate_cache_key(atom_id=42, format='pdf')
        self.assertEqual(key, 'preview:42:pdf')

    def test_generate_cache_path(self):
        """生成缓存路径"""
        path = self.cache.generate_cache_path(atom_id=42, format='pdf')
        self.assertTrue(path.startswith('42/pdf/'))
        self.assertTrue(path.endswith('.pdf'))

    def test_generate_cache_path_with_filename(self):
        """生成带文件名的缓存路径"""
        path = self.cache.generate_cache_path(
            atom_id=42,
            format='pdf',
            filename='document.pdf',
        )
        self.assertIn('document', path)

    def test_put_and_get(self):
        """存入和获取缓存"""
        data = b'preview data content'

        async def _test():
            entry = await self.cache.put(
                atom_id=1,
                format='pdf',
                data=data,
                source_mime_type='application/pdf',
            )
            self.assertTrue(entry.cache_path)

            result = await self.cache.get(atom_id=1, format='pdf')
            self.assertIsNotNone(result)
            self.assertEqual(result.atom_id, 1)
            self.assertEqual(result.format, 'pdf')

        asyncio.run(_test())

    def test_get_miss(self):
        """缓存未命中"""
        async def _test():
            result = await self.cache.get(atom_id=999, format='pdf')
            self.assertIsNone(result)

        asyncio.run(_test())

    def test_cache_expiration(self):
        """缓存过期"""
        short_ttl_cache = PreviewCacheManager(
            cache_dir=self.temp_dir,
            ttl=0,  # 立即过期
        )

        async def _test():
            await short_ttl_cache.put(
                atom_id=1,
                format='pdf',
                data=b'data',
            )

            # TTL=0，应该立即过期
            result = await short_ttl_cache.get(atom_id=1, format='pdf')
            self.assertIsNone(result)

        asyncio.run(_test())

    def test_invalidate(self):
        """使缓存失效"""
        async def _test():
            await self.cache.put(
                atom_id=1,
                format='pdf',
                data=b'data',
            )

            result = await self.cache.invalidate(atom_id=1, format='pdf')
            self.assertTrue(result)

        asyncio.run(_test())

    def test_cleanup_expired(self):
        """清理过期缓存"""
        async def _test():
            # 先存入一些缓存
            await self.cache.put(
                atom_id=1,
                format='pdf',
                data=b'data1',
            )
            await self.cache.put(
                atom_id=2,
                format='pdf',
                data=b'data2',
            )

            # 清理过期缓存
            cleaned = await self.cache.cleanup_expired()
            self.assertIsInstance(cleaned, int)

        asyncio.run(_test())

    def test_get_stats(self):
        """获取缓存统计"""
        stats = self.cache.get_stats()
        self.assertIsInstance(stats, CacheStats)
        self.assertIsInstance(stats.total_entries, int)
        self.assertIsInstance(stats.hit_rate, float)

    def test_redis_not_available_by_default(self):
        """默认 Redis 不可用"""
        self.assertFalse(self.cache.is_redis_available)

    def test_read_cache_data(self):
        """读取缓存文件数据"""
        async def _test():
            await self.cache.put(
                atom_id=1,
                format='pdf',
                data=b'cached content',
            )

            entry = await self.cache.get(atom_id=1, format='pdf')
            if entry:
                data = await self.cache.read_cache_data(entry.cache_path)
                self.assertEqual(data, b'cached content')

        asyncio.run(_test())

    def test_read_nonexistent_cache(self):
        """读取不存在的缓存文件"""
        async def _test():
            data = await self.cache.read_cache_data('nonexistent/path')
            self.assertIsNone(data)

        asyncio.run(_test())


class TestCacheStats(unittest.TestCase):
    """缓存统计数据类测试"""

    def test_hit_rate_zero(self):
        """无请求时命中率为 0"""
        stats = CacheStats()
        self.assertEqual(stats.hit_rate, 0.0)

    def test_hit_rate_calculation(self):
        """命中率计算"""
        stats = CacheStats(hit_count=80, miss_count=20)
        self.assertAlmostEqual(stats.hit_rate, 0.8)

    def test_frozen(self):
        """统计不可变"""
        stats = CacheStats()
        with self.assertRaises(AttributeError):
            stats.hit_count = 100  # type: ignore[misc]


class TestCacheEntry(unittest.TestCase):
    """缓存条目数据类测试"""

    def test_creation(self):
        """创建缓存条目"""
        now = time.time()
        entry = CacheEntry(
            cache_key='preview:1:pdf',
            cache_path='1/pdf/abc.pdf',
            atom_id=1,
            format='pdf',
            source_mime_type='application/pdf',
            file_size=1024,
            created_at=now,
            expires_at=now + DEFAULT_CACHE_TTL,
        )
        self.assertEqual(entry.atom_id, 1)
        self.assertEqual(entry.format, 'pdf')

    def test_frozen(self):
        """缓存条目不可变"""
        entry = CacheEntry(
            cache_key='preview:1:pdf',
            cache_path='',
            atom_id=1,
            format='pdf',
            source_mime_type=None,
            file_size=0,
            created_at=0.0,
            expires_at=0.0,
        )
        with self.assertRaises(AttributeError):
            entry.atom_id = 2  # type: ignore[misc]


class TestHelperFunctions(unittest.TestCase):
    """辅助函数测试"""

    def test_sanitize_filename(self):
        """文件名清理"""
        self.assertEqual(_sanitize_filename('simple.pdf'), 'simple.pdf')

    def test_sanitize_filename_special_chars(self):
        """清理特殊字符"""
        result = _sanitize_filename('file with spaces & special!.pdf')
        self.assertNotIn(' ', result)
        self.assertNotIn('&', result)

    def test_sanitize_filename_long(self):
        """长文件名截断"""
        long_name = 'a' * 300 + '.pdf'
        result = _sanitize_filename(long_name)
        self.assertLessEqual(len(result), 210)

    def test_get_extension_pdf(self):
        """PDF 扩展名"""
        self.assertEqual(_get_extension_for_format('pdf'), '.pdf')

    def test_get_extension_word(self):
        """Word 扩展名"""
        self.assertEqual(_get_extension_for_format('word'), '.docx')

    def test_get_extension_unknown(self):
        """未知格式扩展名"""
        self.assertEqual(_get_extension_for_format('unknown_format'), '.bin')


if __name__ == '__main__':
    unittest.main()
