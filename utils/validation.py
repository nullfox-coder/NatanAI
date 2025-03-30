"""
Validation utilities module.

This module provides data validation utilities for the application.
"""

import re
import json
import logging
from typing import Dict, Any, Optional, List, Union, Callable, TypeVar, Generic, Type
from urllib.parse import urlparse

from utils.errors import ValidationError

# Set up logger
logger = logging.getLogger(__name__)

# Type variables for generic functions
T = TypeVar('T')


def validate_url(url: str, allow_relative: bool = False) -> bool:
    """
    Validate a URL.
    
    Args:
        url: The URL to validate
        allow_relative: Whether to allow relative URLs
        
    Returns:
        True if valid, False otherwise
    """
    if not url:
        return False
        
    # Handle relative URLs if allowed
    if allow_relative and url.startswith('/'):
        return True
        
    try:
        result = urlparse(url)
        # Check for scheme and netloc (hostname)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def validate_email(email: str) -> bool:
    """
    Validate an email address.
    
    Args:
        email: The email to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not email:
        return False
        
    # Simple regex for email validation
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_integer(
    value: Any,
    min_value: Optional[int] = None,
    max_value: Optional[int] = None
) -> bool:
    """
    Validate an integer.
    
    Args:
        value: The value to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        
    Returns:
        True if valid, False otherwise
    """
    try:
        # Convert to int if string
        if isinstance(value, str):
            value = int(value)
        elif not isinstance(value, int) or isinstance(value, bool):
            return False
            
        # Check range if specified
        if min_value is not None and value < min_value:
            return False
        if max_value is not None and value > max_value:
            return False
            
        return True
    except (ValueError, TypeError):
        return False


def validate_float(
    value: Any,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None
) -> bool:
    """
    Validate a float.
    
    Args:
        value: The value to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        
    Returns:
        True if valid, False otherwise
    """
    try:
        # Convert to float if string
        if isinstance(value, str):
            value = float(value)
        elif not isinstance(value, (int, float)) or isinstance(value, bool):
            return False
            
        # Check range if specified
        if min_value is not None and value < min_value:
            return False
        if max_value is not None and value > max_value:
            return False
            
        return True
    except (ValueError, TypeError):
        return False


def validate_string(
    value: Any,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    pattern: Optional[str] = None
) -> bool:
    """
    Validate a string.
    
    Args:
        value: The value to validate
        min_length: Minimum allowed length
        max_length: Maximum allowed length
        pattern: Regular expression pattern to match
        
    Returns:
        True if valid, False otherwise
    """
    if not isinstance(value, str):
        return False
        
    # Check length if specified
    if min_length is not None and len(value) < min_length:
        return False
    if max_length is not None and len(value) > max_length:
        return False
        
    # Check pattern if specified
    if pattern is not None and not re.match(pattern, value):
        return False
        
    return True


def validate_boolean(value: Any) -> bool:
    """
    Validate a boolean.
    
    Args:
        value: The value to validate
        
    Returns:
        True if valid, False otherwise
    """
    if isinstance(value, bool):
        return True
        
    # Handle string representations
    if isinstance(value, str):
        value = value.lower()
        return value in ('true', 'false', '1', '0', 'yes', 'no')
        
    # Handle integer representations
    if isinstance(value, int):
        return value in (0, 1)
        
    return False


def validate_list(
    value: Any,
    item_validator: Optional[Callable[[Any], bool]] = None,
    min_items: Optional[int] = None,
    max_items: Optional[int] = None
) -> bool:
    """
    Validate a list.
    
    Args:
        value: The value to validate
        item_validator: Function to validate individual items
        min_items: Minimum number of items
        max_items: Maximum number of items
        
    Returns:
        True if valid, False otherwise
    """
    if not isinstance(value, list):
        return False
        
    # Check item count if specified
    if min_items is not None and len(value) < min_items:
        return False
    if max_items is not None and len(value) > max_items:
        return False
        
    # Check items if validator specified
    if item_validator:
        return all(item_validator(item) for item in value)
        
    return True


def validate_dict(
    value: Any,
    required_keys: Optional[List[str]] = None,
    optional_keys: Optional[List[str]] = None,
    key_validators: Optional[Dict[str, Callable[[Any], bool]]] = None,
    allow_extra_keys: bool = True
) -> bool:
    """
    Validate a dictionary.
    
    Args:
        value: The value to validate
        required_keys: List of required keys
        optional_keys: List of optional keys
        key_validators: Dictionary of key-specific validator functions
        allow_extra_keys: Whether to allow keys not in required or optional lists
        
    Returns:
        True if valid, False otherwise
    """
    if not isinstance(value, dict):
        return False
        
    # Check required keys
    if required_keys:
        if not all(key in value for key in required_keys):
            return False
            
    # Validate against extra keys if not allowed
    if not allow_extra_keys and (required_keys or optional_keys):
        allowed_keys = set(required_keys or []) | set(optional_keys or [])
        if not set(value.keys()).issubset(allowed_keys):
            return False
            
    # Validate values with key validators
    if key_validators:
        for key, validator in key_validators.items():
            if key in value and not validator(value[key]):
                return False
                
    return True


def validate_json(value: Any) -> bool:
    """
    Validate JSON string.
    
    Args:
        value: The value to validate
        
    Returns:
        True if valid JSON, False otherwise
    """
    if not isinstance(value, str):
        return False
        
    try:
        json.loads(value)
        return True
    except json.JSONDecodeError:
        return False


class Validator(Generic[T]):
    """
    Generic validator for data objects.
    """
    
    def __init__(
        self,
        name: str,
        validators: Dict[str, Dict[str, Any]],
        required_fields: Optional[List[str]] = None
    ):
        """
        Initialize the validator.
        
        Args:
            name: Name of the model being validated
            validators: Dictionary of field validators
            required_fields: List of required fields
        """
        self.name = name
        self.validators = validators
        self.required_fields = required_fields or []
    
    def validate(self, data: Dict[str, Any]) -> List[str]:
        """
        Validate data against the model.
        
        Args:
            data: The data to validate
            
        Returns:
            List of validation errors, empty if valid
        """
        errors = []
        
        # Check required fields
        for field in self.required_fields:
            if field not in data or data[field] is None:
                errors.append(f"Field '{field}' is required")
                
        # Validate fields
        for field, field_def in self.validators.items():
            if field in data and data[field] is not None:
                field_errors = self._validate_field(field, data[field], field_def)
                errors.extend(field_errors)
                
        return errors
    
    def _validate_field(
        self, 
        field_name: str, 
        value: Any, 
        field_def: Dict[str, Any]
    ) -> List[str]:
        """
        Validate a single field.
        
        Args:
            field_name: Name of the field
            value: Value to validate
            field_def: Field validation definition
            
        Returns:
            List of validation errors, empty if valid
        """
        errors = []
        field_type = field_def.get('type', 'any')
        
        # Type validation
        if field_type == 'string':
            if not isinstance(value, str):
                errors.append(f"Field '{field_name}' must be a string")
            else:
                # String-specific validation
                min_length = field_def.get('min_length')
                max_length = field_def.get('max_length')
                pattern = field_def.get('pattern')
                
                if min_length is not None and len(value) < min_length:
                    errors.append(f"Field '{field_name}' must be at least {min_length} characters")
                    
                if max_length is not None and len(value) > max_length:
                    errors.append(f"Field '{field_name}' must be at most {max_length} characters")
                    
                if pattern is not None and not re.match(pattern, value):
                    errors.append(f"Field '{field_name}' must match pattern {pattern}")
                    
        elif field_type == 'integer':
            if not isinstance(value, int) or isinstance(value, bool):
                errors.append(f"Field '{field_name}' must be an integer")
            else:
                # Integer-specific validation
                min_value = field_def.get('min_value')
                max_value = field_def.get('max_value')
                
                if min_value is not None and value < min_value:
                    errors.append(f"Field '{field_name}' must be at least {min_value}")
                    
                if max_value is not None and value > max_value:
                    errors.append(f"Field '{field_name}' must be at most {max_value}")
                    
        elif field_type == 'number' or field_type == 'float':
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                errors.append(f"Field '{field_name}' must be a number")
            else:
                # Number-specific validation
                min_value = field_def.get('min_value')
                max_value = field_def.get('max_value')
                
                if min_value is not None and value < min_value:
                    errors.append(f"Field '{field_name}' must be at least {min_value}")
                    
                if max_value is not None and value > max_value:
                    errors.append(f"Field '{field_name}' must be at most {max_value}")
                    
        elif field_type == 'boolean':
            if not isinstance(value, bool):
                errors.append(f"Field '{field_name}' must be a boolean")
                
        elif field_type == 'array' or field_type == 'list':
            if not isinstance(value, list):
                errors.append(f"Field '{field_name}' must be an array")
            else:
                # Array-specific validation
                min_items = field_def.get('min_items')
                max_items = field_def.get('max_items')
                
                if min_items is not None and len(value) < min_items:
                    errors.append(f"Field '{field_name}' must have at least {min_items} items")
                    
                if max_items is not None and len(value) > max_items:
                    errors.append(f"Field '{field_name}' must have at most {max_items} items")
                    
                # Validate items if item schema provided
                item_schema = field_def.get('items')
                if item_schema:
                    for i, item in enumerate(value):
                        item_errors = self._validate_field(
                            f"{field_name}[{i}]", 
                            item, 
                            item_schema
                        )
                        errors.extend(item_errors)
                        
        elif field_type == 'object' or field_type == 'dict':
            if not isinstance(value, dict):
                errors.append(f"Field '{field_name}' must be an object")
            else:
                # Object-specific validation
                properties = field_def.get('properties', {})
                required = field_def.get('required', [])
                
                # Check required properties
                for req_field in required:
                    if req_field not in value or value[req_field] is None:
                        errors.append(f"Field '{field_name}.{req_field}' is required")
                        
                # Validate properties
                for prop_name, prop_schema in properties.items():
                    if prop_name in value and value[prop_name] is not None:
                        prop_errors = self._validate_field(
                            f"{field_name}.{prop_name}", 
                            value[prop_name], 
                            prop_schema
                        )
                        errors.extend(prop_errors)
                        
        # Enum validation
        enum_values = field_def.get('enum')
        if enum_values is not None and value not in enum_values:
            errors.append(f"Field '{field_name}' must be one of {enum_values}")
            
        # Custom validator function
        validator_func = field_def.get('validator')
        if validator_func and callable(validator_func):
            if not validator_func(value):
                errors.append(f"Field '{field_name}' failed custom validation")
                
        return errors
    
    def validate_or_raise(self, data: Dict[str, Any]) -> None:
        """
        Validate data and raise exception if invalid.
        
        Args:
            data: The data to validate
            
        Raises:
            ValidationError: If validation fails
        """
        errors = self.validate(data)
        if errors:
            error_msg = f"Validation failed for {self.name}: {', '.join(errors)}"
            logger.warning(error_msg)
            raise ValidationError(error_msg, details={"errors": errors}) 