"""PaddleOCR 核心模块

提供 OCR 文字识别功能，支持可选的 PaddleOCR 后端。
- 可选导入 PaddleOCR（PADDLEOCR_AVAILABLE 标志）
- OCR 引擎初始化（懒加载单例模式）
- 图像预处理（灰度化、二值化、去噪）
- 文字识别（支持中英文）
- 结果后处理（文本清理、段落合并）
- 超时处理：单页 60s
- 无 PaddleOCR 时抛出明确错误
"""

import io
import logging
import re
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PaddleOCR = None  # type: ignore[assignment, misc]
    PADDLEOCR_AVAILABLE = False

try:
    from PIL import Image as PILImage
    from PIL import ImageFilter, ImageOps
    PILLOW_AVAILABLE = True
except ImportError:
    PILImage = None  # type: ignore[assignment, misc]
    ImageFilter = None  # type: ignore[assignment, misc]
    ImageOps = None  # type: ignore[assignment, misc]
    PILLOW_AVAILABLE = False

logger = logging.getLogger(__name__)

# 单页 OCR 超时时间（秒）
PAGE_TIMEOUT_SECONDS = 60

# 默认 OCR 语言
DEFAULT_LANGUAGE = 'chi_sim+eng'


@dataclass(frozen=True)
class OCRBox:
    """单个文字识别区域（不可变）"""
    text: str
    confidence: float
    x_min: float
    y_min: float
    x_max: float
    y_max: float


@dataclass(frozen=True)
class OCRPageResult:
    """单页 OCR 识别结果（不可变）"""
    text: str
    boxes: Tuple[OCRBox, ...] = field(default_factory=tuple)
    page_number: int = 1
    processing_time_ms: float = 0.0


@dataclass(frozen=True)
class OCRDocumentResult:
    """文档 OCR 识别结果（不可变）"""
    pages: Tuple[OCRPageResult, ...]
    full_text: str
    total_processing_time_ms: float = 0.0
    language: str = DEFAULT_LANGUAGE


class OCRError(Exception):
    """OCR 相关错误基类"""

    pass


class PaddleOCRNotAvailableError(OCRError):
    """PaddleOCR 不可用错误"""

    def __init__(self) -> None:
        super().__init__(
            'PaddleOCR is not installed. '
            'Install it with: pip install paddleocr paddlepaddle'
        )


class OCRTimeoutError(OCRError):
    """OCR 处理超时错误"""

    def __init__(self, timeout: int = PAGE_TIMEOUT_SECONDS) -> None:
        super().__init__(f'OCR processing timed out after {timeout}s')


class PaddleOCRService:
    """PaddleOCR 服务

    懒加载单例模式，支持图像预处理和文字识别。
    无 PaddleOCR 时抛出明确错误。
    """

    _instance: Optional['PaddleOCRService'] = None
    _lock = threading.Lock()

    def __new__(cls, *args: Any, **kwargs: Any) -> 'PaddleOCRService':
        """单例模式：确保全局只有一个实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(
        self,
        language: str = DEFAULT_LANGUAGE,
        use_gpu: bool = False,
        **kwargs: Any,
    ) -> None:
        """初始化 PaddleOCR 服务

        Args:
            language: OCR 识别语言
            use_gpu: 是否使用 GPU
            **kwargs: 其他 PaddleOCR 参数
        """
        if self._initialized:
            return

        self._language = language
        self._use_gpu = use_gpu
        self._kwargs = kwargs
        self._engine: Any = None
        self._initialized = True

    @property
    def is_available(self) -> bool:
        """PaddleOCR 是否可用"""
        return PADDLEOCR_AVAILABLE

    def _ensure_engine(self) -> Any:
        """懒加载 PaddleOCR 引擎

        Returns:
            PaddleOCR 实例

        Raises:
            PaddleOCRNotAvailableError: PaddleOCR 未安装
        """
        if not PADDLEOCR_AVAILABLE:
            raise PaddleOCRNotAvailableError()

        if self._engine is None:
            lang = self._language.replace('+', '_')
            self._engine = PaddleOCR(
                use_angle_cls=True,
                lang=lang,
                use_gpu=self._use_gpu,
                show_log=False,
                **self._kwargs,
            )
            logger.info(f"PaddleOCR engine initialized: lang={lang}, gpu={self._use_gpu}")

        return self._engine

    def preprocess_image(
        self,
        image_data: bytes,
        operations: Optional[List[str]] = None,
    ) -> bytes:
        """图像预处理

        Args:
            image_data: 原始图像数据
            operations: 预处理操作列表，默认 ['grayscale', 'denoise']

        Returns:
            处理后的图像数据

        Raises:
            OCRError: Pillow 不可用或处理失败
        """
        if not PILLOW_AVAILABLE:
            logger.warning("Pillow not available, skipping preprocessing")
            return image_data

        if operations is None:
            operations = ['grayscale', 'denoise']

        try:
            img = PILImage.open(io.BytesIO(image_data))

            for op in operations:
                img = self._apply_operation(img, op)

            output = io.BytesIO()
            img.save(output, format='PNG')
            return output.getvalue()

        except Exception as e:
            logger.warning(f"Image preprocessing failed: {e}")
            return image_data

    def _apply_operation(self, img: Any, operation: str) -> Any:
        """应用单个预处理操作

        Args:
            img: PIL Image 对象
            operation: 操作名称

        Returns:
            处理后的 PIL Image 对象
        """
        if operation == 'grayscale':
            return img.convert('L')

        if operation == 'binarize':
            gray = img.convert('L') if img.mode != 'L' else img
            return gray.point(lambda x: 255 if x > 128 else 0, '1')

        if operation == 'denoise':
            return img.filter(ImageFilter.MedianFilter(size=3))

        if operation == 'enhance_contrast':
            return ImageOps.autocontrast(img)

        logger.warning(f"Unknown preprocessing operation: {operation}")
        return img

    def recognize_image(
        self,
        image_data: bytes,
        language: Optional[str] = None,
        preprocess: bool = True,
    ) -> OCRPageResult:
        """识别单张图像中的文字

        Args:
            image_data: 图像二进制数据
            language: 识别语言（可选，覆盖默认值）
            preprocess: 是否进行预处理

        Returns:
            OCR 识别结果

        Raises:
            PaddleOCRNotAvailableError: PaddleOCR 未安装
            OCRTimeoutError: 处理超时
            OCRError: 其他 OCR 错误
        """
        import time

        start_time = time.monotonic()

        engine = self._ensure_engine()

        processed_data = image_data
        if preprocess and PILLOW_AVAILABLE:
            processed_data = self.preprocess_image(image_data)

        try:
            result = self._run_ocr_with_timeout(engine, processed_data)
        except OCRTimeoutError:
            raise
        except Exception as e:
            raise OCRError(f'OCR recognition failed: {e}') from e

        processing_time_ms = (time.monotonic() - start_time) * 1000

        return self._parse_ocr_result(result, processing_time_ms)

    def _run_ocr_with_timeout(self, engine: Any, image_data: bytes) -> Any:
        """带超时的 OCR 执行

        Args:
            engine: PaddleOCR 引擎
            image_data: 图像数据

        Returns:
            PaddleOCR 原始结果

        Raises:
            OCRTimeoutError: 处理超时
        """
        result_holder: List[Any] = []
        error_holder: List[Exception] = []

        def _ocr_worker() -> None:
            try:
                img_array = self._bytes_to_array(image_data)
                result = engine.ocr(img_array, cls=True)
                result_holder.append(result)
            except Exception as e:
                error_holder.append(e)

        thread = threading.Thread(target=_ocr_worker, daemon=True)
        thread.start()
        thread.join(timeout=PAGE_TIMEOUT_SECONDS)

        if thread.is_alive():
            raise OCRTimeoutError(timeout=PAGE_TIMEOUT_SECONDS)

        if error_holder:
            raise OCRError(f'OCR worker error: {error_holder[0]}')

        if not result_holder:
            raise OCRError('OCR returned no result')

        return result_holder[0]

    def _bytes_to_array(self, image_data: bytes) -> Any:
        """将图像字节转为 numpy 数组

        Args:
            image_data: 图像二进制数据

        Returns:
            numpy 数组
        """
        import numpy as np

        if PILLOW_AVAILABLE:
            img = PILImage.open(io.BytesIO(image_data))
            return np.array(img)

        raise OCRError('Pillow is required for image conversion')

    def _parse_ocr_result(
        self,
        result: Any,
        processing_time_ms: float,
        page_number: int = 1,
    ) -> OCRPageResult:
        """解析 PaddleOCR 原始结果

        Args:
            result: PaddleOCR 原始输出
            processing_time_ms: 处理耗时
            page_number: 页码

        Returns:
            解析后的 OCRPageResult
        """
        boxes: List[OCRBox] = []
        text_lines: List[str] = []

        if not result or not result[0]:
            return OCRPageResult(
                text='',
                boxes=tuple(),
                page_number=page_number,
                processing_time_ms=processing_time_ms,
            )

        for line in result[0]:
            if not line or len(line) < 2:
                continue

            bbox = line[0]
            text_info = line[1]

            if isinstance(text_info, (list, tuple)) and len(text_info) >= 2:
                text = str(text_info[0])
                confidence = float(text_info[1])
            else:
                text = str(text_info)
                confidence = 0.0

            if bbox and len(bbox) >= 4:
                x_coords = [p[0] for p in bbox]
                y_coords = [p[1] for p in bbox]
                box = OCRBox(
                    text=text,
                    confidence=confidence,
                    x_min=min(x_coords),
                    y_min=min(y_coords),
                    x_max=max(x_coords),
                    y_max=max(y_coords),
                )
                boxes.append(box)

            text_lines.append(text)

        full_text = _merge_paragraphs(text_lines)

        return OCRPageResult(
            text=full_text,
            boxes=tuple(boxes),
            page_number=page_number,
            processing_time_ms=processing_time_ms,
        )

    def recognize_document(
        self,
        image_pages: List[bytes],
        language: Optional[str] = None,
        preprocess: bool = True,
    ) -> OCRDocumentResult:
        """识别多页文档

        Args:
            image_pages: 每页图像的二进制数据列表
            language: 识别语言
            preprocess: 是否预处理

        Returns:
            文档 OCR 识别结果
        """
        import time

        start_time = time.monotonic()
        pages: List[OCRPageResult] = []

        for i, page_data in enumerate(image_pages, 1):
            try:
                page_result = self.recognize_image(
                    image_data=page_data,
                    language=language,
                    preprocess=preprocess,
                )
                pages.append(OCRPageResult(
                    text=page_result.text,
                    boxes=page_result.boxes,
                    page_number=i,
                    processing_time_ms=page_result.processing_time_ms,
                ))
            except OCRError as e:
                logger.error(f"OCR failed for page {i}: {e}")
                pages.append(OCRPageResult(
                    text='',
                    boxes=tuple(),
                    page_number=i,
                    processing_time_ms=0.0,
                ))

        total_time_ms = (time.monotonic() - start_time) * 1000
        full_text = '\n\n'.join(p.text for p in pages if p.text)

        return OCRDocumentResult(
            pages=tuple(pages),
            full_text=full_text,
            total_processing_time_ms=total_time_ms,
            language=language or self._language,
        )

    @classmethod
    def reset_instance(cls) -> None:
        """重置单例实例（仅用于测试）"""
        with cls._lock:
            cls._instance = None


def _merge_paragraphs(text_lines: List[str]) -> str:
    """合并文本行为段落

    规则：
    - 连续的短行合并为同一段落
    - 空行作为段落分隔
    - 去除多余空白

    Args:
        text_lines: 文本行列表

    Returns:
        合并后的文本
    """
    if not text_lines:
        return ''

    paragraphs: List[str] = []
    current_lines: List[str] = []

    for line in text_lines:
        stripped = line.strip()
        if not stripped:
            if current_lines:
                paragraphs.append(' '.join(current_lines))
                current_lines = []
        else:
            current_lines.append(stripped)

    if current_lines:
        paragraphs.append(' '.join(current_lines))

    return '\n\n'.join(paragraphs)


def clean_ocr_text(text: str) -> str:
    """清理 OCR 识别文本

    - 去除多余空白
    - 修复常见 OCR 错误
    - 规范化标点

    Args:
        text: 原始 OCR 文本

    Returns:
        清理后的文本
    """
    if not text:
        return ''

    # 去除行首行尾空白
    text = text.strip()

    # 合并连续空白为单个空格
    text = re.sub(r'[ \t]+', ' ', text)

    # 合并连续换行为双换行（段落分隔）
    text = re.sub(r'\n{3,}', '\n\n', text)

    # 修复常见 OCR 错误
    ocr_fixes = {
        'l1': 'll',
        '0O': 'OO',
        'rn': 'm',
    }

    # 仅在英文上下文中修复
    for wrong, correct in ocr_fixes.items():
        pattern = r'\b' + re.escape(wrong) + r'\b'
        text = re.sub(pattern, correct, text)

    # 规范化中文标点
    cn_punct_map = {
        ',': '，',
        '.': '。',
        '?': '？',
        '!': '！',
        ':': '：',
        ';': '；',
        '(': '（',
        ')': '）',
    }
    for en_punct, cn_punct in cn_punct_map.items():
        # 仅在中文上下文中替换
        text = re.sub(
            r'(?<=[一-鿿])' + re.escape(en_punct) + r'(?=[一-鿿])',
            cn_punct,
            text,
        )

    return text
