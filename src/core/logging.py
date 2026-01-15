import sys
import logging
from pathlib import Path
from loguru import logger

LOG_PATH = Path("logs")
LOG_PATH.mkdir(exist_ok=True)

class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())
        
def setup_app_logging():
    """Cấu hình chính cho logger"""
    
    # Loại bỏ cấu hình mặc định của loguru
    logger.remove()

    # 1. Log ra Console (Cho Dev - Dễ đọc, có màu)
    logger.add(
        sys.stdout,
        enqueue=True,
        backtrace=True,
        level="DEBUG",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )

    # 2. Log ra file (Cho Production - Lưu trữ, xoay vòng file)
    logger.add(
        LOG_PATH / "app_{time:YYYY-MM-DD}.log",
        rotation="10 MB",       # Tạo file mới khi file cũ đạt 10MB
        retention="10 days",    # Giữ log trong 10 ngày
        compression="zip",      # Nén log cũ
        enqueue=True,           # An toàn khi dùng đa luồng/async
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}",
        # Nếu muốn log dạng JSON để dễ parse (cho side project của bạn):
        # serialize=True 
    )

    # 3. Intercept các log từ Uvicorn/FastAPI
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for _log in ["uvicorn", "uvicorn.error", "fastapi"]:
        _logger = logging.getLogger(_log)
        _logger.handlers = [InterceptHandler()]

    return logger

# Khởi tạo logger sẵn sàng để import
log = logger