"""
LangChain implementation of the Tax Chatbot.
Demonstrates LangChain's agent patterns, memory management, and tool integration.
"""

import os
import json
from typing import Dict, Any, List

from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import BaseMessage
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

from tools.legislation_tool import get_legislation
from tools.case_law_tool import get_case_law
from tools.answer_tool import generate_answer
from commands import LangChainCommandProcessor

# Use LangChain-specific prompts
from prompts import get_langchain_prompt_template

# Import session management from original implementation
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from sessions import QuerySession, SessionManager
from base import WorkflowState


class LangChainTaxChatbot:
    """
    LangChain-based implementation showcasing framework strengths:
    - ReAct agent pattern for reasoning
    - Built-in conversation memory
    - Tool integration via decorators
    - Prompt template system
    """
    
    def __init__(self, session_id: str = "default"):
        self.session_id = session_id
        
        # Add session management for source tracking
        self.session_manager = SessionManager()
        
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.0,
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )
        
        # LangChain's built-in memory management
        self.memory = ConversationBufferWindowMemory(
            k=10,  # Keep last 10 exchanges
            memory_key="chat_history",
            return_messages=True,
            input_key="input",
            output_key="output"
        )
        
        # Available tools
        self.tools = [get_legislation, get_case_law, generate_answer]
        
        # LangChain command processor
        self.command_processor = LangChainCommandProcessor()
        
        # Create agent with LangChain's prompt template system
        self.agent = self._create_agent()
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5
        )
    
    def _create_agent(self):
        """Create LangChain agent with ReAct pattern and custom prompt."""
        
        # LangChain's prompt template system - more structured than direct prompts
        prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        return create_openai_tools_agent(self.llm, self.tools, prompt)
    
    def _get_system_prompt(self) -> str:
        """LangChain-specific system prompt with session context."""
        base_prompt = get_langchain_prompt_template("agent_system")
        
        # Get session to add context
        session = self.session_manager.get_session(self.session_id)
        
        if session and session.sources:
            context = "\n\nSESSION CONTEXT:\n"
            context += f"Verzamelde bronnen voor huidige vraag:\n"
            
            # Collect complete source data for generate_tax_answer tool
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
            
            # Add complete source data for generate_tax_answer tool
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
            
            return base_prompt + context
        
        return base_prompt
    
    def process_message(self, user_input: str) -> str:
        """
        Process user message using LangChain's agent executor.
        Showcases LangChain's built-in reasoning and tool orchestration.
        """
        try:
            # Get or create session
            session = self.session_manager.get_or_create_session(self.session_id)
            
            # Add user message to session
            session.add_message("user", user_input)
            
            # Check for LangChain-specific commands first
            command_response = self.command_processor.process_message(user_input, self)
            if command_response:
                session.add_message("assistant", command_response)
                return command_response
            
            # Recreate agent with updated context (LangChain limitation)
            self.agent = self._create_agent()
            self.agent_executor = AgentExecutor(
                agent=self.agent,
                tools=self.tools,
                memory=self.memory,
                verbose=True,
                handle_parsing_errors=True,
                max_iterations=5
            )
            
            # LangChain handles the entire conversation flow, memory, and tool calling
            response = self.agent_executor.invoke({
                "input": user_input
            })
            
            # Track source collection for session context
            self._update_session_with_tool_calls(session, user_input, response)
            
            # Add response to session
            session.add_message("assistant", response["output"])
            
            return response["output"]
            
        except Exception as e:
            return f"Er is een fout opgetreden: {str(e)}"
    
    def _update_session_with_tool_calls(self, session: QuerySession, user_input: str, response: dict):
        """Track tool calls to update session context."""
        # Check if response contains intermediate steps (tool calls)
        if "intermediate_steps" in response:
            for step in response["intermediate_steps"]:
                if len(step) >= 2:
                    action, observation = step[0], step[1] 
                    
                    # Track source collection tools
                    if hasattr(action, 'tool') and action.tool in ["get_legislation", "get_case_law"]:
                        try:
                            # Parse the observation result
                            import json
                            if isinstance(observation, str):
                                result_data = json.loads(observation)
                                if result_data.get("success"):
                                    from base import ToolResult
                                    tool_result = ToolResult(
                                        success=True,
                                        data=result_data.get("data", []),
                                        metadata=result_data.get("metadata", {})
                                    )
                                    session.add_source(action.tool, tool_result)
                                    session.transition_to(WorkflowState.ACTIVE)
                        except Exception as e:
                            print(f"Error parsing tool result: {e}")
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get session information showcasing LangChain's memory."""
        messages = self.memory.chat_memory.messages
        session = self.session_manager.get_session(self.session_id)
        
        base_info = {
            "session_id": self.session_id,
            "framework": "LangChain",
            "message_count": len(messages),
            "memory_type": "ConversationBufferWindowMemory",
            "memory_window": self.memory.k,
            "available_tools": [tool.name for tool in self.tools],
            "agent_type": "OpenAI Tools Agent with ReAct pattern"
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
        """Reset session using LangChain's memory clear."""
        self.memory.clear()
        self.session_manager.delete_session(self.session_id)
        return "Sessie is gereset met LangChain memory management. U kunt een nieuwe vraag stellen."
    
    def list_available_tools(self) -> List[str]:
        """List available tools."""
        return [tool.name for tool in self.tools]
    
    def list_available_commands(self) -> List[str]:
        """List available commands (LangChain handles most automatically)."""
        return ["reset", "session_info", "help"]