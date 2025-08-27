"""
FastAPI server with clean architecture.

This server provides:
- RESTful API endpoints
- Session management
- Error handling
- Health checks
- Admin endpoints
"""

import os
import logging
import sys
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, status
import uuid
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from dotenv import load_dotenv

# Add src to path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from agent import TaxChatbot
from llm import OpenAIClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global chatbot instance (will be initialized on startup)
chatbot: Optional[TaxChatbot] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global chatbot
    
    # Startup
    logger.info("Starting Tax Chatbot API")
    
    try:
        llm_client = OpenAIClient()
        chatbot = TaxChatbot(llm_client=llm_client)
        logger.info("Tax Chatbot API started successfully")
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Tax Chatbot API")
    if chatbot:
        # Clean up old sessions
        chatbot.cleanup_old_sessions(hours=1)


# Create FastAPI app
app = FastAPI(
    title="Tax Chatbot API",
    description="Advanced Dutch tax questions chatbot with clean architecture",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production: specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class ChatMessage(BaseModel):
    """Chat message request model."""
    message: str = Field(..., min_length=1, max_length=5000, description="User message")
    session_id: Optional[str] = Field(default="default", description="Session identifier")


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str = Field(..., description="Chatbot response")
    session_id: str = Field(..., description="Session identifier")
    status: str = Field(..., description="Response status")


class SessionInfo(BaseModel):
    """Session information model."""
    session_id: str
    state: str
    question: str
    sources: Dict[str, str]
    message_count: int
    created_at: str
    updated_at: str
    selected_titles: List[str] = []
    unselected_titles: List[str] = []


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    status: str = Field(default="error", description="Response status")


# Dependency to get chatbot instance
def get_chatbot() -> TaxChatbot:
    """Get the global chatbot instance."""
    if not chatbot:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chatbot service is not available"
        )
    return chatbot


# API Endpoints

@app.get("/", summary="Root endpoint")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Tax Chatbot API",
        "version": "2.0.0",
        "description": "Advanced Dutch tax questions chatbot",
        "features": [
            "Clean architecture",
            "Session management",
            "Command processing",
            "Extensible tool system",
            "Workflow management"
        ],
        "endpoints": {
            "POST /chat": "Send a message to the chatbot",
            "GET /session/{session_id}": "Get session information",
            "DELETE /session/{session_id}": "Reset a session",
            "GET /health": "Health check",
            "GET /tools": "List available tools"
        }
    }


@app.post("/chat", response_model=ChatResponse, summary="Chat with the bot")
async def chat(
    chat_message: ChatMessage,
    bot: TaxChatbot = Depends(get_chatbot)
) -> ChatResponse:
    """
    Send a message to the tax chatbot and receive a response.
    
    The chatbot can handle:
    - General questions about what it can do
    - Tax-related questions with automated source retrieval
    - Commands like 'remove sources', 'reformulate', etc.
    """
    try:
        logger.info(f"Chat request for session {chat_message.session_id}: {chat_message.message[:50]}...")
        
        # Determine session ID (auto-generate if missing/default)
        session_id = chat_message.session_id or ""
        if session_id.strip() == "" or session_id.strip().lower() == "default":
            session_id = f"sess-{uuid.uuid4().hex[:8]}"
        bot.session_id = session_id
        
        # Process the message
        response = bot.process_message(chat_message.message)
        
        return ChatResponse(
            response=response,
            session_id=session_id,
            status="success"
        )
        
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing message: {str(e)}"
        )


@app.get("/session/{session_id}", response_model=SessionInfo, summary="Get session info")
async def get_session_info(
    session_id: str,
    bot: TaxChatbot = Depends(get_chatbot)
) -> SessionInfo:
    """Get information about a specific session."""
    try:
        bot.session_id = session_id
        session_data = bot.get_session_info()
        
        if "error" in session_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=session_data["error"]
            )
        
        return SessionInfo(**session_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving session info: {str(e)}"
        )


@app.delete("/session/{session_id}", summary="Reset session")
async def reset_session(
    session_id: str,
    bot: TaxChatbot = Depends(get_chatbot)
) -> Dict[str, str]:
    """Reset a specific session, clearing all conversation history and state."""
    try:
        bot.session_id = session_id
        message = bot.reset_session()
        
        return {
            "message": message,
            "session_id": session_id,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error resetting session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resetting session: {str(e)}"
        )


@app.get("/health", summary="Health check")
async def health_check():
    """Health check endpoint."""
    try:
        # Check if chatbot is available
        if not chatbot:
            return {
                "status": "unhealthy",
                "message": "Chatbot service is not initialized"
            }
        
        # Check tools
        tools = chatbot.list_available_tools()
        
        return {
            "status": "healthy",
            "timestamp": "2024-01-01T00:00:00Z",  # Would use actual timestamp
            "tools_available": len(tools),
            "version": "2.0.0"
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "message": str(e)
        }


@app.get("/tools", summary="List available tools")
async def list_tools(bot: TaxChatbot = Depends(get_chatbot)) -> Dict[str, Any]:
    """Get a list of all available tools."""
    try:
        tools = bot.list_available_tools()
        
        return {
            "tools": tools,
            "count": len(tools),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error listing tools: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing tools: {str(e)}"
        )


## Commands endpoint removed: conversational intents handled by LLM


# Admin endpoints (could be protected with authentication in production)
@app.post("/admin/cleanup", summary="Clean up old sessions")
async def cleanup_sessions(
    hours: int = 24,
    bot: TaxChatbot = Depends(get_chatbot)
) -> Dict[str, Any]:
    """Clean up sessions older than specified hours."""
    try:
        removed = bot.cleanup_old_sessions(hours)
        
        return {
            "removed_sessions": removed,
            "hours": hours,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during cleanup: {str(e)}"
        )


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return ErrorResponse(
        error=exc.detail,
        status="error"
    ).dict()


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return ErrorResponse(
        error="An unexpected error occurred",
        status="error"
    ).dict()


# Run the server
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("API_PORT", 8000))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    logger.info(f"Starting server on {host}:{port}")
    
    uvicorn.run(
        "server:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
