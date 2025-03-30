"""
Session management module.

This module provides functionality for managing user sessions, including
creation, retrieval, updating, and deletion of sessions.
"""

import logging
import time
import uuid
from typing import Dict, List, Any, Optional

from config.settings import Settings

# Set up logger
logger = logging.getLogger(__name__)


class SessionManager:
    """
    Session manager for user sessions.
    
    Manages the lifecycle of user sessions, including creation, retrieval,
    updating, and deletion.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the session manager.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.session_expiry = settings.session_expiry  # seconds
    
    def create_session(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new session.
        
        Args:
            user_id: Optional user ID to associate with the session
            
        Returns:
            Newly created session
        """
        session_id = str(uuid.uuid4())
        
        session = {
            "id": session_id,
            "user_id": user_id,
            "created_at": time.time(),
            "last_active": time.time(),
            "browser_context_id": None,
            "last_command": None,
            "last_result": None,
            "data": {}
        }
        
        self.sessions[session_id] = session
        logger.info(f"Created new session: {session_id}")
        
        return session
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a session by ID.
        
        Args:
            session_id: The ID of the session to retrieve
            
        Returns:
            The session or None if not found or expired
        """
        session = self.sessions.get(session_id)
        
        if not session:
            logger.warning(f"Session not found: {session_id}")
            return None
        
        # Check if session has expired
        last_active = session.get("last_active", 0)
        if time.time() - last_active > self.session_expiry:
            logger.info(f"Session expired: {session_id}")
            self.delete_session(session_id)
            return None
        
        # Update last active time
        session["last_active"] = time.time()
        return session
    
    def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a session with new data.
        
        Args:
            session_id: The ID of the session to update
            updates: Updates to apply to the session
            
        Returns:
            True if the session was updated, False otherwise
        """
        session = self.get_session(session_id)
        
        if not session:
            logger.warning(f"Cannot update session, not found: {session_id}")
            return False
        
        # Apply updates
        for key, value in updates.items():
            if key != "id":  # Don't allow changing the ID
                if key == "data" and isinstance(value, dict):
                    # Merge data dictionaries
                    if "data" not in session:
                        session["data"] = {}
                    session["data"].update(value)
                else:
                    session[key] = value
        
        # Update last active time
        session["last_active"] = time.time()
        
        logger.debug(f"Updated session: {session_id}")
        return True
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: The ID of the session to delete
            
        Returns:
            True if the session was deleted, False otherwise
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Deleted session: {session_id}")
            return True
        
        logger.warning(f"Cannot delete session, not found: {session_id}")
        return False
    
    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """
        Get all active sessions.
        
        Returns:
            List of all active sessions
        """
        # Filter out expired sessions
        active_sessions = []
        current_time = time.time()
        
        for session_id, session in list(self.sessions.items()):
            last_active = session.get("last_active", 0)
            if current_time - last_active <= self.session_expiry:
                active_sessions.append(session)
            else:
                # Delete expired session
                del self.sessions[session_id]
                logger.info(f"Cleaned up expired session: {session_id}")
        
        return active_sessions
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        expired_count = 0
        current_time = time.time()
        
        for session_id, session in list(self.sessions.items()):
            last_active = session.get("last_active", 0)
            if current_time - last_active > self.session_expiry:
                del self.sessions[session_id]
                expired_count += 1
                logger.info(f"Cleaned up expired session: {session_id}")
        
        return expired_count
    
    def get_session_data(self, session_id: str, key: str, default: Any = None) -> Any:
        """
        Get a specific piece of data from a session.
        
        Args:
            session_id: The ID of the session
            key: The data key to retrieve
            default: Default value if key is not found
            
        Returns:
            The data value or default
        """
        session = self.get_session(session_id)
        
        if not session:
            return default
        
        session_data = session.get("data", {})
        return session_data.get(key, default)
    
    def set_session_data(self, session_id: str, key: str, value: Any) -> bool:
        """
        Set a specific piece of data in a session.
        
        Args:
            session_id: The ID of the session
            key: The data key to set
            value: The value to set
            
        Returns:
            True if successful, False otherwise
        """
        session = self.get_session(session_id)
        
        if not session:
            return False
        
        if "data" not in session:
            session["data"] = {}
        
        session["data"][key] = value
        session["last_active"] = time.time()
        
        return True
    
    def get_sessions_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all active sessions for a specific user.
        
        Args:
            user_id: The user ID to get sessions for
            
        Returns:
            List of active sessions for the user
        """
        user_sessions = []
        current_time = time.time()
        
        for session in self.sessions.values():
            if session.get("user_id") == user_id:
                last_active = session.get("last_active", 0)
                if current_time - last_active <= self.session_expiry:
                    user_sessions.append(session)
        
        return user_sessions
    
    def set_browser_context_id(self, session_id: str, context_id: str) -> bool:
        """
        Associate a browser context with a session.
        
        Args:
            session_id: The ID of the session
            context_id: The ID of the browser context
            
        Returns:
            True if successful, False otherwise
        """
        return self.update_session(session_id, {"browser_context_id": context_id})
