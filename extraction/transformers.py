"""
Extraction transformers module.

This module provides functionality for transforming raw data extracted from 
web pages into structured formats for easier processing and analysis.
"""

import logging
import re
import csv
import io
import json
from typing import Dict, List, Any, Optional, Union, Callable, Set, TypeVar

# Set up logger
logger = logging.getLogger(__name__)

# Type variables for type hinting
T = TypeVar('T')
U = TypeVar('U')


class DataTransformer:
    """
    Base class for transforming extracted data.
    """
    
    @staticmethod
    def to_json(data: Any) -> str:
        """
        Convert data to JSON string.
        
        Args:
            data: The data to convert
            
        Returns:
            JSON string representation of the data
        """
        try:
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
            return json_str
        except Exception as e:
            logger.error(f"Error converting data to JSON: {str(e)}")
            return ""
    
    @staticmethod
    def to_csv(data: List[Dict[str, Any]]) -> str:
        """
        Convert list of dictionaries to CSV string.
        
        Args:
            data: List of dictionaries to convert
            
        Returns:
            CSV string representation of the data
        """
        try:
            if not data:
                return ""
                
            # Get all possible keys from all dictionaries
            fieldnames = set()
            for item in data:
                fieldnames.update(item.keys())
            fieldnames = sorted(list(fieldnames))
            
            # Write to CSV
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
            
            return output.getvalue()
        except Exception as e:
            logger.error(f"Error converting data to CSV: {str(e)}")
            return ""
    
    @staticmethod
    def to_markdown_table(data: List[Dict[str, Any]]) -> str:
        """
        Convert list of dictionaries to Markdown table.
        
        Args:
            data: List of dictionaries to convert
            
        Returns:
            Markdown table representation of the data
        """
        try:
            if not data:
                return ""
                
            # Get all keys from all dictionaries
            all_keys = set()
            for item in data:
                all_keys.update(item.keys())
            
            # Sort keys for consistent output
            headers = sorted(list(all_keys))
            
            # Build markdown table
            table = []
            
            # Add header row
            table.append("| " + " | ".join(headers) + " |")
            
            # Add separator row
            table.append("| " + " | ".join(["---" for _ in headers]) + " |")
            
            # Add data rows
            for item in data:
                row = []
                for key in headers:
                    # Get value, convert to string, and escape pipes
                    value = str(item.get(key, "")).replace("|", "\\|")
                    row.append(value)
                table.append("| " + " | ".join(row) + " |")
            
            return "\n".join(table)
        except Exception as e:
            logger.error(f"Error converting data to Markdown table: {str(e)}")
            return ""
    
    @staticmethod
    def filter_dict_list(data: List[Dict[str, Any]], **kwargs) -> List[Dict[str, Any]]:
        """
        Filter a list of dictionaries by matching field values.
        
        Args:
            data: List of dictionaries to filter
            **kwargs: Key-value pairs to filter by
            
        Returns:
            Filtered list of dictionaries
        """
        try:
            result = []
            
            for item in data:
                include = True
                
                for key, value in kwargs.items():
                    if key not in item or item[key] != value:
                        include = False
                        break
                
                if include:
                    result.append(item)
            
            return result
        except Exception as e:
            logger.error(f"Error filtering data: {str(e)}")
            return []
    
    @staticmethod
    def map_dict_keys(
        data: List[Dict[str, Any]],
        key_map: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Map dictionary keys to new keys.
        
        Args:
            data: List of dictionaries to transform
            key_map: Mapping of old keys to new keys
            
        Returns:
            Transformed list of dictionaries
        """
        try:
            result = []
            
            for item in data:
                new_item = {}
                
                # Add mapped keys
                for old_key, new_key in key_map.items():
                    if old_key in item:
                        new_item[new_key] = item[old_key]
                
                # Add remaining keys that weren't mapped
                for key, value in item.items():
                    if key not in key_map:
                        new_item[key] = value
                
                result.append(new_item)
            
            return result
        except Exception as e:
            logger.error(f"Error mapping dictionary keys: {str(e)}")
            return data  # Return original data on error
    
    @staticmethod
    def apply_function(
        data: List[T],
        func: Callable[[T], U]
    ) -> List[U]:
        """
        Apply a function to each item in a list.
        
        Args:
            data: List to transform
            func: Function to apply to each item
            
        Returns:
            Transformed list
        """
        try:
            return [func(item) for item in data]
        except Exception as e:
            logger.error(f"Error applying function to data: {str(e)}")
            return []


class TextTransformer:
    """
    Transformers for text data.
    """
    
    @staticmethod
    def extract_emails(text: str) -> List[str]:
        """
        Extract email addresses from text.
        
        Args:
            text: The text to extract emails from
            
        Returns:
            List of extracted email addresses
        """
        try:
            # Simple regex for email extraction
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            emails = re.findall(email_pattern, text)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_emails = [email.lower() for email in emails if not (email.lower() in seen or seen.add(email.lower()))]
            
            return unique_emails
        except Exception as e:
            logger.error(f"Error extracting emails: {str(e)}")
            return []
    
    @staticmethod
    def extract_phone_numbers(text: str) -> List[str]:
        """
        Extract phone numbers from text.
        
        Args:
            text: The text to extract phone numbers from
            
        Returns:
            List of extracted phone numbers
        """
        try:
            # Different phone patterns to catch various formats
            patterns = [
                r'\+\d{1,3}\s?\(\d{1,4}\)\s?\d{3,4}[-\s]?\d{3,4}',  # +X (XXX) XXX-XXXX
                r'\+\d{1,3}\s?\d{1,4}\s?\d{3,4}\s?\d{3,4}',         # +X XXX XXX XXXX
                r'\(\d{3,4}\)\s?\d{3,4}[-\s]?\d{3,4}',              # (XXX) XXX-XXXX
                r'\d{3,4}[-\s]?\d{3,4}[-\s]?\d{3,4}',               # XXX-XXX-XXXX
                r'\d{10,12}'                                         # XXXXXXXXXX
            ]
            
            # Find all matches from all patterns
            phone_numbers = []
            for pattern in patterns:
                matches = re.findall(pattern, text)
                phone_numbers.extend(matches)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_numbers = [number for number in phone_numbers if not (number in seen or seen.add(number))]
            
            return unique_numbers
        except Exception as e:
            logger.error(f"Error extracting phone numbers: {str(e)}")
            return []
    
    @staticmethod
    def extract_urls(text: str) -> List[str]:
        """
        Extract URLs from text.
        
        Args:
            text: The text to extract URLs from
            
        Returns:
            List of extracted URLs
        """
        try:
            # URL regex pattern
            url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
            urls = re.findall(url_pattern, text)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_urls = [url for url in urls if not (url in seen or seen.add(url))]
            
            return unique_urls
        except Exception as e:
            logger.error(f"Error extracting URLs: {str(e)}")
            return []
    
    @staticmethod
    def extract_dates(text: str) -> List[str]:
        """
        Extract dates from text.
        
        Args:
            text: The text to extract dates from
            
        Returns:
            List of extracted date strings
        """
        try:
            # Date patterns
            date_patterns = [
                r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',              # MM/DD/YYYY or DD/MM/YYYY
                r'\d{4}[-/]\d{1,2}[-/]\d{1,2}',                # YYYY/MM/DD
                r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}',  # Month DD, YYYY
                r'\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}'      # DD Month YYYY
            ]
            
            # Find all matches from all patterns
            dates = []
            for pattern in date_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                dates.extend(matches)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_dates = [date for date in dates if not (date in seen or seen.add(date))]
            
            return unique_dates
        except Exception as e:
            logger.error(f"Error extracting dates: {str(e)}")
            return []
    
    @staticmethod
    def extract_paragraphs(text: str) -> List[str]:
        """
        Extract paragraphs from text.
        
        Args:
            text: The text to extract paragraphs from
            
        Returns:
            List of paragraphs
        """
        try:
            # Split by double newlines and filter out empty paragraphs
            paragraphs = re.split(r'\n\s*\n', text)
            non_empty_paragraphs = [p.strip() for p in paragraphs if p.strip()]
            
            return non_empty_paragraphs
        except Exception as e:
            logger.error(f"Error extracting paragraphs: {str(e)}")
            return []
    
    @staticmethod
    def clean_whitespace(text: str) -> str:
        """
        Clean excess whitespace from text.
        
        Args:
            text: The text to clean
            
        Returns:
            Cleaned text
        """
        try:
            # Replace multiple spaces with a single space
            cleaned = re.sub(r'\s+', ' ', text)
            # Replace multiple newlines with a single newline
            cleaned = re.sub(r'\n+', '\n', cleaned)
            # Trim whitespace from beginning and end
            cleaned = cleaned.strip()
            
            return cleaned
        except Exception as e:
            logger.error(f"Error cleaning whitespace: {str(e)}")
            return text
    
    @staticmethod
    def summarize_text(text: str, max_length: int = 200) -> str:
        """
        Create a simple summary of text by truncating.
        
        Args:
            text: The text to summarize
            max_length: Maximum length of the summary
            
        Returns:
            Summarized text
        """
        try:
            # Clean whitespace
            cleaned_text = TextTransformer.clean_whitespace(text)
            
            if len(cleaned_text) <= max_length:
                return cleaned_text
            
            # Find the last complete sentence within max_length
            subset = cleaned_text[:max_length]
            last_period = subset.rfind('.')
            
            if last_period > 0:
                return subset[:last_period + 1]
            else:
                # If no sentence boundary found, just truncate and add ellipsis
                return subset.rsplit(' ', 1)[0] + '...'
        except Exception as e:
            logger.error(f"Error summarizing text: {str(e)}")
            return text[:max_length] + '...' if len(text) > max_length else text


class TableTransformer:
    """
    Transformers for table data.
    """
    
    @staticmethod
    def transpose_table(table_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transpose a table (rows become columns).
        
        Args:
            table_data: List of dictionaries representing table rows
            
        Returns:
            Transposed table data
        """
        try:
            if not table_data:
                return []
            
            # Get all column names
            columns = list(table_data[0].keys())
            
            # Create new structure with columns as rows
            result = []
            for col in columns:
                new_row = {"Column": col}
                
                for i, row in enumerate(table_data):
                    new_row[f"Row {i+1}"] = row.get(col, "")
                
                result.append(new_row)
            
            return result
        except Exception as e:
            logger.error(f"Error transposing table: {str(e)}")
            return table_data
    
    @staticmethod
    def pivot_table(
        table_data: List[Dict[str, Any]],
        index_col: str,
        value_col: str,
        pivot_col: str
    ) -> List[Dict[str, Any]]:
        """
        Create a pivot table from tabular data.
        
        Args:
            table_data: List of dictionaries representing table rows
            index_col: Column to use as the index
            value_col: Column containing the values
            pivot_col: Column to pivot (values become new columns)
            
        Returns:
            Pivoted table data
        """
        try:
            if not table_data:
                return []
            
            # Get unique values for the index and pivot columns
            index_values = set()
            pivot_values = set()
            
            for row in table_data:
                index_values.add(row.get(index_col, ""))
                pivot_values.add(row.get(pivot_col, ""))
            
            # Create result structure
            result = []
            
            # Create a dictionary to store the pivoted data
            pivoted_data = {}
            
            # Fill the dictionary with values
            for row in table_data:
                idx_val = row.get(index_col, "")
                pivot_val = row.get(pivot_col, "")
                val = row.get(value_col, "")
                
                if idx_val not in pivoted_data:
                    pivoted_data[idx_val] = {}
                
                pivoted_data[idx_val][pivot_val] = val
            
            # Convert dictionary to list of dictionaries
            for idx_val, values in pivoted_data.items():
                new_row = {index_col: idx_val}
                
                for pivot_val in pivot_values:
                    new_row[str(pivot_val)] = values.get(pivot_val, "")
                
                result.append(new_row)
            
            return result
        except Exception as e:
            logger.error(f"Error creating pivot table: {str(e)}")
            return table_data
    
    @staticmethod
    def add_calculated_column(
        table_data: List[Dict[str, Any]],
        new_column: str,
        calculation: Callable[[Dict[str, Any]], Any]
    ) -> List[Dict[str, Any]]:
        """
        Add a calculated column to a table.
        
        Args:
            table_data: List of dictionaries representing table rows
            new_column: Name of the new column
            calculation: Function that takes a row and returns the calculated value
            
        Returns:
            Table data with the new column
        """
        try:
            result = []
            
            for row in table_data:
                new_row = row.copy()
                new_row[new_column] = calculation(row)
                result.append(new_row)
            
            return result
        except Exception as e:
            logger.error(f"Error adding calculated column: {str(e)}")
            return table_data
    
    @staticmethod
    def aggregate_by_column(
        table_data: List[Dict[str, Any]],
        group_by: str,
        aggregations: Dict[str, Callable[[List[Any]], Any]]
    ) -> List[Dict[str, Any]]:
        """
        Aggregate table data by a column.
        
        Args:
            table_data: List of dictionaries representing table rows
            group_by: Column to group by
            aggregations: Dictionary of column names and aggregation functions
            
        Returns:
            Aggregated table data
        """
        try:
            if not table_data:
                return []
            
            # Group rows by the group_by column
            groups = {}
            
            for row in table_data:
                group_value = row.get(group_by, "")
                
                if group_value not in groups:
                    groups[group_value] = []
                
                groups[group_value].append(row)
            
            # Apply aggregations
            result = []
            
            for group_value, rows in groups.items():
                new_row = {group_by: group_value}
                
                for col, agg_func in aggregations.items():
                    # Extract values for this column
                    values = [row.get(col, None) for row in rows]
                    # Remove None values
                    values = [v for v in values if v is not None]
                    
                    # Apply aggregation function if we have values
                    if values:
                        try:
                            new_row[col] = agg_func(values)
                        except Exception as e:
                            logger.warning(f"Error applying aggregation for column {col}: {str(e)}")
                            new_row[col] = None
                    else:
                        new_row[col] = None
                
                result.append(new_row)
            
            return result
        except Exception as e:
            logger.error(f"Error aggregating table data: {str(e)}")
            return table_data
