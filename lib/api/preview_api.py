"""预览 REST API

提供在线预览相关的 HTTP 端点处理方法。

端点：
- GET /api/preview/{atom_id} — 获取原子内容的预览 URL（旧版，db_mode）
- GET /api/preview/{atom_id}/cache — 获取预览缓存状态（旧版，db_mode）
- GET /api/files/<file_id>/download — 文件下载 URL（新版，通用）
- GET /api/files/<file_id>/preview-info — 预览元数据（新版，通用）
- POST /api/office/convert-to-pdf — Office 转 PDF（预留）

设计说明：
- PreviewAPIHandler 是普通业务处理类，不继承 HTTP 基类
- 每个方法返回 (response_dict, status_code)，由 web_server 的 _json_response 发送
- file_mode 下返回 501 错误（预览功能仅在数据库模式下可用）
- db_mode 下委托给 StorageInterface 的 get_preview_url / get_preview_cache
"""

import os
import mimetypes
import logging
from pathlib import Path
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


# ---------------------------------------------------------------------------
# 文件预览 API（新版，通用）
# ---------------------------------------------------------------------------


def _get_file_path(file_id: str) -> Path | None:
    """
    根据 file_id 获取文件路径

    当前为简化实现，直接映射到 uploads 目录。
    后续可接入数据库查询。
    """
    # 安全检查：防止路径遍历攻击
    if '..' in file_id or '/' in file_id or '\\' in file_id:
        return None

    # 从环境变量或默认配置获取文件存储目录
    upload_dir = os.getenv('UPLOAD_DIR', 'uploads')
    upload_path = Path(upload_dir)

    if not upload_path.exists():
        return None

    # 查找文件（支持带扩展名和不带扩展名）
    for f in upload_path.iterdir():
        if f.is_file():
            # 精确匹配文件名（不含扩展名）或完整文件名
            if f.stem == file_id or f.name == file_id:
                return f

    return None


def _get_mime_type(file_path: Path) -> str:
    """获取文件的 MIME 类型"""
    mime_type, _ = mimetypes.guess_type(str(file_path))
    return mime_type or 'application/octet-stream'


def _classify_preview_type(mime_type: str, extension: str) -> str:
    """
    根据文件类型分类预览类型

    返回值：
    - pdf：PDF 文档
    - office：Office 文档（docx/xlsx/pptx）
    - image：图片
    - video：视频
    - audio：音频
    - code：代码/文本
    - unsupported：不支持预览
    """
    extension = extension.lower()

    # PDF
    if extension == '.pdf' or 'pdf' in mime_type:
        return 'pdf'

    # Office
    office_exts = {'.docx', '.xlsx', '.pptx', '.doc', '.xls', '.ppt', '.odt', '.ods', '.odp'}
    if extension in office_exts or 'officedocument' in mime_type:
        return 'office'

    # 图片
    image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.tiff', '.heic', '.heif'}
    if extension in image_exts or mime_type.startswith('image/'):
        return 'image'

    # 视频
    video_exts = {'.mp4', '.webm', '.mov', '.avi', '.mkv', '.flv', '.m3u8'}
    if extension in video_exts or mime_type.startswith('video/'):
        return 'video'

    # 音频
    audio_exts = {'.mp3', '.wav', '.ogg', '.aac', '.m4a', '.flac'}
    if extension in audio_exts or mime_type.startswith('audio/'):
        return 'audio'

    # 代码/文本
    code_exts = {'.txt', '.md', '.json', '.yaml', '.yml', '.xml', '.csv',
                 '.js', '.ts', '.py', '.go', '.rs', '.java', '.c', '.cpp',
                 '.html', '.css', '.sql', '.sh'}
    if extension in code_exts or mime_type.startswith('text/'):
        return 'code'

    return 'unsupported'


def download_file(file_id: str) -> Tuple[Dict[str, Any], int, Optional[str], Optional[str]]:
    """
    文件下载端点

    提供文件下载 URL，供 Open File Viewer 或 BaseMetas FileView 访问。

    Returns:
        (response_dict, status_code, file_path, mime_type)
        如果成功，response_dict 为空，调用者应使用 file_path 发送文件
    """
    file_path = _get_file_path(file_id)

    if file_path is None:
        return (
            {'success': False, 'error': 'file_not_found', 'message': f'文件 {file_id} 不存在'},
            404,
            None,
            None
        )

    # TODO: 添加权限检查

    mime_type = _get_mime_type(file_path)
    return ({}, 200, str(file_path), mime_type)


def get_preview_info(file_id: str) -> Tuple[Dict[str, Any], int]:
    """
    预览元数据 API

    返回文件预览所需的元信息。
    """
    file_path = _get_file_path(file_id)

    if file_path is None:
        return (
            {'success': False, 'error': 'file_not_found', 'message': f'文件 {file_id} 不存在'},
            404
        )

    # TODO: 添加权限检查

    stat = file_path.stat()
    mime_type = _get_mime_type(file_path)
    extension = file_path.suffix
    preview_type = _classify_preview_type(mime_type, extension)

    return ({
        'success': True,
        'data': {
            'file_id': file_id,
            'file_name': file_path.name,
            'file_size': stat.st_size,
            'mime_type': mime_type,
            'extension': extension,
            'download_url': f'/api/files/{file_id}/download',
            'preview_type': preview_type
        }
    }, 200)


def convert_to_pdf() -> Tuple[Dict[str, Any], int]:
    """
    Office 转 PDF 接口（预留）

    复杂 Office 文档（文本框、绝对定位、自定义字体）需要后端转换服务。
    当前返回提示信息，后期对接 BaseMetas FileView。

    触发条件：
    - reason: "complex-docx" | "legacy-office" | "manual"
    """
    # 此函数需要 Flask request 上下文，在 web_server 中调用
    # 当前返回预留提示
    return ({
        'success': False,
        'error': 'complex_format_not_supported',
        'message': '该文档包含复杂排版，暂不支持在线预览。请联系管理员部署 BaseMetas FileView 服务。',
        'details': {
            'suggestion': '您可以下载文件后使用本地软件打开，或联系系统管理员启用高级预览服务。'
        }
    }, 503)
