"""
Logging utilities module.

This module provides logging configuration and utilities for the application.
"""

import logging
import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional, Union, List, TextIO

# Default log format
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_LOG_LEVEL = "INFO"


def setup_logging(
    log_level: str = None,
    log_file: str = None,
    log_format: str = None,
    enable_console: bool = True
) -> logging.Logger:
    """
    Configure logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
        log_format: Log message format
        enable_console: Whether to log to console
        
    Returns:
        The root logger instance
    """
    # Get root logger
    root_logger = logging.getLogger()
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set log level
    level = getattr(logging, (log_level or DEFAULT_LOG_LEVEL).upper(), logging.INFO)
    root_logger.setLevel(level)
    
    # Format string
    formatter = logging.Formatter(log_format or DEFAULT_LOG_FORMAT)
    
    # Add console handler if enabled
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        # Ensure directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    return root_logger


class JsonFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    """
    
    def __init__(self, include_extra_fields: bool = True):
        """
        Initialize the JSON formatter.
        
        Args:
            include_extra_fields: Whether to include extra fields from record
        """
        super().__init__()
        self.include_extra_fields = include_extra_fields
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record as JSON.
        
        Args:
            record: The log record to format
            
        Returns:
            JSON-formatted log string
        """
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "filename": record.filename,
            "lineno": record.lineno
        }
        
        # Include exception info if available
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        
        # Include extra fields if present and enabled
        if self.include_extra_fields and hasattr(record, "extra_fields"):
            extra = record.extra_fields
            if isinstance(extra, dict):
                for key, value in extra.items():
                    if key not in log_data:
                        log_data[key] = value
        
        return json.dumps(log_data)


def setup_structured_logging(
    log_level: str = None,
    log_file: str = None,
    enable_console: bool = True,
    include_extra_fields: bool = True
) -> logging.Logger:
    """
    Configure structured JSON logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
        enable_console: Whether to log to console
        include_extra_fields: Whether to include extra fields in JSON
        
    Returns:
        The root logger instance
    """
    # Get root logger
    root_logger = logging.getLogger()
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set log level
    level = getattr(logging, (log_level or DEFAULT_LOG_LEVEL).upper(), logging.INFO)
    root_logger.setLevel(level)
    
    # Create formatter
    formatter = JsonFormatter(include_extra_fields=include_extra_fields)
    
    # Add console handler if enabled
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        # Ensure directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    return root_logger


class LogContext:
    """
    Context manager for adding context to log records.
    """
    
    def __init__(self, logger: logging.Logger, **context):
        """
        Initialize the context manager.
        
        Args:
            logger: The logger to add context to
            **context: Context fields to add to log records
        """
        self.logger = logger
        self.context = context
        self.old_factory = logging.getLogRecordFactory()
    
    def __enter__(self):
        """
        Set up the context when entering the with block.
        """
        # Create a new factory that adds our context
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            if not hasattr(record, "extra_fields"):
                record.extra_fields = {}
            
            # Add context to record
            for key, value in self.context.items():
                record.extra_fields[key] = value
            
            return record
        
        # Replace the factory
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Clean up when exiting the with block.
        """
        # Restore the original factory
        logging.setLogRecordFactory(self.old_factory)


class RequestLogger:
    """
    Logger for API requests.
    """
    
    def __init__(self, logger: logging.Logger):
        """
        Initialize the request logger.
        
        Args:
            logger: The logger to use
        """
        self.logger = logger
    
    def log_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Any] = None,
        request_id: Optional[str] = None
    ) -> str:
        """
        Log an API request.
        
        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            body: Request body
            request_id: Request ID for correlation
            
        Returns:
            Request ID for correlation
        """
        # Generate request ID if not provided
        if not request_id:
            request_id = f"req_{int(time.time() * 1000)}"
        
        # Build log data
        log_data = {
            "event": "api_request",
            "request_id": request_id,
            "method": method,
            "url": url
        }
        
        # Add headers (filtered)
        if headers:
            filtered_headers = headers.copy()
            # Remove sensitive headers
            for sensitive in ["authorization", "api-key", "x-api-key"]:
                if sensitive in filtered_headers:
                    filtered_headers[sensitive] = "[REDACTED]"
                    
            log_data["headers"] = filtered_headers
        
        # Add body if present (potentially truncate or filter)
        if body:
            if isinstance(body, dict):
                # Filter out sensitive fields
                filtered_body = self._filter_sensitive_data(body)
                log_data["body"] = filtered_body
            elif isinstance(body, str):
                # Truncate long strings
                if len(body) > 1000:
                    log_data["body"] = body[:1000] + "... [truncated]"
                else:
                    log_data["body"] = body
            else:
                log_data["body_type"] = str(type(body))
        
        # Log with extra fields
        self.logger.info("API Request", extra={"extra_fields": log_data})
        
        return request_id
    
    def log_response(
        self,
        status_code: int,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Any] = None,
        request_id: Optional[str] = None,
        elapsed_ms: Optional[int] = None
    ) -> None:
        """
        Log an API response.
        
        Args:
            status_code: HTTP status code
            headers: Response headers
            body: Response body
            request_id: Request ID for correlation
            elapsed_ms: Elapsed time in milliseconds
        """
        # Build log data
        log_data = {
            "event": "api_response",
            "status_code": status_code
        }
        
        # Add request ID if provided
        if request_id:
            log_data["request_id"] = request_id
        
        # Add elapsed time if provided
        if elapsed_ms:
            log_data["elapsed_ms"] = elapsed_ms
        
        # Add headers
        if headers:
            log_data["headers"] = headers
        
        # Add body if present
        if body:
            if isinstance(body, dict):
                # Filter out sensitive fields
                filtered_body = self._filter_sensitive_data(body)
                log_data["body"] = filtered_body
            elif isinstance(body, str):
                # Truncate long strings
                if len(body) > 1000:
                    log_data["body"] = body[:1000] + "... [truncated]"
                else:
                    log_data["body"] = body
            else:
                log_data["body_type"] = str(type(body))
        
        # Log with extra fields
        log_level = "info" if 200 <= status_code < 400 else "warning" if 400 <= status_code < 500 else "error"
        getattr(self.logger, log_level)("API Response", extra={"extra_fields": log_data})
    
    def _filter_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter sensitive data from a dictionary.
        
        Args:
            data: The data to filter
            
        Returns:
            Filtered data with sensitive fields redacted
        """
        if not isinstance(data, dict):
            return data
            
        sensitive_fields = {
            "password", "token", "secret", "api_key", "apikey", "api-key",
            "authorization", "auth", "credentials", "credit_card", "creditcard",
            "ssn", "social_security", "socialsecurity"
        }
        
        filtered = {}
        for key, value in data.items():
            # Check if key contains sensitive words
            if any(sensitive in key.lower() for sensitive in sensitive_fields):
                filtered[key] = "[REDACTED]"
            elif isinstance(value, dict):
                # Recursively filter nested dictionaries
                filtered[key] = self._filter_sensitive_data(value)
            elif isinstance(value, list) and all(isinstance(item, dict) for item in value):
                # Filter dictionaries in lists
                filtered[key] = [self._filter_sensitive_data(item) for item in value]
            else:
                filtered[key] = value
                
        return filtered


class PerformanceLogger:
    """
    Logger for tracking performance metrics.
    """
    
    def __init__(self, logger: logging.Logger):
        """
        Initialize the performance logger.
        
        Args:
            logger: The logger to use
        """
        self.logger = logger
        self.timers = {}
    
    def start_timer(self, operation: str) -> None:
        """
        Start a timer for an operation.
        
        Args:
            operation: Name of the operation to time
        """
        self.timers[operation] = time.time()
    
    def end_timer(self, operation: str, log_level: str = "debug") -> float:
        """
        End a timer and log the elapsed time.
        
        Args:
            operation: Name of the operation to end
            log_level: Level to log at (debug, info, etc.)
            
        Returns:
            Elapsed time in milliseconds
            
        Raises:
            ValueError: If timer was not started
        """
        if operation not in self.timers:
            raise ValueError(f"Timer for '{operation}' was not started")
            
        elapsed = time.time() - self.timers[operation]
        elapsed_ms = elapsed * 1000
        
        # Remove the timer
        del self.timers[operation]
        
        # Log the elapsed time
        log_data = {
            "event": "performance",
            "operation": operation,
            "elapsed_ms": elapsed_ms
        }
        
        # Log at the specified level
        log_method = getattr(self.logger, log_level, self.logger.debug)
        log_method(f"Operation '{operation}' took {elapsed_ms:.2f}ms", extra={"extra_fields": log_data})
        
        return elapsed_ms
    
    def log_metric(
        self,
        name: str,
        value: Union[int, float],
        unit: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a performance metric.
        
        Args:
            name: Metric name
            value: Metric value
            unit: Metric unit
            context: Additional context for the metric
        """
        log_data = {
            "event": "metric",
            "metric_name": name,
            "metric_value": value
        }
        
        if unit:
            log_data["metric_unit"] = unit
            
        if context:
            log_data["context"] = context
            
        self.logger.info(f"Metric: {name}={value}{f' {unit}' if unit else ''}", 
                         extra={"extra_fields": log_data}) 