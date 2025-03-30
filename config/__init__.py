"""
Configuration module for the Browser AI Agent.

This module provides global settings and prompt templates for the application.
"""

from config.settings import Settings
from config.prompts import get_prompt

__all__ = ['Settings', 'get_prompt']
