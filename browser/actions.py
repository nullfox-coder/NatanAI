"""
Browser actions module.

This module provides functionality for performing common browser actions such as
clicking, typing, scrolling, etc.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Union

from playwright.async_api import BrowserContext, Page, ElementHandle, Error as PlaywrightError

from config.settings import Settings
from browser.elements import find_element

# Set up logger
logger = logging.getLogger(__name__)


async def perform_action(
    browser_context: BrowserContext,
    action: str,
    params: Dict[str, Any],
    settings: Settings
) -> Dict[str, Any]:
    """
    Perform a browser action.
    
    Args:
        browser_context: The browser context to perform the action in
        action: The action to perform
        params: Parameters for the action
        settings: Application settings
        
    Returns:
        Result of the action
    """
    logger.info(f"Performing browser action: {action}")
    
    # Get the current page
    page = await get_current_page(browser_context)
    
    # Dispatch to appropriate action handler
    action_handlers = {
        "click": click_element,
        "type": type_text,
        "press": press_key,
        "scroll": scroll_page,
        "select": select_option,
        "check": check_checkbox,
        "uncheck": uncheck_checkbox,
        "focus": focus_element,
        "hover": hover_element,
        "screenshot": take_screenshot,
        "wait": wait_for,
        "reload": reload_page,
        "goBack": go_back,
        "goForward": go_forward
    }
    
    handler = action_handlers.get(action)
    
    if not handler:
        return {
            "status": "error",
            "error": f"Unknown action: {action}",
            "message": f"The action '{action}' is not supported"
        }
    
    try:
        # Call the appropriate handler
        result = await handler(page, params, settings)
        return result
    
    except PlaywrightError as e:
        logger.error(f"Playwright error performing action {action}: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "message": f"Error performing {action}: {str(e)}"
        }
    
    except Exception as e:
        logger.error(f"Error performing action {action}: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "message": f"Error performing {action}: {str(e)}"
        }


async def get_current_page(browser_context: BrowserContext) -> Page:
    """
    Get the current page from a browser context.
    
    Args:
        browser_context: The browser context to get the page from
        
    Returns:
        The current page
        
    Raises:
        ValueError: If the context has no pages
    """
    pages = browser_context.pages
    
    if not pages:
        # Create a new page
        page = await browser_context.new_page()
        logger.debug("Created new page in context")
        return page
    
    # Return the last page in the context
    return pages[-1]


async def click_element(page: Page, params: Dict[str, Any], settings: Settings) -> Dict[str, Any]:
    """
    Click an element on the page.
    
    Args:
        page: The page to click on
        params: Parameters for the click action
        settings: Application settings
        
    Returns:
        Result of the click action
    """
    element_selector = params.get("element")
    button = params.get("button", "left")  # left, right, middle
    click_count = params.get("clickCount", 1)
    position = params.get("position")  # {x, y} coordinates
    timeout = params.get("timeout", settings.action_timeout)
    force = params.get("force", False)
    
    if not element_selector:
        return {
            "status": "error",
            "error": "No element specified for click",
            "message": "Cannot click without a target element"
        }
    
    # Find the element
    element = await find_element(page, element_selector)
    
    if not element:
        return {
            "status": "error",
            "error": f"Element not found: {element_selector}",
            "message": f"Could not find element: {element_selector}"
        }
    
    # Prepare click options
    click_options = {
        "button": button,
        "click_count": click_count,
        "timeout": timeout,
        "force": force
    }
    
    # Add position if specified
    if position:
        click_options["position"] = position
    
    # Click the element
    await element.click(**click_options)
    
    return {
        "status": "success",
        "message": f"Clicked element: {element_selector}",
        "data": {
            "element": element_selector
        }
    }


async def type_text(page: Page, params: Dict[str, Any], settings: Settings) -> Dict[str, Any]:
    """
    Type text into an element on the page.
    
    Args:
        page: The page to type on
        params: Parameters for the type action
        settings: Application settings
        
    Returns:
        Result of the type action
    """
    element_selector = params.get("element")
    text = params.get("text")
    delay = params.get("delay")  # milliseconds between keystrokes
    timeout = params.get("timeout", settings.action_timeout)
    clear = params.get("clear", False)  # whether to clear the field first
    
    if not element_selector:
        return {
            "status": "error",
            "error": "No element specified for typing",
            "message": "Cannot type without a target element"
        }
    
    if text is None:
        return {
            "status": "error",
            "error": "No text specified for typing",
            "message": "Cannot type without text to type"
        }
    
    # Find the element
    element = await find_element(page, element_selector)
    
    if not element:
        return {
            "status": "error",
            "error": f"Element not found: {element_selector}",
            "message": f"Could not find element: {element_selector}"
        }
    
    # Clear the field if requested
    if clear:
        await element.fill("")
    
    # Prepare type options
    type_options = {
        "timeout": timeout
    }
    
    # Add delay if specified
    if delay is not None:
        type_options["delay"] = delay
    
    # Type the text
    await element.type(text, **type_options)
    
    return {
        "status": "success",
        "message": f"Typed text into element: {element_selector}",
        "data": {
            "element": element_selector,
            "text": text if not text.startswith("password:") else "********"
        }
    }


async def press_key(page: Page, params: Dict[str, Any], settings: Settings) -> Dict[str, Any]:
    """
    Press a key or key combination.
    
    Args:
        page: The page to press the key on
        params: Parameters for the press action
        settings: Application settings
        
    Returns:
        Result of the press action
    """
    key = params.get("key")
    element_selector = params.get("element")  # optional, to focus element first
    timeout = params.get("timeout", settings.action_timeout)
    
    if not key:
        return {
            "status": "error",
            "error": "No key specified for press",
            "message": "Cannot press without a key to press"
        }
    
    # Focus element if specified
    if element_selector:
        element = await find_element(page, element_selector)
        
        if not element:
            return {
                "status": "error",
                "error": f"Element not found: {element_selector}",
                "message": f"Could not find element: {element_selector}"
            }
        
        await element.focus()
    
    # Press the key
    await page.press("body" if not element_selector else None, key, timeout=timeout)
    
    return {
        "status": "success",
        "message": f"Pressed key: {key}",
        "data": {
            "key": key,
            "element": element_selector
        }
    }


async def scroll_page(page: Page, params: Dict[str, Any], settings: Settings) -> Dict[str, Any]:
    """
    Scroll the page or an element.
    
    Args:
        page: The page to scroll
        params: Parameters for the scroll action
        settings: Application settings
        
    Returns:
        Result of the scroll action
    """
    direction = params.get("direction", "down")  # up, down, left, right
    element_selector = params.get("element")  # optional, to scroll a specific element
    amount = params.get("amount")  # pixels or "page"
    behavior = params.get("behavior", "auto")  # auto, smooth
    
    # Convert direction to x, y values
    if direction == "down":
        x, y = 0, 1
    elif direction == "up":
        x, y = 0, -1
    elif direction == "right":
        x, y = 1, 0
    elif direction == "left":
        x, y = -1, 0
    else:
        return {
            "status": "error",
            "error": f"Invalid scroll direction: {direction}",
            "message": f"Invalid scroll direction: {direction}. Must be one of: up, down, left, right"
        }
    
    # Determine scroll amount
    if amount == "page":
        # Get viewport size
        viewport_size = page.viewport_size
        
        if direction in ["down", "up"]:
            amount = viewport_size["height"]
        else:
            amount = viewport_size["width"]
    elif amount is None:
        # Default to 100 pixels
        amount = 100
    
    # Adjust amount based on direction
    if direction in ["up", "left"]:
        amount = -amount
    
    # Scroll the page or element
    if element_selector:
        # Find the element
        element = await find_element(page, element_selector)
        
        if not element:
            return {
                "status": "error",
                "error": f"Element not found: {element_selector}",
                "message": f"Could not find element: {element_selector}"
            }
        
        # Scroll the element into view
        await element.scroll_into_view_if_needed()
        
        # Scroll within the element if needed
        if direction in ["down", "up"]:
            await page.evaluate(
                f'(el) => el.scrollBy(0, {amount})',
                element
            )
        else:
            await page.evaluate(
                f'(el) => el.scrollBy({amount}, 0)',
                element
            )
            
        scroll_target = f"element: {element_selector}"
    else:
        # Scroll the page
        if direction in ["down", "up"]:
            await page.evaluate(f'window.scrollBy(0, {amount})')
        else:
            await page.evaluate(f'window.scrollBy({amount}, 0)')
            
        scroll_target = "page"
    
    return {
        "status": "success",
        "message": f"Scrolled {scroll_target} {direction}",
        "data": {
            "direction": direction,
            "amount": amount,
            "element": element_selector
        }
    }


async def select_option(page: Page, params: Dict[str, Any], settings: Settings) -> Dict[str, Any]:
    """
    Select an option from a select element.
    
    Args:
        page: The page with the select element
        params: Parameters for the select action
        settings: Application settings
        
    Returns:
        Result of the select action
    """
    element_selector = params.get("element")
    value = params.get("value")  # option value
    label = params.get("label")  # option text
    index = params.get("index")  # option index
    timeout = params.get("timeout", settings.action_timeout)
    
    if not element_selector:
        return {
            "status": "error",
            "error": "No element specified for select",
            "message": "Cannot select without a target element"
        }
    
    if value is None and label is None and index is None:
        return {
            "status": "error",
            "error": "No option specified for select",
            "message": "Must specify value, label, or index for select"
        }
    
    # Find the element
    element = await find_element(page, element_selector)
    
    if not element:
        return {
            "status": "error",
            "error": f"Element not found: {element_selector}",
            "message": f"Could not find element: {element_selector}"
        }
    
    # Prepare select options
    select_options = {"timeout": timeout}
    
    if value is not None:
        select_options["value"] = value
    elif label is not None:
        select_options["label"] = label
    elif index is not None:
        select_options["index"] = index
    
    # Select the option
    selected_values = await element.select_option(**select_options)
    
    return {
        "status": "success",
        "message": f"Selected option in element: {element_selector}",
        "data": {
            "element": element_selector,
            "selected_values": selected_values
        }
    }


async def check_checkbox(page: Page, params: Dict[str, Any], settings: Settings) -> Dict[str, Any]:
    """
    Check a checkbox.
    
    Args:
        page: The page with the checkbox
        params: Parameters for the check action
        settings: Application settings
        
    Returns:
        Result of the check action
    """
    element_selector = params.get("element")
    timeout = params.get("timeout", settings.action_timeout)
    force = params.get("force", False)
    
    if not element_selector:
        return {
            "status": "error",
            "error": "No element specified for check",
            "message": "Cannot check without a target element"
        }
    
    # Find the element
    element = await find_element(page, element_selector)
    
    if not element:
        return {
            "status": "error",
            "error": f"Element not found: {element_selector}",
            "message": f"Could not find element: {element_selector}"
        }
    
    # Check the checkbox
    await element.check(timeout=timeout, force=force)
    
    return {
        "status": "success",
        "message": f"Checked checkbox: {element_selector}",
        "data": {
            "element": element_selector
        }
    }


async def uncheck_checkbox(page: Page, params: Dict[str, Any], settings: Settings) -> Dict[str, Any]:
    """
    Uncheck a checkbox.
    
    Args:
        page: The page with the checkbox
        params: Parameters for the uncheck action
        settings: Application settings
        
    Returns:
        Result of the uncheck action
    """
    element_selector = params.get("element")
    timeout = params.get("timeout", settings.action_timeout)
    force = params.get("force", False)
    
    if not element_selector:
        return {
            "status": "error",
            "error": "No element specified for uncheck",
            "message": "Cannot uncheck without a target element"
        }
    
    # Find the element
    element = await find_element(page, element_selector)
    
    if not element:
        return {
            "status": "error",
            "error": f"Element not found: {element_selector}",
            "message": f"Could not find element: {element_selector}"
        }
    
    # Uncheck the checkbox
    await element.uncheck(timeout=timeout, force=force)
    
    return {
        "status": "success",
        "message": f"Unchecked checkbox: {element_selector}",
        "data": {
            "element": element_selector
        }
    }


async def focus_element(page: Page, params: Dict[str, Any], settings: Settings) -> Dict[str, Any]:
    """
    Focus an element.
    
    Args:
        page: The page with the element
        params: Parameters for the focus action
        settings: Application settings
        
    Returns:
        Result of the focus action
    """
    element_selector = params.get("element")
    timeout = params.get("timeout", settings.action_timeout)
    
    if not element_selector:
        return {
            "status": "error",
            "error": "No element specified for focus",
            "message": "Cannot focus without a target element"
        }
    
    # Find the element
    element = await find_element(page, element_selector)
    
    if not element:
        return {
            "status": "error",
            "error": f"Element not found: {element_selector}",
            "message": f"Could not find element: {element_selector}"
        }
    
    # Focus the element
    await element.focus(timeout=timeout)
    
    return {
        "status": "success",
        "message": f"Focused element: {element_selector}",
        "data": {
            "element": element_selector
        }
    }


async def hover_element(page: Page, params: Dict[str, Any], settings: Settings) -> Dict[str, Any]:
    """
    Hover over an element.
    
    Args:
        page: The page with the element
        params: Parameters for the hover action
        settings: Application settings
        
    Returns:
        Result of the hover action
    """
    element_selector = params.get("element")
    position = params.get("position")  # {x, y} coordinates
    timeout = params.get("timeout", settings.action_timeout)
    force = params.get("force", False)
    
    if not element_selector:
        return {
            "status": "error",
            "error": "No element specified for hover",
            "message": "Cannot hover without a target element"
        }
    
    # Find the element
    element = await find_element(page, element_selector)
    
    if not element:
        return {
            "status": "error",
            "error": f"Element not found: {element_selector}",
            "message": f"Could not find element: {element_selector}"
        }
    
    # Prepare hover options
    hover_options = {
        "timeout": timeout,
        "force": force
    }
    
    # Add position if specified
    if position:
        hover_options["position"] = position
    
    # Hover over the element
    await element.hover(**hover_options)
    
    return {
        "status": "success",
        "message": f"Hovered over element: {element_selector}",
        "data": {
            "element": element_selector
        }
    }


async def take_screenshot(page: Page, params: Dict[str, Any], settings: Settings) -> Dict[str, Any]:
    """
    Take a screenshot of the page or an element.
    
    Args:
        page: The page to screenshot
        params: Parameters for the screenshot action
        settings: Application settings
        
    Returns:
        Result of the screenshot action containing base64 encoded image
    """
    element_selector = params.get("element")  # optional, to screenshot a specific element
    full_page = params.get("fullPage", False)
    path = params.get("path")  # optional, to save to a file
    type_format = params.get("type", "png")  # png, jpeg
    quality = params.get("quality", 100)  # 0-100, jpeg only
    
    # Prepare screenshot options
    screenshot_options = {
        "type": type_format,
        "full_page": full_page
    }
    
    # Add quality if jpeg
    if type_format == "jpeg":
        screenshot_options["quality"] = quality
    
    # Add path if specified
    if path:
        screenshot_options["path"] = path
    
    # Take the screenshot
    if element_selector:
        # Find the element
        element = await find_element(page, element_selector)
        
        if not element:
            return {
                "status": "error",
                "error": f"Element not found: {element_selector}",
                "message": f"Could not find element: {element_selector}"
            }
        
        # Screenshot the element
        screenshot = await element.screenshot(**screenshot_options)
        screenshot_target = f"element: {element_selector}"
    else:
        # Screenshot the page
        screenshot = await page.screenshot(**screenshot_options)
        screenshot_target = "page"
    
    # Convert to base64 if not saving to file
    if not path:
        import base64
        screenshot_base64 = base64.b64encode(screenshot).decode("utf-8")
        
        return {
            "status": "success",
            "message": f"Took screenshot of {screenshot_target}",
            "data": {
                "screenshot": screenshot_base64,
                "type": type_format,
                "element": element_selector
            }
        }
    else:
        return {
            "status": "success",
            "message": f"Saved screenshot of {screenshot_target} to {path}",
            "data": {
                "path": path,
                "type": type_format,
                "element": element_selector
            }
        }


async def wait_for(page: Page, params: Dict[str, Any], settings: Settings) -> Dict[str, Any]:
    """
    Wait for a specific condition.
    
    Args:
        page: The page to wait on
        params: Parameters for the wait action
        settings: Application settings
        
    Returns:
        Result of the wait action
    """
    element_selector = params.get("element")
    state = params.get("state")  # visible, hidden, attached, detached
    duration = params.get("duration")  # milliseconds to wait
    timeout = params.get("timeout", settings.wait_timeout)
    
    # If duration specified, just wait
    if duration is not None:
        await asyncio.sleep(duration / 1000)  # Convert to seconds
        
        return {
            "status": "success",
            "message": f"Waited for {duration} milliseconds",
            "data": {
                "duration": duration
            }
        }
    
    # If element and state specified, wait for element state
    if element_selector and state:
        try:
            # Find the element
            locator = page.locator(element_selector)
            
            # Wait for the element state
            if state == "visible":
                await locator.wait_for(state="visible", timeout=timeout)
            elif state == "hidden":
                await locator.wait_for(state="hidden", timeout=timeout)
            elif state == "attached":
                await locator.wait_for(state="attached", timeout=timeout)
            elif state == "detached":
                await locator.wait_for(state="detached", timeout=timeout)
            else:
                return {
                    "status": "error",
                    "error": f"Invalid state: {state}",
                    "message": f"Invalid state: {state}. Must be one of: visible, hidden, attached, detached"
                }
            
            return {
                "status": "success",
                "message": f"Element {element_selector} is now {state}",
                "data": {
                    "element": element_selector,
                    "state": state
                }
            }
            
        except PlaywrightError as e:
            return {
                "status": "error",
                "error": str(e),
                "message": f"Timeout waiting for element {element_selector} to be {state}"
            }
    
    # If only state specified, wait for page state
    if state and not element_selector:
        try:
            if state == "networkidle":
                await page.wait_for_load_state("networkidle", timeout=timeout)
            elif state == "load":
                await page.wait_for_load_state("load", timeout=timeout)
            elif state == "domcontentloaded":
                await page.wait_for_load_state("domcontentloaded", timeout=timeout)
            else:
                return {
                    "status": "error",
                    "error": f"Invalid page state: {state}",
                    "message": f"Invalid page state: {state}. Must be one of: networkidle, load, domcontentloaded"
                }
            
            return {
                "status": "success",
                "message": f"Page reached state: {state}",
                "data": {
                    "state": state
                }
            }
            
        except PlaywrightError as e:
            return {
                "status": "error",
                "error": str(e),
                "message": f"Timeout waiting for page to reach state: {state}"
            }
    
    # No valid wait parameters
    return {
        "status": "error",
        "error": "No valid wait parameters",
        "message": "Must specify element and state, just state, or duration"
    }


async def reload_page(page: Page, params: Dict[str, Any], settings: Settings) -> Dict[str, Any]:
    """
    Reload the current page.
    
    Args:
        page: The page to reload
        params: Parameters for the reload action
        settings: Application settings
        
    Returns:
        Result of the reload action
    """
    timeout = params.get("timeout", settings.navigation_timeout)
    wait_until = params.get("waitUntil", "load")  # load, domcontentloaded, networkidle
    
    # Reload the page
    await page.reload(timeout=timeout, wait_until=wait_until)
    
    return {
        "status": "success",
        "message": "Reloaded page",
        "data": {
            "url": page.url
        }
    }


async def go_back(page: Page, params: Dict[str, Any], settings: Settings) -> Dict[str, Any]:
    """
    Navigate back in history.
    
    Args:
        page: The page to navigate
        params: Parameters for the back action
        settings: Application settings
        
    Returns:
        Result of the back action
    """
    timeout = params.get("timeout", settings.navigation_timeout)
    wait_until = params.get("waitUntil", "load")  # load, domcontentloaded, networkidle
    
    # Go back
    response = await page.go_back(timeout=timeout, wait_until=wait_until)
    
    if not response:
        return {
            "status": "error",
            "error": "Could not go back",
            "message": "Could not go back in history, perhaps at the first page?"
        }
    
    return {
        "status": "success",
        "message": "Navigated back",
        "data": {
            "url": page.url
        }
    }


async def go_forward(page: Page, params: Dict[str, Any], settings: Settings) -> Dict[str, Any]:
    """
    Navigate forward in history.
    
    Args:
        page: The page to navigate
        params: Parameters for the forward action
        settings: Application settings
        
    Returns:
        Result of the forward action
    """
    timeout = params.get("timeout", settings.navigation_timeout)
    wait_until = params.get("waitUntil", "load")  # load, domcontentloaded, networkidle
    
    # Go forward
    response = await page.go_forward(timeout=timeout, wait_until=wait_until)
    
    if not response:
        return {
            "status": "error",
            "error": "Could not go forward",
            "message": "Could not go forward in history, perhaps at the last page?"
        }
    
    return {
        "status": "success",
        "message": "Navigated forward",
        "data": {
            "url": page.url
        }
    }
