"""
Template prompts for language model interactions.

This module defines templates for prompts sent to language models for various
tasks such as command parsing, task planning, and error recovery.
"""

from typing import Dict, List, Any, Optional

# Command parsing prompt
COMMAND_PARSE_TEMPLATE = """
You are an AI assistant that helps parse natural language commands into structured instructions for browser automation.
Analyze the following command and extract the structured information:

Command: {command}

Extract the following information:
1. Primary action (e.g., navigate, click, search, extract, login, fill, etc.)
2. Target website or URL (if specified)
3. Element selectors or descriptions (e.g., "login button", "search box", etc.)
4. Input values (e.g., username, password, search terms, etc.)
5. Additional parameters or constraints

Return the information in JSON format using this structure:
{{
    "action": string,
    "target_url": string or null,
    "elements": [
        {{
            "description": string,
            "role": string (e.g., "input", "button", "link")
        }}
    ],
    "inputs": {{
        key: value pairs of field names and values
    }},
    "parameters": {{
        key: value pairs of additional parameters
    }}
}}

Only include fields that are relevant to the command.
"""

# Task planning prompt
TASK_PLANNING_TEMPLATE = """
You are an AI assistant responsible for planning browser automation tasks.
Break down the following parsed command into a sequence of executable browser automation steps.

Parsed Command: {parsed_command}

Consider:
- Navigation steps required
- User interaction steps (clicking, typing, etc.)
- Waiting conditions (page loads, element visibility)
- Potential error conditions and how to recover
- Data extraction steps (if applicable)

Return a structured plan with the following format:
{{
    "steps": [
        {{
            "action": string (e.g., "navigate", "click", "type", "wait", "extract"),
            "params": {{
                action-specific parameters
            }},
            "description": string,
            "error_recovery": {{
                "conditions": [string],
                "actions": [string]
            }}
        }}
    ],
    "expected_outcome": string
}}

Ensure each step is specific, actionable, and includes all necessary parameters.
"""

# Context enhancement prompt
CONTEXT_ENHANCEMENT_TEMPLATE = """
You are helping a browser automation system understand and maintain context.
Use the following information to provide enhanced context for the current browser state and command sequence:

Current Page: {current_page}
Page Title: {page_title}
Visible Elements: {visible_elements}
Command History: {command_history}
Current Command: {current_command}

Based on this information:
1. Identify what the user is trying to accomplish
2. Note any important elements on the page relevant to the command
3. Suggest how to interpret ambiguous references based on the current state
4. Highlight any contextual information that would help with executing the command

Return your analysis in JSON format:
{{
    "interpreted_goal": string,
    "relevant_elements": [
        {{
            "description": string,
            "importance": string,
            "suggestions": string
        }}
    ],
    "disambiguation": {{
        key: value pairs for ambiguous terms and their likely meanings
    }},
    "context_enhancements": [string]
}}
"""

# Element selection prompt
ELEMENT_SELECTION_TEMPLATE = """
You are helping a browser automation system identify the most appropriate element on a page.
Based on the provided description and page content, identify the best selector to use.

Element Description: {element_description}
Current URL: {current_url}
Available Elements: {available_elements}

Consider:
- Text content matches
- Role/type of element (button, input, link, etc.)
- Attributes (id, class, name, etc.)
- Position on page
- Surrounding context

Return your recommendation in JSON format:
{{
    "best_selector": string,
    "selector_type": string (e.g., "css", "xpath", "text", "role"),
    "confidence": float (0-1),
    "alternative_selectors": [
        {{
            "selector": string,
            "selector_type": string,
            "confidence": float
        }}
    ],
    "reasoning": string
}}
"""

# Error recovery prompt
ERROR_RECOVERY_TEMPLATE = """
You are helping a browser automation system recover from an error.
Analyze the error information and suggest recovery actions.

Error Type: {error_type}
Error Message: {error_message}
Current URL: {current_url}
Current Action: {current_action}
Screenshots: {screenshot_description}
Previous Steps: {previous_steps}

Based on this information:
1. Diagnose the most likely cause of the error
2. Suggest specific recovery actions
3. Provide alternative approaches if the primary recovery fails
4. Indicate if human intervention might be needed

Return your analysis in JSON format:
{{
    "diagnosis": string,
    "primary_recovery": [
        {{
            "action": string,
            "params": {{
                action-specific parameters
            }},
            "rationale": string
        }}
    ],
    "alternative_approaches": [
        {{
            "action": string,
            "params": {{
                action-specific parameters
            }},
            "conditions": string
        }}
    ],
    "requires_human_intervention": boolean,
    "human_intervention_instructions": string or null
}}
"""

# Data extraction prompt
DATA_EXTRACTION_TEMPLATE = """
You are helping a browser automation system extract structured data from a webpage.
Based on the user's request and the current page content, determine the best extraction strategy.

Extraction Request: {extraction_request}
Current URL: {current_url}
Page Content Sample: {page_content_sample}

Consider:
- The type of data being requested (text, table, list, etc.)
- The structure of the page
- The most reliable selectors to target the data
- The desired output format

Return your extraction plan in JSON format:
{{
    "data_type": string (e.g., "table", "list", "text", "form"),
    "extraction_strategy": string,
    "selectors": [
        {{
            "target": string,
            "selector": string,
            "selector_type": string
        }}
    ],
    "processing_steps": [
        string
    ],
    "output_format": string,
    "example_structure": {{
        Example of the expected output structure
    }}
}}
"""

# CAPTCHA detection prompt
CAPTCHA_DETECTION_TEMPLATE = """
You are helping a browser automation system detect and handle CAPTCHA challenges.
Analyze the following page information to determine if a CAPTCHA is present and how to handle it.

Current URL: {current_url}
Page Title: {page_title}
Page Text Sample: {page_text_sample}
Error Messages: {error_messages}
Images Description: {images_description}

Based on this information:
1. Determine if a CAPTCHA is present
2. Identify the type of CAPTCHA
3. Suggest handling strategies

Return your analysis in JSON format:
{{
    "captcha_detected": boolean,
    "captcha_type": string or null,
    "confidence": float (0-1),
    "indicators": [string],
    "handling_strategy": {{
        "approach": string,
        "actions": [string],
        "requires_human": boolean
    }},
    "bypass_possibilities": [string] or null
}}
"""

# Feedback generation prompt
FEEDBACK_GENERATION_TEMPLATE = """
You are helping a browser automation system generate user-friendly feedback.
Create a natural language response based on the outcome of the automation task.

Task Description: {task_description}
Outcome Status: {outcome_status}
Raw Result: {raw_result}
Error Info: {error_info}
Session Summary: {session_summary}

Create a helpful response that:
1. Summarizes what was attempted
2. Explains the outcome clearly
3. Provides relevant details from the result
4. Suggests next steps or alternatives if there were issues
5. Uses a conversational, helpful tone

Return your response as plain text that can be directly shown to the user.
"""

# A dictionary mapping prompt types to their templates
PROMPT_TEMPLATES = {
    "command_parse": COMMAND_PARSE_TEMPLATE,
    "task_planning": TASK_PLANNING_TEMPLATE,
    "context_enhancement": CONTEXT_ENHANCEMENT_TEMPLATE,
    "element_selection": ELEMENT_SELECTION_TEMPLATE,
    "error_recovery": ERROR_RECOVERY_TEMPLATE,
    "data_extraction": DATA_EXTRACTION_TEMPLATE,
    "captcha_detection": CAPTCHA_DETECTION_TEMPLATE,
    "feedback_generation": FEEDBACK_GENERATION_TEMPLATE
}


def get_prompt(prompt_type: str, **kwargs) -> str:
    """
    Get a formatted prompt template.
    
    Args:
        prompt_type: The type of prompt to retrieve
        **kwargs: Variables to format the prompt with
        
    Returns:
        Formatted prompt string
        
    Raises:
        ValueError: If prompt_type is not recognized
    """
    if prompt_type not in PROMPT_TEMPLATES:
        raise ValueError(f"Unknown prompt type: {prompt_type}")
        
    template = PROMPT_TEMPLATES[prompt_type]
    return template.format(**kwargs)
