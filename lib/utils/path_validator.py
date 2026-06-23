"""路径验证工具，防止路径遍历攻击和符号链接逃逸."""

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class PathValidator:
    """路径验证工具，防止路径遍历攻击和符号链接逃逸."""

    def __init__(self, allowed_base_dirs: list[str]):
        """
        初始化路径验证器.

        Args:
            allowed_base_dirs: 允许访问的基础目录列表
        """
        self.allowed_base_dirs = [Path(d).resolve() for d in allowed_base_dirs]

    def _is_symlink_safe(self, resolved_path: Path, base_dir: Path) -> bool:
        """检查路径中的符号链接是否安全.

        逐级检查路径的每个组件，如果中间存在符号链接，
        验证符号链接的目标也在允许的目录内。

        Args:
            resolved_path: 解析后的绝对路径
            base_dir: 允许的基础目录

        Returns:
            bool: 符号链接是否安全
        """
        try:
            # 检查最终路径是否为符号链接
            if resolved_path.is_symlink():
                real_target = resolved_path.resolve()
                try:
                    real_target.relative_to(base_dir)
                except ValueError:
                    logger.warning(
                        f"Symlink target {real_target} is outside "
                        f"allowed directory {base_dir}"
                    )
                    return False

            # 逐级检查路径中的符号链接
            # 从 base_dir 开始，逐步检查每个路径组件
            current = base_dir
            try:
                relative = resolved_path.relative_to(base_dir)
            except ValueError:
                return False

            for part in relative.parts:
                current = current / part

                # 跳过不存在的路径组件
                if not current.exists():
                    continue

                if current.is_symlink():
                    # 符号链接目标必须在允许的目录内
                    link_target = current.resolve()
                    try:
                        link_target.relative_to(base_dir)
                    except ValueError:
                        logger.warning(
                            f"Symlink at {current} points to "
                            f"{link_target} which is outside "
                            f"allowed directory {base_dir}"
                        )
                        return False

            return True
        except (OSError, RuntimeError) as e:
            logger.warning(f"Error checking symlink safety: {e}")
            return False

    def validate_path(self, path: str) -> bool:
        """
        验证路径是否在允许的目录内（包含符号链接检查）.

        Args:
            path: 待验证的路径

        Returns:
            bool: 路径是否安全
        """
        try:
            # 解析为绝对路径
            resolved_path = Path(path).resolve()

            # 检查是否在允许的基础目录内
            for base_dir in self.allowed_base_dirs:
                try:
                    resolved_path.relative_to(base_dir)

                    # 额外检查：符号链接目标是否安全
                    if not self._is_symlink_safe(resolved_path, base_dir):
                        return False

                    return True
                except ValueError:
                    continue

            return False
        except (OSError, RuntimeError):
            # 路径解析失败（如无效字符、不存在的路径等）
            return False

    def sanitize_path(self, path: str) -> Optional[str]:
        """
        净化路径，返回安全的相对路径.

        Args:
            path: 待净化的路径

        Returns:
            Optional[str]: 净化后的路径，如果路径不安全则返回 None
        """
        try:
            # 拒绝空路径
            if not path or not path.strip():
                return None

            # 检测并拒绝危险的路径模式
            dangerous_patterns = [
                '..',           # 路径遍历
                '\x00',         # 空字节注入
                '\n',           # 换行符注入
                '\r',           # 回车符注入
            ]

            # Windows 特殊路径检查
            if os.name == 'nt':
                windows_patterns = [
                    '\\\\',     # UNC 路径（\\server\share）
                    '\\?',      # 扩展长度路径（\\?\）
                ]
                dangerous_patterns.extend(windows_patterns)

            # 先检查原始路径中的危险模式
            for pattern in dangerous_patterns:
                if pattern in path:
                    return None

            # 拒绝绝对路径
            if os.path.isabs(path):
                return None

            # 拒绝 Windows 驱动器字母路径（C:、D: 等）
            if os.name == 'nt' and len(path) >= 2 and path[1] == ':':
                return None

            # 规范化路径（移除多余的斜杠等）
            normalized = os.path.normpath(path)

            # 再次检查规范化后的路径
            if normalized.startswith('..') or '/../' in normalized:
                return None

            # 验证净化后的路径是否在允许的目录内
            # 需要结合基础目录进行验证（包含符号链接检查）
            for base_dir in self.allowed_base_dirs:
                try:
                    full_path = (base_dir / normalized).resolve()
                    full_path.relative_to(base_dir)

                    # 额外检查：符号链接目标是否安全
                    if not self._is_symlink_safe(full_path, base_dir):
                        return None

                    return normalized
                except (ValueError, OSError):
                    continue

            return None
        except (OSError, RuntimeError):
            return None

    def get_safe_path(self, path: str) -> Optional[Path]:
        """
        获取安全的绝对路径对象.

        Args:
            path: 相对路径

        Returns:
            Optional[Path]: 安全的绝对路径，如果路径不安全则返回 None
        """
        sanitized = self.sanitize_path(path)
        if sanitized is None:
            return None

        # 找到匹配的基础目录并返回完整路径
        for base_dir in self.allowed_base_dirs:
            try:
                full_path = (base_dir / sanitized).resolve()
                full_path.relative_to(base_dir)

                # 符号链接检查
                if not self._is_symlink_safe(full_path, base_dir):
                    return None

                return full_path
            except (ValueError, OSError):
                continue

        return None
