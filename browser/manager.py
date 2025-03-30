"""
Browser lifecycle management module.

This module provides functionality for managing the lifecycle of browser
instances, including launching, closing, and creating new contexts.
"""

import logging
import asyncio
import uuid
from typing import Dict, List, Any, Optional, Set

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright

from config.settings import Settings

# Set up logger
logger = logging.getLogger(__name__)


class BrowserManager:
    """
    Browser manager for browser automation.
    
    Manages the lifecycle of browser instances, including launching, closing,
    and creating new contexts.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the browser manager.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.contexts: Dict[str, BrowserContext] = {}
        self.default_context_id: Optional[str] = None
        self.initialized = False
    
    async def initialize(self) -> None:
        """Initialize the browser manager."""
        if self.initialized:
            logger.debug("Browser manager already initialized")
            return
        
        logger.info("Initializing browser manager")
        
        try:
            # Launch playwright
            self.playwright = await async_playwright().start()
            
            # Select browser type
            browser_type = self.settings.browser_type.lower()
            if browser_type == "chromium":
                browser_launcher = self.playwright.chromium
            elif browser_type == "firefox":
                browser_launcher = self.playwright.firefox
            elif browser_type == "webkit":
                browser_launcher = self.playwright.webkit
            else:
                logger.warning(f"Invalid browser type: {browser_type}, defaulting to chromium")
                browser_launcher = self.playwright.chromium
            
            # Launch browser
            self.browser = await browser_launcher.launch(
                headless=self.settings.headless,
                args=self.settings.browser_args,
                slow_mo=self.settings.slow_mo
            )
            
            # Create default context
            default_context = await self.create_context()
            self.default_context_id = default_context["id"]
            
            self.initialized = True
            logger.info(f"Browser manager initialized with {browser_type} browser")
            
        except Exception as e:
            logger.error(f"Error initializing browser manager: {str(e)}")
            await self.cleanup()
            raise
    
    async def cleanup(self) -> None:
        """Clean up resources used by the browser manager."""
        logger.info("Cleaning up browser manager resources")
        
        # Close all contexts
        for context_id, context in list(self.contexts.items()):
            try:
                await context.close()
                logger.debug(f"Closed browser context: {context_id}")
            except Exception as e:
                logger.warning(f"Error closing browser context {context_id}: {str(e)}")
        
        self.contexts = {}
        
        # Close browser
        if self.browser:
            try:
                await self.browser.close()
                logger.debug("Closed browser")
            except Exception as e:
                logger.warning(f"Error closing browser: {str(e)}")
            
            self.browser = None
        
        # Close playwright
        if self.playwright:
            try:
                await self.playwright.stop()
                logger.debug("Stopped playwright")
            except Exception as e:
                logger.warning(f"Error stopping playwright: {str(e)}")
            
            self.playwright = None
        
        self.initialized = False
        logger.info("Browser manager cleanup complete")
    
    async def create_context(self, user_agent: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new browser context.
        
        Args:
            user_agent: Optional user agent string for the context
            
        Returns:
            Information about the created context
        """
        if not self.initialized:
            await self.initialize()
        
        # Generate context ID
        context_id = str(uuid.uuid4())
        
        # Set up context options
        context_options = {
            "viewport": {
                "width": self.settings.viewport_width,
                "height": self.settings.viewport_height
            }
        }
        
        # Set user agent if provided
        if user_agent:
            context_options["user_agent"] = user_agent
        elif self.settings.user_agent:
            context_options["user_agent"] = self.settings.user_agent
        
        # Create context
        context = await self.browser.new_context(**context_options)
        
        # Set default timeouts
        context.set_default_navigation_timeout(self.settings.navigation_timeout)
        context.set_default_timeout(self.settings.action_timeout)
        
        # Store context
        self.contexts[context_id] = context
        
        logger.info(f"Created new browser context: {context_id}")
        
        return {
            "id": context_id,
            "user_agent": context_options.get("user_agent"),
            "viewport": context_options.get("viewport")
        }
    
    async def get_context(self, context_id: str) -> Optional[BrowserContext]:
        """
        Get a browser context by ID.
        
        Args:
            context_id: The ID of the context to retrieve
            
        Returns:
            The browser context or None if not found
        """
        return self.contexts.get(context_id)
    
    async def get_or_create_context(self, session_id: str) -> BrowserContext:
        """
        Get a browser context for a session, creating one if needed.
        
        Args:
            session_id: The session ID to get or create a context for
            
        Returns:
            The browser context for the session
        """
        if not self.initialized:
            await self.initialize()
        
        # Use session ID as context ID for simplicity
        if session_id in self.contexts:
            return self.contexts[session_id]
        
        # Create a new context for this session
        context_info = await self.create_context()
        context_id = context_info["id"]
        
        # Associate the new context with the session ID
        if context_id != session_id:
            self.contexts[session_id] = self.contexts[context_id]
            # We can remove the original entry since we've aliased it
            del self.contexts[context_id]
        
        return self.contexts[session_id]
    
    async def close_context(self, context_id: str) -> bool:
        """
        Close a browser context.
        
        Args:
            context_id: The ID of the context to close
            
        Returns:
            True if the context was closed, False otherwise
        """
        context = self.contexts.get(context_id)
        
        if not context:
            logger.warning(f"Cannot close context, not found: {context_id}")
            return False
        
        try:
            await context.close()
            del self.contexts[context_id]
            
            logger.info(f"Closed browser context: {context_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error closing browser context {context_id}: {str(e)}")
            return False
    
    async def get_page(self, context_id: Optional[str] = None) -> Page:
        """
        Get the current page from a context.
        
        Args:
            context_id: The ID of the context to get the page from, or None to use default
            
        Returns:
            The current page from the context
            
        Raises:
            ValueError: If the context has no pages
        """
        # Use default context if not specified
        if not context_id:
            context_id = self.default_context_id
            
            # Create default context if needed
            if not context_id or context_id not in self.contexts:
                default_context = await self.create_context()
                self.default_context_id = default_context["id"]
                context_id = self.default_context_id
        
        context = self.contexts.get(context_id)
        
        if not context:
            raise ValueError(f"Browser context not found: {context_id}")
        
        # Get existing pages
        pages = context.pages
        
        if not pages:
            # Create a new page
            page = await context.new_page()
            logger.debug(f"Created new page in context {context_id}")
            return page
        
        # Return the last page in the context
        return pages[-1]
    
    async def create_new_page(self, context_id: Optional[str] = None) -> Page:
        """
        Create a new page in a context.
        
        Args:
            context_id: The ID of the context to create the page in, or None to use default
            
        Returns:
            The newly created page
        """
        # Use default context if not specified
        if not context_id:
            context_id = self.default_context_id
            
            # Create default context if needed
            if not context_id or context_id not in self.contexts:
                default_context = await self.create_context()
                self.default_context_id = default_context["id"]
                context_id = self.default_context_id
        
        context = self.contexts.get(context_id)
        
        if not context:
            raise ValueError(f"Browser context not found: {context_id}")
        
        # Create a new page
        page = await context.new_page()
        logger.debug(f"Created new page in context {context_id}")
        
        return page
    
    async def create_persistent_context(self, user_data_dir: str) -> Dict[str, Any]:
        """
        Create a persistent browser context.
        
        Args:
            user_data_dir: Directory to store persistent browser data
            
        Returns:
            Information about the created context
        """
        if not self.initialized:
            await self.initialize()
        
        # Generate context ID
        context_id = str(uuid.uuid4())
        
        # Set up context options
        context_options = {
            "viewport": {
                "width": self.settings.viewport_width,
                "height": self.settings.viewport_height
            },
            "user_data_dir": user_data_dir
        }
        
        # Set user agent if provided
        if self.settings.user_agent:
            context_options["user_agent"] = self.settings.user_agent
        
        # Select browser type
        browser_type = self.settings.browser_type.lower()
        if browser_type == "chromium":
            browser_launcher = self.playwright.chromium
        elif browser_type == "firefox":
            browser_launcher = self.playwright.firefox
        elif browser_type == "webkit":
            browser_launcher = self.playwright.webkit
        else:
            logger.warning(f"Invalid browser type: {browser_type}, defaulting to chromium")
            browser_launcher = self.playwright.chromium
        
        # Launch persistent context
        context = await browser_launcher.launch_persistent_context(
            user_data_dir,
            headless=self.settings.headless,
            args=self.settings.browser_args,
            slow_mo=self.settings.slow_mo,
            **context_options
        )
        
        # Set default timeouts
        context.set_default_navigation_timeout(self.settings.navigation_timeout)
        context.set_default_timeout(self.settings.action_timeout)
        
        # Store context
        self.contexts[context_id] = context
        
        logger.info(f"Created new persistent browser context: {context_id}")
        
        return {
            "id": context_id,
            "user_agent": context_options.get("user_agent"),
            "viewport": context_options.get("viewport"),
            "user_data_dir": user_data_dir
        }
    
    async def capture_screenshot(
        self,
        context_id: Optional[str] = None,
        page_index: int = -1,
        full_page: bool = True
    ) -> bytes:
        """
        Capture a screenshot from a page.
        
        Args:
            context_id: The ID of the context to capture from, or None to use default
            page_index: The index of the page to capture, -1 for last page
            full_page: Whether to capture the full page or just the viewport
            
        Returns:
            The screenshot as bytes
        """
        # Get the context
        if not context_id:
            context_id = self.default_context_id
        
        context = self.contexts.get(context_id)
        
        if not context:
            raise ValueError(f"Browser context not found: {context_id}")
        
        # Get the page
        pages = context.pages
        
        if not pages:
            raise ValueError("No pages in context")
        
        # Get the specified page
        if page_index < 0:
            page_index = len(pages) + page_index
        
        if page_index < 0 or page_index >= len(pages):
            raise ValueError(f"Invalid page index: {page_index}")
        
        page = pages[page_index]
        
        # Capture screenshot
        screenshot = await page.screenshot(full_page=full_page)
        
        return screenshot
