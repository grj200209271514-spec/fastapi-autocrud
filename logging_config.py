import logging
import sys
from contextvars import ContextVar
from pathlib import Path

# 1. 定义 Context Variables
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default="anonymous")

# 2. 定义日志目录
LOG_DIR = Path(".") / "logs"


# 3. 自定义过滤器保持不变
class ContextFilter(logging.Filter):
    """将 request_id 和 user_id 注入到每一条日志记录中。"""

    def filter(self, record):
        record.request_id = request_id_var.get()
        record.user_id = user_id_var.get()
        return True


# 4. 自定义格式化器
# class CustomFormatter(logging.Formatter):
#     """一个自定义的格式化器，它会智能地处理可选的日志字段。"""
#
#     def format(self, record):
#         if hasattr(record, 'error_code') and record.error_code:
#             record.error_code_str = f" [Code:{record.error_code}]"
#         else:
#             record.error_code_str = ""
#         return super().format(record)

# --- (关键修改) 将 LOGGERS_TO_SETUP 定义移到函数外部 ---
# 现在它是一个全局常量，可以被 lifespan.py 正确导入
LOGGERS_TO_SETUP = [
    {"name": "api_traffic", "level": logging.INFO, "filename": "api_traffic.log"},
    {"name": "user_activity", "level": logging.DEBUG, "filename": "user_activity.log"},
    {"name": "error", "level": logging.WARNING, "filename": "error.log"}
]


# 5. 定义设置日志的主函数
def setup_logging():
    """
    配置应用的日志系统，实现控制台和文件双输出。
    """
    LOG_DIR.mkdir(exist_ok=True)

    log_format = (
        "%(asctime)s - [User:%(user_id)s] [%(request_id)s] - "
        "%(levelname)s - %(name)s - %(message)s"
    )
    formatter = logging.Formatter(log_format)

    # --- 创建处理器 ---
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(ContextFilter())

    # --- (修改) 现在直接使用全局的 LOGGERS_TO_SETUP 列表 ---
    for config in LOGGERS_TO_SETUP:
        logger = logging.getLogger(config["name"])
        logger.setLevel(config["level"])
        logger.propagate = False

        if logger.hasHandlers():
            logger.handlers.clear()

        logger.addHandler(console_handler)

        file_handler = logging.FileHandler(LOG_DIR / config["filename"], encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.addFilter(ContextFilter())
        logger.addHandler(file_handler)

