"""
Natural language command parser.

This module provides functionality to parse natural language commands into
structured instructions that can be executed by the browser automation system.
It uses a combination of patterns and language model inference.
"""

import json
import logging
import re
from typing import Dict, List, Any, Optional, Union

from config.settings import Settings
from config.prompts import get_prompt
from utils.validators import validate_parsed_command

# Set up logger
logger = logging.getLogger(__name__)


class CommandParser:
    """
    Parser for natural language commands.
    
    Converts natural language commands into structured instructions using
    pattern matching and language model inference.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the command parser.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.url_pattern = re.compile(
            r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?:/[-\w%!.~\'()*+,;=:@/&?#]*)?'
        )
        # Common actions patterns
        self.navigate_patterns = [
            r'(?:go to|open|navigate to|visit)\s+(?:the\s+)?(?:website|site|page)?\s*(?:at|of|called|named)?\s*([\w\s.-]+)',
            r'(?:go to|open|navigate to|visit)\s+(https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?:/[-\w%!.~\'()*+,;=:@/&?#]*)?)'
        ]
        self.search_patterns = [
            r'(?:search for|look up|find)\s+([\w\s.-]+)',
            r'(?:search|google|bing|yahoo)\s+([\w\s.-]+)'
        ]
        self.login_patterns = [
            r'(?:log|sign) (?:in|into)\s+(?:to\s+)?(?:the\s+)?(?:website|site|page)?\s*(?:at|of|called|named)?\s*([\w\s.-]+)',
            r'(?:log|sign) (?:in|into)\s+(?:to\s+)?(https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?:/[-\w%!.~\'()*+,;=:@/&?#]*)?)',
            r'(?:log|sign) (?:in|into)\s+(?:with|using)\s+(?:username|user)\s+[\'"]?([\w\s@.-]+)[\'"]?\s+(?:and|with)\s+(?:password|pass)\s+[\'"]?([\w\s@.-]+)[\'"]?'
        ]
    
    async def parse_command(self, command: str) -> Dict[str, Any]:
        """
        Parse a natural language command into a structured instruction.
        
        Args:
            command: The natural language command to parse
            
        Returns:
            A structured representation of the command
        """
        logger.info(f"Parsing command: {command}")
        
        # Try pattern matching first for common operations
        pattern_result = self._pattern_match(command)
        if pattern_result:
            logger.debug(f"Parsed via pattern matching: {pattern_result}")
            return pattern_result
        
        # Fall back to language model inference
        lm_result = await self._lm_parse(command)
        logger.debug(f"Parsed via language model: {lm_result}")
        
        # Validate the result
        validated_result = validate_parsed_command(lm_result)
        return validated_result
    
    def _pattern_match(self, command: str) -> Optional[Dict[str, Any]]:
        """
        Parse command using regex pattern matching for common actions.
        
        Args:
            command: The command to parse
            
        Returns:
            Structured command or None if no pattern matches
        """
        # Check for navigation patterns
        for pattern in self.navigate_patterns:
            match = re.search(pattern, command, re.IGNORECASE)
            if match:
                target = match.group(1)
                # Check if the target is a URL
                if not self.url_pattern.match(target) and not target.startswith("http"):
                    # Try to convert to a URL
                    if "." in target and " " not in target:
                        target = f"https://{target}"
                    else:
                        target = f"https://www.google.com/search?q={target.replace(' ', '+')}"
                return {
                    "action": "navigate",
                    "target_url": target,
                    "elements": [],
                    "inputs": {},
                    "parameters": {}
                }
        
        # Check for search patterns
        for pattern in self.search_patterns:
            match = re.search(pattern, command, re.IGNORECASE)
            if match:
                search_term = match.group(1)
                return {
                    "action": "search",
                    "target_url": "https://www.google.com",
                    "elements": [
                        {
                            "description": "search box",
                            "role": "input"
                        }
                    ],
                    "inputs": {
                        "search_term": search_term
                    },
                    "parameters": {}
                }
        
        # Check for login patterns
        for pattern in self.login_patterns:
            match = re.search(pattern, command, re.IGNORECASE)
            if match:
                if len(match.groups()) == 1:
                    # Just site name or URL
                    target = match.group(1)
                    if not self.url_pattern.match(target) and not target.startswith("http"):
                        target = f"https://{target}"
                    return {
                        "action": "login",
                        "target_url": target,
                        "elements": [
                            {
                                "description": "username field",
                                "role": "input"
                            },
                            {
                                "description": "password field",
                                "role": "input"
                            },
                            {
                                "description": "login button",
                                "role": "button"
                            }
                        ],
                        "inputs": {},
                        "parameters": {}
                    }
                elif len(match.groups()) == 2:
                    # Username and password provided
                    username = match.group(1)
                    password = match.group(2)
                    return {
                        "action": "login",
                        "target_url": None,
                        "elements": [
                            {
                                "description": "username field",
                                "role": "input"
                            },
                            {
                                "description": "password field",
                                "role": "input"
                            },
                            {
                                "description": "login button",
                                "role": "button"
                            }
                        ],
                        "inputs": {
                            "username": username,
                            "password": password
                        },
                        "parameters": {}
                    }
        
        # No pattern matched
        return None
    
    async def _lm_parse(self, command: str) -> Dict[str, Any]:
        """
        Parse command using language model inference.
        
        Args:
            command: The command to parse
            
        Returns:
            Structured command from LLM inference
        """
        from nlp.context import ContextManager
        
        # Get the prompt
        prompt = get_prompt("command_parse", command=command)
        
        # Call appropriate LLM API based on settings
        if self.settings.default_llm_provider == "openai":
            result = await self._call_openai(prompt)
        else:  # anthropic
            result = await self._call_anthropic(prompt)
        
        # Extract and parse JSON from the response
        try:
            # Find JSON in the response
            json_match = re.search(r'```json\n(.*?)\n```|{.*}', result, re.DOTALL)
            if json_match:
                json_str = json_match.group(1) if json_match.group(1) else json_match.group(0)
                parsed_result = json.loads(json_str)
            else:
                # Try to parse the entire response as JSON
                parsed_result = json.loads(result)
            
            # Ensure all required fields are present
            if "action" not in parsed_result:
                parsed_result["action"] = "unknown"
            if "target_url" not in parsed_result:
                parsed_result["target_url"] = None
            if "elements" not in parsed_result:
                parsed_result["elements"] = []
            if "inputs" not in parsed_result:
                parsed_result["inputs"] = {}
            if "parameters" not in parsed_result:
                parsed_result["parameters"] = {}
                
            return parsed_result
        except (json.JSONDecodeError, AttributeError) as e:
            logger.error(f"Error parsing LLM response: {e}")
            # Return a minimal valid structure
            return {
                "action": "error",
                "target_url": None,
                "elements": [],
                "inputs": {},
                "parameters": {
                    "error_message": f"Failed to parse command: {str(e)}",
                    "original_command": command
                }
            }
    
    async def _call_openai(self, prompt: str) -> str:
        """
        Call OpenAI API to parse the command.
        
        Args:
            prompt: The prompt to send to the API
            
        Returns:
            Response from the OpenAI API
        """
        # This would be implemented with actual API calls
        # Using a placeholder implementation for now
        logger.debug("Calling OpenAI API")
        try:
            import openai
            
            openai.api_key = self.settings.openai_api_key
            
            response = await openai.ChatCompletion.acreate(
                model=self.settings.openai_model,
                messages=[{"role": "system", "content": prompt}],
                temperature=self.settings.temperature,
                max_tokens=self.settings.max_tokens
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            return "{}"
    
    async def _call_anthropic(self, prompt: str) -> str:
        """
        Call Anthropic API to parse the command.
        
        Args:
            prompt: The prompt to send to the API
            
        Returns:
            Response from the Anthropic API
        """
        # This would be implemented with actual API calls
        # Using a placeholder implementation for now
        logger.debug("Calling Anthropic API")
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)
            
            response = await client.completions.create(
                model=self.settings.anthropic_model,
                prompt=prompt,
                max_tokens_to_sample=self.settings.max_tokens,
                temperature=self.settings.temperature
            )
            
            return response.completion
        except Exception as e:
            logger.error(f"Error calling Anthropic API: {e}")
            return "{}"
