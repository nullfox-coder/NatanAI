"""
State tracking module.

This module provides functionality for tracking the state of browser automation
sessions, including browser state, execution progress, and error conditions.
"""

import logging
import time
from typing import Dict, List, Any, Optional

from config.settings import Settings
from nlp.context import ContextManager

# Set up logger
logger = logging.getLogger(__name__)


class StateTracker:
    """
    State tracker for browser automation.
    
    Tracks and manages the state of browser automation sessions, including
    browser state, execution progress, and error conditions.
    """
    
    def __init__(self, settings: Settings, context_manager: ContextManager):
        """
        Initialize the state tracker.
        
        Args:
            settings: Application settings
            context_manager: Context manager for maintaining conversation context
        """
        self.settings = settings
        self.context_manager = context_manager
        
        # Current execution state
        self.current_state: Dict[str, Any] = {
            "status": "idle",  # idle, running, error, completed
            "current_command": None,
            "current_step": None,
            "current_step_index": None,
            "total_steps": None,
            "steps_completed": 0,
            "start_time": None,
            "end_time": None,
            "last_action": None,
            "last_action_time": None,
            "last_action_result": None,
            "errors": [],
            "warnings": []
        }
        
        # Task history
        self.task_history: List[Dict[str, Any]] = []
    
    def start_execution(self, command: str, task_plan: Dict[str, Any]) -> None:
        """
        Start tracking execution of a task plan.
        
        Args:
            command: The command being executed
            task_plan: The task plan being executed
        """
        # Reset current state
        self.current_state = {
            "status": "running",
            "current_command": command,
            "current_step": task_plan.get("steps", [])[0] if task_plan.get("steps") else None,
            "current_step_index": 0,
            "total_steps": len(task_plan.get("steps", [])),
            "steps_completed": 0,
            "start_time": time.time(),
            "end_time": None,
            "last_action": None,
            "last_action_time": None,
            "last_action_result": None,
            "errors": [],
            "warnings": []
        }
        
        logger.info(f"Started execution: {command}")
        
        # Update context with state
        self.context_manager.update_browser_state({
            "execution_state": self.current_state
        })
    
    def update_state(self, state_updates: Dict[str, Any]) -> None:
        """
        Update the current execution state.
        
        Args:
            state_updates: Updates to the state
        """
        # Update state
        self.current_state.update(state_updates)
        
        # Check if we're moving to the next step
        if "last_step_completed" in state_updates:
            step_idx = state_updates["last_step_completed"]
            
            # Update steps completed
            self.current_state["steps_completed"] = step_idx + 1
            
            # Update current step if we have more steps
            total_steps = self.current_state.get("total_steps", 0)
            if step_idx + 1 < total_steps:
                self.current_state["current_step_index"] = step_idx + 1
                
                # Get current task plan from context
                task_plans = list(self.context_manager.task_plan_history)
                if task_plans:
                    latest_plan = task_plans[-1].get("plan", {})
                    steps = latest_plan.get("steps", [])
                    if step_idx + 1 < len(steps):
                        self.current_state["current_step"] = steps[step_idx + 1]
        
        # Update last action time if action changed
        if "last_action" in state_updates:
            self.current_state["last_action_time"] = time.time()
        
        # Check for errors
        if "last_action_result" in state_updates:
            result = state_updates["last_action_result"]
            if result and result.get("status") == "error":
                error = {
                    "timestamp": time.time(),
                    "action": self.current_state.get("last_action"),
                    "message": result.get("error", "Unknown error"),
                    "details": result
                }
                self.current_state["errors"].append(error)
                
                # Update status to error
                self.current_state["status"] = "error"
        
        logger.debug(f"Updated execution state: {state_updates.keys()}")
        
        # Update context with state
        self.context_manager.update_browser_state({
            "execution_state": self.current_state
        })
    
    def complete_execution(self, result: Dict[str, Any]) -> None:
        """
        Mark execution as completed.
        
        Args:
            result: The final result of execution
        """
        # Update state
        self.current_state.update({
            "status": "completed" if result.get("status") == "success" else "error",
            "end_time": time.time(),
            "last_action_result": result
        })
        
        # Add to history
        history_entry = {
            "command": self.current_state.get("current_command"),
            "start_time": self.current_state.get("start_time"),
            "end_time": self.current_state.get("end_time"),
            "status": self.current_state.get("status"),
            "steps_completed": self.current_state.get("steps_completed"),
            "total_steps": self.current_state.get("total_steps"),
            "errors": self.current_state.get("errors"),
            "result": result
        }
        self.task_history.append(history_entry)
        
        # Truncate history if needed
        max_history = self.settings.max_session_history
        if len(self.task_history) > max_history:
            self.task_history = self.task_history[-max_history:]
        
        logger.info(
            f"Completed execution: {self.current_state.get('current_command')} "
            f"with status {self.current_state.get('status')}"
        )
        
        # Update context with state
        self.context_manager.update_browser_state({
            "execution_state": self.current_state,
            "last_execution_result": result
        })
    
    def add_error(self, error_message: str, error_details: Optional[Dict[str, Any]] = None) -> None:
        """
        Add an error to the current state.
        
        Args:
            error_message: The error message
            error_details: Optional details about the error
        """
        error = {
            "timestamp": time.time(),
            "action": self.current_state.get("last_action"),
            "message": error_message,
            "details": error_details
        }
        
        self.current_state["errors"].append(error)
        self.current_state["status"] = "error"
        
        logger.error(f"Error during execution: {error_message}")
        
        # Update context with state
        self.context_manager.update_browser_state({
            "execution_state": self.current_state
        })
    
    def add_warning(self, warning_message: str, warning_details: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a warning to the current state.
        
        Args:
            warning_message: The warning message
            warning_details: Optional details about the warning
        """
        warning = {
            "timestamp": time.time(),
            "action": self.current_state.get("last_action"),
            "message": warning_message,
            "details": warning_details
        }
        
        self.current_state["warnings"].append(warning)
        
        logger.warning(f"Warning during execution: {warning_message}")
        
        # Update context with state
        self.context_manager.update_browser_state({
            "execution_state": self.current_state
        })
    
    def get_execution_status(self) -> Dict[str, Any]:
        """
        Get the current execution status.
        
        Returns:
            The current execution status
        """
        return {
            "status": self.current_state.get("status"),
            "command": self.current_state.get("current_command"),
            "current_step": self.current_state.get("current_step_index"),
            "total_steps": self.current_state.get("total_steps"),
            "steps_completed": self.current_state.get("steps_completed"),
            "duration": (
                time.time() - self.current_state.get("start_time", time.time())
                if self.current_state.get("status") == "running"
                else (
                    self.current_state.get("end_time", time.time()) - 
                    self.current_state.get("start_time", time.time())
                )
            ),
            "errors": len(self.current_state.get("errors", [])),
            "warnings": len(self.current_state.get("warnings", []))
        }
    
    def get_error_summary(self) -> List[Dict[str, Any]]:
        """
        Get a summary of errors in the current execution.
        
        Returns:
            List of error summaries
        """
        return [{
            "timestamp": error.get("timestamp"),
            "action": error.get("action"),
            "message": error.get("message")
        } for error in self.current_state.get("errors", [])]
    
    def get_task_history(self) -> List[Dict[str, Any]]:
        """
        Get the task execution history.
        
        Returns:
            List of historical task executions
        """
        return self.task_history
    
    def reset(self) -> None:
        """Reset the current execution state."""
        self.current_state = {
            "status": "idle",
            "current_command": None,
            "current_step": None,
            "current_step_index": None,
            "total_steps": None,
            "steps_completed": 0,
            "start_time": None,
            "end_time": None,
            "last_action": None,
            "last_action_time": None,
            "last_action_result": None,
            "errors": [],
            "warnings": []
        }
        
        logger.info("Reset execution state")
        
        # Update context with state
        self.context_manager.update_browser_state({
            "execution_state": self.current_state
        })
