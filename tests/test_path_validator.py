#!/usr/bin/env python3
"""路径验证器的独立测试脚本."""

import os
import sys
import tempfile
from pathlib import Path

# 直接加载 path_validator 模块
sys.path.insert(0, '/Users/Tiandiyiqi/Documents/Prepress/llm-wiki/lib/utils')
from path_validator import PathValidator


def test_basic_validation():
    """测试基本验证功能."""
    print("=" * 60)
    print("测试 1: 基本路径验证")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建测试文件
        base = Path(tmpdir)
        (base / "safe_dir").mkdir()
        (base / "safe_dir" / "file1.md").write_text("content1")

        validator = PathValidator([str(base)])

        # 测试安全路径
        safe_path = str(base / "safe_dir" / "file1.md")
        assert validator.validate_path(safe_path), f"安全路径应该通过: {safe_path}"
        print(f"✓ 安全路径验证通过: {safe_path}")

        # 测试路径遍历攻击
        evil_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "/etc/passwd",
            "../../tmp",
        ]

        for evil in evil_paths:
            result = validator.validate_path(evil)
            assert not result, f"路径遍历攻击应该被拒绝: {evil}"
            print(f"✓ 路径遍历攻击已拦截: {evil}")


def test_sanitize():
    """测试路径净化功能."""
    print("\n" + "=" * 60)
    print("测试 2: 路径净化")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        (base / "safe_dir").mkdir()
        (base / "safe_dir" / "file.md").write_text("content")

        validator = PathValidator([str(base)])

        # 测试净化安全路径
        safe = validator.sanitize_path("safe_dir/file.md")
        assert safe is not None, "安全路径应该被净化"
        print(f"✓ 安全路径净化成功: safe_dir/file.md -> {safe}")

        # 测试净化危险路径
        dangerous_patterns = [
            "../../../etc/passwd",
            "safe_dir/../../../tmp",
            "file.md\x00.exe",
            "file.md\n../../etc",
        ]

        for dangerous in dangerous_patterns:
            result = validator.sanitize_path(dangerous)
            assert result is None, f"危险路径应该被拒绝: {dangerous}"
            print(f"✓ 危险路径已拒绝: {dangerous}")


def test_get_safe_path():
    """测试获取安全路径."""
    print("\n" + "=" * 60)
    print("测试 3: 获取安全路径对象")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        (base / "data").mkdir()
        (base / "data" / "kb1").mkdir()
        (base / "data" / "kb1" / "atom1.md").write_text("atom content")

        validator = PathValidator([str(base)])

        # 测试获取存在的文件
        safe_path = validator.get_safe_path("data/kb1/atom1.md")
        assert safe_path is not None, "应该返回安全路径"
        assert safe_path.exists(), "文件应该存在"
        print(f"✓ 安全路径对象获取成功: {safe_path}")

        # 测试获取不存在的安全路径
        non_existent = validator.get_safe_path("data/kb1/non_existent.md")
        # 即使文件不存在，路径本身可能是安全的
        if non_existent is not None:
            print(f"✓ 不存在的文件路径仍被视为安全: {non_existent}")
        else:
            print(f"✓ 不存在的文件路径被拒绝（严格模式）")

        # 测试危险路径
        evil_path = validator.get_safe_path("../../../etc/passwd")
        assert evil_path is None, "危险路径应该返回 None"
        print(f"✓ 危险路径返回 None: ../../../etc/passwd")


def test_api_server_scenario():
    """测试 API Server 场景."""
    print("\n" + "=" * 60)
    print("测试 4: API Server 场景模拟")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        kb_dir = Path(tmpdir)
        (kb_dir / "atoms").mkdir()
        (kb_dir / "atoms" / "methods").mkdir()
        (kb_dir / "atoms" / "methods" / "design-pattern.md").write_text("# Design Pattern")

        validator = PathValidator([str(kb_dir)])

        # 模拟各种 API 请求
        test_cases = [
            ("atoms/methods/design-pattern", True, "正常的相对路径"),
            ("../../../etc/passwd", False, "路径遍历攻击"),
            ("atoms/../../../tmp", False, "混合路径遍历"),
            ("/etc/passwd", False, "绝对路径"),
            ("atoms/\x00.md", False, "空字节注入"),
            ("atoms/methods/design-pattern.md", True, "完整文件名"),
        ]

        for path, should_be_safe, description in test_cases:
            safe_path = validator.get_safe_path(path)
            is_safe = safe_path is not None

            if should_be_safe:
                assert is_safe, f"{description} 应该是安全的: {path}"
                print(f"✓ {description}: {path}")
            else:
                assert not is_safe, f"{description} 应该被拒绝: {path}"
                print(f"✓ {description} 已拦截: {path}")


def test_multiple_base_dirs():
    """测试多个基础目录."""
    print("\n" + "=" * 60)
    print("测试 5: 多个基础目录")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        dir1 = base / "allowed1"
        dir2 = base / "allowed2"
        forbidden = base / "forbidden"

        dir1.mkdir()
        dir2.mkdir()
        forbidden.mkdir()

        (dir1 / "file1.md").write_text("content1")
        (dir2 / "file2.md").write_text("content2")
        (forbidden / "secret.md").write_text("secret")

        validator = PathValidator([str(dir1), str(dir2)])

        # 测试允许的目录
        assert validator.validate_path(str(dir1 / "file1.md")), "dir1 应该允许访问"
        assert validator.validate_path(str(dir2 / "file2.md")), "dir2 应该允许访问"
        print(f"✓ 允许的目录可以访问")

        # 测试禁止的目录
        assert not validator.validate_path(str(forbidden / "secret.md")), "forbidden 应该被拒绝"
        print(f"✓ 禁止的目录被拦截")


def main():
    """运行所有测试."""
    print("\n🔍 路径验证器测试套件\n")

    try:
        test_basic_validation()
        test_sanitize()
        test_get_safe_path()
        test_api_server_scenario()
        test_multiple_base_dirs()

        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
