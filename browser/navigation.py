"""
Browser navigation module.

This module provides functionality for navigation operations such as
navigating to URLs, managing history, and handling redirects.
"""

import logging
import re
import time
from typing import Dict, List, Any, Optional

from playwright.async_api import Page, Response, Error as PlaywrightError

from config.settings import Settings

# Set up logger
logger = logging.getLogger(__name__)


async def navigate_to(
    page: Page, 
    url: str, 
    settings: Settings,
    wait_until: str = "load",
    timeout: Optional[int] = None
) -> Dict[str, Any]:
    """
    Navigate to a URL.
    
    Args:
        page: The page to navigate
        url: The URL to navigate to
        settings: Application settings
        wait_until: When to consider navigation finished (load, domcontentloaded, networkidle)
        timeout: Optional navigation timeout in milliseconds
        
    Returns:
        Result of the navigation
    """
    logger.info(f"Navigating to {url}")
    
    # Set default timeout if not specified
    if timeout is None:
        timeout = settings.navigation_timeout
    
    # Ensure URL has protocol
    if not url.startswith(('http://', 'https://')):
        # If URL contains a dot but no protocol, assume https
        if '.' in url and not ' ' in url:
            url = f"https://{url}"
        else:
            # Otherwise, assume it's a search term
            url = f"https://www.google.com/search?q={url.replace(' ', '+')}"
            logger.info(f"Converted input to search URL: {url}")
    
    try:
        # Perform the navigation
        response: Optional[Response] = await page.goto(
            url, 
            wait_until=wait_until, 
            timeout=timeout
        )
        
        # Get final URL (after any redirects)
        final_url = page.url
        
        # Check for successful navigation
        if response:
            status = response.status
            ok = response.ok
            
            if not ok:
                logger.warning(f"Navigation received non-OK status code: {status}")
                return {
                    "status": "warning",
                    "url": final_url,
                    "original_url": url,
                    "redirected": final_url != url,
                    "status_code": status,
                    "message": f"Page loaded with status code {status}"
                }
            
            return {
                "status": "success",
                "url": final_url,
                "original_url": url,
                "redirected": final_url != url,
                "status_code": status,
                "message": f"Successfully navigated to {final_url}"
            }
        else:
            # Response might be None for some cases like file://
            return {
                "status": "success",
                "url": final_url,
                "original_url": url,
                "redirected": final_url != url,
                "status_code": None,
                "message": f"Navigated to {final_url} (no response object)"
            }
            
    except PlaywrightError as e:
        logger.error(f"Navigation error: {str(e)}")
        
        # Check if navigation timeout
        if "timeout" in str(e).lower():
            return {
                "status": "error",
                "error": "timeout",
                "url": url,
                "message": f"Navigation timed out after {timeout}ms"
            }
        
        # Other error
        return {
            "status": "error",
            "error": str(e),
            "url": url,
            "message": f"Error navigating to {url}: {str(e)}"
        }


async def refresh_page(
    page: Page,
    settings: Settings,
    wait_until: str = "load",
    timeout: Optional[int] = None
) -> Dict[str, Any]:
    """
    Refresh the current page.
    
    Args:
        page: The page to refresh
        settings: Application settings
        wait_until: When to consider navigation finished (load, domcontentloaded, networkidle)
        timeout: Optional refresh timeout in milliseconds
        
    Returns:
        Result of the refresh
    """
    logger.info("Refreshing page")
    
    # Set default timeout if not specified
    if timeout is None:
        timeout = settings.navigation_timeout
    
    try:
        # Perform the refresh
        response = await page.reload(wait_until=wait_until, timeout=timeout)
        
        # Check for successful refresh
        if response:
            status = response.status
            ok = response.ok
            
            if not ok:
                logger.warning(f"Page refresh received non-OK status code: {status}")
                return {
                    "status": "warning",
                    "url": page.url,
                    "status_code": status,
                    "message": f"Page refreshed with status code {status}"
                }
            
            return {
                "status": "success",
                "url": page.url,
                "status_code": status,
                "message": "Successfully refreshed page"
            }
        else:
            return {
                "status": "success",
                "url": page.url,
                "status_code": None,
                "message": "Refreshed page (no response object)"
            }
            
    except PlaywrightError as e:
        logger.error(f"Page refresh error: {str(e)}")
        
        # Check if navigation timeout
        if "timeout" in str(e).lower():
            return {
                "status": "error",
                "error": "timeout",
                "url": page.url,
                "message": f"Page refresh timed out after {timeout}ms"
            }
        
        # Other error
        return {
            "status": "error",
            "error": str(e),
            "url": page.url,
            "message": f"Error refreshing page: {str(e)}"
        }


async def navigate_back(
    page: Page,
    settings: Settings,
    wait_until: str = "load",
    timeout: Optional[int] = None
) -> Dict[str, Any]:
    """
    Navigate back in browser history.
    
    Args:
        page: The page to navigate
        settings: Application settings
        wait_until: When to consider navigation finished (load, domcontentloaded, networkidle)
        timeout: Optional navigation timeout in milliseconds
        
    Returns:
        Result of the navigation
    """
    logger.info("Navigating back in history")
    
    # Set default timeout if not specified
    if timeout is None:
        timeout = settings.navigation_timeout
    
    try:
        # Perform the back navigation
        response = await page.go_back(wait_until=wait_until, timeout=timeout)
        
        # Check if navigation was successful
        if response:
            status = response.status
            ok = response.ok
            
            if not ok:
                logger.warning(f"Back navigation received non-OK status code: {status}")
                return {
                    "status": "warning",
                    "url": page.url,
                    "status_code": status,
                    "message": f"Navigated back with status code {status}"
                }
            
            return {
                "status": "success",
                "url": page.url,
                "status_code": status,
                "message": "Successfully navigated back"
            }
        else:
            # If no response, check if URL changed
            if page.url:
                return {
                    "status": "success",
                    "url": page.url,
                    "status_code": None,
                    "message": "Navigated back (no response object)"
                }
            else:
                return {
                    "status": "error",
                    "error": "no_history",
                    "message": "Cannot navigate back, no history available"
                }
            
    except PlaywrightError as e:
        logger.error(f"Back navigation error: {str(e)}")
        
        # Check if navigation timeout
        if "timeout" in str(e).lower():
            return {
                "status": "error",
                "error": "timeout",
                "message": f"Back navigation timed out after {timeout}ms"
            }
        
        # Check if no history
        if "no history" in str(e).lower():
            return {
                "status": "error",
                "error": "no_history",
                "message": "Cannot navigate back, no history available"
            }
        
        # Other error
        return {
            "status": "error",
            "error": str(e),
            "message": f"Error navigating back: {str(e)}"
        }


async def navigate_forward(
    page: Page,
    settings: Settings,
    wait_until: str = "load",
    timeout: Optional[int] = None
) -> Dict[str, Any]:
    """
    Navigate forward in browser history.
    
    Args:
        page: The page to navigate
        settings: Application settings
        wait_until: When to consider navigation finished (load, domcontentloaded, networkidle)
        timeout: Optional navigation timeout in milliseconds
        
    Returns:
        Result of the navigation
    """
    logger.info("Navigating forward in history")
    
    # Set default timeout if not specified
    if timeout is None:
        timeout = settings.navigation_timeout
    
    try:
        # Perform the forward navigation
        response = await page.go_forward(wait_until=wait_until, timeout=timeout)
        
        # Check if navigation was successful
        if response:
            status = response.status
            ok = response.ok
            
            if not ok:
                logger.warning(f"Forward navigation received non-OK status code: {status}")
                return {
                    "status": "warning",
                    "url": page.url,
                    "status_code": status,
                    "message": f"Navigated forward with status code {status}"
                }
            
            return {
                "status": "success",
                "url": page.url,
                "status_code": status,
                "message": "Successfully navigated forward"
            }
        else:
            # If no response, check if URL changed
            if page.url:
                return {
                    "status": "success",
                    "url": page.url,
                    "status_code": None,
                    "message": "Navigated forward (no response object)"
                }
            else:
                return {
                    "status": "error",
                    "error": "no_history",
                    "message": "Cannot navigate forward, no forward history available"
                }
            
    except PlaywrightError as e:
        logger.error(f"Forward navigation error: {str(e)}")
        
        # Check if navigation timeout
        if "timeout" in str(e).lower():
            return {
                "status": "error",
                "error": "timeout",
                "message": f"Forward navigation timed out after {timeout}ms"
            }
        
        # Check if no forward history
        if "no history" in str(e).lower():
            return {
                "status": "error",
                "error": "no_forward_history",
                "message": "Cannot navigate forward, no forward history available"
            }
        
        # Other error
        return {
            "status": "error",
            "error": str(e),
            "message": f"Error navigating forward: {str(e)}"
        }


async def wait_for_navigation(
    page: Page,
    settings: Settings,
    wait_until: str = "load",
    timeout: Optional[int] = None
) -> Dict[str, Any]:
    """
    Wait for navigation to complete.
    
    Args:
        page: The page to wait on
        settings: Application settings
        wait_until: When to consider navigation finished (load, domcontentloaded, networkidle)
        timeout: Optional navigation timeout in milliseconds
        
    Returns:
        Result of the wait operation
    """
    logger.info(f"Waiting for navigation state: {wait_until}")
    
    # Set default timeout if not specified
    if timeout is None:
        timeout = settings.navigation_timeout
    
    try:
        # Wait for the specified navigation state
        await page.wait_for_load_state(state=wait_until, timeout=timeout)
        
        return {
            "status": "success",
            "url": page.url,
            "state": wait_until,
            "message": f"Navigation reached state: {wait_until}"
        }
            
    except PlaywrightError as e:
        logger.error(f"Wait for navigation error: {str(e)}")
        
        # Check if timeout
        if "timeout" in str(e).lower():
            return {
                "status": "error",
                "error": "timeout",
                "url": page.url,
                "state": wait_until,
                "message": f"Timeout waiting for navigation state: {wait_until}"
            }
        
        # Other error
        return {
            "status": "error",
            "error": str(e),
            "url": page.url,
            "state": wait_until,
            "message": f"Error waiting for navigation: {str(e)}"
        }


async def wait_for_url(
    page: Page,
    url_pattern: str,
    settings: Settings,
    is_regex: bool = False,
    timeout: Optional[int] = None
) -> Dict[str, Any]:
    """
    Wait for URL to match a pattern.
    
    Args:
        page: The page to wait on
        url_pattern: The URL pattern to match
        settings: Application settings
        is_regex: Whether the pattern is a regular expression
        timeout: Optional timeout in milliseconds
        
    Returns:
        Result of the wait operation
    """
    logger.info(f"Waiting for URL to match: {url_pattern}")
    
    # Set default timeout if not specified
    if timeout is None:
        timeout = settings.navigation_timeout
    
    try:
        # Build the pattern
        if is_regex:
            pattern = re.compile(url_pattern)
        else:
            # For non-regex, convert to a simple pattern with wildcards
            # Convert * to .* for regex
            pattern_str = url_pattern.replace("*", ".*")
            pattern = re.compile(pattern_str)
        
        # Wait for URL to match
        start_time = time.time()
        current_url = page.url
        
        while (time.time() - start_time) * 1000 < timeout:
            current_url = page.url
            
            if pattern.search(current_url):
                return {
                    "status": "success",
                    "url": current_url,
                    "pattern": url_pattern,
                    "message": f"URL matches pattern: {url_pattern}"
                }
            
            # Wait a bit before checking again
            await page.wait_for_timeout(100)
        
        # If we get here, timeout occurred
        return {
            "status": "error",
            "error": "timeout",
            "url": current_url,
            "pattern": url_pattern,
            "message": f"Timeout waiting for URL to match pattern: {url_pattern}"
        }
            
    except Exception as e:
        logger.error(f"Wait for URL error: {str(e)}")
        
        return {
            "status": "error",
            "error": str(e),
            "url": page.url if page else "unknown",
            "pattern": url_pattern,
            "message": f"Error waiting for URL: {str(e)}"
        }


async def get_page_info(page: Page) -> Dict[str, Any]:
    """
    Get information about the current page.
    
    Args:
        page: The page to get information for
        
    Returns:
        Information about the page
    """
    try:
        # Get basic page information
        url = page.url
        title = await page.title()
        
        # Get page metadata
        metadata = await page.evaluate("""
            () => {
                const metadata = {};
                const metaTags = document.querySelectorAll('meta');
                
                metaTags.forEach(tag => {
                    const name = tag.getAttribute('name') || tag.getAttribute('property');
                    const content = tag.getAttribute('content');
                    
                    if (name && content) {
                        metadata[name] = content;
                    }
                });
                
                return metadata;
            }
        """)
        
        # Check if page has forms
        has_forms = await page.evaluate("() => document.querySelectorAll('form').length > 0")
        
        # Check if page has login forms
        has_login_form = await page.evaluate("""
            () => {
                const forms = Array.from(document.querySelectorAll('form'));
                return forms.some(form => {
                    const inputs = form.querySelectorAll('input');
                    const hasPasswordField = Array.from(inputs).some(input => 
                        input.type === 'password'
                    );
                    return hasPasswordField;
                });
            }
        """)
        
        return {
            "url": url,
            "title": title,
            "metadata": metadata,
            "has_forms": has_forms,
            "has_login_form": has_login_form
        }
        
    except Exception as e:
        logger.error(f"Error getting page info: {str(e)}")
        
        # Return basic info on error
        return {
            "url": page.url if page else "unknown",
            "title": "Error retrieving page info",
            "error": str(e)
        }
