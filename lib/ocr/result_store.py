"""OCR 结果存储模块

提供 OCR 识别结果的持久化存储：
- OCR 文本结果存 PostgreSQL
- 结构化 JSON 存文件系统
- 复用 StorageInterface
"""

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# OCR 结果文件存储目录
DEFAULT_OCR_STORAGE_PATH = 'ocr_results'

# 内联存储阈值：JSON 结果 < 100KB 存数据库
INLINE_JSON_THRESHOLD = 100 * 1024


@dataclass(frozen=True)
class OCRStorageResult:
    """OCR 存储结果（不可变）"""
    task_id: int
    asset_id: int
    text_stored: bool
    json_stored: bool
    json_storage_type: str  # 'inline' | 'external'
    json_storage_path: Optional[str] = None
    error: Optional[str] = None


class OCRResultStore:
    """OCR 结果存储

    文本结果存 PostgreSQL，结构化 JSON 存文件系统或数据库。
    """

    def __init__(
        self,
        db: Any = None,
        external_storage: Any = None,
        storage_base_path: str = DEFAULT_OCR_STORAGE_PATH,
    ) -> None:
        """初始化 OCR 结果存储

        Args:
            db: 数据库管理器
            external_storage: 外部存储提供者（需提供 store/read/delete）
            storage_base_path: 外部存储基础路径
        """
        self.db = db
        self.external_storage = external_storage
        self.storage_base_path = storage_base_path

    async def store_result(
        self,
        task_id: int,
        asset_id: int,
        result_text: str,
        result_json: Optional[Dict[str, Any]] = None,
    ) -> OCRStorageResult:
        """存储 OCR 识别结果

        Args:
            task_id: OCR 任务 ID
            asset_id: 图像资产 ID
            result_text: 识别文本
            result_json: 结构化 JSON 结果

        Returns:
            存储结果
        """
        json_stored = False
        json_storage_type = 'inline'
        json_storage_path: Optional[str] = None

        # 存储文本到数据库
        text_stored = await self._store_text(task_id, result_text)

        # 存储 JSON 结果
        if result_json is not None:
            json_stored, json_storage_type, json_storage_path = (
                await self._store_json(task_id, asset_id, result_json)
            )

        return OCRStorageResult(
            task_id=task_id,
            asset_id=asset_id,
            text_stored=text_stored,
            json_stored=json_stored,
            json_storage_type=json_storage_type,
            json_storage_path=json_storage_path,
        )

    async def _store_text(self, task_id: int, result_text: str) -> bool:
        """存储文本结果到数据库

        Args:
            task_id: 任务 ID
            result_text: 识别文本

        Returns:
            是否成功
        """
        if not self.db:
            logger.warning("No database available, text not stored")
            return False

        try:
            await self.db.execute(
                '''
                UPDATE ocr_tasks
                SET result_text = $1, status = 'completed',
                    processing_completed_at = NOW()
                WHERE id = $2
                ''',
                result_text, task_id,
            )
            return True

        except Exception as e:
            logger.error(f"Failed to store OCR text: {e}")
            return False

    async def _store_json(
        self,
        task_id: int,
        asset_id: int,
        result_json: Dict[str, Any],
    ) -> tuple:
        """存储 JSON 结果

        小结果存数据库，大结果存外部存储。

        Args:
            task_id: 任务 ID
            asset_id: 资产 ID
            result_json: JSON 数据

        Returns:
            (是否成功, 存储类型, 存储路径)
        """
        json_str = json.dumps(result_json, ensure_ascii=False)
        json_size = len(json_str.encode('utf-8'))

        # 小结果直接存数据库
        if json_size <= INLINE_JSON_THRESHOLD or not self.external_storage:
            return await self._store_json_inline(task_id, result_json)

        # 大结果存外部存储
        return await self._store_json_external(task_id, asset_id, json_str)

    async def _store_json_inline(
        self,
        task_id: int,
        result_json: Dict[str, Any],
    ) -> tuple:
        """内联存储 JSON 到数据库

        Args:
            task_id: 任务 ID
            result_json: JSON 数据

        Returns:
            (是否成功, 'inline', None)
        """
        if not self.db:
            return False, 'inline', None

        try:
            await self.db.execute(
                '''
                UPDATE ocr_tasks
                SET result_json = $1
                WHERE id = $2
                ''',
                json.dumps(result_json, ensure_ascii=False),
                task_id,
            )
            return True, 'inline', None

        except Exception as e:
            logger.error(f"Failed to store OCR JSON inline: {e}")
            return False, 'inline', None

    async def _store_json_external(
        self,
        task_id: int,
        asset_id: int,
        json_str: str,
    ) -> tuple:
        """外部存储 JSON

        Args:
            task_id: 任务 ID
            asset_id: 资产 ID
            json_str: JSON 字符串

        Returns:
            (是否成功, 'external', 存储路径)
        """
        if not self.external_storage:
            return False, 'inline', None

        try:
            storage_path = _generate_json_storage_path(
                asset_id=asset_id,
                task_id=task_id,
            )

            await self.external_storage.store(
                storage_path,
                json_str.encode('utf-8'),
            )

            # 更新数据库记录中的路径引用
            if self.db:
                await self.db.execute(
                    '''
                    UPDATE ocr_tasks
                    SET result_json = $1
                    WHERE id = $2
                    ''',
                    json.dumps({
                        'storage_type': 'external',
                        'storage_path': storage_path,
                    }),
                    task_id,
                )

            return True, 'external', storage_path

        except Exception as e:
            logger.error(f"Failed to store OCR JSON externally: {e}")
            return False, 'external', None

    async def get_result(
        self,
        task_id: int,
    ) -> Optional[Dict[str, Any]]:
        """获取 OCR 结果

        Args:
            task_id: 任务 ID

        Returns:
            结果字典，不存在返回 None
        """
        if not self.db:
            return None

        try:
            record = await self.db.fetch_one(
                'SELECT * FROM ocr_tasks WHERE id = $1',
                task_id,
            )

            if not record:
                return None

            result = {
                'task_id': record.get('id'),
                'asset_id': record.get('asset_id'),
                'status': record.get('status'),
                'text': record.get('result_text'),
                'json': record.get('result_json'),
                'error': record.get('error_message'),
                'retry_count': record.get('retry_count', 0),
            }

            # 如果 JSON 存储在外部，读取并合并
            result_json = record.get('result_json')
            if isinstance(result_json, dict) and result_json.get('storage_type') == 'external':
                external_data = await self._load_external_json(
                    result_json.get('storage_path', '')
                )
                if external_data is not None:
                    result = {**result, 'json': external_data}

            return result

        except Exception as e:
            logger.error(f"Failed to get OCR result: {e}")
            return None

    async def _load_external_json(self, storage_path: str) -> Optional[Dict[str, Any]]:
        """从外部存储加载 JSON

        Args:
            storage_path: 存储路径

        Returns:
            JSON 数据，失败返回 None
        """
        if not self.external_storage or not storage_path:
            return None

        try:
            data = await self.external_storage.read(storage_path)
            if data:
                return json.loads(data.decode('utf-8'))
            return None

        except Exception as e:
            logger.error(f"Failed to load external JSON: {e}")
            return None

    async def get_results_by_asset(
        self,
        asset_id: int,
    ) -> List[Dict[str, Any]]:
        """获取资产的所有 OCR 结果

        Args:
            asset_id: 资产 ID

        Returns:
            结果列表
        """
        if not self.db:
            return []

        try:
            records = await self.db.fetch_all(
                '''
                SELECT * FROM ocr_tasks
                WHERE asset_id = $1
                ORDER BY created_at DESC
                ''',
                asset_id,
            )

            return [
                {
                    'task_id': r.get('id'),
                    'asset_id': r.get('asset_id'),
                    'status': r.get('status'),
                    'text': r.get('result_text'),
                    'created_at': r.get('created_at'),
                }
                for r in records
            ]

        except Exception as e:
            logger.error(f"Failed to get OCR results by asset: {e}")
            return []

    async def delete_result(self, task_id: int) -> bool:
        """删除 OCR 结果

        Args:
            task_id: 任务 ID

        Returns:
            是否成功
        """
        if not self.db:
            return False

        try:
            # 先检查是否有外部存储的 JSON
            record = await self.db.fetch_one(
                'SELECT result_json FROM ocr_tasks WHERE id = $1',
                task_id,
            )

            if record and isinstance(record.get('result_json'), dict):
                storage_path = record['result_json'].get('storage_path')
                if storage_path and self.external_storage:
                    await self.external_storage.delete(storage_path)

            # 删除数据库记录
            await self.db.execute(
                'DELETE FROM ocr_tasks WHERE id = $1',
                task_id,
            )

            return True

        except Exception as e:
            logger.error(f"Failed to delete OCR result: {e}")
            return False


def _generate_json_storage_path(asset_id: int, task_id: int) -> str:
    """生成 JSON 外部存储路径

    Args:
        asset_id: 资产 ID
        task_id: 任务 ID

    Returns:
        存储路径
    """
    now = datetime.now(timezone.utc)
    date_prefix = now.strftime('%Y/%m')
    unique_id = uuid.uuid4().hex[:8]

    return f"ocr_results/{asset_id}/{date_prefix}/{task_id}_{unique_id}.json"
