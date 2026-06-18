import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from dataops.config import PATHS, resolve_path

LOGS_DIR = resolve_path(PATHS.get("logs", {}).get("dir", "logs"))
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Default log format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

def get_logger(name: str, filename: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers if already configured
    if logger.handlers:
        return logger

    log_file = LOGS_DIR / filename
    
    # Rotating File Handler (Max 5MB per file, keep 3 backups)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    file_handler.setLevel(logging.INFO)
    
    # Stream Handler (console output)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    stream_handler.setLevel(logging.INFO)
    
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    
    return logger

# Loggers for specific stages
ingestion_logger = get_logger("ingestion", "ingestion.log")
processing_logger = get_logger("processing", "processing.log")
feature_store_logger = get_logger("feature_store", "feature_store.log")
training_logger = get_logger("training", "training.log")
dashboard_logger = get_logger("dashboard", "dashboard.log")
