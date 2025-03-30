"""
Extraction selectors module.

This module provides functionality for identifying and selecting content
based on context, using various selector strategies.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Union, Tuple, Callable

from playwright.async_api import Page, ElementHandle, Locator

from browser.elements import find_element, get_elements, get_element_properties

# Set up logger
logger = logging.getLogger(__name__)


class ContentSelector:
    """
    Selects content from web pages based on various strategies.
    """
    
    def __init__(self, page: Page):
        """
        Initialize the content selector.
        
        Args:
            page: The page to select content from
        """
        self.page = page
    
    async def select_by_query(self, query: str) -> Optional[ElementHandle]:
        """
        Select content using a CSS, XPath, or text query.
        
        Args:
            query: The query to select content with
            
        Returns:
            The selected element or None if not found
        """
        element = await find_element(self.page, query)
        return element
    
    async def select_elements_by_query(self, query: str) -> List[ElementHandle]:
        """
        Select multiple elements using a CSS, XPath, or text query.
        
        Args:
            query: The query to select elements with
            
        Returns:
            The list of selected elements
        """
        elements = await get_elements(self.page, query)
        return elements
    
    async def select_by_semantic_query(self, semantic_query: str) -> Optional[ElementHandle]:
        """
        Select content based on a semantic description.
        
        Args:
            semantic_query: The semantic description of the content to select
            
        Returns:
            The selected element or None if not found
        """
        # Use semantic scoring to find the best matching element
        matching_elements = await self._score_elements_by_semantic_query(semantic_query)
        
        if matching_elements and len(matching_elements) > 0:
            # Return the highest scoring element
            return matching_elements[0]["element"]
            
        return None
    
    async def select_elements_by_semantic_query(
        self, 
        semantic_query: str, 
        limit: int = 5
    ) -> List[ElementHandle]:
        """
        Select multiple elements based on a semantic description.
        
        Args:
            semantic_query: The semantic description of the content to select
            limit: Maximum number of elements to return
            
        Returns:
            The list of selected elements
        """
        # Use semantic scoring to find matching elements
        matching_elements = await self._score_elements_by_semantic_query(semantic_query)
        
        # Return the top N elements
        return [item["element"] for item in matching_elements[:limit]]
    
    async def _score_elements_by_semantic_query(
        self, 
        semantic_query: str
    ) -> List[Dict[str, Any]]:
        """
        Score elements based on how well they match a semantic query.
        
        Args:
            semantic_query: The semantic description of the content to select
            
        Returns:
            List of dictionaries with elements and their scores
        """
        # Get all visible interactive elements
        elements = await self._get_candidate_elements()
        
        # Score each element based on relevant attributes
        scored_elements = []
        
        # Normalize query for better matching
        query_terms = self._extract_keywords(semantic_query.lower())
        
        for element in elements:
            # Get element properties to score against
            properties = await get_element_properties(element)
            
            # Calculate score based on term matching
            score = 0
            
            # Check text content
            text = properties.get("text", "").lower()
            for term in query_terms:
                if term in text:
                    score += 2  # Higher weight for text content
            
            # Check description
            description = properties.get("description", "").lower()
            for term in query_terms:
                if term in description:
                    score += 3  # Higher weight for description (often contains label/name)
            
            # Check attributes
            attributes = properties.get("attributes", {})
            for attr_name, attr_value in attributes.items():
                if isinstance(attr_value, str):
                    attr_value = attr_value.lower()
                    for term in query_terms:
                        if term in attr_value:
                            # Higher weight for important attributes
                            if attr_name in ["id", "name", "title", "aria-label", "placeholder"]:
                                score += 2
                            else:
                                score += 1
            
            # Bonus for role matching with query
            role = properties.get("role", "").lower()
            role_terms = ["button", "link", "input", "checkbox", "radio", "select", "menu", "tab"]
            for term in role_terms:
                if term in query_terms and term in role:
                    score += 3  # Significant bonus for role match
            
            # Only include elements with a positive score
            if score > 0:
                scored_elements.append({
                    "element": element,
                    "score": score,
                    "properties": properties
                })
        
        # Sort by score in descending order
        scored_elements.sort(key=lambda x: x["score"], reverse=True)
        
        return scored_elements
    
    async def _get_candidate_elements(self) -> List[ElementHandle]:
        """
        Get a list of candidate elements for semantic selection.
        
        Returns:
            List of candidate elements
        """
        # Get all interactive elements
        selectors = [
            "a", "button", "input", "select", "textarea", 
            "[role='button']", "[role='link']", "[role='menuitem']", 
            "[role='tab']", "[role='checkbox']", "[role='radio']",
            "[role='switch']", "[role='textbox']", "[role='combobox']",
            "h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "th",
            "div[id]", "div[class]", "span[id]", "span[class]",
            "section", "article", "main", "aside", "header", "footer"
        ]
        
        all_elements = []
        for selector in selectors:
            try:
                elements = await self.page.query_selector_all(selector)
                all_elements.extend(elements)
            except Exception as e:
                logger.debug(f"Error getting elements with selector {selector}: {str(e)}")
        
        # Filter out invisible elements
        visible_elements = []
        for element in all_elements:
            try:
                is_visible = await element.is_visible()
                if is_visible:
                    visible_elements.append(element)
            except Exception:
                continue
                
        return visible_elements
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract keywords from text, filtering out common stop words.
        
        Args:
            text: The text to extract keywords from
            
        Returns:
            List of keywords
        """
        # Basic stopwords list
        stopwords = {'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                    'to', 'of', 'and', 'or', 'but', 'in', 'on', 'at', 'for', 'with',
                    'by', 'about', 'against', 'between', 'into', 'through', 'during',
                    'before', 'after', 'above', 'below', 'from', 'up', 'down', 'that',
                    'this', 'these', 'those', 'it', 'its'}
        
        # Split by non-alphanumeric characters and filter out stopwords and short words
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [word for word in words if word not in stopwords and len(word) > 1]
        
        return keywords


class TableSelector:
    """
    Specialized selector for tables and structured data.
    """
    
    def __init__(self, page: Page):
        """
        Initialize the table selector.
        
        Args:
            page: The page to select tables from
        """
        self.page = page
    
    async def select_best_table(self, description: str) -> Optional[ElementHandle]:
        """
        Select the best matching table based on a description.
        
        Args:
            description: The description of the table to select
            
        Returns:
            The selected table element or None if not found
        """
        # Get all tables on the page
        tables = await self.page.query_selector_all("table")
        
        if not tables:
            logger.debug("No tables found on the page")
            return None
        
        best_table = None
        highest_score = -1
        
        description_keywords = set(self._extract_keywords(description.lower()))
        
        for table in tables:
            score = 0
            
            # Check for caption
            caption = await table.query_selector("caption")
            if caption:
                caption_text = await self.page.evaluate("el => el.textContent", caption)
                if caption_text:
                    caption_keywords = set(self._extract_keywords(caption_text.lower()))
                    # Score based on keyword overlap
                    score += len(description_keywords.intersection(caption_keywords)) * 2
            
            # Check for table headers
            headers = await table.query_selector_all("th")
            header_texts = []
            for header in headers:
                header_text = await self.page.evaluate("el => el.textContent", header)
                if header_text:
                    header_texts.append(header_text.lower())
            
            # Score based on keyword presence in headers
            for keyword in description_keywords:
                for header_text in header_texts:
                    if keyword in header_text:
                        score += 1
            
            # Check for a table heading or description nearby
            previous_element = await self.page.evaluate("""
                (table) => {
                    let prev = table.previousElementSibling;
                    if (prev && ['H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'P'].includes(prev.tagName)) {
                        return prev.textContent;
                    }
                    return null;
                }
            """, table)
            
            if previous_element:
                prev_keywords = set(self._extract_keywords(previous_element.lower()))
                score += len(description_keywords.intersection(prev_keywords)) * 2
            
            # Update best match if this table has a higher score
            if score > highest_score:
                highest_score = score
                best_table = table
        
        # If no table matches well, just return the first table
        if highest_score == 0 and tables:
            return tables[0]
            
        return best_table
    
    async def select_all_tables(self) -> List[Dict[str, Any]]:
        """
        Select all tables on the page with metadata.
        
        Returns:
            List of tables with metadata
        """
        tables = await self.page.query_selector_all("table")
        
        result = []
        for i, table in enumerate(tables):
            # Get table metadata
            metadata = {}
            
            # Get caption if available
            caption = await table.query_selector("caption")
            if caption:
                metadata["caption"] = await self.page.evaluate("el => el.textContent", caption)
            
            # Get headers
            headers = await table.query_selector_all("th")
            header_texts = []
            for header in headers:
                header_text = await self.page.evaluate("el => el.textContent", header)
                header_texts.append(header_text.strip())
            
            if header_texts:
                metadata["headers"] = header_texts
            
            # Count rows and columns
            rows = await table.query_selector_all("tr")
            metadata["row_count"] = len(rows)
            
            if rows:
                # Get column count from first row
                first_row = rows[0]
                cells = await first_row.query_selector_all("td, th")
                metadata["column_count"] = len(cells)
            
            # Get heading or description from previous element
            previous_element = await self.page.evaluate("""
                (table) => {
                    let prev = table.previousElementSibling;
                    if (prev && ['H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'P'].includes(prev.tagName)) {
                        return {
                            tag: prev.tagName.toLowerCase(),
                            text: prev.textContent
                        };
                    }
                    return null;
                }
            """, table)
            
            if previous_element:
                metadata["previous_element"] = previous_element
            
            result.append({
                "index": i,
                "table": table,
                "metadata": metadata
            })
        
        return result
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract keywords from text, filtering out common stop words.
        
        Args:
            text: The text to extract keywords from
            
        Returns:
            List of keywords
        """
        # Basic stopwords list
        stopwords = {'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                    'to', 'of', 'and', 'or', 'but', 'in', 'on', 'at', 'for', 'with',
                    'by', 'about', 'against', 'between', 'into', 'through', 'during',
                    'before', 'after', 'above', 'below', 'from', 'up', 'down', 'that',
                    'this', 'these', 'those', 'it', 'its'}
        
        # Split by non-alphanumeric characters and filter out stopwords and short words
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [word for word in words if word not in stopwords and len(word) > 1]
        
        return keywords


class FormSelector:
    """
    Specialized selector for forms and form elements.
    """
    
    def __init__(self, page: Page):
        """
        Initialize the form selector.
        
        Args:
            page: The page to select forms from
        """
        self.page = page
    
    async def select_form(self, description: Optional[str] = None) -> Optional[ElementHandle]:
        """
        Select a form based on an optional description.
        
        Args:
            description: Optional description of the form to select
            
        Returns:
            The selected form element or None if not found
        """
        # Get all forms
        forms = await self.page.query_selector_all("form")
        
        if not forms:
            logger.debug("No forms found on the page")
            return None
        
        # If no description provided, return the first form
        if not description:
            return forms[0]
        
        best_form = None
        highest_score = -1
        
        description_keywords = set(self._extract_keywords(description.lower()))
        
        for form in forms:
            score = 0
            
            # Check form attributes
            attributes = await self._get_element_attributes(form)
            
            # Score based on attribute matches
            for attr_name, attr_value in attributes.items():
                if isinstance(attr_value, str):
                    attr_value = attr_value.lower()
                    for keyword in description_keywords:
                        if keyword in attr_value:
                            score += 1
            
            # Check form fields
            fields = await form.query_selector_all("input, select, textarea, button")
            for field in fields:
                field_attrs = await self._get_element_attributes(field)
                
                # Score based on field attributes matching the description
                for attr_name, attr_value in field_attrs.items():
                    if isinstance(attr_value, str):
                        attr_value = attr_value.lower()
                        for keyword in description_keywords:
                            if keyword in attr_value:
                                # Higher weight for important attributes
                                if attr_name in ["id", "name", "placeholder", "aria-label"]:
                                    score += 2
                                else:
                                    score += 1
            
            # Check for labels within the form
            labels = await form.query_selector_all("label")
            for label in labels:
                label_text = await self.page.evaluate("el => el.textContent", label)
                if label_text:
                    label_text = label_text.lower()
                    for keyword in description_keywords:
                        if keyword in label_text:
                            score += 2  # Higher weight for visible labels
            
            # Update best match if this form has a higher score
            if score > highest_score:
                highest_score = score
                best_form = form
        
        # If no form matches well, just return the first form
        if highest_score == 0 and forms:
            return forms[0]
            
        return best_form
    
    async def select_input_field(
        self, 
        form: ElementHandle, 
        field_description: str
    ) -> Optional[ElementHandle]:
        """
        Select an input field within a form based on a description.
        
        Args:
            form: The form element containing the field
            field_description: Description of the field to select
            
        Returns:
            The selected input field or None if not found
        """
        # Get all fields in the form
        fields = await form.query_selector_all("input, select, textarea")
        
        if not fields:
            logger.debug("No input fields found in the form")
            return None
        
        best_field = None
        highest_score = -1
        
        description_keywords = set(self._extract_keywords(field_description.lower()))
        
        for field in fields:
            score = 0
            
            # Get field attributes
            attributes = await self._get_element_attributes(field)
            
            # Score based on attribute matches
            for attr_name, attr_value in attributes.items():
                if isinstance(attr_value, str):
                    attr_value = attr_value.lower()
                    for keyword in description_keywords:
                        if keyword in attr_value:
                            # Higher weight for important attributes
                            if attr_name in ["id", "name", "placeholder", "aria-label"]:
                                score += 2
                            else:
                                score += 1
            
            # Check for an associated label
            field_id = attributes.get("id", "")
            if field_id:
                label = await self.page.query_selector(f"label[for='{field_id}']")
                if label:
                    label_text = await self.page.evaluate("el => el.textContent", label)
                    if label_text:
                        label_text = label_text.lower()
                        for keyword in description_keywords:
                            if keyword in label_text:
                                score += 3  # Higher weight for explicitly associated labels
            
            # Check if the field is inside a label
            is_inside_label = await self.page.evaluate("""
                (field) => {
                    let el = field;
                    while (el && el.tagName !== 'FORM') {
                        if (el.tagName === 'LABEL') {
                            return true;
                        }
                        el = el.parentElement;
                    }
                    return false;
                }
            """, field)
            
            if is_inside_label:
                # Get the parent label text
                label_text = await self.page.evaluate("""
                    (field) => {
                        let el = field;
                        while (el && el.tagName !== 'FORM') {
                            if (el.tagName === 'LABEL') {
                                return el.textContent;
                            }
                            el = el.parentElement;
                        }
                        return '';
                    }
                """, field)
                
                if label_text:
                    label_text = label_text.lower()
                    for keyword in description_keywords:
                        if keyword in label_text:
                            score += 3  # Higher weight for containing labels
            
            # Update best match if this field has a higher score
            if score > highest_score:
                highest_score = score
                best_field = field
        
        # If no field matches well, return None
        if highest_score == 0:
            return None
            
        return best_field
    
    async def _get_element_attributes(self, element: ElementHandle) -> Dict[str, str]:
        """
        Get all attributes of an element.
        
        Args:
            element: The element to get attributes for
            
        Returns:
            Dictionary of attribute names and values
        """
        attributes = await self.page.evaluate("""
            (el) => {
                const attrs = {};
                for (const attr of el.attributes) {
                    attrs[attr.name] = attr.value;
                }
                return attrs;
            }
        """, element)
        
        return attributes
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract keywords from text, filtering out common stop words.
        
        Args:
            text: The text to extract keywords from
            
        Returns:
            List of keywords
        """
        # Basic stopwords list
        stopwords = {'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                    'to', 'of', 'and', 'or', 'but', 'in', 'on', 'at', 'for', 'with',
                    'by', 'about', 'against', 'between', 'into', 'through', 'during',
                    'before', 'after', 'above', 'below', 'from', 'up', 'down', 'that',
                    'this', 'these', 'those', 'it', 'its'}
        
        # Split by non-alphanumeric characters and filter out stopwords and short words
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [word for word in words if word not in stopwords and len(word) > 1]
        
        return keywords
