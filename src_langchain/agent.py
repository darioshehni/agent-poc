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
        """LangChain-specific system prompt - more aggressive about tool usage."""
        return get_langchain_prompt_template("agent_system")
    
    def process_message(self, user_input: str) -> str:
        """
        Process user message using LangChain's agent executor.
        Showcases LangChain's built-in reasoning and tool orchestration.
        """
        try:
            # Check for LangChain-specific commands first
            command_response = self.command_processor.process_message(user_input, self)
            if command_response:
                return command_response
            
            # LangChain handles the entire conversation flow, memory, and tool calling
            response = self.agent_executor.invoke({
                "input": user_input
            })
            
            return response["output"]
            
        except Exception as e:
            return f"Er is een fout opgetreden: {str(e)}"
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get session information showcasing LangChain's memory."""
        messages = self.memory.chat_memory.messages
        
        return {
            "session_id": self.session_id,
            "framework": "LangChain",
            "message_count": len(messages),
            "memory_type": "ConversationBufferWindowMemory",
            "memory_window": self.memory.k,
            "available_tools": [tool.name for tool in self.tools],
            "agent_type": "OpenAI Tools Agent with ReAct pattern"
        }
    
    def reset_session(self) -> str:
        """Reset session using LangChain's memory clear."""
        self.memory.clear()
        return "Sessie is gereset met LangChain memory management. U kunt een nieuwe vraag stellen."
    
    def list_available_tools(self) -> List[str]:
        """List available tools."""
        return [tool.name for tool in self.tools]
    
    def list_available_commands(self) -> List[str]:
        """List available commands (LangChain handles most automatically)."""
        return ["reset", "session_info", "help"]