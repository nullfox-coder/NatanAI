"""
Helper utilities module.

This module provides general-purpose helper functions for the application.
"""

import os
import re
import uuid
import json
import time
import random
import hashlib
import datetime
from typing import Dict, List, Any, Optional, Union, Tuple, Callable, TypeVar, Generic

T = TypeVar('T')


def generate_id(prefix: str = "") -> str:
    """
    Generate a unique ID.
    
    Args:
        prefix: Optional prefix for the ID
        
    Returns:
        A unique ID string
    """
    unique_id = str(uuid.uuid4())
    if prefix:
        return f"{prefix}_{unique_id}"
    return unique_id


def generate_timestamp() -> int:
    """
    Generate a current timestamp in milliseconds.
    
    Returns:
        Current timestamp in milliseconds
    """
    return int(time.time() * 1000)


def format_timestamp(
    timestamp: Union[int, float],
    format_str: str = "%Y-%m-%d %H:%M:%S"
) -> str:
    """
    Format a timestamp into a human-readable string.
    
    Args:
        timestamp: Timestamp in seconds or milliseconds
        format_str: Format string for the result
        
    Returns:
        Formatted timestamp string
    """
    # Convert to seconds if in milliseconds
    if timestamp > 1e10:  # More than 10 billion means it's in milliseconds
        timestamp /= 1000
        
    dt = datetime.datetime.fromtimestamp(timestamp)
    return dt.strftime(format_str)


def throttle(func: Callable, rate_limit: float) -> Callable:
    """
    Decorator to throttle a function call rate.
    
    Args:
        func: Function to throttle
        rate_limit: Minimum time between calls in seconds
        
    Returns:
        Throttled function
    """
    last_called = [0.0]  # Use a list for nonlocal mutable value
    
    def wrapper(*args, **kwargs):
        now = time.time()
        elapsed = now - last_called[0]
        
        if elapsed < rate_limit:
            time.sleep(rate_limit - elapsed)
            
        last_called[0] = time.time()
        return func(*args, **kwargs)
        
    return wrapper


def retry(
    max_attempts: int = 3,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
    delay: float = 1.0,
    backoff: float = 2.0,
    logger: Optional[Any] = None
) -> Callable:
    """
    Decorator for retrying a function upon exception.
    
    Args:
        max_attempts: Maximum number of retry attempts
        exceptions: Exception types to catch and retry
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier
        logger: Optional logger to log retries
        
    Returns:
        Retry decorator
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            attempt = 0
            current_delay = delay
            
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        raise
                        
                    if logger:
                        logger.warning(
                            f"Retry {attempt}/{max_attempts} for {func.__name__} "
                            f"due to {type(e).__name__}: {str(e)}"
                        )
                        
                    time.sleep(current_delay)
                    current_delay *= backoff
                    
        return wrapper
    return decorator


def chunks(lst: List[T], n: int) -> List[List[T]]:
    """
    Split a list into chunks of size n.
    
    Args:
        lst: List to split
        n: Maximum chunk size
        
    Returns:
        List of chunks
    """
    return [lst[i:i + n] for i in range(0, len(lst), n)]


def deep_get(d: Dict[str, Any], keys: Union[str, List[str]], default: Any = None) -> Any:
    """
    Safely access nested dictionary values.
    
    Args:
        d: Dictionary to access
        keys: Key path as string with dots or list of keys
        default: Default value if path not found
        
    Returns:
        Value at the key path or default
    """
    if not isinstance(d, dict):
        return default
        
    if isinstance(keys, str):
        keys = keys.split('.')
        
    if not keys:
        return d
        
    key = keys[0]
    if key not in d:
        return default
        
    if len(keys) == 1:
        return d[key]
        
    return deep_get(d[key], keys[1:], default)


def deep_set(d: Dict[str, Any], keys: Union[str, List[str]], value: Any) -> Dict[str, Any]:
    """
    Set a value in a nested dictionary, creating intermediate dictionaries as needed.
    
    Args:
        d: Dictionary to modify
        keys: Key path as string with dots or list of keys
        value: Value to set
        
    Returns:
        Modified dictionary
    """
    if isinstance(keys, str):
        keys = keys.split('.')
        
    if not keys:
        return d
        
    key = keys[0]
    if len(keys) == 1:
        d[key] = value
        return d
        
    if key not in d or not isinstance(d[key], dict):
        d[key] = {}
        
    deep_set(d[key], keys[1:], value)
    return d


def deep_merge(d1: Dict[str, Any], d2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively merge two dictionaries.
    
    Args:
        d1: First dictionary (modified in-place)
        d2: Second dictionary (values override d1)
        
    Returns:
        Merged dictionary (d1 modified in-place)
    """
    for key, value in d2.items():
        if key in d1 and isinstance(d1[key], dict) and isinstance(value, dict):
            deep_merge(d1[key], value)
        else:
            d1[key] = value
    return d1


def safe_json_serialize(obj: Any) -> Any:
    """
    Convert an object to a JSON-serializable representation.
    
    Args:
        obj: Object to serialize
        
    Returns:
        JSON-serializable representation of the object
    """
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: safe_json_serialize(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple, set)):
        return [safe_json_serialize(v) for v in obj]
    elif hasattr(obj, "to_dict"):
        return safe_json_serialize(obj.to_dict())
    elif hasattr(obj, "__dict__"):
        return safe_json_serialize(obj.__dict__)
    else:
        return str(obj)


def truncate_string(s: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate a string to a maximum length.
    
    Args:
        s: String to truncate
        max_length: Maximum length
        suffix: Suffix to add to truncated string
        
    Returns:
        Truncated string
    """
    if not s or len(s) <= max_length:
        return s
    return s[:max_length-len(suffix)] + suffix


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing unsafe characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Replace unsafe characters with underscore
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove control characters
    sanitized = re.sub(r'[\x00-\x1F\x7F]', '', sanitized)
    
    # Ensure file name is not empty
    if not sanitized or sanitized.isspace():
        sanitized = 'file'
        
    return sanitized


def human_readable_size(size_bytes: int) -> str:
    """
    Convert bytes to a human-readable size string.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Human-readable size string
    """
    if size_bytes < 0:
        raise ValueError("Size must be non-negative")
        
    if size_bytes == 0:
        return "0 B"
        
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    i = 0
    while size_bytes >= 1024 and i < len(units) - 1:
        size_bytes /= 1024
        i += 1
        
    return f"{size_bytes:.2f} {units[i]}"


def extract_urls_from_text(text: str) -> List[str]:
    """
    Extract URLs from text.
    
    Args:
        text: Text to extract URLs from
        
    Returns:
        List of extracted URLs
    """
    # URL regular expression pattern
    url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
    return re.findall(url_pattern, text)


def hash_string(s: str, algorithm: str = 'sha256') -> str:
    """
    Generate a hash of a string.
    
    Args:
        s: String to hash
        algorithm: Hash algorithm to use (md5, sha1, sha256, sha512)
        
    Returns:
        Hex digest of the hash
    """
    if algorithm == 'md5':
        return hashlib.md5(s.encode()).hexdigest()
    elif algorithm == 'sha1':
        return hashlib.sha1(s.encode()).hexdigest()
    elif algorithm == 'sha512':
        return hashlib.sha512(s.encode()).hexdigest()
    else:  # Default to sha256
        return hashlib.sha256(s.encode()).hexdigest()


def ensure_dir(directory: str) -> None:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory: Directory path
    """
    if not os.path.exists(directory):
        os.makedirs(directory)


def is_valid_json(json_str: str) -> bool:
    """
    Check if a string is valid JSON.
    
    Args:
        json_str: String to check
        
    Returns:
        True if valid JSON, False otherwise
    """
    try:
        json.loads(json_str)
        return True
    except Exception:
        return False


def random_delay(min_delay: float = 0.5, max_delay: float = 2.0) -> None:
    """
    Sleep for a random amount of time within a range.
    
    Args:
        min_delay: Minimum delay in seconds
        max_delay: Maximum delay in seconds
    """
    delay = random.uniform(min_delay, max_delay)
    time.sleep(delay)


def extract_domain(url: str) -> str:
    """
    Extract the domain from a URL.
    
    Args:
        url: URL to extract domain from
        
    Returns:
        Domain name
    """
    if not url:
        return ""
        
    # Match domain in URL
    match = re.search(r'https?://(?:www\.)?([^/]+)', url)
    if match:
        return match.group(1)
        
    return ""
