"""
Configuration settings for the Browser AI Agent.

This module defines global settings for timeouts, API keys, browser configurations,
and other application-wide parameters.
"""

import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class Settings:
    """
    Global configuration settings for the application.
    """
    # Browser settings
    headless: bool = True
    browser_type: str = "chromium"  # "chromium", "firefox", or "webkit"
    browser_args: List[str] = field(default_factory=lambda: ["--disable-dev-shm-usage"])
    user_agent: Optional[str] = None
    viewport_width: int = 1280
    viewport_height: int = 720
    
    # Timeouts (in milliseconds)
    navigation_timeout: int = 30000  # 30 seconds
    action_timeout: int = 10000      # 10 seconds
    wait_timeout: int = 5000         # 5 seconds
    
    # Network settings
    slow_mo: int = 50  # Slow down actions by 50ms (helpful for debugging)
    download_path: str = "./downloads"
    
    # API keys (fetched from environment variables)
    openai_api_key: str = field(default_factory=lambda: os.environ.get("OPENAI_API_KEY", ""))
    anthropic_api_key: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", ""))
    
    # LLM settings
    default_llm_provider: str = "openai"  # "openai" or "anthropic"
    openai_model: str = "gpt-4"
    anthropic_model: str = "claude-3-opus-20240229"
    temperature: float = 0.2
    max_tokens: int = 1000
    
    # Session settings
    session_expiry: int = 60 * 60  # 1 hour in seconds
    max_session_history: int = 50  # Maximum number of commands to remember
    
    # Retry settings
    max_retries: int = 3
    retry_delay: int = 1000  # 1 second delay between retries
    
    # API Server settings
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = "browser_ai_agent.log"
    
    # CAPTCHA handling
    captcha_detection_enabled: bool = True
    captcha_service: Optional[str] = None  # "2captcha", "anticaptcha", etc.
    captcha_api_key: str = field(default_factory=lambda: os.environ.get("CAPTCHA_API_KEY", ""))
    
    # Data extraction
    extraction_defaults: Dict[str, Any] = field(default_factory=lambda: {
        "table_format": "json",
        "list_format": "json",
        "text_format": "plain"
    })
    
    def __post_init__(self):
        """Validate settings after initialization."""
        # Convert timeouts to ints
        self.navigation_timeout = int(self.navigation_timeout)
        self.action_timeout = int(self.action_timeout)
        self.wait_timeout = int(self.wait_timeout)
        
        # Create download directory if it doesn't exist
        os.makedirs(self.download_path, exist_ok=True)
        
        # Validate browser type
        valid_browsers = ["chromium", "firefox", "webkit"]
        if self.browser_type not in valid_browsers:
            raise ValueError(f"Browser type must be one of {valid_browsers}")
        
        # Validate LLM provider
        valid_providers = ["openai", "anthropic"]
        if self.default_llm_provider not in valid_providers:
            raise ValueError(f"LLM provider must be one of {valid_providers}")
            
    @classmethod
    def from_env(cls) -> 'Settings':
        """
        Create Settings from environment variables.
        
        Returns:
            Settings instance with values from environment variables
        """
        return cls(
            headless=os.environ.get("BROWSER_HEADLESS", "true").lower() == "true",
            browser_type=os.environ.get("BROWSER_TYPE", "chromium"),
            navigation_timeout=int(os.environ.get("NAVIGATION_TIMEOUT", 30000)),
            action_timeout=int(os.environ.get("ACTION_TIMEOUT", 10000)),
            wait_timeout=int(os.environ.get("WAIT_TIMEOUT", 5000)),
            default_llm_provider=os.environ.get("DEFAULT_LLM_PROVIDER", "openai"),
            openai_model=os.environ.get("OPENAI_MODEL", "gpt-4"),
            anthropic_model=os.environ.get("ANTHROPIC_MODEL", "claude-3-opus-20240229"),
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
        )
