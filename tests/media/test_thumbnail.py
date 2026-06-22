"""ThumbnailGenerator 测试

测试缩略图生成模块：
- 3 种尺寸生成（small/medium/large）
- 保持纵横比
- JPEG/PNG/WebP 输出
- 异常图片处理
- 尺寸约束验证
"""

import io
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# 直接导入 media 模块
_media_path = str(Path(__file__).parent.parent.parent / 'lib' / 'media')
if _media_path not in sys.path:
    sys.path.insert(0, _media_path)

from thumbnail import (
    THUMBNAIL_SIZES,
    ThumbnailGenerator,
    ThumbnailSize,
    compute_thumbnail_dimensions,
)


class TestThumbnailSizes(unittest.TestCase):
    """缩略图尺寸配置测试"""

    def test_small_size_defined(self):
        """small 尺寸应定义为 200x200"""
        self.assertIn('small', THUMBNAIL_SIZES)
        small = THUMBNAIL_SIZES['small']
        self.assertEqual(small.max_width, 200)
        self.assertEqual(small.max_height, 200)

    def test_medium_size_defined(self):
        """medium 尺寸应定义为 600x600"""
        self.assertIn('medium', THUMBNAIL_SIZES)
        medium = THUMBNAIL_SIZES['medium']
        self.assertEqual(medium.max_width, 600)
        self.assertEqual(medium.max_height, 600)

    def test_large_size_defined(self):
        """large 尺寸应定义为 1200x1200"""
        self.assertIn('large', THUMBNAIL_SIZES)
        large = THUMBNAIL_SIZES['large']
        self.assertEqual(large.max_width, 1200)
        self.assertEqual(large.max_height, 1200)


class TestComputeThumbnailDimensions(unittest.TestCase):
    """缩略图尺寸计算测试"""

    def test_landscape_image_small(self):
        """横向图像应按宽度缩放"""
        width, height = compute_thumbnail_dimensions(800, 600, 200, 200)
        self.assertLessEqual(width, 200)
        self.assertLessEqual(height, 200)
        # 保持纵横比 4:3
        self.assertAlmostEqual(width / height, 800 / 600, places=2)

    def test_portrait_image_small(self):
        """纵向图像应按高度缩放"""
        width, height = compute_thumbnail_dimensions(600, 800, 200, 200)
        self.assertLessEqual(width, 200)
        self.assertLessEqual(height, 200)
        self.assertAlmostEqual(width / height, 600 / 800, places=2)

    def test_square_image(self):
        """正方形图像应等比缩放"""
        width, height = compute_thumbnail_dimensions(500, 500, 200, 200)
        self.assertEqual(width, 200)
        self.assertEqual(height, 200)

    def test_already_small_image(self):
        """已经足够小的图像不放大"""
        width, height = compute_thumbnail_dimensions(100, 80, 200, 200)
        self.assertEqual(width, 100)
        self.assertEqual(height, 80)

    def test_very_wide_image(self):
        """超宽图像应按宽度限制"""
        width, height = compute_thumbnail_dimensions(2000, 200, 600, 600)
        self.assertEqual(width, 600)
        self.assertLessEqual(height, 600)

    def test_very_tall_image(self):
        """超高图像应按高度限制"""
        width, height = compute_thumbnail_dimensions(200, 2000, 600, 600)
        self.assertEqual(height, 600)
        self.assertLessEqual(width, 600)

    def test_zero_size_returns_original(self):
        """零尺寸约束应返回原始尺寸"""
        width, height = compute_thumbnail_dimensions(800, 600, 0, 0)
        self.assertEqual(width, 800)
        self.assertEqual(height, 600)


class TestThumbnailGenerator(unittest.TestCase):
    """ThumbnailGenerator 集成测试"""

    def _create_test_image(self, width=800, height=600, fmt='PNG'):
        """创建测试图像字节"""
        try:
            from PIL import Image
            img = Image.new('RGB', (width, height), color='blue')
            buf = io.BytesIO()
            img.save(buf, format=fmt)
            return buf.getvalue()
        except ImportError:
            return b'\x89PNG\r\n\x1a\n' + b'\x00' * 100

    @patch('thumbnail.PILImage')
    @patch('thumbnail.PILLOW_AVAILABLE', True)
    def test_generate_single_thumbnail(self, mock_pil):
        """生成单个缩略图"""
        mock_thumb = MagicMock()
        mock_thumb.size = (200, 150)
        mock_thumb.mode = 'RGB'
        mock_thumb.thumbnail = MagicMock()
        mock_thumb.save = MagicMock()

        mock_original = MagicMock()
        mock_original.size = (800, 600)
        mock_original.mode = 'RGB'
        mock_original.copy.return_value = mock_thumb
        mock_pil.open.return_value = mock_original

        with patch('thumbnail.io.BytesIO') as mock_bio:
            mock_bio_instance = MagicMock()
            mock_bio_instance.getvalue.return_value = b'thumb_data'
            mock_bio.return_value = mock_bio_instance

            generator = ThumbnailGenerator()
            result = generator.generate(b'fake_image_data', 'image/png', 'small')

        self.assertIsNotNone(result)
        # thumbnail 是在 copy 后的副本上调用的
        mock_thumb.thumbnail.assert_called_once()

    @patch('thumbnail.PILImage')
    @patch('thumbnail.PILLOW_AVAILABLE', True)
    def test_generate_all_variants(self, mock_pil):
        """生成所有变体缩略图"""
        mock_original = MagicMock()
        mock_original.size = (1600, 1200)
        mock_original.mode = 'RGB'

        mock_thumb = MagicMock()
        mock_thumb.size = (200, 150)
        mock_thumb.save = MagicMock()
        mock_thumb.copy.return_value = mock_thumb

        mock_original.copy.return_value = mock_thumb
        mock_pil.open.return_value = mock_original

        # mock BytesIO for save output
        with patch('thumbnail.io.BytesIO') as mock_bio:
            mock_bio_instance = MagicMock()
            mock_bio_instance.getvalue.return_value = b'thumb_data'
            mock_bio.return_value = mock_bio_instance

            generator = ThumbnailGenerator()
            results = generator.generate_all(b'fake_image_data', 'image/png')

            self.assertIn('small', results)
            self.assertIn('medium', results)
            self.assertIn('large', results)
            self.assertEqual(len(results), 3)

    @patch('thumbnail.PILLOW_AVAILABLE', False)
    def test_generate_without_pillow(self):
        """Pillow 不可用时应返回空结果"""
        generator = ThumbnailGenerator()
        result = generator.generate(b'fake_data', 'image/png', 'small')
        self.assertIsNone(result)

    @patch('thumbnail.PILImage')
    @patch('thumbnail.PILLOW_AVAILABLE', True)
    def test_generate_handles_corrupt_image(self, mock_pil):
        """处理损坏的图像数据"""
        mock_pil.open.side_effect = Exception("Corrupt image")

        generator = ThumbnailGenerator()
        result = generator.generate(b'corrupt_data', 'image/png', 'small')
        self.assertIsNone(result)

    @patch('thumbnail.PILImage')
    @patch('thumbnail.PILLOW_AVAILABLE', True)
    def test_generate_all_handles_partial_failure(self, mock_pil):
        """部分变体生成失败时仍返回成功的结果"""
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] > 2:
                raise Exception("Memory error")
            mock_img = MagicMock()
            mock_img.size = (800, 600)
            mock_img.mode = 'RGB'
            mock_thumb = MagicMock()
            mock_thumb.save = MagicMock()
            mock_img.copy.return_value = mock_thumb
            return mock_img

        mock_pil.open.side_effect = side_effect

        with patch('thumbnail.io.BytesIO') as mock_bio:
            mock_bio_instance = MagicMock()
            mock_bio_instance.getvalue.return_value = b'thumb_data'
            mock_bio.return_value = mock_bio_instance

            generator = ThumbnailGenerator()
            results = generator.generate_all(b'fake_data', 'image/png')
            # 至少应有部分成功
            self.assertGreaterEqual(len(results), 1)

    def test_output_format_jpeg(self):
        """JPEG 输出格式应正确"""
        generator = ThumbnailGenerator(output_format='JPEG')
        self.assertEqual(generator.output_format, 'JPEG')

    def test_output_format_png(self):
        """PNG 输出格式应正确"""
        generator = ThumbnailGenerator(output_format='PNG')
        self.assertEqual(generator.output_format, 'PNG')

    def test_output_format_webp(self):
        """WebP 输出格式应正确"""
        generator = ThumbnailGenerator(output_format='WEBP')
        self.assertEqual(generator.output_format, 'WEBP')

    @patch('thumbnail.PILImage')
    @patch('thumbnail.PILLOW_AVAILABLE', True)
    def test_rgba_image_converted_for_jpeg(self, mock_pil):
        """RGBA 图像在 JPEG 输出时应转换为 RGB"""
        mock_thumb = MagicMock()
        mock_thumb.size = (200, 150)
        mock_thumb.mode = 'RGBA'
        mock_thumb.thumbnail = MagicMock()
        mock_thumb.save = MagicMock()

        # convert 返回一个新的 RGB 图像
        mock_rgb = MagicMock()
        mock_rgb.save = MagicMock()

        mock_thumb.convert.return_value = mock_rgb

        mock_original = MagicMock()
        mock_original.size = (800, 600)
        mock_original.mode = 'RGBA'
        mock_original.copy.return_value = mock_thumb
        mock_pil.open.return_value = mock_original

        with patch('thumbnail.io.BytesIO') as mock_bio:
            mock_bio_instance = MagicMock()
            mock_bio_instance.getvalue.return_value = b'thumb_data'
            mock_bio.return_value = mock_bio_instance

            generator = ThumbnailGenerator(output_format='JPEG')
            result = generator.generate(b'fake_data', 'image/png', 'small')

        # 应该在副本上调用 convert('RGB') 因为 JPEG 不支持 alpha
        mock_thumb.convert.assert_called_with('RGB')


class TestThumbnailSizeDataclass(unittest.TestCase):
    """ThumbnailSize 数据类测试"""

    def test_thumbnail_size_creation(self):
        """ThumbnailSize 应正确创建"""
        size = ThumbnailSize(name='test', max_width=300, max_height=300)
        self.assertEqual(size.name, 'test')
        self.assertEqual(size.max_width, 300)
        self.assertEqual(size.max_height, 300)

    def test_thumbnail_size_immutable(self):
        """ThumbnailSize 应为不可变"""
        size = ThumbnailSize(name='test', max_width=300, max_height=300)
        with self.assertRaises(AttributeError):
            size.max_width = 400


if __name__ == '__main__':
    unittest.main()
