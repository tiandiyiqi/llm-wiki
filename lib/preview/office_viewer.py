"""KKFileView Office 文档转换模块

提供 Office 文档预览功能，支持可选的 KKFileView 后端。
- KKFileView 后端服务集成
- Office 文档转换 URL 生成
- 支持 Word/Excel/PPT
- 错误处理（KKFileView 不可用时降级提示）
- 可选依赖（KKFILEVIEW_AVAILABLE 标志）
"""

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urljoin

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    httpx = None  # type: ignore[assignment, misc]
    HTTPX_AVAILABLE = False

logger = logging.getLogger(__name__)

# KKFileView 可用性标志
KKFILEVIEW_AVAILABLE = HTTPX_AVAILABLE

# 默认 KKFileView 服务地址
DEFAULT_KKFILEVIEW_URL = 'http://localhost:8012'

# 支持的 Office MIME 类型
OFFICE_MIME_TYPES: Dict[str, str] = {
    # Word
    'application/msword': 'word',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'word',
    # Excel
    'application/vnd.ms-excel': 'excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'excel',
    # PPT
    'application/vnd.ms-powerpoint': 'ppt',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'ppt',
    # PDF
    'application/pdf': 'pdf',
}

# KKFileView 请求超时（秒）
KKFILEVIEW_TIMEOUT = 30


@dataclass(frozen=True)
class PreviewURL:
    """预览 URL（不可变）"""
    url: str
    format: str
    source_mime_type: str
    is_available: bool = True
    error: Optional[str] = None


class KKFileViewNotAvailableError(Exception):
    """KKFileView 不可用错误"""

    def __init__(self) -> None:
        super().__init__(
            'KKFileView service is not available. '
            'Ensure KKFileView is running or install httpx: pip install httpx'
        )


class OfficeViewerService:
    """Office 文档预览服务

    集成 KKFileView 后端，提供 Office 文档转换和预览 URL 生成。
    KKFileView 不可用时提供降级提示。
    """

    def __init__(
        self,
        kkfileview_url: str = DEFAULT_KKFILEVIEW_URL,
        timeout: int = KKFILEVIEW_TIMEOUT,
    ) -> None:
        """初始化 Office 文档预览服务

        Args:
            kkfileview_url: KKFileView 服务地址
            timeout: 请求超时时间（秒）
        """
        self._kkfileview_url = kkfileview_url.rstrip('/')
        self._timeout = timeout

    @property
    def is_available(self) -> bool:
        """KKFileView 是否可用"""
        return KKFILEVIEW_AVAILABLE

    def get_preview_url(
        self,
        file_url: str,
        source_mime_type: Optional[str] = None,
    ) -> PreviewURL:
        """生成预览 URL

        Args:
            file_url: 源文件 URL
            source_mime_type: 源文件 MIME 类型

        Returns:
            预览 URL 对象
        """
        if not KKFILEVIEW_AVAILABLE:
            return PreviewURL(
                url='',
                format=_get_format_from_mime(source_mime_type or ''),
                source_mime_type=source_mime_type or '',
                is_available=False,
                error='KKFileView service not available',
            )

        preview_format = _get_format_from_mime(source_mime_type or '')

        if preview_format == 'pdf':
            # PDF 直接返回原始 URL
            return PreviewURL(
                url=file_url,
                format='pdf',
                source_mime_type=source_mime_type or 'application/pdf',
                is_available=True,
            )

        # 构建 KKFileView 预览 URL
        encoded_url = _base64_encode_url(file_url)
        preview_url = f"{self._kkfileview_url}/onlinePreview?url={encoded_url}"

        return PreviewURL(
            url=preview_url,
            format=preview_format,
            source_mime_type=source_mime_type or '',
            is_available=True,
        )

    async def check_health(self) -> Dict[str, Any]:
        """检查 KKFileView 服务健康状态

        Returns:
            健康状态字典
        """
        if not HTTPX_AVAILABLE or httpx is None:
            return {
                'available': False,
                'error': 'httpx not installed',
            }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(f"{self._kkfileview_url}/")

                return {
                    'available': response.status_code == 200,
                    'status_code': response.status_code,
                    'url': self._kkfileview_url,
                }

        except Exception as e:
            return {
                'available': False,
                'error': str(e),
                'url': self._kkfileview_url,
            }

    async def convert_document(
        self,
        file_url: str,
        source_mime_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """转换 Office 文档为预览格式

        Args:
            file_url: 源文件 URL
            source_mime_type: 源文件 MIME 类型

        Returns:
            转换结果字典
        """
        if not KKFILEVIEW_AVAILABLE:
            return {
                'success': False,
                'error': 'KKFileView service not available',
                'fallback': self._get_fallback_message(source_mime_type),
            }

        preview = self.get_preview_url(file_url, source_mime_type)

        if not preview.is_available:
            return {
                'success': False,
                'error': preview.error,
                'fallback': self._get_fallback_message(source_mime_type),
            }

        return {
            'success': True,
            'preview_url': preview.url,
            'format': preview.format,
            'source_mime_type': preview.source_mime_type,
        }

    def _get_fallback_message(self, mime_type: Optional[str]) -> str:
        """获取降级提示信息

        Args:
            mime_type: MIME 类型

        Returns:
            降级提示文本
        """
        format_name = _get_format_from_mime(mime_type or '')

        messages = {
            'word': 'Word 文档预览需要 KKFileView 服务，请下载后查看',
            'excel': 'Excel 文档预览需要 KKFileView 服务，请下载后查看',
            'ppt': 'PPT 文档预览需要 KKFileView 服务，请下载后查看',
        }

        return messages.get(format_name, '文档预览服务不可用，请下载后查看')

    def get_supported_mime_types(self) -> List[str]:
        """获取支持的 MIME 类型列表

        Returns:
            MIME 类型列表
        """
        return list(OFFICE_MIME_TYPES.keys())


def _get_format_from_mime(mime_type: str) -> str:
    """从 MIME 类型获取预览格式

    Args:
        mime_type: MIME 类型

    Returns:
        预览格式字符串
    """
    return OFFICE_MIME_TYPES.get(mime_type, 'other')


def _base64_encode_url(url: str) -> str:
    """Base64 编码文件 URL（KKFileView 要求）

    Args:
        url: 原始 URL

    Returns:
        Base64 编码后的 URL
    """
    import base64

    encoded = base64.b64encode(url.encode('utf-8')).decode('utf-8')
    return quote(encoded, safe='')
