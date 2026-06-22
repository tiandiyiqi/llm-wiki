"""缩略图生成模块

使用 Pillow 生成多种尺寸的图像缩略图，支持：
- 3 种预设尺寸：small(200x200), medium(600x600), large(1200x1200)
- JPEG/PNG/WebP 输出格式
- 保持纵横比
- 异常图片容错处理
"""

import io
import logging
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

try:
    from PIL import Image as PILImage
    PILLOW_AVAILABLE = True
except ImportError:
    PILImage = None
    PILLOW_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ThumbnailSize:
    """缩略图尺寸定义（不可变）"""
    name: str
    max_width: int
    max_height: int


# 预设缩略图尺寸
THUMBNAIL_SIZES: Dict[str, ThumbnailSize] = {
    'small': ThumbnailSize(name='small', max_width=200, max_height=200),
    'medium': ThumbnailSize(name='medium', max_width=600, max_height=600),
    'large': ThumbnailSize(name='large', max_width=1200, max_height=1200),
}


def compute_thumbnail_dimensions(
    orig_width: int,
    orig_height: int,
    max_width: int,
    max_height: int,
) -> Tuple[int, int]:
    """计算缩略图尺寸，保持纵横比

    Args:
        orig_width: 原始宽度
        orig_height: 原始高度
        max_width: 最大宽度
        max_height: 最大高度

    Returns:
        (目标宽度, 目标高度) 元组
    """
    if max_width <= 0 or max_height <= 0:
        return (orig_width, orig_height)

    # 如果原图已经足够小，不放大
    if orig_width <= max_width and orig_height <= max_height:
        return (orig_width, orig_height)

    # 计算缩放比例
    width_ratio = max_width / orig_width
    height_ratio = max_height / orig_height
    ratio = min(width_ratio, height_ratio)

    new_width = int(orig_width * ratio)
    new_height = int(orig_height * ratio)

    # 确保最小尺寸为 1
    return (max(1, new_width), max(1, new_height))


class ThumbnailGenerator:
    """缩略图生成器

    生成多种尺寸的图像缩略图，保持纵横比。
    支持 JPEG/PNG/WebP 输出格式。
    """

    def __init__(
        self,
        output_format: str = 'PNG',
        quality: int = 85,
    ):
        """初始化缩略图生成器

        Args:
            output_format: 输出格式（PNG/JPEG/WEBP）
            quality: JPEG/WebP 输出质量（1-100）
        """
        self.output_format = output_format.upper()
        self.quality = max(1, min(100, quality))

    def generate(
        self,
        image_data: bytes,
        mime_type: str,
        size_name: str,
    ) -> Optional[bytes]:
        """生成单个缩略图

        Args:
            image_data: 原始图像二进制数据
            mime_type: 原始图像 MIME 类型
            size_name: 尺寸名称（small/medium/large）

        Returns:
            缩略图二进制数据，失败返回 None
        """
        if not PILLOW_AVAILABLE or PILImage is None:
            logger.warning("Pillow not available, cannot generate thumbnails")
            return None

        size_config = THUMBNAIL_SIZES.get(size_name)
        if not size_config:
            logger.warning(f"Unknown thumbnail size: {size_name}")
            return None

        try:
            return self._generate_thumbnail(
                image_data, size_config,
            )
        except Exception as e:
            logger.warning(f"Failed to generate {size_name} thumbnail: {e}")
            return None

    def generate_all(
        self,
        image_data: bytes,
        mime_type: str,
    ) -> Dict[str, bytes]:
        """生成所有预设尺寸的缩略图

        Args:
            image_data: 原始图像二进制数据
            mime_type: 原始图像 MIME 类型

        Returns:
            {size_name: thumbnail_bytes} 字典
        """
        results: Dict[str, bytes] = {}

        for size_name in THUMBNAIL_SIZES:
            try:
                thumbnail = self.generate(image_data, mime_type, size_name)
                if thumbnail is not None:
                    results[size_name] = thumbnail
            except Exception as e:
                logger.warning(f"Failed to generate {size_name} variant: {e}")

        return results

    def _generate_thumbnail(
        self,
        image_data: bytes,
        size_config: ThumbnailSize,
    ) -> bytes:
        """生成缩略图核心逻辑

        Args:
            image_data: 原始图像数据
            size_config: 尺寸配置

        Returns:
            缩略图二进制数据
        """
        img = PILImage.open(io.BytesIO(image_data))

        # 计算目标尺寸
        target_width, target_height = compute_thumbnail_dimensions(
            img.size[0], img.size[1],
            size_config.max_width, size_config.max_height,
        )

        # 创建副本并缩放
        thumb = img.copy()
        thumb.thumbnail((target_width, target_height), PILImage.LANCZOS)

        # 处理 RGBA → RGB 转换（JPEG 不支持 alpha 通道）
        if self.output_format == 'JPEG' and thumb.mode in ('RGBA', 'LA', 'P'):
            thumb = thumb.convert('RGB')

        # 保存到内存
        output = io.BytesIO()
        save_kwargs = {'format': self.output_format}

        if self.output_format == 'JPEG':
            save_kwargs['quality'] = self.quality
            save_kwargs['optimize'] = True
        elif self.output_format == 'WEBP':
            save_kwargs['quality'] = self.quality

        thumb.save(output, **save_kwargs)
        return output.getvalue()
