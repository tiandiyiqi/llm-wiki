"""路径验证工具的单元测试."""

import os
import tempfile
from pathlib import Path

import pytest

from lib.utils.path_validator import PathValidator


class TestPathValidator:
    """PathValidator 测试类."""

    @pytest.fixture
    def temp_dir(self):
        """创建临时测试目录."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建一些测试文件和目录
            base = Path(tmpdir)
            (base / "safe_dir").mkdir()
            (base / "safe_dir" / "file1.md").write_text("content1")
            (base / "safe_dir" / "subdir").mkdir()
            (base / "safe_dir" / "subdir" / "file2.md").write_text("content2")
            yield base

    def test_init_with_string_paths(self, temp_dir):
        """测试使用字符串路径初始化."""
        validator = PathValidator([str(temp_dir)])
        assert len(validator.allowed_base_dirs) == 1
        assert validator.allowed_base_dirs[0] == temp_dir.resolve()

    def test_init_with_path_objects(self, temp_dir):
        """测试使用 Path 对象初始化."""
        validator = PathValidator([temp_dir])
        assert len(validator.allowed_base_dirs) == 1
        assert validator.allowed_base_dirs[0] == temp_dir.resolve()

    def test_validate_safe_path(self, temp_dir):
        """测试验证安全路径."""
        validator = PathValidator([str(temp_dir)])

        # 安全的相对路径
        assert validator.validate_path(str(temp_dir / "safe_dir" / "file1.md"))
        assert validator.validate_path(str(temp_dir / "safe_dir" / "subdir" / "file2.md"))

    def test_reject_path_traversal_attack(self, temp_dir):
        """测试拒绝路径遍历攻击."""
        validator = PathValidator([str(temp_dir / "safe_dir")])

        # 路径遍历攻击应该被拒绝
        assert not validator.validate_path("../../../etc/passwd")
        assert not validator.validate_path("../../windows/system32")
        assert not validator.validate_path("../../../tmp")

    def test_reject_absolute_path_outside_base(self, temp_dir):
        """测试拒绝基础目录外的绝对路径."""
        validator = PathValidator([str(temp_dir / "safe_dir")])

        # 绝对路径在基础目录外
        assert not validator.validate_path("/etc/passwd")
        assert not validator.validate_path("/tmp/evil")

    def test_sanitize_removes_dangerous_patterns(self, temp_dir):
        """测试净化危险模式."""
        validator = PathValidator([str(temp_dir)])

        # 包含路径遍历的路径应该被拒绝
        assert validator.sanitize_path("../../../etc/passwd") is None
        assert validator.sanitize_path("..\\..\\..\\windows\\system32") is None

    def test_sanitize_null_byte_injection(self, temp_dir):
        """测试拒绝空字节注入."""
        validator = PathValidator([str(temp_dir)])

        # 空字节注入
        assert validator.sanitize_path("safe_dir/file1.md\x00.exe") is None

    def test_sanitize_newline_injection(self, temp_dir):
        """测试拒绝换行符注入."""
        validator = PathValidator([str(temp_dir)])

        # 换行符注入
        assert validator.sanitize_path("safe_dir/file1.md\n../../etc/passwd") is None
        assert validator.sanitize_path("safe_dir/file1.md\r\n../../etc/passwd") is None

    def test_sanitize_safe_relative_path(self, temp_dir):
        """测试净化安全的相对路径."""
        validator = PathValidator([str(temp_dir)])

        # 安全的相对路径应该通过
        result = validator.sanitize_path("safe_dir/file1.md")
        assert result is not None
        assert "safe_dir" in result

    def test_get_safe_path_returns_path_object(self, temp_dir):
        """测试获取安全的路径对象."""
        validator = PathValidator([str(temp_dir)])

        safe_path = validator.get_safe_path("safe_dir/file1.md")
        assert safe_path is not None
        assert isinstance(safe_path, Path)
        assert safe_path.exists()

    def test_get_safe_path_rejects_traversal(self, temp_dir):
        """测试获取安全路径拒绝遍历."""
        validator = PathValidator([str(temp_dir / "safe_dir")])

        # 尝试访问基础目录外
        safe_path = validator.get_safe_path("../../../tmp/evil")
        assert safe_path is None

    def test_multiple_base_dirs(self, temp_dir):
        """测试多个基础目录."""
        # 创建另一个安全目录
        other_dir = temp_dir / "other_safe"
        other_dir.mkdir()

        validator = PathValidator([str(temp_dir / "safe_dir"), str(other_dir)])

        # 两个目录都应该允许访问
        assert validator.validate_path(str(temp_dir / "safe_dir" / "file1.md"))
        assert validator.validate_path(str(other_dir))

        # 其他目录应该被拒绝
        assert not validator.validate_path(str(temp_dir / "other_dir"))

    def test_symlink_escape(self, temp_dir):
        """测试符号链接逃逸防护."""
        # 创建一个指向基础目录外的符号链接
        link_target = temp_dir.parent / "outside_target"
        link_target.mkdir(exist_ok=True)

        try:
            link = temp_dir / "safe_dir" / "evil_link"
            link.symlink_to(link_target)

            validator = PathValidator([str(temp_dir / "safe_dir")])

            # 尝试通过符号链接访问
            # 解析后的路径应该在基础目录外
            assert not validator.validate_path(str(link))
        finally:
            # 清理
            if link_target.exists():
                link_target.rmdir()

    def test_windows_style_path_traversal(self, temp_dir):
        """测试 Windows 风格的路径遍历."""
        validator = PathValidator([str(temp_dir)])

        # Windows 风格的路径遍历
        assert validator.sanitize_path("..\\..\\..\\windows\\system32") is None
        assert validator.sanitize_path("safe_dir\\..\\..\\..\\etc") is None

    def test_double_slash_normalization(self, temp_dir):
        """测试双斜杠规范化."""
        validator = PathValidator([str(temp_dir)])

        # 双斜杠应该被正确处理
        safe_path = validator.sanitize_path("safe_dir//file1.md")
        # 结果可能是 None（因为双斜杠可能被视为异常）或规范化后的路径
        # 取决于实现策略
        if safe_path is not None:
            assert "//" not in safe_path

    def test_empty_path(self, temp_dir):
        """测试空路径."""
        validator = PathValidator([str(temp_dir)])

        # 空路径应该是无效的
        assert validator.sanitize_path("") is None

    def test_path_with_spaces(self, temp_dir):
        """测试包含空格的路径."""
        # 创建包含空格的文件
        space_dir = temp_dir / "safe dir"
        space_dir.mkdir()
        space_file = space_dir / "file with spaces.md"
        space_file.write_text("content")

        validator = PathValidator([str(temp_dir)])

        # 包含空格的路径应该是有效的
        safe_path = validator.get_safe_path("safe dir/file with spaces.md")
        assert safe_path is not None
        assert safe_path.exists()

    def test_path_validator_in_real_scenario(self, temp_dir):
        """测试真实场景中的路径验证器."""
        validator = PathValidator([str(temp_dir)])

        # 模拟 API 请求中的各种路径
        test_cases = [
            ("safe_dir/file1.md", True),  # 正常路径
            ("safe_dir/subdir/file2.md", True),  # 子目录
            ("../../../etc/passwd", False),  # 路径遍历
            ("..\\..\\..\\windows\\system32", False),  # Windows 遍历
            ("/etc/passwd", False),  # 绝对路径
            ("safe_dir/../../../tmp", False),  # 混合路径
            ("safe_dir/\x00.md", False),  # 空字节注入
            ("safe_dir/file.md\n../../etc", False),  # 换行注入
        ]

        for path, should_be_safe in test_cases:
            result = validator.get_safe_path(path)
            if should_be_safe:
                assert result is not None, f"Path should be safe: {path}"
            else:
                assert result is None, f"Path should be unsafe: {path}"
