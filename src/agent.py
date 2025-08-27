"""
Tax Chatbot Agent with clean, extensible architecture.

This implementation focuses on:
- Clean separation of concerns
- Extensible tool system
- Proper state management
- Command pattern for user actions
- Professional error handling
- Easy testing and maintenance
"""

import json
import logging
from typing import Dict, Any, List, Optional

from base import WorkflowState, ToolManager
from sessions import QuerySession, SessionManager
from commands import CommandProcessor
from llm import OpenAIClient, LLMClient
from tools.legislation_tool import LegislationTool
from tools.case_law_tool import CaseLawTool
from tools.answer_tool import AnswerTool
from prompts import get_prompt_template

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaxChatbot:
    """
    Advanced Tax Chatbot with clean architecture.
    
    Features:
    - Intelligent workflow management
    - Extensible tool system
    - User command processing
    - Multi-session support
    - Comprehensive error handling
    """
    
    def __init__(
        self,
        llm_client: LLMClient = None,
        session_id: str = "default"
    ):
        """
        Initialize the chatbot with clean architecture components.
        
        Args:
            llm_client: Optional custom LLM client
            session_id: Session identifier for multi-user support
        """
        
        # Core components
        self.llm_client = llm_client or OpenAIClient()
        self.session_manager = SessionManager()
        self.tool_manager = ToolManager()
        self.command_processor = CommandProcessor()
        
        # Current session
        self.session_id = session_id
        
        # Initialize system
        self._setup_tools()
        
        logger.info(f"TaxChatbot initialized for session: {session_id}")
    
    def _setup_tools(self) -> None:
        """Register all available tools."""
        
        # Create tool instances
        answer_tool = AnswerTool(self.llm_client)
        
        # Register tools
        self.tool_manager.register(LegislationTool())
        self.tool_manager.register(CaseLawTool())
        self.tool_manager.register(answer_tool)
        
        # Validate all tools
        validation_errors = self.tool_manager.validate_tools()
        if validation_errors:
            logger.warning(f"Tool validation issues: {validation_errors}")
        
        logger.info(f"Registered {len(self.tool_manager.list_tools())} tools")
    
    
    def process_message(self, user_input: str) -> str:
        """
        Main entry point for processing user messages.
        
        This method:
        1. Gets or creates user session
        2. Checks for commands first
        3. Processes with AI if not a command
        4. Updates workflow state
        5. Returns appropriate response
        """
        
        try:
            # Get session
            session = self.session_manager.get_or_create_session(self.session_id)
            
            # Add user message to history
            session.add_message("user", user_input)
            
            logger.info(f"Processing message for session {self.session_id}: {user_input[:50]}...")
            
            # Check for commands first
            command_response = self.command_processor.process_message(user_input, session)
            if command_response:
                session.add_message("assistant", command_response)
                return command_response
            
            # No need for explicit confirmation handling - LLM handles it via context
            
            # Process with AI
            response = self._process_with_ai(session)
            
            # Add response to history
            session.add_message("assistant", response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            return f"Er is een onverwachte fout opgetreden: {str(e)}. Probeer het opnieuw."
    
    def _process_with_ai(self, session: QuerySession) -> str:
        """Process message using AI with function calling."""
        
        # Build system prompt
        system_prompt = self._build_system_prompt(session)
        
        # Prepare conversation messages
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add recent conversation history (last 10 messages)
        recent_history = session.conversation_history[-10:]
        for msg in recent_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Get available tools
        tools = self.tool_manager.get_function_schemas()
        
        try:
            # Make initial AI request
            response = self.llm_client.chat_completion(
                messages=messages,
                tools=tools,
                temperature=0.0
            )
            
            response_message = response["choices"][0]["message"]
            
            # Handle function calls
            if "tool_calls" in response_message:
                return self._handle_function_calls(session, messages, response_message)
            else:
                # Direct response without function calls
                return response_message["content"] or "Ik kon geen passend antwoord genereren."
                
        except Exception as e:
            logger.error(f"Error in AI processing: {str(e)}", exc_info=True)
            return f"Er is een fout opgetreden bij het verwerken van uw vraag: {str(e)}"
    
    def _handle_function_calls(
        self, 
        session: QuerySession, 
        messages: List[Dict[str, str]], 
        response_message: Dict[str, Any]
    ) -> str:
        """Handle AI function calls and return final response."""
        
        # Add assistant message with tool calls to conversation
        messages.append({
            "role": "assistant",
            "content": response_message.get("content"),
            "tool_calls": response_message["tool_calls"]
        })
        
        # Execute each function call
        for tool_call in response_message["tool_calls"]:
            try:
                function_name = tool_call["function"]["name"]
                arguments = json.loads(tool_call["function"]["arguments"])
                
                logger.info(f"Executing tool: {function_name}")
                
                # Execute tool through manager
                result_str = self.tool_manager.execute_function_call(function_name, arguments)
                result_data = json.loads(result_str)
                
                # Update session state if this was a source-gathering tool
                if function_name in ["get_legislation", "get_case_law"] and result_data["success"]:
                    tool_result = self.tool_manager.execute_tool(function_name, **arguments)
                    session.add_source(function_name, tool_result)
                    session.transition_to(WorkflowState.ACTIVE)
                
                # Add tool result to conversation
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": result_str
                })
                
            except Exception as e:
                logger.error(f"Error executing tool call: {str(e)}")
                # Add error result
                error_result = json.dumps({"success": False, "error": str(e)})
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": error_result
                })
        
        # Get final response after all function calls
        try:
            # Update system prompt
            messages[0]["content"] = self._build_system_prompt(session)
            
            final_response = self.llm_client.chat_completion(
                messages=messages,
                temperature=0.0
            )
            
            final_content = final_response["choices"][0]["message"]["content"]
            return final_content or "Ik kon geen antwoord genereren op basis van de beschikbare informatie."
            
        except Exception as e:
            logger.error(f"Error getting final response: {str(e)}")
            return f"Er is een fout opgetreden bij het genereren van het finale antwoord: {str(e)}"
    
    def _build_system_prompt(self, session) -> str:
        """Build system prompt with session context."""
        base_prompt = get_prompt_template("agent_system")
        
        # Add session context if there are sources
        if session.sources:
            context = "\n\nSESSION CONTEXT:\n"
            context += f"Verzamelde bronnen voor huidige vraag:\n"
            
            for tool_name, result in session.sources.items():
                if result.success:
                    context += f"- {tool_name}: ✓ Beschikbaar\n"
                    if result.data:
                        # Add first item as example
                        first_item = result.data[0] if isinstance(result.data, list) and result.data else str(result.data)
                        context += f"  Voorbeeld: {first_item[:100]}...\n"
                else:
                    context += f"- {tool_name}: ✗ Gefaald\n"
            
            context += "\nBij gebruikersbevestiging, gebruik generate_tax_answer met deze verzamelde bronnen."
            return base_prompt + context
        
        return base_prompt
    
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get information about the current session."""
        session = self.session_manager.get_session(self.session_id)
        if not session:
            return {"error": "No active session"}
        
        return {
            "session_id": session.session_id,
            "state": session.state.value,
            "question": session.current_question,
            "sources": session.get_source_summary(),
            "message_count": len(session.conversation_history),
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat()
        }
    
    def reset_session(self) -> str:
        """Reset the current session."""
        self.session_manager.delete_session(self.session_id)
        logger.info(f"Reset session: {self.session_id}")
        return "Sessie is gereset. U kunt een nieuwe vraag stellen."
    
    def add_tool(self, tool) -> None:
        """Add a new tool to the manager."""
        self.tool_manager.register(tool)
        logger.info(f"Added tool: {tool.name}")
    
    def list_available_tools(self) -> List[str]:
        """Get list of available tools."""
        return self.tool_manager.list_tools()
    
    def list_available_commands(self) -> List[str]:
        """Get list of available commands."""
        return self.command_processor.list_commands()
    
    def cleanup_old_sessions(self, hours: int = 24) -> int:
        """Clean up old sessions."""
        removed = self.session_manager.cleanup_old_sessions(hours)
        logger.info(f"Cleaned up {removed} old sessions")
        return removed