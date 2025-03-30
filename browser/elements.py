"""
Browser elements module.

This module provides functionality for finding and interacting with elements on the page.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Union, Tuple

from playwright.async_api import Page, ElementHandle, Locator

# Set up logger
logger = logging.getLogger(__name__)


async def find_element(
    page: Page, 
    selector: str, 
    timeout: int = 5000
) -> Optional[ElementHandle]:
    """
    Find an element on the page.
    
    Args:
        page: The page to find the element on
        selector: The selector to use (CSS, XPath, or text)
        timeout: How long to wait for the element in milliseconds
        
    Returns:
        The found element or None if not found
    """
    try:
        # Check if selector is CSS, XPath, or text
        if selector.startswith('//') or selector.startswith('(//'):
            # XPath selector
            return await page.wait_for_selector(selector, timeout=timeout, state="attached")
        elif selector.startswith('text=') or selector.startswith('text/'):
            # Text selector
            text = selector.replace('text=', '').replace('text/', '')
            return await page.wait_for_selector(f"text={text}", timeout=timeout, state="attached")
        else:
            # CSS selector
            return await page.wait_for_selector(selector, timeout=timeout, state="attached")
    except Exception as e:
        logger.debug(f"Element not found with selector: {selector}. Error: {str(e)}")
        return None


async def get_elements(
    page: Page, 
    selector: str, 
    timeout: int = 5000
) -> List[ElementHandle]:
    """
    Get all elements matching a selector.
    
    Args:
        page: The page to find elements on
        selector: The selector to use (CSS, XPath, or text)
        timeout: How long to wait for at least one element in milliseconds
        
    Returns:
        List of matching elements (empty if none found)
    """
    try:
        # First check if any elements exist
        await page.wait_for_selector(selector, timeout=timeout, state="attached")
        
        # Get all matching elements
        elements = await page.query_selector_all(selector)
        return elements
    except Exception as e:
        logger.debug(f"No elements found with selector: {selector}. Error: {str(e)}")
        return []


async def find_element_by_text(
    page: Page, 
    text: str, 
    exact: bool = False, 
    timeout: int = 5000
) -> Optional[ElementHandle]:
    """
    Find an element by its text content.
    
    Args:
        page: The page to find the element on
        text: The text to search for
        exact: Whether to match the exact text or contain the text
        timeout: How long to wait for the element in milliseconds
        
    Returns:
        The found element or None if not found
    """
    try:
        if exact:
            selector = f"text=\"{text}\""
        else:
            selector = f"text=/{text}/i"
            
        return await page.wait_for_selector(selector, timeout=timeout, state="attached")
    except Exception as e:
        logger.debug(f"Element not found with text: {text}. Error: {str(e)}")
        return None


async def find_element_by_role(
    page: Page, 
    role: str, 
    name: Optional[str] = None, 
    exact: bool = False,
    timeout: int = 5000
) -> Optional[ElementHandle]:
    """
    Find an element by its ARIA role and optionally by name.
    
    Args:
        page: The page to find the element on
        role: The ARIA role (button, link, textbox, etc.)
        name: Optional name (text content) of the element
        exact: Whether to match the exact name or contain the name
        timeout: How long to wait for the element in milliseconds
        
    Returns:
        The found element or None if not found
    """
    try:
        # Create role selector
        if name:
            if exact:
                selector = f"role={role}[name=\"{name}\"]"
            else:
                selector = f"role={role}[name=/{name}/i]"
        else:
            selector = f"role={role}"
            
        return await page.wait_for_selector(selector, timeout=timeout, state="attached")
    except Exception as e:
        name_str = f" with name '{name}'" if name else ""
        logger.debug(f"Element not found with role: {role}{name_str}. Error: {str(e)}")
        return None


async def find_input_element(
    page: Page, 
    label_or_placeholder: str, 
    timeout: int = 5000
) -> Optional[ElementHandle]:
    """
    Find an input element by its label text or placeholder.
    
    Args:
        page: The page to find the input on
        label_or_placeholder: The label text or placeholder to search for
        timeout: How long to wait for the element in milliseconds
        
    Returns:
        The found input element or None if not found
    """
    try:
        # Try by label first
        # Look for a label with this text
        label = await find_element_by_text(page, label_or_placeholder, exact=False, timeout=timeout//2)
        
        if label:
            # Check for 'for' attribute
            for_id = await label.get_attribute('for')
            if for_id:
                # Find input with this ID
                input_el = await page.wait_for_selector(f"#{for_id}", timeout=timeout//2, state="attached")
                if input_el:
                    return input_el
                    
            # If no 'for' attribute or input not found, look for input inside label
            input_el = await label.query_selector('input, textarea, select')
            if input_el:
                return input_el
        
        # Try by placeholder
        input_el = await page.wait_for_selector(
            f"input[placeholder*='{label_or_placeholder}' i], textarea[placeholder*='{label_or_placeholder}' i]",
            timeout=timeout//2,
            state="attached"
        )
        if input_el:
            return input_el
            
        # Try by aria-label
        input_el = await page.wait_for_selector(
            f"input[aria-label*='{label_or_placeholder}' i], textarea[aria-label*='{label_or_placeholder}' i]",
            timeout=timeout//2,
            state="attached"
        )
        if input_el:
            return input_el
            
        # Try by role
        input_el = await find_element_by_role(page, "textbox", label_or_placeholder, exact=False, timeout=timeout//2)
        return input_el
            
    except Exception as e:
        logger.debug(f"Input element not found with label/placeholder: {label_or_placeholder}. Error: {str(e)}")
        return None


async def find_button_element(
    page: Page, 
    text_or_aria: str, 
    timeout: int = 5000
) -> Optional[ElementHandle]:
    """
    Find a button element by its text, aria-label, or title.
    
    Args:
        page: The page to find the button on
        text_or_aria: The button text, aria-label, or title to search for
        timeout: How long to wait for the element in milliseconds
        
    Returns:
        The found button element or None if not found
    """
    try:
        # Try by role first
        button = await find_element_by_role(page, "button", text_or_aria, exact=False, timeout=timeout//3)
        if button:
            return button
        
        # Try by text
        button = await find_element_by_text(page, text_or_aria, exact=False, timeout=timeout//3)
        if button and await is_clickable_element(button):
            return button
        
        # Try by aria-label or title
        selectors = [
            f"button[aria-label*='{text_or_aria}' i]",
            f"button[title*='{text_or_aria}' i]",
            f"input[type='button'][value*='{text_or_aria}' i]",
            f"input[type='submit'][value*='{text_or_aria}' i]",
            f"a[role='button'][aria-label*='{text_or_aria}' i]",
            f"a[role='button'][title*='{text_or_aria}' i]",
            f"*[role='button'][aria-label*='{text_or_aria}' i]",
            f"*[role='button'][title*='{text_or_aria}' i]"
        ]
        
        for selector in selectors:
            try:
                button = await page.wait_for_selector(selector, timeout=timeout//len(selectors), state="attached")
                if button:
                    return button
            except:
                continue
                
        return None
            
    except Exception as e:
        logger.debug(f"Button element not found with text/aria: {text_or_aria}. Error: {str(e)}")
        return None


async def is_clickable_element(element: ElementHandle) -> bool:
    """
    Check if an element is likely to be clickable.
    
    Args:
        element: The element to check
        
    Returns:
        True if the element is likely to be clickable, False otherwise
    """
    try:
        # Get element tag
        tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
        
        # Naturally clickable elements
        clickable_tags = ["button", "a", "input", "select", "option", "textarea"]
        if tag_name in clickable_tags:
            return True
        
        # Check for role
        role = await element.get_attribute("role")
        clickable_roles = ["button", "link", "menuitem", "tab", "checkbox", "radio", "switch"]
        if role in clickable_roles:
            return True
        
        # Check for listeners
        has_listeners = await element.evaluate("""
            el => {
                const clickable = el.onclick != null || el.getAttribute('onclick') != null;
                const style = window.getComputedStyle(el);
                const isStyleClickable = style.cursor == 'pointer';
                return clickable || isStyleClickable;
            }
        """)
        
        return has_listeners
    except Exception:
        return False


async def get_visible_elements(page: Page) -> List[Dict[str, Any]]:
    """
    Get all visible interactive elements on the page.
    
    Args:
        page: The page to find elements on
        
    Returns:
        List of visible interactive elements with their properties
    """
    elements = []
    
    # Get all interactive elements
    selectors = [
        "a", "button", "input", "select", "textarea", 
        "[role='button']", "[role='link']", "[role='menuitem']", 
        "[role='tab']", "[role='checkbox']", "[role='radio']",
        "[role='switch']", "[role='textbox']", "[role='combobox']"
    ]
    
    for selector in selectors:
        elements_of_type = await page.query_selector_all(selector)
        
        for element in elements_of_type:
            try:
                # Check if element is visible
                is_visible = await element.is_visible()
                
                if not is_visible:
                    continue
                
                # Get element properties
                properties = await get_element_properties(element)
                elements.append(properties)
                
            except Exception as e:
                logger.debug(f"Error processing element: {str(e)}")
                continue
    
    return elements


async def get_element_properties(element: ElementHandle) -> Dict[str, Any]:
    """
    Get properties of an element.
    
    Args:
        element: The element to get properties for
        
    Returns:
        Dictionary of element properties
    """
    try:
        # Get basic properties
        tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
        
        # Get element text
        text_content = await element.evaluate("el => el.textContent || ''")
        text_content = text_content.strip() if text_content else ""
        
        # Get element attributes
        attributes = await element.evaluate("""
            el => {
                const attrs = {};
                for (const attr of el.attributes) {
                    attrs[attr.name] = attr.value;
                }
                return attrs;
            }
        """)
        
        # Determine element role
        role = attributes.get("role", "")
        if not role:
            # Infer role from tag
            role_map = {
                "a": "link",
                "button": "button",
                "input": attributes.get("type", "textbox"),
                "select": "combobox",
                "textarea": "textbox",
                "img": "img"
            }
            role = role_map.get(tag_name, "")
        
        # Get element description (best identifier)
        description = ""
        for prop in ["aria-label", "title", "name", "placeholder", "alt"]:
            if prop in attributes and attributes[prop]:
                description = attributes[prop]
                break
        
        # If no description, use text content
        if not description and text_content and len(text_content) < 100:
            description = text_content
        
        # If still no description, use ID or class
        if not description:
            description = attributes.get("id") or attributes.get("class") or f"{tag_name} element"
        
        # Get element position
        bounding_box = await element.bounding_box()
        position = {
            "x": bounding_box.x if bounding_box else 0,
            "y": bounding_box.y if bounding_box else 0,
            "width": bounding_box.width if bounding_box else 0,
            "height": bounding_box.height if bounding_box else 0
        }
        
        # Construct element properties
        properties = {
            "tag": tag_name,
            "role": role,
            "description": description,
            "text": text_content[:100] + ("..." if len(text_content) > 100 else ""),
            "attributes": attributes,
            "position": position
        }
        
        return properties
        
    except Exception as e:
        logger.debug(f"Error getting element properties: {str(e)}")
        return {
            "tag": "unknown",
            "role": "unknown",
            "description": "Error getting element properties",
            "text": "",
            "attributes": {},
            "position": {"x": 0, "y": 0, "width": 0, "height": 0}
        }


async def extract_element_text(element: ElementHandle) -> str:
    """
    Extract text content from an element.
    
    Args:
        element: The element to extract text from
        
    Returns:
        The text content of the element
    """
    try:
        text = await element.evaluate("el => el.textContent || ''")
        return text.strip()
    except Exception as e:
        logger.debug(f"Error extracting element text: {str(e)}")
        return ""


async def get_element_attributes(element: ElementHandle) -> Dict[str, str]:
    """
    Get all attributes of an element.
    
    Args:
        element: The element to get attributes for
        
    Returns:
        Dictionary of attribute names and values
    """
    try:
        attributes = await element.evaluate("""
            el => {
                const attrs = {};
                for (const attr of el.attributes) {
                    attrs[attr.name] = attr.value;
                }
                return attrs;
            }
        """)
        return attributes
    except Exception as e:
        logger.debug(f"Error getting element attributes: {str(e)}")
        return {}


async def get_element_value(element: ElementHandle) -> str:
    """
    Get the value of an input element.
    
    Args:
        element: The element to get the value for
        
    Returns:
        The value of the element
    """
    try:
        tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
        
        if tag_name in ["input", "textarea", "select"]:
            value = await element.evaluate("el => el.value || ''")
            return value
        else:
            return await extract_element_text(element)
    except Exception as e:
        logger.debug(f"Error getting element value: {str(e)}")
        return ""
