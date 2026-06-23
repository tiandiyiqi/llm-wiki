"""预览 REST API

提供在线预览相关的 HTTP 端点处理方法。

端点：
- GET /api/preview/{atom_id} — 获取原子内容的预览 URL
- GET /api/preview/{atom_id}/cache — 获取预览缓存状态

设计说明：
- PreviewAPIHandler 是普通业务处理类，不继承 HTTP 基类
- 每个方法返回 (response_dict, status_code)，由 web_server 的 _json_response 发送
- file_mode 下返回 501 错误（预览功能仅在数据库模式下可用）
- db_mode 下委托给 StorageInterface 的 get_preview_url / get_preview_cache
"""

import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class PreviewAPIHandler:
    """预览 API 处理器

    提供在线预览的 REST API 端点处理方法。
    不继承任何 HTTP 基类，仅返回 (response_dict, status_code) 元组，
    由 web_server 的 _json_response 统一发送。
    """

    def __init__(self, storage: Any):
        """初始化预览 API 处理器

        Args:
            storage: StorageInterface 实例（FileSystemStorage 或 DatabaseStorage）
        """
        self.storage = storage

    def _check_db_mode(self) -> Optional[Tuple[Dict[str, Any], int]]:
        """检查当前存储模式是否为 db_mode

        Returns:
            如果为 file_mode，返回错误响应元组；
            如果为 db_mode，返回 None（表示检查通过）
        """
        if self.storage.mode == 'file':
            return (
                {
                    'error': '预览功能仅在数据库模式下可用',
                    'mode': 'file',
                },
                501,
            )
        return None

    def get_preview(
        self,
        atom_id: str,
        format: str = 'html',
        source_mime_type: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], int]:
        """获取预览 URL

        Args:
            atom_id: 知识原子 ID
            format: 预览格式（html/pdf），默认 html
            source_mime_type: 源文件 MIME 类型（可选）

        Returns:
            (response_dict, status_code) 元组
        """
        # file_mode 检查
        mode_error = self._check_db_mode()
        if mode_error is not None:
            return mode_error

        try:
            numeric_id = int(atom_id)
        except (ValueError, TypeError):
            return (
                {
                    'error': f'无效的原子 ID: {atom_id}',
                    'atom_id': atom_id,
                },
                400,
            )

        try:
            from ..web_server import _run_async

            result = _run_async(
                self.storage.get_preview_url(
                    atom_id=numeric_id,
                    format=format,
                    source_mime_type=source_mime_type,
                )
            )

            if result is None:
                return (
                    {
                        'error': f'未找到原子 {atom_id} 的预览',
                        'atom_id': atom_id,
                    },
                    404,
                )

            return {
                'success': True,
                'atom_id': numeric_id,
                **result,
            }, 200

        except Exception as e:
            logger.error("Failed to get preview for atom %s: %s", atom_id, e)
            return (
                {
                    'error': f'获取预览失败: {str(e)}',
                    'atom_id': atom_id,
                },
                500,
            )

    def get_cache(
        self,
        atom_id: str,
        format: str = 'html',
    ) -> Tuple[Dict[str, Any], int]:
        """获取预览缓存状态

        Args:
            atom_id: 知识原子 ID
            format: 预览格式（html/pdf），默认 html

        Returns:
            (response_dict, status_code) 元组
        """
        # file_mode 检查
        mode_error = self._check_db_mode()
        if mode_error is not None:
            return mode_error

        try:
            numeric_id = int(atom_id)
        except (ValueError, TypeError):
            return (
                {
                    'error': f'无效的原子 ID: {atom_id}',
                    'atom_id': atom_id,
                },
                400,
            )

        try:
            from ..web_server import _run_async

            result = _run_async(
                self.storage.get_preview_cache(
                    atom_id=numeric_id,
                    format=format,
                )
            )

            if result is None:
                return (
                    {
                        'cached': False,
                        'atom_id': numeric_id,
                        'format': format,
                        'message': '缓存不存在',
                    },
                    200,
                )

            return {
                'success': True,
                'cached': True,
                'atom_id': numeric_id,
                **result,
            }, 200

        except Exception as e:
            logger.error("Failed to get preview cache for atom %s: %s", atom_id, e)
            return (
                {
                    'error': f'获取预览缓存失败: {str(e)}',
                    'atom_id': atom_id,
                },
                500,
            )
