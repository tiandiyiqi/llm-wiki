"""统一日志配置

为整个项目提供统一的日志配置，替换 print 语句。
包含敏感信息脱敏功能，防止密码、token 等泄露。
"""

import logging
import re
import sys
from pathlib import Path
from typing import Optional, Any


# 日志格式
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 需要脱敏的敏感字段
SENSITIVE_FIELDS = [
    'password',
    'passwd',
    'pwd',
    'token',
    'api_key',
    'apikey',
    'secret',
    'secret_key',
    'access_token',
    'refresh_token',
    'auth_token',
    'credential',
    'private_key',
    'session_id',
    'email',
    'phone',
    'mobile',
]

# 脱敏模式（正则表达式）
SENSITIVE_PATTERNS = [
    # API Key 格式 (sk-开头，包含连字符)
    re.compile(r'(sk-[a-zA-Z0-9\-_]{10,})', re.IGNORECASE),
    # Token 格式 (Bearer Token)
    re.compile(r'(Bearer\s+[a-zA-Z0-9\-_\.]{10,})', re.IGNORECASE),
    # 密码格式 (password: value 或 password": "value")
    re.compile(r'(password\s*[:=]\s*[^\s,}\]]+)', re.IGNORECASE),
    # API Key 格式 (api_key: value)
    re.compile(r'(api[_-]?key\s*[:=]\s*[a-zA-Z0-9\-_]{10,})', re.IGNORECASE),
    # Token 格式 (token: value)
    re.compile(r'(token\s*[:=]\s*[a-zA-Z0-9\-_]{10,})', re.IGNORECASE),
    # Email 格式（部分脱敏）
    re.compile(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', re.IGNORECASE),
]


class SensitiveDataFilter(logging.Filter):
    """敏感数据过滤器，自动脱敏日志中的敏感信息."""

    def filter(self, record: logging.LogRecord) -> bool:
        """过滤并脱敏日志记录中的敏感信息.

        Args:
            record: 日志记录

        Returns:
            总是返回 True（允许记录），但会修改消息
        """
        # 脱敏消息文本
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = self._sanitize(record.msg)

        # 脱敏格式化后的消息
        if hasattr(record, 'getMessage'):
            original_msg = record.getMessage()
            sanitized_msg = self._sanitize(original_msg)
            # 修改 args 以反映脱敏后的消息
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {k: self._sanitize_value(v) if k in SENSITIVE_FIELDS else v
                                   for k, v in record.args.items()}
                elif isinstance(record.args, tuple):
                    record.args = tuple(self._sanitize_value(arg) for arg in record.args)

        return True

    def _sanitize(self, text: str) -> str:
        """脱敏文本中的敏感信息.

        Args:
            text: 原始文本

        Returns:
            脱敏后的文本
        """
        # 应用所有敏感模式
        for pattern in SENSITIVE_PATTERNS:
            text = pattern.sub(self._mask_match, text)

        # 脱敏 JSON 格式的敏感字段
        text = self._sanitize_json_fields(text)

        return text

    def _mask_match(self, match: re.Match) -> str:
        """掩码匹配到的敏感信息.

        Args:
            match: 正则匹配对象

        Returns:
            掩码后的字符串
        """
        matched_text = match.group(0)
        if len(matched_text) <= 8:
            return '***'
        else:
            # 保留前 3 个字符，其余用 *** 替换
            return matched_text[:3] + '***' + matched_text[-3:]

    def _sanitize_json_fields(self, text: str) -> str:
        """脱敏 JSON 格式中的敏感字段值.

        Args:
            text: 包含可能的 JSON 内容的文本

        Returns:
            脱敏后的文本
        """
        # 匹配 "password": "value", "token": "value" 等
        for field in SENSITIVE_FIELDS:
            # 匹配 "field": "value" 或 'field': 'value'
            pattern = re.compile(
                rf'["\']({field})["\']\s*:\s*["\']([^"\']+)["\']',
                re.IGNORECASE
            )
            text = pattern.sub(rf'"\1": "***"', text)

        return text

    def _sanitize_value(self, value: Any) -> Any:
        """脱敏单个值.

        Args:
            value: 原始值

        Returns:
            脱敏后的值
        """
        if isinstance(value, str):
            return self._sanitize(value)
        elif isinstance(value, dict):
            return {k: '***' if k in SENSITIVE_FIELDS else v
                    for k, v in value.items()}
        else:
            return value


def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    format_string: Optional[str] = None,
    enable_sanitization: bool = True
) -> None:
    """配置全局日志（带脱敏功能）

    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径（可选）
        format_string: 自定义格式字符串（可选）
        enable_sanitization: 是否启用敏感信息脱敏（默认 True）
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # 创建格式器
    formatter = logging.Formatter(
        format_string or LOG_FORMAT,
        datefmt=DATE_FORMAT
    )

    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 清除现有处理器
    root_logger.handlers.clear()

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # 添加敏感数据过滤器
    if enable_sanitization:
        console_handler.addFilter(SensitiveDataFilter())

    root_logger.addHandler(console_handler)

    # 文件处理器（如果指定）
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)

        # 文件日志也需要脱敏
        if enable_sanitization:
            file_handler.addFilter(SensitiveDataFilter())

        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """获取日志器

    Args:
        name: 日志器名称（通常使用 __name__）

    Returns:
        配置好的日志器实例
    """
    return logging.getLogger(name)


# 模块级日志器
logger = get_logger(__name__)
