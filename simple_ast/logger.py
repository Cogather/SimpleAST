"""
日志配置模块

统一管理项目的日志输出，将日志写入文件而不是控制台
"""
import logging
from pathlib import Path
from datetime import datetime


def setup_logger(name: str = "simple_ast", log_dir: str = "logs",
                 log_file_path: str = None) -> logging.Logger:
    """
    配置并返回日志记录器

    Args:
        name: 日志记录器名称
        log_dir: 日志文件目录（当 log_file_path 为 None 时使用）
        log_file_path: 指定的日志文件路径（如果提供，则直接使用）

    Returns:
        配置好的 Logger 实例
    """
    # 创建日志目录
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # 确定日志文件路径
    if log_file_path:
        log_file = Path(log_file_path)
    else:
        # 生成日志文件名（带完整时间戳，每次运行创建新文件）
        log_file = log_path / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    # 创建 logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # 清除已有的 handlers（确保每次运行使用新的日志文件）
    logger.handlers.clear()

    # 创建文件 handler（使用 'a' 模式追加，因为可能 analyze.py 已经创建了这个文件）
    file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)

    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)

    # 添加 handler 到 logger
    logger.addHandler(file_handler)

    return logger


# 全局默认 logger
_default_logger = None


def get_logger() -> logging.Logger:
    """
    获取默认的全局 logger

    Returns:
        Logger 实例
    """
    global _default_logger
    if _default_logger is None:
        _default_logger = setup_logger()
    return _default_logger
