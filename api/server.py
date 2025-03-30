"""
API server module.

This module provides the FastAPI server for the application.
"""

import os
import json
import logging
import asyncio
import uvicorn
from typing import Dict, List, Any, Optional, Union
from fastapi import FastAPI, HTTPException, Depends, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config.settings import Settings, load_settings
from controller.workflow import WorkflowController
from controller.session import SessionManager
from utils.errors import BrowserAIError, APIError
from utils.logging import setup_logging, RequestLogger

# Set up logger
logger = logging.getLogger(__name__)
request_logger = RequestLogger(logger)

# Load settings
settings = load_settings()

# Create FastAPI app
app = FastAPI(
    title="Browser AI Agent API",
    description="API for controlling the Browser AI Agent",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Application state
app_state = {
    "workflow_controller": None,
    "session_manager": None,
    "initialized": False
}


# Models
class CommandRequest(BaseModel):
    """Command request model."""
    command: str = Field(..., description="Natural language command to execute")
    session_id: Optional[str] = Field(None, description="Session ID")
    user_id: Optional[str] = Field(None, description="User ID")
    options: Optional[Dict[str, Any]] = Field(None, description="Additional options")


class CommandResponse(BaseModel):
    """Command response model."""
    session_id: str = Field(..., description="Session ID")
    success: bool = Field(..., description="Whether the command was successful")
    message: str = Field(..., description="Response message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    error: Optional[Dict[str, Any]] = Field(None, description="Error information if any")


class SessionResponse(BaseModel):
    """Session response model."""
    session_id: str = Field(..., description="Session ID")
    created_at: int = Field(..., description="Creation timestamp")
    last_active: int = Field(..., description="Last activity timestamp")
    user_id: Optional[str] = Field(None, description="User ID")
    browser_context_id: Optional[str] = Field(None, description="Browser context ID")


class ErrorResponse(BaseModel):
    """Error response model."""
    status: str = Field("error", description="Response status")
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")


# Dependencies
async def get_workflow_controller() -> WorkflowController:
    """Get the workflow controller."""
    if not app_state["initialized"]:
        raise HTTPException(
            status_code=503,
            detail="Server is initializing. Please try again later."
        )
    return app_state["workflow_controller"]


async def get_session_manager() -> SessionManager:
    """Get the session manager."""
    if not app_state["initialized"]:
        raise HTTPException(
            status_code=503,
            detail="Server is initializing. Please try again later."
        )
    return app_state["session_manager"]


# Exception handler
@app.exception_handler(BrowserAIError)
async def browser_ai_exception_handler(request: Request, exc: BrowserAIError):
    """Handle BrowserAIError exceptions."""
    error_code = exc.__class__.__name__
    status_code = 400
    
    # Map exception types to status codes
    if isinstance(exc, APIError) and hasattr(exc, "details") and "status_code" in exc.details:
        status_code = exc.details["status_code"]
    
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            code=error_code,
            message=str(exc),
            details=getattr(exc, "details", None)
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            code="InternalServerError",
            message="An unexpected error occurred",
            details={"error": str(exc)}
        ).dict()
    )


# Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log requests and responses."""
    # Generate request ID
    request_id = request_logger.log_request(
        method=request.method,
        url=str(request.url),
        headers=dict(request.headers)
    )
    
    # Start timer
    start_time = asyncio.get_event_loop().time()
    
    # Call next middleware/route handler
    try:
        response = await call_next(request)
        
        # Log response
        elapsed_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
        request_logger.log_response(
            status_code=response.status_code,
            request_id=request_id,
            elapsed_ms=elapsed_ms
        )
        
        return response
    except Exception as e:
        # Log error response
        elapsed_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
        request_logger.log_response(
            status_code=500,
            request_id=request_id,
            elapsed_ms=elapsed_ms,
            body={"error": str(e)}
        )
        raise


# Routes
@app.get("/", response_model=Dict[str, Any])
async def root():
    """Root endpoint."""
    return {
        "name": "Browser AI Agent API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health", response_model=Dict[str, Any])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy" if app_state["initialized"] else "initializing",
        "initialized": app_state["initialized"]
    }


@app.post("/commands", response_model=CommandResponse)
async def execute_command(
    command_request: CommandRequest,
    workflow: WorkflowController = Depends(get_workflow_controller)
):
    """Execute a command."""
    try:
        result = await workflow.execute_command(
            command=command_request.command,
            session_id=command_request.session_id,
            user_id=command_request.user_id,
            options=command_request.options or {}
        )
        
        return CommandResponse(
            session_id=result["session_id"],
            success=result["success"],
            message=result["message"],
            data=result.get("data")
        )
    except BrowserAIError as e:
        return CommandResponse(
            session_id=command_request.session_id or "error",
            success=False,
            message=str(e),
            error={
                "type": e.__class__.__name__,
                "details": getattr(e, "details", {})
            }
        )


@app.get("/sessions", response_model=List[SessionResponse])
async def list_sessions(
    session_manager: SessionManager = Depends(get_session_manager)
):
    """List all active sessions."""
    sessions = session_manager.get_all_sessions()
    return [
        SessionResponse(
            session_id=session["id"],
            created_at=session["created_at"],
            last_active=session["last_active"],
            user_id=session.get("user_id"),
            browser_context_id=session.get("browser_context_id")
        )
        for session in sessions
    ]


@app.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Get a session by ID."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    return SessionResponse(
        session_id=session["id"],
        created_at=session["created_at"],
        last_active=session["last_active"],
        user_id=session.get("user_id"),
        browser_context_id=session.get("browser_context_id")
    )


@app.delete("/sessions/{session_id}", response_model=Dict[str, Any])
async def delete_session(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Delete a session by ID."""
    success = session_manager.delete_session(session_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    return {
        "status": "success",
        "message": f"Session {session_id} deleted"
    }


@app.post("/sessions", response_model=SessionResponse)
async def create_session(
    user_id: Optional[str] = None,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Create a new session."""
    session = session_manager.create_session(user_id=user_id)
    
    return SessionResponse(
        session_id=session["id"],
        created_at=session["created_at"],
        last_active=session["last_active"],
        user_id=session.get("user_id"),
        browser_context_id=session.get("browser_context_id")
    )


# Startup and shutdown events
@app.on_event("startup")
async def startup():
    """Initialize the application on startup."""
    try:
        logger.info("Starting API server")
        
        # Set up components
        from browser.manager import BrowserManager
        from controller.state import StateTracker
        
        browser_manager = BrowserManager(settings)
        session_manager = SessionManager(settings)
        state_tracker = StateTracker(settings)
        
        workflow_controller = WorkflowController(
            settings=settings,
            browser_manager=browser_manager,
            session_manager=session_manager,
            state_tracker=state_tracker
        )
        
        # Initialize workflow controller
        await workflow_controller.initialize()
        
        # Update app state
        app_state["workflow_controller"] = workflow_controller
        app_state["session_manager"] = session_manager
        app_state["initialized"] = True
        
        logger.info("API server started successfully")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}", exc_info=True)
        # Don't set initialized to True
        raise


@app.on_event("shutdown")
async def shutdown():
    """Clean up resources on shutdown."""
    logger.info("Shutting down API server")
    
    if app_state["workflow_controller"]:
        try:
            await app_state["workflow_controller"].cleanup()
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}", exc_info=True)
    
    logger.info("API server shutdown complete")


def start_server():
    """Start the API server."""
    # Set up logging
    setup_logging(
        log_level=settings.log_level,
        log_file=settings.log_file
    )
    
    # Start server
    uvicorn.run(
        "api.server:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.development_mode
    )


if __name__ == "__main__":
    start_server() 