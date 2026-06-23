"""OCR 任务队列模块

提供 OCR 任务队列功能，支持可选的 Celery + Redis 后端。
- 可选导入 Celery + Redis
- CELERY_AVAILABLE / REDIS_AVAILABLE 标志
- Celery 任务定义
- Redis broker 配置
- 重试策略：3 次指数退避（1s, 2s, 4s）
- 死信队列：超过重试次数标记为 dead_letter
- 超时处理：单页 60s，整文档 10min
- 无 Celery 时提供同步执行接口（降级为直接调用）
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

try:
    from celery import Celery
    CELERY_AVAILABLE = True
except ImportError:
    Celery = None  # type: ignore[assignment, misc]
    CELERY_AVAILABLE = False

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None  # type: ignore[assignment, misc]
    REDIS_AVAILABLE = False

from .paddle_ocr import (
    OCRError,
    OCRTimeoutError,
    PaddleOCRService,
    PADDLEOCR_AVAILABLE,
)

logger = logging.getLogger(__name__)

# 重试配置
DEFAULT_MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]  # 指数退避（秒）

# 超时配置
PAGE_TIMEOUT_SECONDS = 60
DOCUMENT_TIMEOUT_SECONDS = 600  # 10 分钟

# Celery 配置
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/1'


@dataclass(frozen=True)
class OCRTaskConfig:
    """OCR 任务配置（不可变）"""
    language: str = 'chi_sim+eng'
    max_retries: int = DEFAULT_MAX_RETRIES
    page_timeout: int = PAGE_TIMEOUT_SECONDS
    document_timeout: int = DOCUMENT_TIMEOUT_SECONDS
    preprocess: bool = True


@dataclass(frozen=True)
class OCRTaskResult:
    """OCR 任务结果（不可变）"""
    task_id: str
    asset_id: int
    status: str
    result_text: Optional[str] = None
    result_json: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    processing_time_ms: float = 0.0


class OCRTaskQueue:
    """OCR 任务队列

    支持 Celery 异步和同步两种执行模式。
    无 Celery 时降级为同步直接调用。
    """

    def __init__(
        self,
        db: Any = None,
        celery_app: Any = None,
        redis_client: Any = None,
        config: Optional[OCRTaskConfig] = None,
    ) -> None:
        """初始化 OCR 任务队列

        Args:
            db: 数据库管理器
            celery_app: Celery 应用实例（可选）
            redis_client: Redis 客户端（可选）
            config: OCR 任务配置
        """
        self.db = db
        self._celery_app = celery_app
        self._redis_client = redis_client
        self._config = config or OCRTaskConfig()
        self._ocr_service: Optional[PaddleOCRService] = None

    @property
    def is_async(self) -> bool:
        """是否为异步模式（Celery 可用）"""
        return CELERY_AVAILABLE and self._celery_app is not None

    @property
    def is_redis_available(self) -> bool:
        """Redis 是否可用"""
        return REDIS_AVAILABLE and self._redis_client is not None

    def _get_ocr_service(self) -> PaddleOCRService:
        """获取 OCR 服务实例

        Returns:
            PaddleOCRService 实例
        """
        if self._ocr_service is None:
            self._ocr_service = PaddleOCRService(
                language=self._config.language,
            )
        return self._ocr_service

    async def submit_task(
        self,
        asset_id: int,
        image_data: bytes,
        user_id: Optional[str] = None,
        language: Optional[str] = None,
    ) -> OCRTaskResult:
        """提交 OCR 任务

        Args:
            asset_id: 图像资产 ID
            image_data: 图像二进制数据
            user_id: 提交用户 ID
            language: OCR 语言（可选）

        Returns:
            OCR 任务结果
        """
        task_id = _generate_task_id(asset_id)

        # 写入数据库任务记录
        if self.db:
            await self._create_task_record(
                asset_id=asset_id,
                task_id=task_id,
                user_id=user_id,
                language=language or self._config.language,
            )

        if self.is_async:
            return await self._submit_async_task(
                task_id=task_id,
                asset_id=asset_id,
                image_data=image_data,
                language=language,
            )

        return await self._execute_sync_task(
            task_id=task_id,
            asset_id=asset_id,
            image_data=image_data,
            language=language,
        )

    async def _submit_async_task(
        self,
        task_id: str,
        asset_id: int,
        image_data: bytes,
        language: Optional[str] = None,
    ) -> OCRTaskResult:
        """提交异步 Celery 任务

        Args:
            task_id: 任务 ID
            asset_id: 资产 ID
            image_data: 图像数据
            language: OCR 语言

        Returns:
            OCR 任务结果（pending 状态）
        """
        try:
            self._celery_app.send_task(
                'ocr.process_image',
                args=[asset_id, image_data, language],
                kwargs={'task_id': task_id},
                task_id=task_id,
                retry=True,
                retry_policy={
                    'max_retries': self._config.max_retries,
                    'interval_start': RETRY_DELAYS[0],
                    'interval_step': 1,
                    'interval_max': RETRY_DELAYS[-1],
                },
                soft_time_limit=self._config.document_timeout,
                time_limit=self._config.document_timeout + 30,
            )

            logger.info(f"Submitted async OCR task: {task_id}")

            return OCRTaskResult(
                task_id=task_id,
                asset_id=asset_id,
                status='pending',
            )

        except Exception as e:
            logger.error(f"Failed to submit async task: {e}")
            return OCRTaskResult(
                task_id=task_id,
                asset_id=asset_id,
                status='failed',
                error_message=f'Task submission failed: {e}',
            )

    async def _execute_sync_task(
        self,
        task_id: str,
        asset_id: int,
        image_data: bytes,
        language: Optional[str] = None,
    ) -> OCRTaskResult:
        """同步执行 OCR 任务（降级模式）

        Args:
            task_id: 任务 ID
            asset_id: 资产 ID
            image_data: 图像数据
            language: OCR 语言

        Returns:
            OCR 任务结果
        """
        if not PADDLEOCR_AVAILABLE:
            error_msg = 'PaddleOCR not available, cannot execute OCR task'
            logger.error(error_msg)

            if self.db:
                await self._update_task_record(
                    task_id=task_id,
                    status='failed',
                    error_message=error_msg,
                )

            return OCRTaskResult(
                task_id=task_id,
                asset_id=asset_id,
                status='failed',
                error_message=error_msg,
            )

        retry_count = 0
        last_error: Optional[str] = None

        while retry_count <= self._config.max_retries:
            try:
                if self.db:
                    await self._update_task_record(
                        task_id=task_id,
                        status='processing',
                    )

                result = await self._do_ocr(
                    image_data=image_data,
                    language=language,
                )

                if self.db:
                    await self._update_task_record(
                        task_id=task_id,
                        status='completed',
                        result_text=result.get('text'),
                        result_json=result.get('json'),
                    )

                return OCRTaskResult(
                    task_id=task_id,
                    asset_id=asset_id,
                    status='completed',
                    result_text=result.get('text'),
                    result_json=result.get('json'),
                    retry_count=retry_count,
                    processing_time_ms=result.get('processing_time_ms', 0.0),
                )

            except OCRTimeoutError as e:
                retry_count += 1
                last_error = f'OCR timeout: {e}'

                if retry_count <= self._config.max_retries:
                    delay = RETRY_DELAYS[min(retry_count - 1, len(RETRY_DELAYS) - 1)]
                    logger.warning(
                        f"OCR timeout, retry {retry_count}/{self._config.max_retries} "
                        f"after {delay}s"
                    )
                    time.sleep(delay)
                continue

            except OCRError as e:
                retry_count += 1
                last_error = str(e)

                if retry_count <= self._config.max_retries:
                    delay = RETRY_DELAYS[min(retry_count - 1, len(RETRY_DELAYS) - 1)]
                    logger.warning(
                        f"OCR error, retry {retry_count}/{self._config.max_retries} "
                        f"after {delay}s: {e}"
                    )
                    time.sleep(delay)
                continue

        # 超过重试次数，标记为死信
        dead_letter_msg = (
            f'Exceeded max retries ({self._config.max_retries}): {last_error}'
        )
        logger.error(f"OCR task {task_id} moved to dead_letter: {dead_letter_msg}")

        if self.db:
            await self._update_task_record(
                task_id=task_id,
                status='dead_letter',
                error_message=dead_letter_msg,
                retry_count=retry_count,
            )

        return OCRTaskResult(
            task_id=task_id,
            asset_id=asset_id,
            status='dead_letter',
            error_message=dead_letter_msg,
            retry_count=retry_count,
        )

    async def _do_ocr(
        self,
        image_data: bytes,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """执行 OCR 识别

        Args:
            image_data: 图像数据
            language: OCR 语言

        Returns:
            识别结果字典

        Raises:
            OCRError: OCR 识别失败
        """
        service = self._get_ocr_service()
        page_result = service.recognize_image(
            image_data=image_data,
            language=language,
            preprocess=self._config.preprocess,
        )

        import json

        result_json = None
        if page_result.boxes:
            result_json = {
                'boxes': [
                    {
                        'text': box.text,
                        'confidence': box.confidence,
                        'bbox': [box.x_min, box.y_min, box.x_max, box.y_max],
                    }
                    for box in page_result.boxes
                ],
                'page_number': page_result.page_number,
            }

        return {
            'text': page_result.text,
            'json': result_json,
            'processing_time_ms': page_result.processing_time_ms,
        }

    async def _create_task_record(
        self,
        asset_id: int,
        task_id: str,
        user_id: Optional[str] = None,
        language: str = 'chi_sim+eng',
    ) -> None:
        """创建数据库任务记录

        Args:
            asset_id: 资产 ID
            task_id: 任务 ID
            user_id: 用户 ID
            language: OCR 语言
        """
        if not self.db:
            return

        try:
            await self.db.execute(
                '''
                INSERT INTO ocr_tasks (
                    asset_id, status, language, created_by
                ) VALUES ($1, $2, $3, $4)
                ''',
                asset_id, 'pending', language, user_id,
            )
        except Exception as e:
            logger.error(f"Failed to create OCR task record: {e}")

    async def _update_task_record(
        self,
        task_id: str,
        status: str,
        result_text: Optional[str] = None,
        result_json: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        retry_count: Optional[int] = None,
    ) -> None:
        """更新数据库任务记录

        Args:
            task_id: 任务 ID
            status: 任务状态
            result_text: 识别文本
            result_json: 识别 JSON
            error_message: 错误信息
            retry_count: 重试次数
        """
        if not self.db:
            return

        try:
            import json

            sets: List[str] = ['status = $2', 'updated_at = NOW()']
            params: List[Any] = [int(task_id.split('-')[-1]) if '-' in task_id else 0, status]
            param_idx = 3

            if result_text is not None:
                sets.append(f'result_text = ${param_idx}')
                params.append(result_text)
                param_idx += 1

            if result_json is not None:
                sets.append(f'result_json = ${param_idx}')
                params.append(json.dumps(result_json))
                param_idx += 1

            if error_message is not None:
                sets.append(f'error_message = ${param_idx}')
                params.append(error_message)
                param_idx += 1

            if retry_count is not None:
                sets.append(f'retry_count = ${param_idx}')
                params.append(retry_count)
                param_idx += 1

            if status == 'processing':
                sets.append('processing_started_at = NOW()')

            if status in ('completed', 'failed', 'dead_letter'):
                sets.append('processing_completed_at = NOW()')

            sql = f"UPDATE ocr_tasks SET {', '.join(sets)} WHERE id = $1"
            await self.db.execute(sql, *params)

        except Exception as e:
            logger.error(f"Failed to update OCR task record: {e}")

    async def get_task_status(self, task_id: str) -> Optional[OCRTaskResult]:
        """获取任务状态

        Args:
            task_id: 任务 ID

        Returns:
            任务结果，不存在返回 None
        """
        if not self.db:
            return None

        try:
            record = await self.db.fetch_one(
                'SELECT * FROM ocr_tasks WHERE id = $1',
                int(task_id) if task_id.isdigit() else 0,
            )

            if not record:
                return None

            return OCRTaskResult(
                task_id=str(record.get('id', task_id)),
                asset_id=record.get('asset_id', 0),
                status=record.get('status', 'pending'),
                result_text=record.get('result_text'),
                result_json=record.get('result_json'),
                error_message=record.get('error_message'),
                retry_count=record.get('retry_count', 0),
            )

        except Exception as e:
            logger.error(f"Failed to get task status: {e}")
            return None

    async def retry_dead_letter(self, task_id: str) -> OCRTaskResult:
        """重试死信任务

        Args:
            task_id: 任务 ID

        Returns:
            重试结果
        """
        if self.db:
            await self._update_task_record(
                task_id=task_id,
                status='pending',
                retry_count=0,
                error_message=None,
            )

        return OCRTaskResult(
            task_id=task_id,
            asset_id=0,
            status='pending',
        )


def create_celery_app(broker_url: str = CELERY_BROKER_URL) -> Any:
    """创建 Celery 应用实例

    Args:
        broker_url: Redis broker URL

    Returns:
        Celery 实例，不可用时返回 None
    """
    if not CELERY_AVAILABLE:
        logger.warning("Celery not available, async task queue disabled")
        return None

    try:
        app = Celery(
            'llm_wiki_ocr',
            broker=broker_url,
            backend=CELERY_RESULT_BACKEND,
        )

        app.conf.update(
            task_serializer='json',
            result_serializer='json',
            accept_content=['json'],
            timezone='UTC',
            enable_utc=True,
            task_track_started=True,
            task_acks_late=True,
            worker_prefetch_multiplier=1,
        )

        return app

    except Exception as e:
        logger.error(f"Failed to create Celery app: {e}")
        return None


def _generate_task_id(asset_id: int) -> str:
    """生成任务 ID

    Args:
        asset_id: 资产 ID

    Returns:
        任务 ID 字符串
    """
    import uuid

    return f"ocr-{asset_id}-{uuid.uuid4().hex[:8]}"
