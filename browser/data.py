"""
Browser data extraction module.

This module provides functionality for extracting data from web pages,
including text, tables, links, and structured data.
"""

import logging
import re
import json
from typing import Dict, List, Any, Optional, Union, Tuple

from playwright.async_api import Page, ElementHandle

from browser.elements import find_element, get_elements, extract_element_text, get_element_attributes

# Set up logger
logger = logging.getLogger(__name__)


async def extract_page_text(page: Page) -> str:
    """
    Extract all visible text from a page.
    
    Args:
        page: The page to extract text from
        
    Returns:
        The visible text content from the page
    """
    try:
        text = await page.evaluate("""
            () => {
                // Get all text nodes
                const walker = document.createTreeWalker(
                    document.body, 
                    NodeFilter.SHOW_TEXT, 
                    {
                        acceptNode: function(node) {
                            // Skip hidden elements
                            if (node.parentElement && 
                                window.getComputedStyle(node.parentElement).display === 'none') {
                                return NodeFilter.FILTER_REJECT;
                            }
                            // Skip empty nodes
                            if (node.textContent.trim() === '') {
                                return NodeFilter.FILTER_REJECT;
                            }
                            return NodeFilter.FILTER_ACCEPT;
                        }
                    }
                );
                
                // Collect text
                const textContent = [];
                let currentNode;
                while (currentNode = walker.nextNode()) {
                    let text = currentNode.textContent.trim();
                    if (text) {
                        // Check if this is part of a form control, if so, add label info
                        let parent = currentNode.parentElement;
                        if (parent && 
                            (parent.tagName === 'LABEL' || 
                            parent.tagName === 'BUTTON' || 
                            parent.tagName === 'A' ||
                            parent.tagName === 'H1' ||
                            parent.tagName === 'H2' ||
                            parent.tagName === 'H3' ||
                            parent.tagName === 'H4' ||
                            parent.tagName === 'H5' ||
                            parent.tagName === 'H6' ||
                            parent.tagName === 'P')) {
                            // Give preference to headers and paragraphs by adding a newline
                            textContent.push(text);
                            if (['H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'P'].includes(parent.tagName)) {
                                textContent.push(''); // Add empty line after headers and paragraphs
                            }
                        } else {
                            textContent.push(text);
                        }
                    }
                }
                
                return textContent.join('\\n').replace(/\\n{3,}/g, '\\n\\n');
            }
        """)
        
        return text
    except Exception as e:
        logger.error(f"Error extracting page text: {str(e)}")
        return ""


async def extract_selected_text(page: Page, selector: str) -> str:
    """
    Extract text from a selected element.
    
    Args:
        page: The page to extract from
        selector: CSS selector for the element
        
    Returns:
        The text content of the selected element
    """
    try:
        element = await find_element(page, selector)
        
        if not element:
            return ""
            
        text = await extract_element_text(element)
        return text
    except Exception as e:
        logger.error(f"Error extracting text from selector {selector}: {str(e)}")
        return ""


async def extract_table_data(page: Page, table_selector: str = "table") -> List[Dict[str, str]]:
    """
    Extract data from an HTML table into a list of dictionaries.
    
    Args:
        page: The page containing the table
        table_selector: CSS selector for the table
        
    Returns:
        List of dictionaries, each representing a row in the table
    """
    try:
        table_data = await page.evaluate(f"""
            (tableSelector) => {{
                const table = document.querySelector(tableSelector);
                if (!table) return [];
                
                // Get header cells
                const headerCells = Array.from(table.querySelectorAll('thead th, tr:first-child th, tr:first-child td'));
                
                // If no header row found, create column names (Column1, Column2, etc.)
                let headers = headerCells.map(cell => cell.textContent.trim());
                if (headers.length === 0) {{
                    // Try to determine number of columns from the first data row
                    const firstRow = table.querySelector('tr');
                    if (firstRow) {{
                        const cellCount = firstRow.querySelectorAll('td, th').length;
                        headers = Array.from({{length: cellCount}}, (_, i) => `Column${{i+1}}`);
                    }}
                }}
                
                // If still no headers, return empty result
                if (headers.length === 0) return [];
                
                // Get all data rows (skip header row if present)
                const rows = Array.from(table.querySelectorAll('tr')).slice(headerCells.length > 0 ? 1 : 0);
                
                // Convert rows to objects
                return rows.map(row => {{
                    const cells = Array.from(row.querySelectorAll('td, th'));
                    const rowData = {{}};
                    
                    // Map cell data to headers (for as many cells as there are headers)
                    headers.forEach((header, index) => {{
                        if (index < cells.length) {{
                            // Use header as property name
                            rowData[header] = cells[index].textContent.trim();
                        }} else {{
                            // Handle case where row has fewer cells than headers
                            rowData[header] = '';
                        }}
                    }});
                    
                    return rowData;
                }}).filter(row => Object.values(row).some(value => value !== '')); // Filter out empty rows
            }}
        """, table_selector)
        
        return table_data
    except Exception as e:
        logger.error(f"Error extracting table data: {str(e)}")
        return []


async def extract_all_tables(page: Page) -> Dict[str, List[Dict[str, str]]]:
    """
    Extract data from all HTML tables on the page.
    
    Args:
        page: The page containing the tables
        
    Returns:
        Dictionary of table data, with keys like "Table1", "Table2", etc.
    """
    try:
        # Find all tables
        tables = await get_elements(page, "table")
        
        result = {}
        
        for i, _ in enumerate(tables):
            table_data = await extract_table_data(page, f"table:nth-of-type({i+1})")
            if table_data:
                result[f"Table{i+1}"] = table_data
                
        return result
    except Exception as e:
        logger.error(f"Error extracting all tables: {str(e)}")
        return {}


async def extract_links(page: Page, filter_pattern: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Extract all links from a page, optionally filtered by URL pattern.
    
    Args:
        page: The page to extract links from
        filter_pattern: Optional regex pattern to filter URLs
        
    Returns:
        List of dictionaries with link information
    """
    try:
        # Get all links
        links = await page.evaluate("""
            () => {
                const links = Array.from(document.querySelectorAll('a[href]'));
                return links.map(link => {
                    return {
                        text: link.textContent.trim(),
                        href: link.href,
                        title: link.title || '',
                        target: link.target || '',
                        aria_label: link.getAttribute('aria-label') || ''
                    };
                });
            }
        """)
        
        # Filter links if pattern provided
        if filter_pattern:
            pattern = re.compile(filter_pattern)
            links = [link for link in links if pattern.search(link["href"])]
            
        return links
    except Exception as e:
        logger.error(f"Error extracting links: {str(e)}")
        return []


async def extract_metadata(page: Page) -> Dict[str, str]:
    """
    Extract metadata from the page (title, description, og tags, etc.).
    
    Args:
        page: The page to extract metadata from
        
    Returns:
        Dictionary of metadata
    """
    try:
        metadata = await page.evaluate("""
            () => {
                const metadata = {
                    title: document.title || '',
                    description: '',
                    url: window.location.href
                };
                
                // Get meta tags
                const metaTags = Array.from(document.querySelectorAll('meta'));
                
                metaTags.forEach(tag => {
                    const name = tag.getAttribute('name');
                    const property = tag.getAttribute('property');
                    const content = tag.getAttribute('content');
                    
                    if (name && content) {
                        metadata[name] = content;
                    } else if (property && content) {
                        metadata[property] = content;
                    }
                });
                
                // Special handling for description
                if (metadata['description'] === '') {
                    const descTag = metaTags.find(tag => 
                        tag.getAttribute('name') === 'description' || 
                        tag.getAttribute('property') === 'og:description'
                    );
                    
                    if (descTag) {
                        metadata['description'] = descTag.getAttribute('content') || '';
                    }
                }
                
                return metadata;
            }
        """)
        
        return metadata
    except Exception as e:
        logger.error(f"Error extracting metadata: {str(e)}")
        return {"title": page.title() if page else "", "url": page.url if page else ""}


async def extract_structured_data(page: Page) -> List[Dict[str, Any]]:
    """
    Extract structured data (JSON-LD, microdata) from the page.
    
    Args:
        page: The page to extract structured data from
        
    Returns:
        List of structured data objects
    """
    try:
        # Extract JSON-LD data
        json_ld = await page.evaluate("""
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
        
        # Simplify and return combined results
        return json_ld
    except Exception as e:
        logger.error(f"Error extracting structured data: {str(e)}")
        return []


async def extract_form_data(page: Page, form_selector: str = "form") -> Dict[str, Any]:
    """
    Extract form fields and values.
    
    Args:
        page: The page containing the form
        form_selector: CSS selector for the form
        
    Returns:
        Dictionary of form field information
    """
    try:
        form_data = await page.evaluate(f"""
            (formSelector) => {{
                const form = document.querySelector(formSelector);
                if (!form) return {{}};
                
                const formData = {{
                    action: form.action || '',
                    method: form.method || 'get',
                    fields: []
                }};
                
                // Get all form fields
                const fields = form.querySelectorAll('input, select, textarea, button[type="submit"]');
                
                Array.from(fields).forEach(field => {{
                    // Skip hidden fields
                    if (field.type === 'hidden') return;
                    
                    // Get field label
                    let label = '';
                    const id = field.id;
                    
                    if (id) {{
                        const labelElement = document.querySelector(`label[for="${{id}}"]`);
                        if (labelElement) {{
                            label = labelElement.textContent.trim();
                        }}
                    }}
                    
                    // If no label found, check if field is inside a label
                    if (!label) {{
                        let parent = field.parentElement;
                        while (parent && parent !== form) {{
                            if (parent.tagName === 'LABEL') {{
                                label = parent.textContent.trim();
                                // Remove field value from label text if present
                                if (field.value) {{
                                    label = label.replace(field.value, '').trim();
                                }}
                                break;
                            }}
                            parent = parent.parentElement;
                        }}
                    }}
                    
                    // If still no label, use placeholder or name
                    if (!label) {{
                        label = field.placeholder || field.name || field.id || field.type;
                    }}
                    
                    const fieldInfo = {{
                        type: field.type || field.tagName.toLowerCase(),
                        name: field.name || '',
                        id: field.id || '',
                        label: label,
                        value: field.value || '',
                        placeholder: field.placeholder || '',
                        required: field.required || false,
                        disabled: field.disabled || false
                    }};
                    
                    // Additional info for select fields
                    if (field.tagName === 'SELECT') {{
                        fieldInfo.options = Array.from(field.options).map(option => {{
                            return {{
                                value: option.value,
                                text: option.text,
                                selected: option.selected
                            }};
                        }});
                    }}
                    
                    // Additional info for radio/checkbox
                    if (field.type === 'radio' || field.type === 'checkbox') {{
                        fieldInfo.checked = field.checked;
                    }}
                    
                    formData.fields.push(fieldInfo);
                }});
                
                return formData;
            }}
        """, form_selector)
        
        return form_data
    except Exception as e:
        logger.error(f"Error extracting form data: {str(e)}")
        return {"fields": []}


async def extract_all_forms(page: Page) -> List[Dict[str, Any]]:
    """
    Extract all forms from the page.
    
    Args:
        page: The page containing the forms
        
    Returns:
        List of form data dictionaries
    """
    try:
        # Count forms
        form_count = await page.evaluate("""
            () => document.querySelectorAll('form').length
        """)
        
        forms = []
        for i in range(form_count):
            form_data = await extract_form_data(page, f"form:nth-of-type({i+1})")
            if form_data and "fields" in form_data and form_data["fields"]:
                forms.append(form_data)
                
        return forms
    except Exception as e:
        logger.error(f"Error extracting all forms: {str(e)}")
        return []


async def extract_main_content(page: Page) -> str:
    """
    Extract the main content from a page, using heuristics to identify it.
    
    Args:
        page: The page to extract content from
        
    Returns:
        The main content text
    """
    try:
        content = await page.evaluate("""
            () => {
                // Try to find main content using common selectors
                const contentSelectors = [
                    'main',
                    'article',
                    '#content',
                    '.content',
                    '#main',
                    '.main',
                    '.post',
                    '.article',
                    '[role="main"]'
                ];
                
                let mainElement = null;
                
                // Try each selector
                for (const selector of contentSelectors) {
                    const element = document.querySelector(selector);
                    if (element) {
                        // Check if element has substantial content
                        const text = element.textContent.trim();
                        if (text.length > 100) {
                            mainElement = element;
                            break;
                        }
                    }
                }
                
                // If no main content found, use the element with most text
                if (!mainElement) {
                    // Get all elements that might contain content
                    const contentElements = Array.from(document.querySelectorAll('div, section, td'));
                    
                    let maxLength = 0;
                    
                    for (const element of contentElements) {
                        // Skip elements with very little content
                        const text = element.textContent.trim();
                        if (text.length > maxLength && text.length > 200) {
                            maxLength = text.length;
                            mainElement = element;
                        }
                    }
                }
                
                // If still nothing found, return the body content
                if (!mainElement) {
                    return document.body.textContent.trim();
                }
                
                // Extract text from the main element, preserving some structure
                const extractText = (element) => {
                    let result = [];
                    const childNodes = element.childNodes;
                    
                    for (const node of childNodes) {
                        if (node.nodeType === Node.TEXT_NODE) {
                            const text = node.textContent.trim();
                            if (text) result.push(text);
                        } else if (node.nodeType === Node.ELEMENT_NODE) {
                            // Handle specific elements
                            const tag = node.tagName.toLowerCase();
                            
                            if (['script', 'style', 'noscript', 'iframe', 'audio', 'video'].includes(tag)) {
                                continue; // Skip these elements
                            }
                            
                            if (['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'blockquote', 'pre', 'tr'].includes(tag)) {
                                // For block elements, add their text and a newline
                                const text = node.textContent.trim();
                                if (text) {
                                    result.push(text);
                                    result.push(''); // Add empty line
                                }
                            } else if (tag === 'br') {
                                result.push('');
                            } else if (tag === 'img') {
                                // Add image alt text if available
                                const alt = node.alt;
                                if (alt) result.push(`[Image: ${alt}]`);
                            } else {
                                // Recursively process other elements
                                const childTexts = extractText(node);
                                if (childTexts) result.push(...childTexts);
                            }
                        }
                    }
                    
                    return result;
                };
                
                const textParts = extractText(mainElement);
                return textParts.join('\\n').replace(/\\n{3,}/g, '\\n\\n'); // Normalize newlines
            }
        """)
        
        return content
    except Exception as e:
        logger.error(f"Error extracting main content: {str(e)}")
        return await extract_page_text(page)  # Fall back to full page text


async def extract_data_by_query(
    page: Page, 
    data_query: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Extract data from a page according to a query specification.
    
    Args:
        page: The page to extract data from
        data_query: A dictionary specifying what to extract
        
    Returns:
        Dictionary of extracted data
    """
    result = {}
    
    try:
        # Process each query item
        for key, query in data_query.items():
            if isinstance(query, str):
                # If query is a string, treat it as a selector and extract text
                if query == "url":
                    result[key] = page.url
                elif query == "title":
                    result[key] = await page.title()
                elif query == "full_text":
                    result[key] = await extract_page_text(page)
                elif query == "main_content":
                    result[key] = await extract_main_content(page)
                elif query == "metadata":
                    result[key] = await extract_metadata(page)
                elif query == "structured_data":
                    result[key] = await extract_structured_data(page)
                else:
                    # Assume it's a selector
                    result[key] = await extract_selected_text(page, query)
                    
            elif isinstance(query, dict):
                # More complex query
                query_type = query.get("type", "text")
                selector = query.get("selector", "")
                
                if query_type == "text" and selector:
                    result[key] = await extract_selected_text(page, selector)
                    
                elif query_type == "table" and selector:
                    result[key] = await extract_table_data(page, selector)
                    
                elif query_type == "tables":
                    result[key] = await extract_all_tables(page)
                    
                elif query_type == "links":
                    filter_pattern = query.get("filter", None)
                    result[key] = await extract_links(page, filter_pattern)
                    
                elif query_type == "forms":
                    if selector:
                        result[key] = await extract_form_data(page, selector)
                    else:
                        result[key] = await extract_all_forms(page)
                        
                elif query_type == "attributes" and selector:
                    element = await find_element(page, selector)
                    if element:
                        result[key] = await get_element_attributes(element)
                    else:
                        result[key] = {}
                        
                elif query_type == "html" and selector:
                    element = await find_element(page, selector)
                    if element:
                        html = await page.evaluate("(el) => el.outerHTML", element)
                        result[key] = html
                    else:
                        result[key] = ""
    
    except Exception as e:
        logger.error(f"Error processing data query: {str(e)}")
        result["error"] = str(e)
    
    return result


async def search_text_on_page(page: Page, search_text: str, case_sensitive: bool = False) -> List[Dict[str, Any]]:
    """
    Search for text on a page and return occurrences with context.
    
    Args:
        page: The page to search
        search_text: The text to search for
        case_sensitive: Whether to perform a case-sensitive search
        
    Returns:
        List of occurrences with context
    """
    try:
        occurrences = await page.evaluate("""
            (searchText, caseSensitive) => {
                const results = [];
                const searchRegex = new RegExp(searchText, caseSensitive ? 'g' : 'gi');
                
                // Create a tree walker to navigate text nodes
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    {
                        acceptNode: function(node) {
                            // Skip hidden elements
                            if (node.parentElement && 
                                window.getComputedStyle(node.parentElement).display === 'none') {
                                return NodeFilter.FILTER_REJECT;
                            }
                            // Skip empty nodes
                            if (node.textContent.trim() === '') {
                                return NodeFilter.FILTER_REJECT;
                            }
                            
                            // Accept nodes containing the search text
                            if (node.textContent.match(searchRegex)) {
                                return NodeFilter.FILTER_ACCEPT;
                            }
                            
                            return NodeFilter.FILTER_REJECT;
                        }
                    }
                );
                
                // Find matching nodes
                let node;
                while (node = walker.nextNode()) {
                    const text = node.textContent;
                    let match;
                    
                    // Reset regex for each search
                    searchRegex.lastIndex = 0;
                    
                    while ((match = searchRegex.exec(text)) !== null) {
                        // Get the position of the match
                        const position = match.index;
                        
                        // Extract context (text before and after)
                        const start = Math.max(0, position - 40);
                        const end = Math.min(text.length, position + searchText.length + 40);
                        let context = text.substring(start, end);
                        
                        // Add ellipsis if we truncated
                        if (start > 0) context = '...' + context;
                        if (end < text.length) context = context + '...';
                        
                        // Get element information for locating this result
                        let element = node.parentElement;
                        const tagName = element.tagName.toLowerCase();
                        const id = element.id;
                        const classList = Array.from(element.classList);
                        
                        // Try to build a basic selector to find this element
                        let selector = tagName;
                        if (id) selector += `#${id}`;
                        else if (classList.length > 0) {
                            selector += `.${classList.join('.')}`;
                        }
                        
                        results.push({
                            text: match[0],
                            context: context,
                            selector: selector
                        });
                    }
                }
                
                return results;
            }
        """, search_text, case_sensitive)
        
        return occurrences
    except Exception as e:
        logger.error(f"Error searching for text on page: {str(e)}")
        return [] 