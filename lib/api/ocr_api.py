"""OCR REST API 处理器

提供 OCR 相关的 HTTP 端点处理方法，由 web_server.py 路由器调用。

端点：
- POST /api/ocr/submit — 提交 OCR 任务
- GET  /api/ocr/tasks/{task_id} — 查询任务状态/结果
- GET  /api/ocr/assets/{asset_id} — 查询资产的所有 OCR 结果
"""

import logging
from typing import Any, Dict, Optional, Tuple

from ..core.storage_interface import StorageInterface

logger = logging.getLogger(__name__)

# file_mode 下 OCR 不可用的错误响应
_FILE_MODE_ERROR: Dict[str, Any] = {
    'error': 'OCR 功能仅在数据库模式下可用',
    'mode': 'file',
}
_FILE_MODE_STATUS = 501


class OCRAPIHandler:
    """OCR API 处理器

    普通业务处理类，不继承任何 HTTP 基类。
    每个方法返回 (response_dict, status_code) 元组，
    由 web_server 的 _json_response 发送。

    当 storage.mode == 'file' 时，所有端点返回 501。
    当 storage.mode == 'db' 时，委托给 storage 的 OCR 方法。
    """

    def __init__(self, storage: 'StorageInterface'):
        """初始化 OCR API 处理器

        Args:
            storage: 存储接口实例（FileSystemStorage 或 DatabaseStorage）
        """
        self.storage = storage

    def _check_mode(self) -> Optional[Tuple[Dict[str, Any], int]]:
        """检查存储模式是否支持 OCR

        Returns:
            若为 file_mode，返回错误响应元组；若为 db_mode，返回 None
        """
        if self.storage.mode == 'file':
            return (_FILE_MODE_ERROR, _FILE_MODE_STATUS)
        return None

    def submit(self, data: dict, user_id: str = None) -> Tuple[Dict[str, Any], int]:
        """提交 OCR 任务

        委托给 storage.submit_ocr_task()。

        Args:
            data: 请求体字典，需包含：
                - asset_id (int): 资产 ID
                - image_data (bytes): 图片二进制数据
                - language (str, 可选): OCR 语言
            user_id: 提交用户 ID

        Returns:
            (response_dict, status_code) 元组
        """
        mode_error = self._check_mode()
        if mode_error is not None:
            return mode_error

        # 参数校验
        asset_id = data.get('asset_id')
        image_data = data.get('image_data')

        if asset_id is None:
            return ({'error': '缺少必填参数: asset_id'}, 400)
        if image_data is None:
            return ({'error': '缺少必填参数: image_data'}, 400)

        try:
            from ..web_server import _run_async

            result = _run_async(
                self.storage.submit_ocr_task(
                    asset_id=int(asset_id),
                    image_data=image_data,
                    user_id=user_id,
                    language=data.get('language'),
                )
            )

            logger.info(
                "OCR task submitted: asset_id=%s, user=%s",
                asset_id,
                user_id,
            )
            return (result, 201)

        except Exception as e:
            logger.error("Failed to submit OCR task: %s", e)
            return ({'error': f'提交 OCR 任务失败: {e}'}, 500)

    def get_task(self, task_id: int) -> Tuple[Dict[str, Any], int]:
        """查询 OCR 任务状态/结果

        委托给 storage.get_ocr_result()。

        Args:
            task_id: OCR 任务 ID

        Returns:
            (response_dict, status_code) 元组
        """
        mode_error = self._check_mode()
        if mode_error is not None:
            return mode_error

        try:
            from ..web_server import _run_async

            result = _run_async(
                self.storage.get_ocr_result(task_id=int(task_id))
            )

            if result is None:
                return ({'error': f'OCR 任务不存在: {task_id}'}, 404)

            return (result, 200)

        except Exception as e:
            logger.error("Failed to get OCR task %s: %s", task_id, e)
            return ({'error': f'查询 OCR 任务失败: {e}'}, 500)

    def get_by_asset(self, asset_id: int) -> Tuple[Dict[str, Any], int]:
        """查询资产的所有 OCR 结果

        委托给 storage.get_ocr_results_by_asset()。

        Args:
            asset_id: 资产 ID

        Returns:
            (response_dict, status_code) 元组
        """
        mode_error = self._check_mode()
        if mode_error is not None:
            return mode_error

        try:
            from ..web_server import _run_async

            results = _run_async(
                self.storage.get_ocr_results_by_asset(asset_id=int(asset_id))
            )

            return ({'results': results, 'count': len(results)}, 200)

        except Exception as e:
            logger.error(
                "Failed to get OCR results for asset %s: %s",
                asset_id,
                e,
            )
            return ({'error': f'查询资产 OCR 结果失败: {e}'}, 500)
