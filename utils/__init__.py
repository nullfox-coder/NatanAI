"""
Utilities package.

This package provides various utility functions and classes for the application.
"""

from utils.errors import (
    BrowserAIError, BrowserError, NavigationError, ElementNotFoundError,
    TimeoutError, ParserError, APIError, NLPError, ExtractionError,
    ValidationError, ConfigError, format_exception, handle_exception,
    get_error_recovery_strategy, error_to_user_message, log_exception
)

from utils.logging import (
    setup_logging, setup_structured_logging, JsonFormatter,
    LogContext, RequestLogger, PerformanceLogger
)

from utils.validation import (
    validate_url, validate_email, validate_integer, validate_float,
    validate_string, validate_boolean, validate_list, validate_dict,
    validate_json, Validator
)

__all__ = [
    # Errors
    'BrowserAIError', 'BrowserError', 'NavigationError', 'ElementNotFoundError',
    'TimeoutError', 'ParserError', 'APIError', 'NLPError', 'ExtractionError',
    'ValidationError', 'ConfigError', 'format_exception', 'handle_exception',
    'get_error_recovery_strategy', 'error_to_user_message', 'log_exception',
    
    # Logging
    'setup_logging', 'setup_structured_logging', 'JsonFormatter',
    'LogContext', 'RequestLogger', 'PerformanceLogger',
    
    # Validation
    'validate_url', 'validate_email', 'validate_integer', 'validate_float',
    'validate_string', 'validate_boolean', 'validate_list', 'validate_dict',
    'validate_json', 'Validator'
]
