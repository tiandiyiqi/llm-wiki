"""
文件预览 API 单元测试

测试 PLAN-008 新增的文件预览 API：
- /api/files/<file_id>/download
- /api/files/<file_id>/preview-info
- /api/office/convert-to-pdf
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# 导入被测模块
from lib.api.preview_api import (
    _get_file_path,
    _get_mime_type,
    _classify_preview_type,
    download_file,
    get_preview_info,
    convert_to_pdf,
)


class TestGetFilePath:
    """测试 _get_file_path 函数"""

    def test_path_traversal_blocked(self, tmp_path):
        """路径遍历攻击应被阻止"""
        # 创建测试目录
        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir()
        (upload_dir / "test.txt").write_text("content")

        with patch.dict(os.environ, {"UPLOAD_DIR": str(upload_dir)}):
            # 尝试路径遍历
            assert _get_file_path("../../../etc/passwd") is None
            assert _get_file_path("..%2F..%2F..%2Fetc%2Fpasswd") is None
            assert _get_file_path("subdir/../../../etc/passwd") is None

    def test_find_file_by_stem(self, tmp_path):
        """按文件名（不含扩展名）查找"""
        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir()
        (upload_dir / "document.pdf").write_text("pdf content")

        with patch.dict(os.environ, {"UPLOAD_DIR": str(upload_dir)}):
            result = _get_file_path("document")
            assert result is not None
            assert result.name == "document.pdf"

    def test_find_file_by_full_name(self, tmp_path):
        """按完整文件名查找"""
        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir()
        (upload_dir / "report.xlsx").write_text("excel content")

        with patch.dict(os.environ, {"UPLOAD_DIR": str(upload_dir)}):
            result = _get_file_path("report.xlsx")
            assert result is not None
            assert result.name == "report.xlsx"

    def test_file_not_found(self, tmp_path):
        """文件不存在"""
        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir()

        with patch.dict(os.environ, {"UPLOAD_DIR": str(upload_dir)}):
            assert _get_file_path("nonexistent") is None


class TestGetMimeType:
    """测试 _get_mime_type 函数"""

    def test_pdf_mime_type(self, tmp_path):
        """PDF MIME 类型"""
        file_path = tmp_path / "document.pdf"
        assert _get_mime_type(file_path) == "application/pdf"

    def test_image_mime_type(self, tmp_path):
        """图片 MIME 类型"""
        assert _get_mime_type(tmp_path / "image.jpg") == "image/jpeg"
        assert _get_mime_type(tmp_path / "image.png") == "image/png"

    def test_unknown_mime_type(self, tmp_path):
        """未知扩展名返回 MIME 类型（可能是 system-specific）"""
        file_path = tmp_path / "file.xyz"
        # .xyz 的 MIME 类型在不同系统可能不同（chemical/x-xyz 或 application/octet-stream）
        mime = _get_mime_type(file_path)
        # 只要返回了一个有效的 MIME 类型即可
        assert mime is not None
        assert isinstance(mime, str)


class TestClassifyPreviewType:
    """测试 _classify_preview_type 函数"""

    def test_pdf_classification(self):
        """PDF 分类"""
        assert _classify_preview_type("application/pdf", ".pdf") == "pdf"
        assert _classify_preview_type("application/pdf", ".PDF") == "pdf"

    def test_office_classification(self):
        """Office 分类"""
        assert _classify_preview_type("application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".docx") == "office"
        assert _classify_preview_type("application/octet-stream", ".xlsx") == "office"
        assert _classify_preview_type("application/octet-stream", ".pptx") == "office"

    def test_image_classification(self):
        """图片分类"""
        assert _classify_preview_type("image/jpeg", ".jpg") == "image"
        assert _classify_preview_type("image/png", ".png") == "image"
        assert _classify_preview_type("application/octet-stream", ".webp") == "image"

    def test_video_classification(self):
        """视频分类"""
        assert _classify_preview_type("video/mp4", ".mp4") == "video"
        assert _classify_preview_type("application/octet-stream", ".webm") == "video"

    def test_audio_classification(self):
        """音频分类"""
        assert _classify_preview_type("audio/mpeg", ".mp3") == "audio"
        assert _classify_preview_type("application/octet-stream", ".wav") == "audio"

    def test_code_classification(self):
        """代码/文本分类"""
        assert _classify_preview_type("text/plain", ".txt") == "code"
        assert _classify_preview_type("application/octet-stream", ".md") == "code"
        assert _classify_preview_type("application/octet-stream", ".json") == "code"
        assert _classify_preview_type("application/octet-stream", ".py") == "code"

    def test_unsupported_classification(self):
        """不支持预览"""
        assert _classify_preview_type("application/octet-stream", ".exe") == "unsupported"
        assert _classify_preview_type("application/octet-stream", ".zip") == "unsupported"


class TestDownloadFile:
    """测试 download_file 函数"""

    def test_file_not_found(self):
        """文件不存在"""
        result, status, path, mime = download_file("nonexistent")
        assert status == 404
        assert result["error"] == "file_not_found"

    def test_file_found(self, tmp_path):
        """文件存在"""
        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir()
        (upload_dir / "test.pdf").write_bytes(b"pdf content")

        with patch.dict(os.environ, {"UPLOAD_DIR": str(upload_dir)}):
            result, status, path, mime = download_file("test")
            assert status == 200
            assert path is not None
            assert "test.pdf" in path
            assert mime == "application/pdf"


class TestGetPreviewInfo:
    """测试 get_preview_info 函数"""

    def test_file_not_found(self):
        """文件不存在"""
        result, status = get_preview_info("nonexistent")
        assert status == 404
        assert result["error"] == "file_not_found"

    def test_preview_info_success(self, tmp_path):
        """获取预览信息成功"""
        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir()
        (upload_dir / "document.pdf").write_bytes(b"pdf content")

        with patch.dict(os.environ, {"UPLOAD_DIR": str(upload_dir)}):
            result, status = get_preview_info("document")
            assert status == 200
            assert result["success"] is True
            assert result["data"]["file_name"] == "document.pdf"
            assert result["data"]["preview_type"] == "pdf"
            assert "download_url" in result["data"]


class TestConvertToPdf:
    """测试 convert_to_pdf 函数"""

    def test_returns_503(self):
        """当前返回 503 服务不可用"""
        result, status = convert_to_pdf()
        assert status == 503
        assert result["error"] == "complex_format_not_supported"
        assert "BaseMetas FileView" in result["message"]

    def test_contains_suggestion(self):
        """包含友好的用户建议"""
        result, _ = convert_to_pdf()
        assert "suggestion" in result["details"]
