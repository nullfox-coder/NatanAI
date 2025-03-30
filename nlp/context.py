"""
Context management module.

This module provides functionality to maintain conversation context and command
history to enhance understanding of user commands and improve task execution.
"""

import json
import logging
import time
from typing import Dict, List, Any, Optional, Deque
from collections import deque

from config.settings import Settings
from config.prompts import get_prompt

# Set up logger
logger = logging.getLogger(__name__)


class ContextManager:
    """
    Context manager for maintaining conversation context.
    
    Maintains conversation history, browser state, and other contextual
    information to enhance command understanding and task execution.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the context manager.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.max_history = settings.max_session_history
        
        # Command history, newest at the end
        self.command_history: Deque[Dict[str, Any]] = deque(maxlen=self.max_history)
        
        # Task plan history, newest at the end
        self.task_plan_history: Deque[Dict[str, Any]] = deque(maxlen=self.max_history)
        
        # Current browser state
        self.current_state: Dict[str, Any] = {
            "url": None,
            "title": None,
            "is_logged_in": False,
            "visible_elements": [],
            "form_data": {},
            "last_action": None,
            "last_action_time": None,
            "last_action_result": None,
            "errors": []
        }
        
        # Session variables (username, preferences, etc.)
        self.session_vars: Dict[str, Any] = {}
        
        # Entity memory (recognized entities)
        self.entities: Dict[str, Any] = {}
    
    def add_command(self, command: str, parsed_command: Dict[str, Any]) -> None:
        """
        Add a command to the history.
        
        Args:
            command: The original command string
            parsed_command: The parsed command structure
        """
        entry = {
            "timestamp": time.time(),
            "original": command,
            "parsed": parsed_command
        }
        self.command_history.append(entry)
        logger.debug(f"Added command to history: {command}")
    
    def add_task_plan(self, task_plan: Dict[str, Any]) -> None:
        """
        Add a task plan to the history.
        
        Args:
            task_plan: The task plan to add
        """
        entry = {
            "timestamp": time.time(),
            "plan": task_plan
        }
        self.task_plan_history.append(entry)
        logger.debug(f"Added task plan to history with {len(task_plan['steps'])} steps")
    
    def update_browser_state(self, state_updates: Dict[str, Any]) -> None:
        """
        Update the current browser state.
        
        Args:
            state_updates: Updates to the browser state
        """
        self.current_state.update(state_updates)
        
        # Add timestamp for the update
        self.current_state["last_updated"] = time.time()
        
        logger.debug(f"Updated browser state: {state_updates.keys()}")
    
    def add_entity(self, entity_type: str, entity_value: Any, entity_id: Optional[str] = None) -> str:
        """
        Add an entity to the context.
        
        Args:
            entity_type: Type of entity (e.g., "website", "user", "product")
            entity_value: Value of the entity
            entity_id: Optional ID for the entity, auto-generated if None
            
        Returns:
            The entity ID
        """
        if entity_id is None:
            entity_id = f"{entity_type}_{len(self.entities) + 1}"
            
        self.entities[entity_id] = {
            "type": entity_type,
            "value": entity_value,
            "first_seen": time.time(),
            "last_used": time.time(),
            "usage_count": 1
        }
        
        logger.debug(f"Added entity: {entity_type} - {entity_id}")
        return entity_id
    
    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an entity by ID.
        
        Args:
            entity_id: The ID of the entity to retrieve
            
        Returns:
            The entity dictionary or None if not found
        """
        entity = self.entities.get(entity_id)
        if entity:
            # Update usage stats
            entity["last_used"] = time.time()
            entity["usage_count"] += 1
            
        return entity
    
    def find_entities_by_type(self, entity_type: str) -> List[Dict[str, Any]]:
        """
        Find all entities of a specific type.
        
        Args:
            entity_type: The type of entities to find
            
        Returns:
            List of matching entities with their IDs
        """
        results = []
        for entity_id, entity in self.entities.items():
            if entity["type"] == entity_type:
                results.append({
                    "id": entity_id,
                    **entity
                })
        
        return results
    
    def get_recent_commands(self, count: int = 5) -> List[Dict[str, Any]]:
        """
        Get the most recent commands.
        
        Args:
            count: Maximum number of commands to retrieve
            
        Returns:
            List of recent commands, most recent first
        """
        return list(reversed(list(self.command_history)[-count:]))
    
    def get_session_var(self, key: str, default: Any = None) -> Any:
        """
        Get a session variable.
        
        Args:
            key: Variable key
            default: Default value if key is not found
            
        Returns:
            Variable value or default
        """
        return self.session_vars.get(key, default)
    
    def set_session_var(self, key: str, value: Any) -> None:
        """
        Set a session variable.
        
        Args:
            key: Variable key
            value: Variable value
        """
        self.session_vars[key] = value
        logger.debug(f"Set session variable: {key}")
    
    def clear_history(self) -> None:
        """Clear command and task plan history."""
        self.command_history.clear()
        self.task_plan_history.clear()
        logger.info("Cleared command and task plan history")
    
    async def enhance_context(self, current_command: str) -> Dict[str, Any]:
        """
        Enhance context for the current command using LLM.
        
        Args:
            current_command: The current command to enhance context for
            
        Returns:
            Enhanced context information
        """
        # Build context for prompt
        current_page = self.current_state.get("url", "Unknown")
        page_title = self.current_state.get("title", "Unknown")
        
        # Format visible elements for prompt
        visible_elements = self.current_state.get("visible_elements", [])
        visible_elements_str = "\n".join([
            f"- {el.get('role', 'element')}: {el.get('description', 'unknown')}" 
            for el in visible_elements[:20]  # Limit to 20 elements
        ])
        
        # Format command history for prompt
        recent_commands = self.get_recent_commands(5)
        command_history_str = "\n".join([
            f"- {i+1}. \"{cmd['original']}\" ({cmd['parsed']['action']})"
            for i, cmd in enumerate(recent_commands)
        ])
        
        # Get the prompt
        prompt = get_prompt(
            "context_enhancement",
            current_page=current_page,
            page_title=page_title,
            visible_elements=visible_elements_str,
            command_history=command_history_str,
            current_command=current_command
        )
        
        # Call appropriate LLM API
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
                enhanced_context = json.loads(json_str)
            else:
                # Try to parse the entire response as JSON
                enhanced_context = json.loads(result)
                
            logger.debug(f"Enhanced context: {enhanced_context}")
            return enhanced_context
            
        except (json.JSONDecodeError, AttributeError) as e:
            logger.error(f"Error parsing LLM context enhancement response: {e}")
            # Return a minimal valid structure
            return {
                "interpreted_goal": "Unknown",
                "relevant_elements": [],
                "disambiguation": {},
                "context_enhancements": []
            }
    
    def export_context(self) -> Dict[str, Any]:
        """
        Export the current context as a dictionary.
        
        Returns:
            The complete context as a dictionary
        """
        return {
            "browser_state": self.current_state,
            "command_history": list(self.command_history),
            "task_plan_history": list(self.task_plan_history),
            "session_vars": self.session_vars,
            "entities": self.entities
        }
    
    def import_context(self, context_data: Dict[str, Any]) -> None:
        """
        Import context from a dictionary.
        
        Args:
            context_data: The context data to import
        """
        if "browser_state" in context_data:
            self.current_state = context_data["browser_state"]
            
        if "command_history" in context_data:
            self.command_history = deque(
                context_data["command_history"],
                maxlen=self.max_history
            )
            
        if "task_plan_history" in context_data:
            self.task_plan_history = deque(
                context_data["task_plan_history"],
                maxlen=self.max_history
            )
            
        if "session_vars" in context_data:
            self.session_vars = context_data["session_vars"]
            
        if "entities" in context_data:
            self.entities = context_data["entities"]
            
        logger.info("Imported context data")
