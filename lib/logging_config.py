"""统一日志配置

为整个项目提供统一的日志配置，替换 print 语句。
"""

import logging
import sys
from pathlib import Path
from typing import Optional


# 日志格式
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    format_string: Optional[str] = None
) -> None:
    """配置全局日志

    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径（可选）
        format_string: 自定义格式字符串（可选）
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
    root_logger.addHandler(console_handler)

    # 文件处理器（如果指定）
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
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
