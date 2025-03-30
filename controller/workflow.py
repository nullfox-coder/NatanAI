"""
Workflow orchestration module.

This module is responsible for orchestrating the execution of task sequences,
managing the overall workflow from natural language command to browser actions.
"""

import logging
import traceback
from typing import Dict, List, Any, Optional, Tuple, Union

from config.settings import Settings
from nlp.parser import CommandParser
from nlp.planner import TaskPlanner
from nlp.context import ContextManager
from controller.session import SessionManager
from controller.state import StateTracker
from browser.manager import BrowserManager
from error.classifier import ErrorClassifier
from error.recovery import RecoveryStrategy
from error.feedback import FeedbackGenerator

# Set up logger
logger = logging.getLogger(__name__)


class WorkflowController:
    """
    Workflow controller for browser automation.
    
    Orchestrates the execution of tasks, from parsing natural language commands
    to executing browser actions and handling errors.
    """
    
    def __init__(self, settings: Settings, session_manager: SessionManager):
        """
        Initialize the workflow controller.
        
        Args:
            settings: Application settings
            session_manager: Session manager for user sessions
        """
        self.settings = settings
        self.session_manager = session_manager
        
        # Initialize components
        self.context_manager = ContextManager(settings)
        self.command_parser = CommandParser(settings)
        self.task_planner = TaskPlanner(settings, self.context_manager)
        self.state_tracker = StateTracker(settings, self.context_manager)
        self.browser_manager = BrowserManager(settings)
        self.error_classifier = ErrorClassifier(settings)
        self.recovery_strategy = RecoveryStrategy(settings)
        self.feedback_generator = FeedbackGenerator(settings)
        
        self.initialized = False
    
    async def initialize(self) -> None:
        """Initialize the workflow controller and its components."""
        if not self.initialized:
            logger.info("Initializing workflow controller")
            await self.browser_manager.initialize()
            self.initialized = True
    
    async def cleanup(self) -> None:
        """Clean up resources used by the workflow controller."""
        if self.initialized:
            logger.info("Cleaning up workflow controller resources")
            await self.browser_manager.cleanup()
            self.initialized = False
    
    async def execute_command(self, command: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a natural language command.
        
        Args:
            command: The natural language command to execute
            session_id: Optional session ID for the user
            
        Returns:
            Result of the command execution
        """
        # Ensure controller is initialized
        if not self.initialized:
            await self.initialize()
        
        logger.info(f"Executing command: {command}")
        
        try:
            # Get or create session
            if session_id:
                session = self.session_manager.get_session(session_id)
                if not session:
                    return {
                        "status": "error",
                        "message": f"Session {session_id} not found",
                        "data": None
                    }
            else:
                session = self.session_manager.create_session()
                session_id = session["id"]
            
            # Parse the command
            parsed_command = await self.command_parser.parse_command(command)
            logger.debug(f"Parsed command: {parsed_command}")
            
            # Add to context
            self.context_manager.add_command(command, parsed_command)
            
            # Enhance context
            enhanced_context = await self.context_manager.enhance_context(command)
            logger.debug(f"Enhanced context: {enhanced_context}")
            
            # Plan tasks
            task_plan = await self.task_planner.plan_tasks(parsed_command)
            logger.debug(f"Task plan: {task_plan}")
            
            # Execute the task plan
            result = await self._execute_task_plan(task_plan, session_id)
            
            # Update session with results
            self.session_manager.update_session(session_id, {
                "last_command": command,
                "last_result": result
            })
            
            # Generate user-friendly feedback
            feedback = await self.feedback_generator.generate_feedback(
                command,
                task_plan,
                result,
                self.context_manager.export_context()
            )
            
            return {
                "status": "success" if result.get("status") == "success" else "error",
                "message": feedback,
                "data": result.get("data"),
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"Error executing command: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Generate error feedback
            error_feedback = await self.feedback_generator.generate_error_feedback(
                command,
                str(e),
                traceback.format_exc()
            )
            
            return {
                "status": "error",
                "message": error_feedback,
                "data": {
                    "error": str(e),
                    "original_command": command
                },
                "session_id": session_id
            }
    
    async def _execute_task_plan(self, task_plan: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        Execute a task plan.
        
        Args:
            task_plan: The task plan to execute
            session_id: The session ID
            
        Returns:
            Result of the task plan execution
        """
        logger.info(f"Executing task plan with {len(task_plan['steps'])} steps")
        
        steps = task_plan.get("steps", [])
        expected_outcome = task_plan.get("expected_outcome", "Complete the requested action")
        
        result = {
            "status": "success",
            "message": f"Completed all {len(steps)} steps successfully: {expected_outcome}",
            "data": {},
            "steps_completed": 0,
            "steps_total": len(steps),
            "errors": []
        }
        
        # No steps to execute
        if not steps:
            result["message"] = "No steps to execute"
            return result
        
        # Get the browser context for this session
        browser_context = await self.browser_manager.get_or_create_context(session_id)
        
        # Execute each step in order
        for i, step in enumerate(steps):
            step_action = step.get("action", "unknown")
            step_params = step.get("params", {})
            step_description = step.get("description", f"Step {i+1}")
            error_recovery = step.get("error_recovery", {})
            
            logger.info(f"Executing step {i+1}/{len(steps)}: {step_description}")
            
            try:
                # Execute the step
                step_result = await self._execute_step(
                    browser_context,
                    step_action,
                    step_params,
                    session_id
                )
                
                # Update state with step result
                self.state_tracker.update_state({
                    "last_action": step_action,
                    "last_action_result": step_result,
                    "last_step_completed": i
                })
                
                # Check if step execution was successful
                if step_result.get("status") == "error":
                    # Try recovery
                    recovered, recovery_result = await self._try_recovery(
                        browser_context,
                        step,
                        step_result,
                        error_recovery,
                        session_id
                    )
                    
                    if not recovered:
                        # Could not recover, abort execution
                        result["status"] = "error"
                        result["message"] = f"Failed at step {i+1}/{len(steps)}: {step_description}"
                        result["data"] = recovery_result
                        result["steps_completed"] = i
                        result["errors"].append({
                            "step": i + 1,
                            "action": step_action,
                            "error": recovery_result.get("error")
                        })
                        break
                    
                    # Successfully recovered
                    logger.info(f"Successfully recovered from error in step {i+1}")
                    step_result = recovery_result
                
                # If the step produced data, add it to the result
                if "data" in step_result:
                    # If this is an extraction step, store it as the main result data
                    if step_action == "extract":
                        result["data"] = step_result["data"]
                    else:
                        # Otherwise, store it in the step results
                        if "step_results" not in result["data"]:
                            result["data"]["step_results"] = []
                        result["data"]["step_results"].append({
                            "step": i + 1,
                            "description": step_description,
                            "data": step_result["data"]
                        })
                
                # Update steps completed
                result["steps_completed"] = i + 1
                
            except Exception as e:
                logger.error(f"Error executing step {i+1}: {str(e)}")
                logger.error(traceback.format_exc())
                
                # Try recovery
                recovered, recovery_result = await self._try_recovery(
                    browser_context,
                    step,
                    {
                        "status": "error",
                        "error": str(e),
                        "traceback": traceback.format_exc()
                    },
                    error_recovery,
                    session_id
                )
                
                if not recovered:
                    # Could not recover, abort execution
                    result["status"] = "error"
                    result["message"] = f"Error at step {i+1}/{len(steps)}: {step_description} - {str(e)}"
                    result["data"] = {"error": str(e)}
                    result["steps_completed"] = i
                    result["errors"].append({
                        "step": i + 1,
                        "action": step_action,
                        "error": str(e)
                    })
                    break
                
                # Successfully recovered
                logger.info(f"Successfully recovered from exception in step {i+1}")
        
        # Update result message based on steps completed
        if result["status"] == "success":
            result["message"] = f"Completed all {len(steps)} steps successfully: {expected_outcome}"
        elif result["steps_completed"] > 0:
            result["message"] = (
                f"Partially completed {result['steps_completed']}/{len(steps)} steps. "
                f"Failed at step {result['steps_completed'] + 1}: {result['errors'][-1]['error']}"
            )
        
        return result
    
    async def _execute_step(
        self,
        browser_context: Any,
        action: str,
        params: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """
        Execute a single step in a task plan.
        
        Args:
            browser_context: The browser context to use
            action: The action to perform
            params: Parameters for the action
            session_id: The session ID
            
        Returns:
            Result of the step execution
        """
        # Import action handlers here to avoid circular imports
        from browser.actions import perform_action
        from browser.navigation import navigate
        from extraction.selectors import extract_data
        
        # Execute the appropriate action
        if action == "navigate":
            result = await navigate(browser_context, params, self.settings)
            
            # Update context with new page info
            if result["status"] == "success":
                page_info = result.get("data", {}).get("page_info", {})
                self.context_manager.update_browser_state({
                    "url": page_info.get("url"),
                    "title": page_info.get("title"),
                    "visible_elements": page_info.get("visible_elements", [])
                })
                
        elif action == "extract":
            result = await extract_data(browser_context, params, self.settings)
            
        elif action == "user_input":
            # Handle user input specially
            prompt = params.get("prompt", "Please provide input:")
            field = params.get("field")
            is_password = params.get("is_password", False)
            
            # In a real application, this would prompt the user for input
            # For now, we'll simulate it by looking for a default in the context
            input_value = None
            if field and field.lower() == "username field":
                input_value = self.context_manager.get_session_var("username")
            elif field and field.lower() == "password field":
                input_value = self.context_manager.get_session_var("password")
            
            if input_value:
                # Use the value from context
                result = {
                    "status": "success",
                    "message": f"Using saved {field}",
                    "data": {
                        "input": input_value if not is_password else "********"
                    }
                }
                
                # Now use the browser action to type this value
                from browser.actions import perform_action
                type_result = await perform_action(
                    browser_context,
                    "type",
                    {
                        "element": field,
                        "text": input_value
                    },
                    self.settings
                )
                
                if type_result["status"] == "error":
                    result = type_result
            else:
                # In a real application, we would prompt the user here
                # For now, simulate an error
                result = {
                    "status": "error",
                    "error": f"User input required but no value found for {field}",
                    "message": f"Please provide a value for {field}"
                }
                
        elif action == "check":
            # Special condition checking action
            condition = params.get("condition")
            
            if condition == "login_success":
                # Check if login was successful by looking for login indicators
                # This would use more sophisticated logic in a real implementation
                is_logged_in = False
                
                # Get current page content to look for login indicators
                page = await browser_context.page()
                title = await page.title()
                url = page.url
                
                # Simple check: see if we're redirected away from login page
                # and if common login-related terms are not in the URL
                if "login" not in url.lower() and "signin" not in url.lower():
                    is_logged_in = True
                
                # Update the login state in context
                self.context_manager.update_browser_state({
                    "is_logged_in": is_logged_in
                })
                
                if is_logged_in:
                    result = {
                        "status": "success",
                        "message": "Login successful",
                        "data": {
                            "is_logged_in": True
                        }
                    }
                else:
                    result = {
                        "status": "error",
                        "error": "Login verification failed",
                        "message": "Could not verify successful login"
                    }
            else:
                # Unknown condition
                result = {
                    "status": "error",
                    "error": f"Unknown condition to check: {condition}",
                    "message": f"Cannot check unknown condition: {condition}"
                }
                
        elif action == "error":
            # This is an error step, just return the error
            result = {
                "status": "error",
                "error": params.get("error_message", "Unknown error"),
                "message": params.get("error_message", "Unknown error")
            }
        else:
            # For all other actions, use the general action handler
            result = await perform_action(browser_context, action, params, self.settings)
        
        return result
    
    async def _try_recovery(
        self,
        browser_context: Any,
        step: Dict[str, Any],
        step_result: Dict[str, Any],
        error_recovery: Dict[str, Any],
        session_id: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Try to recover from an error.
        
        Args:
            browser_context: The browser context
            step: The step that failed
            step_result: The result of the failed step
            error_recovery: Error recovery configuration
            session_id: The session ID
            
        Returns:
            Tuple of (recovered, result)
        """
        logger.info(f"Attempting to recover from error: {step_result.get('error')}")
        
        # Classify the error
        error_info = step_result.get("error", "Unknown error")
        error_type = self.error_classifier.classify_error(error_info)
        
        # Check if we have recovery actions for this error type
        conditions = error_recovery.get("conditions", [])
        actions = error_recovery.get("actions", [])
        
        # If the error type matches a condition, try the recovery actions
        if error_type in conditions or "any" in conditions:
            # Try each recovery action in order
            for action in actions:
                if action == "retry":
                    # Retry the step
                    logger.info(f"Retrying step: {step.get('description')}")
                    retry_result = await self._execute_step(
                        browser_context,
                        step.get("action"),
                        step.get("params", {}),
                        session_id
                    )
                    
                    if retry_result.get("status") == "success":
                        return True, retry_result
                    
                elif action == "wait":
                    # Wait and retry
                    logger.info("Waiting before retry")
                    import asyncio
                    await asyncio.sleep(self.settings.retry_delay / 1000)  # Convert ms to seconds
                    
                    logger.info(f"Retrying step after wait: {step.get('description')}")
                    retry_result = await self._execute_step(
                        browser_context,
                        step.get("action"),
                        step.get("params", {}),
                        session_id
                    )
                    
                    if retry_result.get("status") == "success":
                        return True, retry_result
                    
                elif action == "scroll_into_view":
                    # Try to scroll the element into view
                    logger.info("Attempting to scroll element into view")
                    
                    # Extract element from step params
                    element = None
                    if step.get("action") in ["click", "type", "wait"]:
                        element = step.get("params", {}).get("element")
                    
                    if element:
                        from browser.actions import perform_action
                        
                        # Scroll to element
                        scroll_result = await perform_action(
                            browser_context,
                            "scroll",
                            {
                                "element": element,
                                "behavior": "smooth"
                            },
                            self.settings
                        )
                        
                        # Retry the step
                        logger.info(f"Retrying step after scroll: {step.get('description')}")
                        retry_result = await self._execute_step(
                            browser_context,
                            step.get("action"),
                            step.get("params", {}),
                            session_id
                        )
                        
                        if retry_result.get("status") == "success":
                            return True, retry_result
                
                elif action == "check_connection":
                    # Check internet connection
                    logger.info("Checking internet connection")
                    
                    # In a real implementation, we would check the connection
                    # For now, just wait and retry
                    import asyncio
                    await asyncio.sleep(2)
                    
                    logger.info(f"Retrying step after connection check: {step.get('description')}")
                    retry_result = await self._execute_step(
                        browser_context,
                        step.get("action"),
                        step.get("params", {}),
                        session_id
                    )
                    
                    if retry_result.get("status") == "success":
                        return True, retry_result
                
                elif action == "find_login_link":
                    # Try to find a login link
                    logger.info("Searching for login link")
                    
                    from browser.elements import find_element_by_text
                    
                    # Look for common login links
                    for text in ["Log in", "Sign in", "Login", "Signin"]:
                        found = await find_element_by_text(browser_context, text)
                        
                        if found:
                            # Click the login link
                            from browser.actions import perform_action
                            
                            click_result = await perform_action(
                                browser_context,
                                "click",
                                {
                                    "element": found
                                },
                                self.settings
                            )
                            
                            # Wait for page to load
                            import asyncio
                            await asyncio.sleep(1)
                            
                            # Retry the step
                            logger.info(f"Retrying step after finding login link: {step.get('description')}")
                            retry_result = await self._execute_step(
                                browser_context,
                                step.get("action"),
                                step.get("params", {}),
                                session_id
                            )
                            
                            if retry_result.get("status") == "success":
                                return True, retry_result
                
                elif action == "press_enter":
                    # Try pressing Enter instead of clicking
                    logger.info("Trying to press Enter instead of clicking")
                    
                    from browser.actions import perform_action
                    
                    # Press Enter
                    press_result = await perform_action(
                        browser_context,
                        "press",
                        {
                            "key": "Enter"
                        },
                        self.settings
                    )
                    
                    # Check if successful
                    if press_result.get("status") == "success":
                        return True, press_result
                
                elif action == "check_login_status":
                    # Try to check login status
                    logger.info("Checking login status")
                    
                    # Execute a check operation
                    check_result = await self._execute_step(
                        browser_context,
                        "check",
                        {
                            "condition": "login_success"
                        },
                        session_id
                    )
                    
                    # If login is successful, consider recovery successful
                    if check_result.get("status") == "success":
                        return True, check_result
                
                elif action == "handle_captcha":
                    # Try to handle CAPTCHA
                    logger.info("Attempting to handle CAPTCHA")
                    
                    # This would use a CAPTCHA handling service in a real implementation
                    # For now, just report that we need human intervention
                    captcha_result = {
                        "status": "error",
                        "error": "CAPTCHA detected, human intervention required",
                        "message": "CAPTCHA detected, please solve it manually",
                        "requires_human": True
                    }
                    
                    return False, captcha_result
                
                elif action == "report_login_error":
                    # Report login error
                    logger.info("Reporting login error")
                    
                    # Get any error messages on the page
                    from browser.elements import get_error_messages
                    
                    error_messages = await get_error_messages(browser_context)
                    
                    error_result = {
                        "status": "error",
                        "error": "Login failed",
                        "message": f"Login failed: {', '.join(error_messages) if error_messages else 'Unknown error'}",
                        "data": {
                            "error_messages": error_messages
                        }
                    }
                    
                    return False, error_result
                
                elif action == "abort":
                    # Abort recovery
                    logger.info("Aborting recovery as specified in error_recovery.actions")
                    return False, step_result
        
        # No recovery possible
        logger.warning(f"No recovery possible for error type: {error_type}")
        return False, step_result
