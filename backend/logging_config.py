import logging
import json
import time
from contextvars import ContextVar
import uuid

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="system")
tenant_id_var: ContextVar[str] = ContextVar("tenant_id", default="system")

class StructuredJsonFormatter(logging.Formatter):
    """Formatter JSON pour Cloud Logging."""
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": trace_id_var.get(),
            "tenant_id": tenant_id_var.get(),
        }
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_data)

def setup_logging():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(StructuredJsonFormatter())
    root_logger.addHandler(console_handler)
    
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    
    logging.info("Logging JSON initialisé.")
