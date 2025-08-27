"""
LlamaIndex implementation of the Tax Chatbot.
Demonstrates LlamaIndex's ChatEngine, query processing, and tool integration.
"""

import os
import json
from typing import Dict, Any, List

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.openai import OpenAI
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.chat_engine import SimpleChatEngine
from llama_index.core.workflow import Context

from tools.legislation_tool import legislation_tool
from tools.case_law_tool import case_law_tool
from tools.answer_tool import answer_tool
from commands import LlamaIndexCommandProcessor

# Use LlamaIndex-specific prompts
from prompts import get_llamaindex_prompt_template

# Import session management from original implementation
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from sessions import QuerySession, SessionManager
from base import WorkflowState


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
        
        # Add session management for source tracking
        self.session_manager = SessionManager()
        
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
        
        # Create FunctionAgent with current LlamaIndex architecture
        self.agent = FunctionAgent(
            tools=self.tools,
            llm=self.llm,
            system_prompt=self._get_system_prompt()
        )
        
        # Context is handled internally by FunctionAgent
        self.context = None
    
    def _get_system_prompt(self) -> str:
        """LlamaIndex-specific system prompt with session context."""
        base_prompt = get_llamaindex_prompt_template("agent_system")
        
        # Get session to add context
        session = self.session_manager.get_session(self.session_id)
        
        if session and session.sources:
            context = "\n\nSESSION CONTEXT:\n"
            context += f"Verzamelde bronnen voor huidige vraag:\n"
            
            # Collect complete source data for generate_answer tool
            legislation_sources = []
            case_law_sources = []
            
            for tool_name, result in session.sources.items():
                if result.success:
                    context += f"- {tool_name}: ✓ Beschikbaar\n"
                    if result.data:
                        # Show first item completely for display
                        first_item = result.data[0] if isinstance(result.data, list) and result.data else str(result.data)
                        context += f"  Voorbeeld: {first_item}\n"
                        
                        # Collect complete sources for tool use
                        if tool_name == "get_legislation":
                            legislation_sources = result.data if isinstance(result.data, list) else [str(result.data)]
                        elif tool_name == "get_case_law":
                            case_law_sources = result.data if isinstance(result.data, list) else [str(result.data)]
                else:
                    context += f"- {tool_name}: ✗ Gefaald\n"
            
            # Add complete source data for generate_answer tool
            context += "\nBij gebruikersbevestiging, gebruik generate_answer met deze COMPLETE verzamelde bronnen:\n"
            
            if legislation_sources:
                context += "\nLEGISLATIE BRONNEN voor generate_answer:\n"
                for i, source in enumerate(legislation_sources, 1):
                    context += f"{i}. {source}\n"
            
            if case_law_sources:
                context += "\nJURISPRUDENTIE BRONNEN voor generate_answer:\n"
                for i, source in enumerate(case_law_sources, 1):
                    context += f"{i}. {source}\n"
            
            context += "\nROEP generate_answer aan met question={user_question}, legislation={deze wetgeving lijst}, case_law={deze jurisprudentie lijst}"
            
            final_prompt = base_prompt + context
            print(f"🦙 DEBUG: LlamaIndex using enhanced prompt: {final_prompt[:200]}...")
            return final_prompt
        
        print(f"🦙 DEBUG: LlamaIndex using base prompt: {base_prompt[:200]}...")
        return base_prompt
    
    def process_message(self, user_input: str) -> str:
        """
        Process user message using LlamaIndex's agent and query processing.
        Showcases LlamaIndex's approach to conversation flow.
        """
        try:
            # Get or create session
            session = self.session_manager.get_or_create_session(self.session_id)
            
            # Add user message to session
            session.add_message("user", user_input)
            
            # Check for LlamaIndex-specific commands first
            command_response = self.command_processor.process_message(user_input, self)
            if command_response:
                session.add_message("assistant", command_response)
                return command_response
            
            # Update agent with new system prompt including session context
            # Note: LlamaIndex may still have limitations with prompt updates
            self.agent.system_prompt = self._get_system_prompt()
            
            # LlamaIndex handles query processing, tool calling, and response synthesis
            response = self.agent.chat(user_input)
            
            # Track source collection for session context
            self._update_session_with_tool_calls(session, user_input, response)
            
            # Add response to session
            response_str = str(response)
            session.add_message("assistant", response_str)
            
            return response_str
            
        except Exception as e:
            return f"Er is een fout opgetreden in LlamaIndex: {str(e)}"
    
    def _update_session_with_tool_calls(self, session: QuerySession, user_input: str, response):
        """Track tool calls to update session context."""
        # Note: LlamaIndex FunctionAgent may not expose tool call details as easily
        # This is a limitation of the framework architecture
        try:
            # Check if response has source information (tool calls are hidden in LlamaIndex)
            response_str = str(response)
            
            # Heuristic: if response mentions sources or tools, mark session as active
            if any(keyword in response_str.lower() for keyword in ["wetgeving", "jurisprudentie", "bronnen", "wet op", "ecli"]):
                session.transition_to(WorkflowState.ACTIVE)
                
                # This is a simplified approximation since LlamaIndex doesn't expose tool call details easily
                print(f"🦙 DEBUG: Detected potential tool usage, marking session as active")
        except Exception as e:
            print(f"Error tracking LlamaIndex tool calls: {e}")
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get session information showcasing LlamaIndex's capabilities."""
        session = self.session_manager.get_session(self.session_id)
        
        base_info = {
            "session_id": self.session_id,
            "framework": "LlamaIndex",
            "memory_type": "ChatMemoryBuffer",
            "memory_token_limit": self.memory.token_limit,
            "available_tools": [tool.metadata.name for tool in self.tools],
            "agent_type": "FunctionAgent with workflow (updated architecture)",
            "llm_model": self.llm.model,
            "features": [
                "Query transformation",
                "Response synthesis", 
                "Tool integration via FunctionTool",
                "Chat memory management"
            ]
        }
        
        # Add session context if available
        if session:
            base_info.update({
                "state": session.state.value,
                "sources": session.get_source_summary(),
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat()
            })
        
        return base_info
    
    def reset_session(self) -> str:
        """Reset session using LlamaIndex's memory management."""
        self.memory.reset()
        self.session_manager.delete_session(self.session_id)
        return "Sessie is gereset met LlamaIndex memory management. U kunt een nieuwe vraag stellen."
    
    def list_available_tools(self) -> List[str]:
        """List available LlamaIndex tools."""
        return [tool.metadata.name for tool in self.tools]
    
    def list_available_commands(self) -> List[str]:
        """List available commands."""
        return ["reset", "session_info", "help"]