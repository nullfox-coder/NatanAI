"""
Test framework for the browser automation application.

This module provides base classes and utilities for testing the application.
"""

import os
import sys
import time
import json
import asyncio
import logging
import unittest
from typing import Dict, List, Any, Optional, Union, Callable, Awaitable, Type
from unittest.mock import MagicMock, patch

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import application modules
from config.settings import Settings, load_settings
from browser.manager import BrowserManager
from controller.workflow import WorkflowController
from controller.session import SessionManager
from controller.state import StateTracker
from utils.errors import BrowserAIError
from utils.logging import setup_logging


class MockElementHandle:
    """Mock ElementHandle for testing element interactions."""
    
    def __init__(self, element_id: str = "mock_element", tag_name: str = "div",
                 attributes: Dict[str, str] = None, text_content: str = "Mock Element"):
        self.element_id = element_id
        self.tag_name = tag_name
        self.attributes = attributes or {}
        self.text_content = text_content
        self.is_visible_value = True
        self.children = []
        
    async def get_attribute(self, name: str) -> Optional[str]:
        """Mock get_attribute method."""
        return self.attributes.get(name)
        
    async def text_content(self) -> str:
        """Mock text_content method."""
        return self.text_content
        
    async def is_visible(self) -> bool:
        """Mock is_visible method."""
        return self.is_visible_value
        
    async def query_selector(self, selector: str) -> Optional['MockElementHandle']:
        """Mock query_selector method."""
        # Simple mock implementation that returns first child if any exist
        return self.children[0] if self.children else None
        
    async def query_selector_all(self, selector: str) -> List['MockElementHandle']:
        """Mock query_selector_all method."""
        return self.children
        
    def set_is_visible(self, visible: bool):
        """Set is_visible return value."""
        self.is_visible_value = visible
        
    def add_child(self, child: 'MockElementHandle'):
        """Add a child element."""
        self.children.append(child)


class MockPage:
    """Mock Page for testing page interactions."""
    
    def __init__(self, url: str = "https://example.com", title: str = "Example Page"):
        self.url = url
        self.title = title
        self.content = "<html><body><h1>Mock Page</h1></body></html>"
        self.elements = {}  # Maps selectors to MockElementHandle objects
        self.navigation_history = []
        self.screenshot_data = b"mock_screenshot_data"
        self.cookies = []
        self.event_listeners = {}
        
    async def goto(self, url: str, **kwargs) -> None:
        """Mock goto method."""
        self.url = url
        self.navigation_history.append(url)
        
    async def get_by_role(self, role: str, **kwargs) -> 'MockElementHandle':
        """Mock get_by_role method."""
        # Return a mock element for the specified role
        element = MockElementHandle(element_id=f"mock_{role}", tag_name="div")
        return element
        
    async def query_selector(self, selector: str) -> Optional[MockElementHandle]:
        """Mock query_selector method."""
        return self.elements.get(selector)
        
    async def query_selector_all(self, selector: str) -> List[MockElementHandle]:
        """Mock query_selector_all method."""
        if selector in self.elements:
            return [self.elements[selector]]
        return []
        
    async def evaluate(self, js_code: str, *args) -> Any:
        """Mock evaluate method."""
        # Return mock data based on the js_code
        if "document.title" in js_code:
            return self.title
        if "document.documentElement.outerHTML" in js_code:
            return self.content
        return None
        
    async def screenshot(self, **kwargs) -> bytes:
        """Mock screenshot method."""
        return self.screenshot_data
        
    async def get_cookies(self) -> List[Dict[str, Any]]:
        """Mock get_cookies method."""
        return self.cookies
        
    async def set_cookie(self, cookie: Dict[str, Any]) -> None:
        """Mock set_cookie method."""
        self.cookies.append(cookie)
        
    async def add_event_listener(self, event: str, callback: Callable) -> None:
        """Mock add_event_listener method."""
        if event not in self.event_listeners:
            self.event_listeners[event] = []
        self.event_listeners[event].append(callback)
        
    def add_mock_element(self, selector: str, element: MockElementHandle) -> None:
        """Add a mock element for a selector."""
        self.elements[selector] = element
        
    def set_content(self, content: str) -> None:
        """Set page content."""
        self.content = content


class MockBrowserContext:
    """Mock BrowserContext for testing browser context interactions."""
    
    def __init__(self, browser_type: str = "chromium"):
        self.browser_type = browser_type
        self.id = "mock_context_id"
        self.pages = []
        self.is_closed = False
        
    async def new_page(self) -> MockPage:
        """Mock new_page method."""
        page = MockPage()
        self.pages.append(page)
        return page
        
    async def close(self) -> None:
        """Mock close method."""
        self.is_closed = True


class MockBrowser:
    """Mock Browser for testing browser interactions."""
    
    def __init__(self, browser_type: str = "chromium"):
        self.browser_type = browser_type
        self.contexts = []
        self.is_closed = False
        
    async def new_context(self, **kwargs) -> MockBrowserContext:
        """Mock new_context method."""
        context = MockBrowserContext(self.browser_type)
        self.contexts.append(context)
        return context
        
    async def close(self) -> None:
        """Mock close method."""
        self.is_closed = True


class MockPlaywright:
    """Mock Playwright for testing."""
    
    def __init__(self):
        self.chromium = MockBrowserLauncher("chromium")
        self.firefox = MockBrowserLauncher("firefox")
        self.webkit = MockBrowserLauncher("webkit")
        
    async def stop(self) -> None:
        """Mock stop method."""
        pass


class MockBrowserLauncher:
    """Mock Browser Launcher for testing."""
    
    def __init__(self, browser_type: str):
        self.browser_type = browser_type
        
    async def launch(self, **kwargs) -> MockBrowser:
        """Mock launch method."""
        return MockBrowser(self.browser_type)


class BaseTestCase(unittest.TestCase):
    """Base test case for application tests."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test class."""
        # Configure logging
        cls.logger = setup_logging(log_level="DEBUG")
        
        # Load settings from test config
        cls.settings = load_settings(config_path="config/test_settings.json")
        if not cls.settings:
            cls.settings = Settings()  # Use default settings if test settings not found
            
        # Set test config values
        cls.settings.testing = True
        cls.settings.headless = True
        cls.settings.browser_type = "chromium"
        
        # Create event loop for async tests
        cls.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(cls.loop)
    
    @classmethod
    def tearDownClass(cls):
        """Tear down test class."""
        cls.loop.close()
    
    def setUp(self):
        """Set up test case."""
        # Create mocks
        self.mock_playwright = MockPlaywright()
        self.mock_browser = MockBrowser()
        self.mock_context = MockBrowserContext()
        self.mock_page = MockPage()
        
        # Common patches
        self.playwright_patch = patch('playwright.async_api.async_playwright')
        self.mock_async_playwright = self.playwright_patch.start()
        self.mock_async_playwright.return_value.__aenter__.return_value = self.mock_playwright
        
    def tearDown(self):
        """Tear down test case."""
        # Stop patches
        self.playwright_patch.stop()
    
    def run_async(self, coro):
        """Run coroutine in the event loop."""
        return self.loop.run_until_complete(coro)


class BrowserTestCase(BaseTestCase):
    """Test case specifically for browser-related tests."""
    
    def setUp(self):
        """Set up test case."""
        super().setUp()
        
        # Create browser manager with mocks
        self.browser_manager = BrowserManager(self.settings)
        self.browser_manager._browser = self.mock_browser
        self.browser_manager._context = self.mock_context
        self.browser_manager._playwright = self.mock_playwright
        
    def tearDown(self):
        """Tear down test case."""
        # Clean up browser manager
        self.run_async(self.browser_manager.cleanup())
        super().tearDown()


class ControllerTestCase(BaseTestCase):
    """Test case specifically for controller-related tests."""
    
    def setUp(self):
        """Set up test case."""
        super().setUp()
        
        # Create mocked dependencies
        self.mock_browser_manager = MagicMock(spec=BrowserManager)
        self.mock_session_manager = MagicMock(spec=SessionManager)
        self.mock_state_tracker = MagicMock(spec=StateTracker)
        
        # Create workflow controller with mocks
        self.workflow = WorkflowController(
            settings=self.settings,
            browser_manager=self.mock_browser_manager,
            session_manager=self.mock_session_manager,
            state_tracker=self.mock_state_tracker
        )
        
    def tearDown(self):
        """Tear down test case."""
        # Clean up controller
        self.run_async(self.workflow.cleanup())
        super().tearDown()


class EndToEndTestCase(BaseTestCase):
    """Test case for end-to-end tests."""
    
    def setUp(self):
        """Set up test case."""
        super().setUp()
        
        # Create real components for end-to-end testing
        self.browser_manager = BrowserManager(self.settings)
        self.session_manager = SessionManager(self.settings)
        self.state_tracker = StateTracker(self.settings)
        
        # Create workflow controller
        self.workflow = WorkflowController(
            settings=self.settings,
            browser_manager=self.browser_manager,
            session_manager=self.session_manager,
            state_tracker=self.state_tracker
        )
        
        # Initialize components
        self.run_async(self.workflow.initialize())
        
    def tearDown(self):
        """Tear down test case."""
        # Clean up components
        self.run_async(self.workflow.cleanup())
        super().tearDown()


def async_test(coro):
    """Decorator for running async test functions."""
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro(*args, **kwargs))
    return wrapper


def skip_if_no_browser(test_func):
    """Decorator to skip tests if browser is not available."""
    async def check_browser():
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                await browser.close()
            return True
        except Exception:
            return False
    
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        browser_available = loop.run_until_complete(check_browser())
        if not browser_available:
            raise unittest.SkipTest("Browser not available for testing")
        return test_func(*args, **kwargs)
    
    return wrapper 