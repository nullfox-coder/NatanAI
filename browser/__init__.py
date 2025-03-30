"""
Browser automation module for the Browser AI Agent.

This module provides functionality for browser automation, including launching
browsers, navigating web pages, and interacting with elements.
"""

from browser.manager import BrowserManager
from browser.actions import perform_action
from browser.elements import find_element, get_visible_elements
from browser.navigation import navigate_to, wait_for_navigation, get_page_info
from browser.data import extract_page_text, extract_main_content, extract_data_by_query

__all__ = [
    'BrowserManager', 
    'perform_action',
    'find_element',
    'get_visible_elements',
    'navigate_to',
    'wait_for_navigation',
    'get_page_info',
    'extract_page_text',
    'extract_main_content',
    'extract_data_by_query'
]
