"""
日志配置模块
使用 loguru 提供增强日志功能
"""

import sys
from loguru import logger
from app.config import settings

def setup_logger():
    """配置日志系统"""

    logger.remove()

    logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>",
        level = "DEBUG" if settings.debug else "INFO"
    )

    logger.add(
        "logs/app.log",
        rotation = "500MB",           # 日志轮转
        retention = "10 days",        # 保留时间
        compression = "zip",          # 压缩
        serialize = True,             # JSON 格式
        level = "INFO"
    )

    logger.add(
        "logs/error.log",
        rotation = "100MB",
        retention = "30 days",
        compression="zip",
        level = "ERROR",
        backtrace = True,          # 记录异常堆栈
        diagnose = True            # 记录变量值
    )

    return logger

app_logger = setup_logger()