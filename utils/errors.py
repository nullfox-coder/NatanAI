"""
Error handling utilities module.

This module provides exception classes and error handling utilities for the application.
"""

import logging
import traceback
from typing import Dict, Any, Optional, List, Tuple, Type, Union

# Set up logger
logger = logging.getLogger(__name__)


class BrowserAIError(Exception):
    """Base exception class for the application."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the exception.
        
        Args:
            message: Error message
            details: Additional error details
        """
        self.message = message
        self.details = details or {}
        super().__init__(message)


class BrowserError(BrowserAIError):
    """Exception raised for browser-related errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the exception.
        
        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(f"Browser error: {message}", details)


class NavigationError(BrowserError):
    """Exception raised for navigation-related errors."""
    
    def __init__(self, message: str, url: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the exception.
        
        Args:
            message: Error message
            url: The URL that failed to navigate
            details: Additional error details
        """
        details = details or {}
        details["url"] = url
        super().__init__(f"Navigation error: {message}", details)


class ElementNotFoundError(BrowserError):
    """Exception raised when an element cannot be found."""
    
    def __init__(self, selector: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the exception.
        
        Args:
            selector: The selector that failed to find an element
            details: Additional error details
        """
        details = details or {}
        details["selector"] = selector
        super().__init__(f"Element not found: {selector}", details)


class TimeoutError(BrowserError):
    """Exception raised when an operation times out."""
    
    def __init__(self, operation: str, timeout: float, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the exception.
        
        Args:
            operation: The operation that timed out
            timeout: The timeout value in seconds
            details: Additional error details
        """
        details = details or {}
        details["operation"] = operation
        details["timeout"] = timeout
        super().__init__(f"Operation timed out: {operation} (after {timeout}s)", details)


class ParserError(BrowserAIError):
    """Exception raised for parsing-related errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the exception.
        
        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(f"Parser error: {message}", details)


class APIError(BrowserAIError):
    """Exception raised for API-related errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the exception.
        
        Args:
            message: Error message
            status_code: HTTP status code
            details: Additional error details
        """
        details = details or {}
        if status_code is not None:
            details["status_code"] = status_code
        super().__init__(f"API error: {message}", details)


class NLPError(BrowserAIError):
    """Exception raised for NLP-related errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the exception.
        
        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(f"NLP error: {message}", details)


class ExtractionError(BrowserAIError):
    """Exception raised for data extraction errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the exception.
        
        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(f"Extraction error: {message}", details)


class ValidationError(BrowserAIError):
    """Exception raised for validation errors."""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the exception.
        
        Args:
            message: Error message
            field: The field that failed validation
            details: Additional error details
        """
        details = details or {}
        if field is not None:
            details["field"] = field
        super().__init__(f"Validation error: {message}", details)


class ConfigError(BrowserAIError):
    """Exception raised for configuration errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the exception.
        
        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(f"Configuration error: {message}", details)


def format_exception(
    exc: Exception,
    include_traceback: bool = True
) -> Dict[str, Any]:
    """
    Format an exception into a standardized dictionary.
    
    Args:
        exc: The exception to format
        include_traceback: Whether to include the traceback
        
    Returns:
        Dictionary with formatted exception details
    """
    result = {
        "type": exc.__class__.__name__,
        "message": str(exc)
    }
    
    # Add details for BrowserAIError
    if isinstance(exc, BrowserAIError) and exc.details:
        result["details"] = exc.details
    
    # Add traceback if requested
    if include_traceback:
        result["traceback"] = traceback.format_exc()
    
    return result


def get_error_recovery_strategy(error: Exception) -> Tuple[str, Dict[str, Any]]:
    """
    Get a recovery strategy for an error.
    
    Args:
        error: The exception to get a recovery strategy for
        
    Returns:
        Tuple of (strategy_name, strategy_params)
    """
    # Default strategy
    default_strategy = ("retry", {"max_retries": 3, "delay": 1.0})
    
    # Define strategies based on error type
    if isinstance(error, NavigationError):
        return ("retry_navigation", {"max_retries": 3, "delay": 2.0})
    
    elif isinstance(error, ElementNotFoundError):
        return ("wait_and_retry", {"max_retries": 5, "delay": 1.0, "increasing_delay": True})
    
    elif isinstance(error, TimeoutError):
        return ("increase_timeout", {"timeout_multiplier": 2.0, "max_timeout": 60.0})
    
    elif isinstance(error, ParserError):
        return ("alternative_parser", {"fallback_parsers": ["simple", "regex"]})
    
    elif isinstance(error, APIError):
        # Different strategy based on status code
        details = getattr(error, "details", {})
        status_code = details.get("status_code", 0)
        
        if status_code == 429:  # Too Many Requests
            return ("backoff_retry", {"max_retries": 5, "initial_delay": 2.0, "backoff_factor": 2.0})
        elif status_code >= 500:  # Server errors
            return ("retry", {"max_retries": 3, "delay": 5.0})
        else:
            return ("report_error", {"notify_user": True})
    
    # Default fallback
    return default_strategy


def error_to_user_message(error: Exception) -> str:
    """
    Convert an error to a user-friendly message.
    
    Args:
        error: The exception to convert
        
    Returns:
        User-friendly error message
    """
    # Base message for different error types
    if isinstance(error, NavigationError):
        url = getattr(error, "details", {}).get("url", "the requested page")
        return f"I couldn't navigate to {url}. The page might be unavailable or taking too long to load."
    
    elif isinstance(error, ElementNotFoundError):
        selector = getattr(error, "details", {}).get("selector", "the element")
        return f"I couldn't find {selector} on the page. It might not exist or it might be loading."
    
    elif isinstance(error, TimeoutError):
        operation = getattr(error, "details", {}).get("operation", "the operation")
        return f"{operation} took too long to complete. The website might be slow or unresponsive."
    
    elif isinstance(error, ParserError):
        return "I had trouble understanding the content on the page. The format might be unexpected."
    
    elif isinstance(error, APIError):
        details = getattr(error, "details", {})
        status_code = details.get("status_code", 0)
        
        if status_code == 429:
            return "The service is limiting requests. Please try again later."
        elif status_code >= 500:
            return "The service is experiencing technical difficulties. Please try again later."
        else:
            return "There was a problem with the service request. Please check your inputs and try again."
    
    elif isinstance(error, NLPError):
        return "I had trouble understanding your request. Could you please rephrase it?"
    
    elif isinstance(error, ExtractionError):
        return "I had trouble extracting the data you requested. The content might not be in the expected format."
    
    elif isinstance(error, ValidationError):
        field = getattr(error, "details", {}).get("field", "input")
        return f"There was a problem with the {field}. Please check it and try again."
    
    elif isinstance(error, ConfigError):
        return "There's a configuration issue. Please check your settings and try again."
    
    # Generic fallback
    return f"An error occurred: {str(error)}"


def log_exception(
    error: Exception,
    level: str = "error",
    include_traceback: bool = True
) -> None:
    """
    Log an exception with appropriate formatting.
    
    Args:
        error: The exception to log
        level: Logging level ('debug', 'info', 'warning', 'error', 'critical')
        include_traceback: Whether to include the traceback
    """
    # Get the logger method based on level
    logger_method = getattr(logger, level.lower(), logger.error)
    
    # Format the error message
    error_type = error.__class__.__name__
    error_message = str(error)
    
    # Get additional details for BrowserAIError
    if isinstance(error, BrowserAIError) and error.details:
        details_str = ", ".join([f"{k}={v}" for k, v in error.details.items()])
        log_message = f"{error_type}: {error_message} - {details_str}"
    else:
        log_message = f"{error_type}: {error_message}"
    
    # Log the message
    if include_traceback:
        logger_method(log_message, exc_info=True)
    else:
        logger_method(log_message)


def handle_exception(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    raise_error: bool = False
) -> Dict[str, Any]:
    """
    Handle an exception with standardized error processing.
    
    Args:
        error: The exception to handle
        context: Additional context about where the error occurred
        raise_error: Whether to re-raise the error after handling
        
    Returns:
        Dictionary with error information and recovery strategy
        
    Raises:
        The original exception if raise_error is True
    """
    # Log the error
    log_exception(error)
    
    # Format the error details
    error_details = format_exception(error)
    
    # Add context if provided
    if context:
        error_details["context"] = context
    
    # Get recovery strategy
    strategy_name, strategy_params = get_error_recovery_strategy(error)
    error_details["recovery_strategy"] = {
        "name": strategy_name,
        "params": strategy_params
    }
    
    # Add user-friendly message
    error_details["user_message"] = error_to_user_message(error)
    
    # Re-raise if requested
    if raise_error:
        raise error
    
    return error_details 