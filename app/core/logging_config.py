import logging
import sys
from contextvars import ContextVar
from pathlib import Path
from typing import Union

# Context Variables 保持不变
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default="anonymous")

# --- (关键) 将 LOG_DIR 的定义和计算放在这里，作为单一事实来源 ---
# __file__ 是当前文件 (logging_config.py) 的路径
# .parent 指向上级目录 (core/)
# .parent.parent 指向再上一级 (app/)
# .parent.parent.parent 指向最终的项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
LOG_DIR = PROJECT_ROOT / "logs"


class ContextFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_var.get()
        record.user_id = user_id_var.get()
        return True

class LevelFilter(logging.Filter):
    def __init__(self, level):
        super().__init__()
        self.level = level
    def filter(self, record):
        return record.levelno < self.level

LOGGERS_TO_SETUP = [
    {"name": "api_traffic", "level": logging.INFO, "filename": "api_traffic.log"},
]


def setup_logging(log_dir: Union[Path, str]):
    """
    配置应用的日志系统。
    它会自动使用在本文件中定义的 LOG_DIR。
    """
    LOG_DIR = Path(log_dir)
    LOG_DIR.mkdir(exist_ok=True)

    log_format = (
        "%(asctime)s - [User:%(user_id)s] [%(request_id)s] - "
        "%(levelname)s - %(name)s - %(message)s"
    )
    formatter = logging.Formatter(log_format)
    context_filter = ContextFilter()

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # 控制台 Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(context_filter)
    console_handler.setLevel(logging.DEBUG)

    # info.log 文件 Handler
    info_file_handler = logging.FileHandler(LOG_DIR / "info.log", encoding='utf-8')
    info_file_handler.setFormatter(formatter)
    info_file_handler.addFilter(context_filter)
    info_file_handler.setLevel(logging.INFO)
    info_file_handler.addFilter(LevelFilter(logging.WARNING))

    # error.log 文件 Handler
    error_file_handler = logging.FileHandler(LOG_DIR / "error.log", encoding='utf-8')
    error_file_handler.setFormatter(formatter)
    error_file_handler.addFilter(context_filter)
    error_file_handler.setLevel(logging.WARNING)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(info_file_handler)
    root_logger.addHandler(error_file_handler)

    # 单独配置专用的 logger
    for config in LOGGERS_TO_SETUP:
        logger = logging.getLogger(config["name"])
        logger.setLevel(config["level"])
        logger.propagate = False
        if logger.hasHandlers():
            logger.handlers.clear()
        logger.addHandler(console_handler)
        file_handler = logging.FileHandler(LOG_DIR / config["filename"], encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.addFilter(context_filter)
        logger.addHandler(file_handler)