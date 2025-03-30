#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Browser AI Agent - Main Entry Point

This module serves as the main entry point for the Browser AI Agent application,
setting up command-line interface or API server as needed.
"""

import argparse
import asyncio
import logging
import sys
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import Settings
from utils.logger import setup_logger
from api.interact import setup_interact_routes
from api.extract import setup_extract_routes
from controller.workflow import WorkflowController
from controller.session import SessionManager


def setup_api_server(settings: Settings) -> FastAPI:
    """
    Set up and configure the FastAPI server.
    
    Args:
        settings: Application settings
        
    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="Browser AI Agent API",
        description="API for browser automation via natural language commands",
        version="1.0.0"
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Setup routes
    setup_interact_routes(app)
    setup_extract_routes(app)
    
    return app


async def run_cli_mode(settings: Settings) -> None:
    """
    Run the application in CLI mode, accepting commands from stdin.
    
    Args:
        settings: Application settings
    """
    logger = logging.getLogger("browser_ai_agent")
    
    session_manager = SessionManager(settings)
    workflow_controller = WorkflowController(settings, session_manager)
    
    logger.info("Browser AI Agent CLI started. Type 'exit' to quit.")
    
    while True:
        try:
            command = input("\nEnter command: ")
            if command.lower() in ("exit", "quit"):
                break
                
            result = await workflow_controller.execute_command(command)
            print(f"\nResult: {result}")
            
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down...")
            break
        except Exception as e:
            logger.error(f"Error processing command: {str(e)}")
    
    # Cleanup
    await workflow_controller.cleanup()
    logger.info("Browser AI Agent CLI shutdown complete")


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Browser AI Agent")
    parser.add_argument(
        "--mode", 
        type=str, 
        choices=["api", "cli"], 
        default="cli",
        help="Run in API server mode or command-line interface mode"
    )
    parser.add_argument(
        "--host", 
        type=str, 
        default="127.0.0.1",
        help="Host to bind the API server to (API mode only)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8000,
        help="Port to bind the API server to (API mode only)"
    )
    parser.add_argument(
        "--headless", 
        action="store_true",
        help="Run browser in headless mode"
    )
    parser.add_argument(
        "--debug", 
        action="store_true",
        help="Enable debug logging"
    )
    
    return parser.parse_args()


def main() -> None:
    """
    Main entry point for the application.
    """
    # Parse command line arguments
    args = parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logger(log_level)
    logger = logging.getLogger("browser_ai_agent")
    
    # Load settings
    settings = Settings(headless=args.headless)
    
    if args.mode == "api":
        # API server mode
        import uvicorn
        
        app = setup_api_server(settings)
        logger.info(f"Starting API server on {args.host}:{args.port}")
        
        uvicorn.run(app, host=args.host, port=args.port)
    else:
        # CLI mode
        try:
            asyncio.run(run_cli_mode(settings))
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down...")
        except Exception as e:
            logger.error(f"Fatal error: {str(e)}")
            sys.exit(1)


if __name__ == "__main__":
    main()
