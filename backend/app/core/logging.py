"""
日志配置模块
使用Python标准库logging，遵循FastAPI最佳实践
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from app.core.config import settings

# 创建logs目录
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# 日志格式
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 配置根日志记录器
logger = logging.getLogger("easy_data")
logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

# 清除已有的处理器
logger.handlers.clear()

# 控制台处理器
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
console_formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# 文件处理器（轮转日志）
file_handler = RotatingFileHandler(
    LOG_DIR / "easy_data.log",
    maxBytes=10 * 1024 * 1024,
    backupCount=10,
    encoding="utf-8",  # 10MB
)
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# 错误日志文件处理器
error_file_handler = RotatingFileHandler(
    LOG_DIR / "easy_data_error.log",
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
    encoding="utf-8",
)
error_file_handler.setLevel(logging.ERROR)
error_file_handler.setFormatter(file_formatter)
logger.addHandler(error_file_handler)

# 防止日志传播到根日志记录器
logger.propagate = False


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    获取日志记录器

    Args:
        name: 日志记录器名称，如果为None则返回根日志记录器

    Returns:
        logging.Logger实例
    """
    if name:
        return logging.getLogger(f"easy_data.{name}")
    return logger
