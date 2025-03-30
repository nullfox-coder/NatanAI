"""
Tests for browser navigation functionality.

This module tests the navigation functionality of the browser module.
"""

import unittest
import asyncio
from tests.test_framework import BrowserTestCase, async_test, skip_if_no_browser
from browser.navigation import navigate_to, go_back, go_forward, refresh_page


class TestBrowserNavigation(BrowserTestCase):
    """Test case for browser navigation functionality."""

    @async_test
    async def test_navigate_to(self):
        """Test navigating to a URL."""
        # Set up
        page = self.mock_page
        self.browser_manager.get_current_page = asyncio.coroutine(lambda: page)
        
        # Test
        url = "https://example.com/test"
        result = await navigate_to(self.browser_manager, url)
        
        # Assert
        self.assertTrue(result)
        self.assertEqual(page.url, url)
        self.assertEqual(page.navigation_history[-1], url)

    @async_test
    async def test_go_back(self):
        """Test navigating back in history."""
        # Set up
        page = self.mock_page
        page.navigation_history = [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3"
        ]
        page.url = page.navigation_history[-1]
        self.browser_manager.get_current_page = asyncio.coroutine(lambda: page)
        
        # Test
        result = await go_back(self.browser_manager)
        
        # Assert
        self.assertTrue(result)
        self.assertEqual(page.url, "https://example.com/page2")

    @async_test
    async def test_go_forward(self):
        """Test navigating forward in history."""
        # Set up
        page = self.mock_page
        page.navigation_history = [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3"
        ]
        # Set current page to the middle of history
        page.url = page.navigation_history[1]
        self.browser_manager.get_current_page = asyncio.coroutine(lambda: page)
        
        # Test 
        result = await go_forward(self.browser_manager)
        
        # Assert
        self.assertTrue(result)
        self.assertEqual(page.url, "https://example.com/page3")

    @async_test
    async def test_refresh_page(self):
        """Test refreshing the current page."""
        # Set up
        page = self.mock_page
        page.url = "https://example.com/test"
        page.reload_called = False
        
        # Mock the reload method
        original_goto = page.goto
        
        async def mock_reload(**kwargs):
            page.reload_called = True
            await original_goto(page.url, **kwargs)
            
        page.reload = mock_reload
        self.browser_manager.get_current_page = asyncio.coroutine(lambda: page)
        
        # Test
        result = await refresh_page(self.browser_manager)
        
        # Assert
        self.assertTrue(result)
        self.assertTrue(page.reload_called)
        self.assertEqual(page.url, "https://example.com/test")

    @skip_if_no_browser
    @async_test
    async def test_navigate_to_real(self):
        """Test navigating to a URL with a real browser (integration test)."""
        # Initialize a real browser manager
        await self.browser_manager.initialize()
        
        try:
            # Create a page
            page = await self.browser_manager.create_page()
            
            # Navigate to a test URL
            url = "https://example.com"
            result = await navigate_to(self.browser_manager, url)
            
            # Assert
            self.assertTrue(result)
            current_page = await self.browser_manager.get_current_page()
            self.assertTrue(current_page.url.startswith("https://example.com"))
            
        finally:
            # Clean up
            await self.browser_manager.cleanup()


if __name__ == '__main__':
    unittest.main() 