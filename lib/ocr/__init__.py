"""OCR 文字识别模块

提供图像 OCR 文字识别功能，支持可选的 PaddleOCR 后端。
"""

from .paddle_ocr import PaddleOCRService, PADDLEOCR_AVAILABLE
from .task_queue import OCRTaskQueue, CELERY_AVAILABLE, REDIS_AVAILABLE
from .result_store import OCRResultStore

__all__ = [
    'PaddleOCRService',
    'PADDLEOCR_AVAILABLE',
    'OCRTaskQueue',
    'CELERY_AVAILABLE',
    'REDIS_AVAILABLE',
    'OCRResultStore',
]
