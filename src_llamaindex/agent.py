"""
LlamaIndex implementation of the Tax Chatbot.
Demonstrates LlamaIndex's ChatEngine, query processing, and tool integration.
"""

import os
import json
from typing import Dict, Any, List

from llama_index.core.agent import ReActAgent
from llama_index.llms.openai import OpenAI
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.chat_engine import SimpleChatEngine

from tools.legislation_tool import legislation_tool
from tools.case_law_tool import case_law_tool
from tools.answer_tool import answer_tool
from commands import LlamaIndexCommandProcessor

# Use LlamaIndex-specific prompts
from prompts import get_llamaindex_prompt_template


class LlamaIndexTaxChatbot:
    """
    LlamaIndex-based implementation showcasing framework strengths:
    - Query processing and transformation
    - Response synthesis
    - Tool integration via FunctionTool
    - Chat memory management
    """
    
    def __init__(self, session_id: str = "default"):
        self.session_id = session_id
        
        # LlamaIndex OpenAI LLM
        self.llm = OpenAI(
            model="gpt-4o-mini",
            temperature=0.0,
            api_key=os.getenv('OPENAI_API_KEY')
        )
        
        # LlamaIndex tools
        self.tools = [legislation_tool, case_law_tool, answer_tool]
        
        # LlamaIndex memory management
        self.memory = ChatMemoryBuffer.from_defaults(token_limit=4000)
        
        # LlamaIndex command processor
        self.command_processor = LlamaIndexCommandProcessor()
        
        # Create ReActAgent with LlamaIndex
        self.agent = ReActAgent.from_tools(
            tools=self.tools,
            llm=self.llm,
            memory=self.memory,
            verbose=True,
            system_prompt=self._get_system_prompt()
        )
    
    def _get_system_prompt(self) -> str:
        """LlamaIndex-specific system prompt - forces workflow compliance."""
        prompt = get_llamaindex_prompt_template("agent_system")
        print(f"🦙 DEBUG: LlamaIndex using system prompt: {prompt[:200]}...")
        return prompt
    
    def process_message(self, user_input: str) -> str:
        """
        Process user message using LlamaIndex's agent and query processing.
        Showcases LlamaIndex's approach to conversation flow.
        """
        try:
            # Check for LlamaIndex-specific commands first
            command_response = self.command_processor.process_message(user_input, self)
            if command_response:
                return command_response
            
            # LlamaIndex handles query processing, tool calling, and response synthesis
            response = self.agent.chat(user_input)
            
            return str(response)
            
        except Exception as e:
            return f"Er is een fout opgetreden in LlamaIndex: {str(e)}"
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get session information showcasing LlamaIndex's capabilities."""
        return {
            "session_id": self.session_id,
            "framework": "LlamaIndex",
            "memory_type": "ChatMemoryBuffer",
            "memory_token_limit": self.memory.token_limit,
            "available_tools": [tool.metadata.name for tool in self.tools],
            "agent_type": "ReActAgent with query processing",
            "llm_model": self.llm.model,
            "features": [
                "Query transformation",
                "Response synthesis", 
                "Tool integration via FunctionTool",
                "Chat memory management"
            ]
        }
    
    def reset_session(self) -> str:
        """Reset session using LlamaIndex's memory management."""
        self.memory.reset()
        return "Sessie is gereset met LlamaIndex memory management. U kunt een nieuwe vraag stellen."
    
    def list_available_tools(self) -> List[str]:
        """List available LlamaIndex tools."""
        return [tool.metadata.name for tool in self.tools]
    
    def list_available_commands(self) -> List[str]:
        """List available commands."""
        return ["reset", "session_info", "help"]