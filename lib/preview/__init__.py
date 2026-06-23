"""预览模块

提供文档预览功能，支持 PDF.js 前端查看、KKFileView Office 文档转换。
"""

from .office_viewer import OfficeViewerService, KKFILEVIEW_AVAILABLE
from .cache_manager import PreviewCacheManager

__all__ = [
    'OfficeViewerService',
    'KKFILEVIEW_AVAILABLE',
    'PreviewCacheManager',
]
