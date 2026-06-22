"""图像存储与处理模块

提供图像上传、存储、缩略图生成和变体管理功能。
"""

from .image_storage import ImageStorageService
from .thumbnail import ThumbnailGenerator

__all__ = [
    'ImageStorageService',
    'ThumbnailGenerator',
]
