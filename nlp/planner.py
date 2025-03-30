"""
Task planning module.

This module is responsible for converting structured command instructions into
executable task sequences that can be performed by the browser automation system.
"""

import json
import logging
from typing import Dict, List, Any, Optional

from config.settings import Settings
from config.prompts import get_prompt
from nlp.context import ContextManager

# Set up logger
logger = logging.getLogger(__name__)


class TaskPlanner:
    """
    Task planner for browser automation.
    
    Converts structured command instructions into a sequence of executable
    browser automation steps.
    """
    
    def __init__(self, settings: Settings, context_manager: ContextManager):
        """
        Initialize the task planner.
        
        Args:
            settings: Application settings
            context_manager: Context manager for maintaining conversation context
        """
        self.settings = settings
        self.context_manager = context_manager
        
        # Map of action types to planning functions
        self.action_planners = {
            "navigate": self._plan_navigation,
            "click": self._plan_click,
            "search": self._plan_search,
            "extract": self._plan_extraction,
            "login": self._plan_login,
            "fill": self._plan_form_fill,
            "scroll": self._plan_scroll,
            "wait": self._plan_wait,
        }
    
    async def plan_tasks(self, parsed_command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a parsed command into a task plan.
        
        Args:
            parsed_command: The parsed command to convert to tasks
            
        Returns:
            A task plan with executable steps
        """
        logger.info(f"Planning tasks for command: {parsed_command['action']}")
        
        # Check if we have a specialized planner for this action
        action = parsed_command.get("action", "unknown")
        if action in self.action_planners:
            # Use specialized planning
            task_plan = await self.action_planners[action](parsed_command)
            logger.debug(f"Generated task plan using specialized planner: {task_plan}")
        else:
            # Use general LLM planning
            task_plan = await self._plan_with_llm(parsed_command)
            logger.debug(f"Generated task plan using LLM: {task_plan}")
        
        # Add task plan to context
        self.context_manager.add_task_plan(task_plan)
        
        return task_plan
    
    async def _plan_with_llm(self, parsed_command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use language model to generate a task plan.
        
        Args:
            parsed_command: The parsed command to convert to tasks
            
        Returns:
            Task plan from LLM inference
        """
        # Get planning prompt
        command_str = json.dumps(parsed_command, indent=2)
        prompt = get_prompt("task_planning", parsed_command=command_str)
        
        # Call appropriate LLM API based on settings
        if self.settings.default_llm_provider == "openai":
            from nlp.parser import CommandParser
            result = await CommandParser(self.settings)._call_openai(prompt)
        else:  # anthropic
            from nlp.parser import CommandParser
            result = await CommandParser(self.settings)._call_anthropic(prompt)
        
        # Extract and parse JSON from the response
        try:
            import re
            
            # Find JSON in the response
            json_match = re.search(r'```json\n(.*?)\n```|{.*}', result, re.DOTALL)
            if json_match:
                json_str = json_match.group(1) if json_match.group(1) else json_match.group(0)
                task_plan = json.loads(json_str)
            else:
                # Try to parse the entire response as JSON
                task_plan = json.loads(result)
            
            # Ensure plan has required fields
            if "steps" not in task_plan:
                task_plan["steps"] = []
            if "expected_outcome" not in task_plan:
                task_plan["expected_outcome"] = "Complete the requested action"
                
            # Validate steps structure
            for i, step in enumerate(task_plan["steps"]):
                if "action" not in step:
                    step["action"] = "unknown"
                if "params" not in step:
                    step["params"] = {}
                if "description" not in step:
                    step["description"] = f"Step {i+1}"
                if "error_recovery" not in step:
                    step["error_recovery"] = {
                        "conditions": ["timeout", "element_not_found"],
                        "actions": ["retry", "wait", "abort"]
                    }
            
            return task_plan
        
        except (json.JSONDecodeError, AttributeError) as e:
            logger.error(f"Error parsing LLM task plan response: {e}")
            # Return a minimal valid task plan
            return {
                "steps": [
                    {
                        "action": "error",
                        "params": {
                            "error_message": f"Failed to create task plan: {str(e)}"
                        },
                        "description": "Error in task planning",
                        "error_recovery": {
                            "conditions": [],
                            "actions": ["abort"]
                        }
                    }
                ],
                "expected_outcome": "Error in task planning"
            }
    
    async def _plan_navigation(self, parsed_command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a task plan for navigation.
        
        Args:
            parsed_command: The parsed navigation command
            
        Returns:
            Task plan for navigation
        """
        target_url = parsed_command.get("target_url")
        
        if not target_url:
            return {
                "steps": [
                    {
                        "action": "error",
                        "params": {
                            "error_message": "No target URL provided for navigation"
                        },
                        "description": "Error: Missing target URL",
                        "error_recovery": {
                            "conditions": [],
                            "actions": ["abort"]
                        }
                    }
                ],
                "expected_outcome": "Error: Cannot navigate without a target URL"
            }
        
        # Simple navigation plan
        return {
            "steps": [
                {
                    "action": "navigate",
                    "params": {
                        "url": target_url,
                        "wait_until": "networkidle"
                    },
                    "description": f"Navigate to {target_url}",
                    "error_recovery": {
                        "conditions": ["timeout", "navigation_error"],
                        "actions": ["retry", "check_connection", "abort"]
                    }
                }
            ],
            "expected_outcome": f"Successfully navigated to {target_url}"
        }
    
    async def _plan_click(self, parsed_command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a task plan for clicking an element.
        
        Args:
            parsed_command: The parsed click command
            
        Returns:
            Task plan for clicking
        """
        elements = parsed_command.get("elements", [])
        
        if not elements:
            return {
                "steps": [
                    {
                        "action": "error",
                        "params": {
                            "error_message": "No target element provided for clicking"
                        },
                        "description": "Error: Missing target element",
                        "error_recovery": {
                            "conditions": [],
                            "actions": ["abort"]
                        }
                    }
                ],
                "expected_outcome": "Error: Cannot click without a target element"
            }
        
        # Get the first element description
        element_desc = elements[0].get("description", "element")
        
        # Click plan
        steps = []
        
        # First, make sure we're on the right page if URL is provided
        if parsed_command.get("target_url"):
            steps.append({
                "action": "navigate",
                "params": {
                    "url": parsed_command["target_url"],
                    "wait_until": "networkidle"
                },
                "description": f"Navigate to {parsed_command['target_url']}",
                "error_recovery": {
                    "conditions": ["timeout", "navigation_error"],
                    "actions": ["retry", "check_connection", "abort"]
                }
            })
        
        # Add step to wait for the element to be visible
        steps.append({
            "action": "wait",
            "params": {
                "element": element_desc,
                "state": "visible",
                "timeout": self.settings.wait_timeout
            },
            "description": f"Wait for {element_desc} to be visible",
            "error_recovery": {
                "conditions": ["timeout", "element_not_found"],
                "actions": ["scroll_into_view", "retry", "abort"]
            }
        })
        
        # Add click step
        steps.append({
            "action": "click",
            "params": {
                "element": element_desc
            },
            "description": f"Click on {element_desc}",
            "error_recovery": {
                "conditions": ["element_not_found", "element_not_clickable"],
                "actions": ["scroll_into_view", "retry", "abort"]
            }
        })
        
        return {
            "steps": steps,
            "expected_outcome": f"Successfully clicked on {element_desc}"
        }
    
    async def _plan_search(self, parsed_command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a task plan for performing a search.
        
        Args:
            parsed_command: The parsed search command
            
        Returns:
            Task plan for searching
        """
        search_term = parsed_command.get("inputs", {}).get("search_term")
        
        if not search_term:
            return {
                "steps": [
                    {
                        "action": "error",
                        "params": {
                            "error_message": "No search term provided"
                        },
                        "description": "Error: Missing search term",
                        "error_recovery": {
                            "conditions": [],
                            "actions": ["abort"]
                        }
                    }
                ],
                "expected_outcome": "Error: Cannot search without a search term"
            }
        
        # Search plan
        steps = []
        
        # First, navigate to the search engine if provided
        target_url = parsed_command.get("target_url", "https://www.google.com")
        steps.append({
            "action": "navigate",
            "params": {
                "url": target_url,
                "wait_until": "networkidle"
            },
            "description": f"Navigate to {target_url}",
            "error_recovery": {
                "conditions": ["timeout", "navigation_error"],
                "actions": ["retry", "check_connection", "abort"]
            }
        })
        
        # Wait for search box
        search_box_desc = "search box"
        for element in parsed_command.get("elements", []):
            if element.get("role") == "input":
                search_box_desc = element.get("description", search_box_desc)
                break
                
        steps.append({
            "action": "wait",
            "params": {
                "element": search_box_desc,
                "state": "visible",
                "timeout": self.settings.wait_timeout
            },
            "description": f"Wait for {search_box_desc} to be visible",
            "error_recovery": {
                "conditions": ["timeout", "element_not_found"],
                "actions": ["retry", "abort"]
            }
        })
        
        # Type search term
        steps.append({
            "action": "type",
            "params": {
                "element": search_box_desc,
                "text": search_term
            },
            "description": f"Type '{search_term}' into {search_box_desc}",
            "error_recovery": {
                "conditions": ["element_not_found", "input_error"],
                "actions": ["retry", "abort"]
            }
        })
        
        # Submit search
        steps.append({
            "action": "press",
            "params": {
                "key": "Enter"
            },
            "description": "Press Enter to submit search",
            "error_recovery": {
                "conditions": ["timeout"],
                "actions": ["retry", "abort"]
            }
        })
        
        # Wait for results
        steps.append({
            "action": "wait",
            "params": {
                "state": "networkidle",
                "timeout": self.settings.navigation_timeout
            },
            "description": "Wait for search results to load",
            "error_recovery": {
                "conditions": ["timeout"],
                "actions": ["retry", "abort"]
            }
        })
        
        return {
            "steps": steps,
            "expected_outcome": f"Successfully searched for '{search_term}'"
        }
    
    async def _plan_extraction(self, parsed_command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a task plan for extracting data from a page.
        
        Args:
            parsed_command: The parsed extraction command
            
        Returns:
            Task plan for data extraction
        """
        # For more complex extraction, use LLM planning
        return await self._plan_with_llm(parsed_command)
    
    async def _plan_login(self, parsed_command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a task plan for logging into a website.
        
        Args:
            parsed_command: The parsed login command
            
        Returns:
            Task plan for login
        """
        target_url = parsed_command.get("target_url")
        username = parsed_command.get("inputs", {}).get("username")
        password = parsed_command.get("inputs", {}).get("password")
        
        if not target_url:
            return {
                "steps": [
                    {
                        "action": "error",
                        "params": {
                            "error_message": "No target URL provided for login"
                        },
                        "description": "Error: Missing target URL",
                        "error_recovery": {
                            "conditions": [],
                            "actions": ["abort"]
                        }
                    }
                ],
                "expected_outcome": "Error: Cannot login without a target website"
            }
        
        # Login plan
        steps = []
        
        # Navigate to the website
        steps.append({
            "action": "navigate",
            "params": {
                "url": target_url,
                "wait_until": "networkidle"
            },
            "description": f"Navigate to {target_url}",
            "error_recovery": {
                "conditions": ["timeout", "navigation_error"],
                "actions": ["retry", "check_connection", "abort"]
            }
        })
        
        # Find and interact with username field
        steps.append({
            "action": "wait",
            "params": {
                "element": "username field",
                "state": "visible",
                "timeout": self.settings.wait_timeout
            },
            "description": "Wait for username field to be visible",
            "error_recovery": {
                "conditions": ["timeout", "element_not_found"],
                "actions": ["retry", "find_login_link", "abort"]
            }
        })
        
        if username:
            steps.append({
                "action": "type",
                "params": {
                    "element": "username field",
                    "text": username
                },
                "description": f"Type username '{username}'",
                "error_recovery": {
                    "conditions": ["element_not_found", "input_error"],
                    "actions": ["retry", "abort"]
                }
            })
        else:
            steps.append({
                "action": "user_input",
                "params": {
                    "prompt": "Please enter your username:",
                    "field": "username field"
                },
                "description": "Request and input username from user",
                "error_recovery": {
                    "conditions": ["element_not_found", "input_error"],
                    "actions": ["retry", "abort"]
                }
            })
        
        # Find and interact with password field
        steps.append({
            "action": "wait",
            "params": {
                "element": "password field",
                "state": "visible",
                "timeout": self.settings.wait_timeout
            },
            "description": "Wait for password field to be visible",
            "error_recovery": {
                "conditions": ["timeout", "element_not_found"],
                "actions": ["retry", "abort"]
            }
        })
        
        if password:
            steps.append({
                "action": "type",
                "params": {
                    "element": "password field",
                    "text": password
                },
                "description": "Type password (hidden)",
                "error_recovery": {
                    "conditions": ["element_not_found", "input_error"],
                    "actions": ["retry", "abort"]
                }
            })
        else:
            steps.append({
                "action": "user_input",
                "params": {
                    "prompt": "Please enter your password:",
                    "field": "password field",
                    "is_password": True
                },
                "description": "Request and input password from user",
                "error_recovery": {
                    "conditions": ["element_not_found", "input_error"],
                    "actions": ["retry", "abort"]
                }
            })
        
        # Submit login form
        steps.append({
            "action": "click",
            "params": {
                "element": "login button"
            },
            "description": "Click login button",
            "error_recovery": {
                "conditions": ["element_not_found", "element_not_clickable"],
                "actions": ["retry", "press_enter", "abort"]
            }
        })
        
        # Wait for login completion
        steps.append({
            "action": "wait",
            "params": {
                "state": "networkidle",
                "timeout": self.settings.navigation_timeout
            },
            "description": "Wait for login to complete",
            "error_recovery": {
                "conditions": ["timeout", "navigation_error"],
                "actions": ["check_login_status", "retry", "abort"]
            }
        })
        
        # Check for login errors
        steps.append({
            "action": "check",
            "params": {
                "condition": "login_success"
            },
            "description": "Verify successful login",
            "error_recovery": {
                "conditions": ["login_failed", "captcha_detected"],
                "actions": ["handle_captcha", "report_login_error", "abort"]
            }
        })
        
        return {
            "steps": steps,
            "expected_outcome": "Successfully logged in to the website"
        }
    
    async def _plan_form_fill(self, parsed_command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a task plan for filling out a form.
        
        Args:
            parsed_command: The parsed form fill command
            
        Returns:
            Task plan for form filling
        """
        # For complex form filling, use LLM planning
        return await self._plan_with_llm(parsed_command)
    
    async def _plan_scroll(self, parsed_command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a task plan for scrolling on a page.
        
        Args:
            parsed_command: The parsed scroll command
            
        Returns:
            Task plan for scrolling
        """
        direction = parsed_command.get("parameters", {}).get("direction", "down")
        amount = parsed_command.get("parameters", {}).get("amount", "page")
        
        # Scroll plan
        return {
            "steps": [
                {
                    "action": "scroll",
                    "params": {
                        "direction": direction,
                        "amount": amount
                    },
                    "description": f"Scroll {direction} by {amount}",
                    "error_recovery": {
                        "conditions": ["page_error"],
                        "actions": ["retry", "abort"]
                    }
                }
            ],
            "expected_outcome": f"Successfully scrolled {direction}"
        }
    
    async def _plan_wait(self, parsed_command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a task plan for waiting on a page.
        
        Args:
            parsed_command: The parsed wait command
            
        Returns:
            Task plan for waiting
        """
        duration = parsed_command.get("parameters", {}).get("duration", 2000)  # Default 2 seconds
        
        # Wait plan
        return {
            "steps": [
                {
                    "action": "wait",
                    "params": {
                        "duration": duration
                    },
                    "description": f"Wait for {duration} milliseconds",
                    "error_recovery": {
                        "conditions": [],
                        "actions": []
                    }
                }
            ],
            "expected_outcome": f"Successfully waited for {duration} milliseconds"
        }
