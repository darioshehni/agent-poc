"""
LangChain FastAPI server implementation.
Demonstrates framework integration with REST API.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any
import uvicorn
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from agent import LangChainTaxChatbot


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: str
    framework: str = "LangChain"


# Global chatbot instances (in production, use proper session management)
chatbots: Dict[str, LangChainTaxChatbot] = {}

app = FastAPI(
    title="Dutch Tax Chatbot API - LangChain",
    description="LangChain implementation of the Dutch Tax Chatbot with ReAct agents",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


def get_or_create_chatbot(session_id: str) -> LangChainTaxChatbot:
    """Get or create a chatbot instance for the session."""
    if session_id not in chatbots:
        chatbots[session_id] = LangChainTaxChatbot(session_id=session_id)
    return chatbots[session_id]


@app.get("/")
async def root():
    """API information."""
    return {
        "name": "Dutch Tax Chatbot API",
        "framework": "LangChain", 
        "version": "1.0.0",
        "description": "LangChain implementation showcasing ReAct agents and memory management",
        "endpoints": {
            "chat": "POST /chat - Send message to chatbot",
            "session": "GET /session/{id} - Get session info",
            "health": "GET /health - Health check",
            "tools": "GET /tools - List available tools",
            "commands": "GET /commands - List available commands"
        }
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with the LangChain tax chatbot."""
    try:
        chatbot = get_or_create_chatbot(request.session_id)
        response = chatbot.process_message(request.message)
        
        return ChatResponse(
            response=response,
            session_id=request.session_id,
            timestamp=datetime.now().isoformat(),
            framework="LangChain"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")


@app.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """Get session information."""
    try:
        if session_id not in chatbots:
            raise HTTPException(status_code=404, detail="Session not found")
            
        chatbot = chatbots[session_id]
        session_info = chatbot.get_session_info()
        
        return JSONResponse(content=session_info)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting session info: {str(e)}")


@app.delete("/session/{session_id}")
async def reset_session(session_id: str):
    """Reset a specific session."""
    try:
        if session_id in chatbots:
            chatbots[session_id].reset_session()
            return {"message": f"Session {session_id} reset successfully", "framework": "LangChain"}
        else:
            raise HTTPException(status_code=404, detail="Session not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resetting session: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "framework": "LangChain",
        "timestamp": datetime.now().isoformat(),
        "active_sessions": len(chatbots)
    }


@app.get("/tools")
async def list_tools():
    """List available tools."""
    # Create a temporary chatbot to get tool list
    temp_chatbot = LangChainTaxChatbot("temp")
    tools = temp_chatbot.list_available_tools()
    
    return {
        "framework": "LangChain",
        "tools": tools,
        "tool_type": "LangChain @tool decorators"
    }


@app.get("/commands")
async def list_commands():
    """List available commands."""
    temp_chatbot = LangChainTaxChatbot("temp")
    commands = temp_chatbot.list_available_commands()
    
    return {
        "framework": "LangChain",
        "commands": commands
    }


@app.post("/admin/cleanup")
async def cleanup_sessions():
    """Clean up sessions (admin endpoint)."""
    global chatbots
    old_count = len(chatbots)
    chatbots.clear()
    
    return {
        "message": f"Cleaned up {old_count} sessions",
        "framework": "LangChain"
    }


if __name__ == "__main__":
    # Configuration
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8001))  # Different port to avoid conflicts
    
    print(f"🚀 Starting LangChain Tax Chatbot API on {host}:{port}")
    print(f"📚 Documentation: http://localhost:{port}/docs")
    
    uvicorn.run(app, host=host, port=port)