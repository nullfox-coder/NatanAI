"""
Extraction parsers module.

This module provides functionality for extracting structured data from web elements,
such as tables, lists, and other structured content.
"""

import logging
import re
import json
from typing import Dict, List, Any, Optional, Union, Tuple

from playwright.async_api import Page, ElementHandle

from browser.elements import find_element, get_elements, extract_element_text

# Set up logger
logger = logging.getLogger(__name__)


class BaseParser:
    """
    Base class for parsers with common utilities.
    """
    
    def __init__(self, page: Page):
        """
        Initialize the base parser.
        
        Args:
            page: The page to parse content from
        """
        self.page = page
    
    async def get_element_text(self, element: ElementHandle) -> str:
        """
        Get the text content of an element.
        
        Args:
            element: The element to get text from
            
        Returns:
            The text content of the element
        """
        try:
            text = await extract_element_text(element)
            return text
        except Exception as e:
            logger.error(f"Error extracting element text: {str(e)}")
            return ""
    
    async def get_element_attribute(self, element: ElementHandle, attribute: str) -> str:
        """
        Get the value of an element's attribute.
        
        Args:
            element: The element to get the attribute from
            attribute: The attribute name
            
        Returns:
            The attribute value or empty string if not found
        """
        try:
            value = await element.get_attribute(attribute)
            return value if value is not None else ""
        except Exception as e:
            logger.error(f"Error getting element attribute: {str(e)}")
            return ""
    
    async def get_element_inner_html(self, element: ElementHandle) -> str:
        """
        Get the inner HTML of an element.
        
        Args:
            element: The element to get HTML from
            
        Returns:
            The inner HTML of the element
        """
        try:
            html = await self.page.evaluate("el => el.innerHTML", element)
            return html
        except Exception as e:
            logger.error(f"Error getting element inner HTML: {str(e)}")
            return ""
    
    async def element_exists(self, selector: str) -> bool:
        """
        Check if an element exists.
        
        Args:
            selector: The selector to check
            
        Returns:
            True if the element exists, False otherwise
        """
        try:
            element = await self.page.query_selector(selector)
            return element is not None
        except Exception:
            return False


class TableParser(BaseParser):
    """
    Parser for table elements.
    """
    
    async def parse_table(self, table_element: ElementHandle) -> List[Dict[str, str]]:
        """
        Parse a table into a list of dictionaries.
        
        Args:
            table_element: The table element to parse
            
        Returns:
            List of dictionaries, each representing a row in the table
        """
        try:
            # Get table data via JavaScript for efficient parsing
            table_data = await self.page.evaluate("""
                (table) => {
                    // Get header cells
                    const headerCells = Array.from(table.querySelectorAll('thead th, tr:first-child th, tr:first-child td'));
                    
                    // If no header row found, create column names (Column1, Column2, etc.)
                    let headers = headerCells.map(cell => cell.textContent.trim());
                    if (headers.length === 0) {
                        // Try to determine number of columns from the first data row
                        const firstRow = table.querySelector('tr');
                        if (firstRow) {
                            const cellCount = firstRow.querySelectorAll('td, th').length;
                            headers = Array.from({length: cellCount}, (_, i) => `Column${i+1}`);
                        }
                    }
                    
                    // If still no headers, return empty result
                    if (headers.length === 0) return [];
                    
                    // Get all data rows (skip header row if present)
                    const rows = Array.from(table.querySelectorAll('tr')).slice(headerCells.length > 0 ? 1 : 0);
                    
                    // Convert rows to objects
                    return rows.map(row => {
                        const cells = Array.from(row.querySelectorAll('td, th'));
                        const rowData = {};
                        
                        // Map cell data to headers (for as many cells as there are headers)
                        headers.forEach((header, index) => {
                            if (index < cells.length) {
                                // Use header as property name
                                rowData[header] = cells[index].textContent.trim();
                            } else {
                                // Handle case where row has fewer cells than headers
                                rowData[header] = '';
                            }
                        });
                        
                        return rowData;
                    }).filter(row => Object.values(row).some(value => value !== '')); // Filter out empty rows
                }
            """, table_element)
            
            return table_data
        except Exception as e:
            logger.error(f"Error parsing table: {str(e)}")
            return []
    
    async def parse_table_with_options(
        self, 
        table_element: ElementHandle,
        options: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """
        Parse a table with additional options.
        
        Args:
            table_element: The table element to parse
            options: Parsing options:
                - include_header: Whether to include the header row
                - max_rows: Maximum number of rows to parse
                - columns: List of column indices or names to include
                - transform: Function to transform each row
            
        Returns:
            List of dictionaries, each representing a row in the table
        """
        try:
            # Parse the basic table data
            table_data = await self.parse_table(table_element)
            
            # Apply options
            include_header = options.get("include_header", False)
            max_rows = options.get("max_rows", None)
            columns = options.get("columns", None)
            
            # Limit rows if specified
            if max_rows is not None and max_rows > 0:
                table_data = table_data[:max_rows]
            
            # Filter columns if specified
            if columns is not None and len(columns) > 0:
                # If columns are specified by name
                if isinstance(columns[0], str):
                    filtered_data = []
                    for row in table_data:
                        filtered_row = {col: row.get(col, "") for col in columns if col in row}
                        filtered_data.append(filtered_row)
                    table_data = filtered_data
                # If columns are specified by index
                elif isinstance(columns[0], int):
                    if table_data:
                        headers = list(table_data[0].keys())
                        selected_headers = [headers[i] for i in columns if i < len(headers)]
                        
                        filtered_data = []
                        for row in table_data:
                            filtered_row = {header: row.get(header, "") for header in selected_headers}
                            filtered_data.append(filtered_row)
                        table_data = filtered_data
            
            return table_data
        except Exception as e:
            logger.error(f"Error parsing table with options: {str(e)}")
            return []
    
    async def get_table_headers(self, table_element: ElementHandle) -> List[str]:
        """
        Get the headers of a table.
        
        Args:
            table_element: The table element
            
        Returns:
            List of header strings
        """
        try:
            headers = await self.page.evaluate("""
                (table) => {
                    const headerCells = Array.from(table.querySelectorAll('thead th, tr:first-child th, tr:first-child td'));
                    return headerCells.map(cell => cell.textContent.trim());
                }
            """, table_element)
            
            return headers
        except Exception as e:
            logger.error(f"Error getting table headers: {str(e)}")
            return []


class ListParser(BaseParser):
    """
    Parser for list elements.
    """
    
    async def parse_list(self, list_element: ElementHandle) -> List[str]:
        """
        Parse a list into a list of strings.
        
        Args:
            list_element: The list element to parse (ul, ol, dl)
            
        Returns:
            List of strings, each representing an item in the list
        """
        try:
            # Check the type of list
            tag_name = await self.page.evaluate("el => el.tagName.toLowerCase()", list_element)
            
            if tag_name in ["ul", "ol"]:
                # Parse unordered or ordered list
                items = await self.page.evaluate("""
                    (list) => {
                        const listItems = Array.from(list.querySelectorAll('li'));
                        return listItems.map(item => item.textContent.trim());
                    }
                """, list_element)
                
                return items
            elif tag_name == "dl":
                # Parse definition list (returns pairs of terms and descriptions)
                items = await self.page.evaluate("""
                    (list) => {
                        const result = [];
                        const terms = Array.from(list.querySelectorAll('dt'));
                        
                        terms.forEach(term => {
                            let description = '';
                            let descElement = term.nextElementSibling;
                            
                            if (descElement && descElement.tagName === 'DD') {
                                description = descElement.textContent.trim();
                            }
                            
                            result.push({
                                term: term.textContent.trim(),
                                description: description
                            });
                        });
                        
                        return result;
                    }
                """, list_element)
                
                # Convert to list of formatted strings
                return [f"{item['term']}: {item['description']}" for item in items]
            else:
                # Not a recognized list type
                return []
        except Exception as e:
            logger.error(f"Error parsing list: {str(e)}")
            return []
    
    async def parse_list_items_with_links(self, list_element: ElementHandle) -> List[Dict[str, str]]:
        """
        Parse a list including any links in the items.
        
        Args:
            list_element: The list element to parse
            
        Returns:
            List of dictionaries with item text and link information
        """
        try:
            items = await self.page.evaluate("""
                (list) => {
                    const listItems = Array.from(list.querySelectorAll('li'));
                    
                    return listItems.map(item => {
                        const link = item.querySelector('a');
                        
                        if (link) {
                            return {
                                text: item.textContent.trim(),
                                link_text: link.textContent.trim(),
                                link_url: link.href,
                                has_link: true
                            };
                        } else {
                            return {
                                text: item.textContent.trim(),
                                link_text: '',
                                link_url: '',
                                has_link: false
                            };
                        }
                    });
                }
            """, list_element)
            
            return items
        except Exception as e:
            logger.error(f"Error parsing list items with links: {str(e)}")
            return []


class FormParser(BaseParser):
    """
    Parser for form elements.
    """
    
    async def parse_form(self, form_element: ElementHandle) -> Dict[str, Any]:
        """
        Parse a form into a structured representation.
        
        Args:
            form_element: The form element to parse
            
        Returns:
            Dictionary with form information and fields
        """
        try:
            form_data = await self.page.evaluate("""
                (form) => {
                    const formData = {
                        action: form.action || '',
                        method: form.method || 'get',
                        id: form.id || '',
                        name: form.name || '',
                        fields: []
                    };
                    
                    // Get all form fields
                    const fields = form.querySelectorAll('input, select, textarea, button[type="submit"]');
                    
                    Array.from(fields).forEach(field => {
                        // Skip hidden fields
                        if (field.type === 'hidden') {
                            return;
                        }
                        
                        // Get field label
                        let label = '';
                        const id = field.id;
                        
                        if (id) {
                            const labelElement = document.querySelector(`label[for="${id}"]`);
                            if (labelElement) {
                                label = labelElement.textContent.trim();
                            }
                        }
                        
                        // If no label found, check if field is inside a label
                        if (!label) {
                            let parent = field.parentElement;
                            while (parent && parent !== form) {
                                if (parent.tagName === 'LABEL') {
                                    label = parent.textContent.trim();
                                    // Remove field value from label text if present
                                    if (field.value) {
                                        label = label.replace(field.value, '').trim();
                                    }
                                    break;
                                }
                                parent = parent.parentElement;
                            }
                        }
                        
                        // If still no label, use placeholder or name
                        if (!label) {
                            label = field.placeholder || field.name || field.id || field.type;
                        }
                        
                        const fieldInfo = {
                            type: field.type || field.tagName.toLowerCase(),
                            name: field.name || '',
                            id: field.id || '',
                            label: label,
                            value: field.value || '',
                            placeholder: field.placeholder || '',
                            required: field.required || false,
                            disabled: field.disabled || false
                        };
                        
                        // Additional info for select fields
                        if (field.tagName === 'SELECT') {
                            fieldInfo.options = Array.from(field.options).map(option => {
                                return {
                                    value: option.value,
                                    text: option.text,
                                    selected: option.selected
                                };
                            });
                        }
                        
                        // Additional info for radio/checkbox
                        if (field.type === 'radio' || field.type === 'checkbox') {
                            fieldInfo.checked = field.checked;
                        }
                        
                        formData.fields.push(fieldInfo);
                    });
                    
                    return formData;
                }
            """, form_element)
            
            return form_data
        except Exception as e:
            logger.error(f"Error parsing form: {str(e)}")
            return {"fields": []}
    
    async def get_form_values(self, form_element: ElementHandle) -> Dict[str, str]:
        """
        Get the current values of all fields in a form.
        
        Args:
            form_element: The form element
            
        Returns:
            Dictionary of field names and their values
        """
        try:
            values = await self.page.evaluate("""
                (form) => {
                    const result = {};
                    const fields = form.querySelectorAll('input, select, textarea');
                    
                    Array.from(fields).forEach(field => {
                        // Skip buttons and submit fields
                        if (field.type === 'button' || field.type === 'submit') {
                            return;
                        }
                        
                        const name = field.name || field.id;
                        if (!name) return;
                        
                        // Handle different input types
                        if (field.type === 'checkbox' || field.type === 'radio') {
                            if (field.checked) {
                                result[name] = field.value || 'on';
                            }
                        } else if (field.tagName === 'SELECT' && field.multiple) {
                            // Handle multi-select
                            result[name] = Array.from(field.selectedOptions).map(opt => opt.value);
                        } else {
                            // Text inputs, textareas, select dropdowns
                            result[name] = field.value || '';
                        }
                    });
                    
                    return result;
                }
            """, form_element)
            
            return values
        except Exception as e:
            logger.error(f"Error getting form values: {str(e)}")
            return {}


class StructuredContentParser(BaseParser):
    """
    Parser for various types of structured content.
    """
    
    async def parse_json_ld(self) -> List[Dict[str, Any]]:
        """
        Parse JSON-LD structured data from the page.
        
        Returns:
            List of parsed JSON-LD data objects
        """
        try:
            json_ld_data = await self.page.evaluate("""
                () => {
                    const jsonLdScripts = Array.from(document.querySelectorAll('script[type="application/ld+json"]'));
                    
                    return jsonLdScripts.map(script => {
                        try {
                            return JSON.parse(script.textContent);
                        } catch (e) {
                            return null;
                        }
                    }).filter(data => data !== null);
                }
            """)
            
            return json_ld_data
        except Exception as e:
            logger.error(f"Error parsing JSON-LD data: {str(e)}")
            return []
    
    async def parse_meta_tags(self) -> Dict[str, str]:
        """
        Parse meta tags from the page.
        
        Returns:
            Dictionary of meta tag names/properties and their content
        """
        try:
            meta_data = await self.page.evaluate("""
                () => {
                    const metaTags = Array.from(document.querySelectorAll('meta'));
                    const result = {};
                    
                    metaTags.forEach(tag => {
                        const name = tag.getAttribute('name');
                        const property = tag.getAttribute('property');
                        const content = tag.getAttribute('content');
                        
                        if (name && content) {
                            result[name] = content;
                        } else if (property && content) {
                            result[property] = content;
                        }
                    });
                    
                    return result;
                }
            """)
            
            return meta_data
        except Exception as e:
            logger.error(f"Error parsing meta tags: {str(e)}")
            return {}
    
    async def parse_heading_structure(self) -> List[Dict[str, Any]]:
        """
        Parse the heading structure of the page.
        
        Returns:
            List of headings with their level, text, and ID
        """
        try:
            headings = await self.page.evaluate("""
                () => {
                    const headings = Array.from(document.querySelectorAll('h1, h2, h3, h4, h5, h6'));
                    
                    return headings.map(heading => {
                        return {
                            level: parseInt(heading.tagName.substring(1)),
                            text: heading.textContent.trim(),
                            id: heading.id || '',
                            has_anchor: heading.querySelector('a') !== null
                        };
                    });
                }
            """)
            
            return headings
        except Exception as e:
            logger.error(f"Error parsing heading structure: {str(e)}")
            return []
    
    async def parse_navigation_menu(self) -> List[Dict[str, Any]]:
        """
        Parse navigation menus from the page.
        
        Returns:
            List of navigation items with their text, URL, and children
        """
        try:
            navigation = await self.page.evaluate("""
                () => {
                    // Helper function to extract menu items
                    const extractMenuItems = (container) => {
                        const items = [];
                        
                        // Get direct li children
                        const listItems = Array.from(container.children).filter(child => 
                            child.tagName === 'LI'
                        );
                        
                        listItems.forEach(item => {
                            const link = item.querySelector('a');
                            const subMenu = item.querySelector('ul, ol');
                            
                            const menuItem = {
                                text: item.textContent.trim(),
                                has_link: !!link,
                                url: link ? link.href : '',
                                link_text: link ? link.textContent.trim() : '',
                                children: []
                            };
                            
                            // Extract submenu if present
                            if (subMenu) {
                                menuItem.children = extractMenuItems(subMenu);
                            }
                            
                            items.push(menuItem);
                        });
                        
                        return items;
                    };
                    
                    // Try to find navigation menus
                    const navElements = [
                        ...Array.from(document.querySelectorAll('nav')),
                        ...Array.from(document.querySelectorAll('[role="navigation"]')),
                        ...Array.from(document.querySelectorAll('.nav, .menu, .navigation'))
                    ];
                    
                    return navElements.map(nav => {
                        // Find the first ul or ol in the nav
                        const menu = nav.querySelector('ul, ol');
                        
                        return {
                            id: nav.id || '',
                            class: nav.className || '',
                            items: menu ? extractMenuItems(menu) : []
                        };
                    }).filter(nav => nav.items.length > 0);
                }
            """)
            
            return navigation
        except Exception as e:
            logger.error(f"Error parsing navigation menu: {str(e)}")
            return []
