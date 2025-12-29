import logging
import json
import time
from typing import Any, Dict, Optional
from datetime import datetime
from uuid import uuid4
from contextvars import ContextVar

# Context var to store request ID across async calls
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="system")

class JsonFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings after parsing the LogRecord.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_record: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "request_id": request_id_ctx.get(),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno
        }
        
        # Add extra fields if available
        if hasattr(record, "extra"):
            log_record.update(record.extra)
            
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_record)

def setup_logger(name: str = "vornics_backend") -> logging.Logger:
    """Configure and return a structured logger"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplicates
    if logger.handlers:
        logger.handlers.clear()
        
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    
    # Also silence uvicorn access logs and intercept them if needed, 
    # but for now we focus on application logs
    
    return logger

# Global logger instance
logger = setup_logger()
