"""
Tax Chatbot Agent with clean, extensible architecture.

This implementation focuses on:
- Clean separation of concerns
- Extensible tool system
- Proper state management
- Professional error handling
- Easy testing and maintenance

The agent now delegates prompt/context construction and tool-call execution to
dedicated helpers so this file remains an orchestration layer.
"""

import json
import logging
from typing import Dict, Any, List, Optional

from base import WorkflowState, ToolManager
from sessions import QuerySession, SessionManager
from llm import OpenAIClient, LLMClient
from tools.legislation_tool import LegislationTool
from tools.case_law_tool import CaseLawTool
from tools.answer_tool import AnswerTool
from tools.remove_sources_tool import RemoveSourcesTool
from context import ContextBuilder
from tool_calls import ToolCallHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaxChatbot:
    """Orchestrates chat between the user, tools, and the LLM.

    Responsibilities:
    - Maintain per-session state via SessionManager
    - Issue LLM calls with function-calling tools available
    - Delegate tool-call execution and context construction to helpers
    - Return the assistant's final response as a string
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
        self.context_builder = ContextBuilder()
        self.tool_call_handler = ToolCallHandler(self.tool_manager)
        
        # Current session
        self.session_id = session_id
        
        # Initialize system
        self._setup_tools()
        
        logger.info(f"TaxChatbot initialized for session: {session_id}")
    
    def _setup_tools(self) -> None:
        """Register all available tools."""
        
        # Create tool instances
        answer_tool = AnswerTool(
            llm_client=self.llm_client,
            session_manager=self.session_manager,
            session_id_getter=lambda: self.session_id,
        )
        remove_tool = RemoveSourcesTool(
            llm_client=self.llm_client,
            session_manager=self.session_manager,
            session_id_getter=lambda: self.session_id,
        )
        
        # Register tools
        self.tool_manager.register(LegislationTool())
        self.tool_manager.register(CaseLawTool())
        self.tool_manager.register(answer_tool)
        self.tool_manager.register(remove_tool)
        
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
            # Track the current question for downstream tools unless it's a short confirmation
            if not self._is_confirmation(user_input):
                session.current_question = user_input
            
            logger.info(f"Processing message for session {self.session_id}: {user_input[:50]}...")
            
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
        """Process one user turn using LLM + tools, returning assistant text."""

        # Build system prompt
        system_prompt = self.context_builder.build_system_prompt(session)
        
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
                # Execute tool calls, update session, extend messages
                self.tool_call_handler.handle(session, messages, response_message)
                # Persist dossier snapshot (best-effort)
                try:
                    self.session_manager.save_session(session)
                except Exception:
                    pass

                # Refresh system prompt with updated session context
                messages[0]["content"] = self.context_builder.build_system_prompt(session)

                # Get final response from the LLM
                final_response = self.llm_client.chat_completion(
                    messages=messages,
                    temperature=0.0
                )
                final_content = final_response["choices"][0]["message"].get("content")
                return final_content or "Ik kon geen antwoord genereren op basis van de beschikbare informatie."
            else:
                # Direct response without function calls
                return response_message["content"] or "Ik kon geen passend antwoord genereren."
                
        except Exception as e:
            logger.error(f"Error in AI processing: {str(e)}", exc_info=True)
            return f"Er is een fout opgetreden bij het verwerken van uw vraag: {str(e)}"
    
    # Context building and tool-call execution are delegated to helpers
    
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get information about the current session."""
        session = self.session_manager.get_session(self.session_id)
        if not session:
            return {"error": "No active session"}
        
        info = {
            "session_id": session.session_id,
            "state": session.state.value,
            "question": session.current_question,
            "sources": session.get_source_summary(),
            "message_count": len(session.conversation_history),
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
        }

        # Add selected vs unselected titles for quick confirmation UIs
        try:
            info["selected_titles"] = session.dossier.selected_titles()
            info["unselected_titles"] = session.dossier.unselected_titles()
        except Exception:
            info["selected_titles"] = []
            info["unselected_titles"] = []

        return info
    
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
    
    # Commands removed: agent handles conversational intents via LLM
    
    def cleanup_old_sessions(self, hours: int = 24) -> int:
        """Clean up old sessions."""
        removed = self.session_manager.cleanup_old_sessions(hours)
        logger.info(f"Cleaned up {removed} old sessions")
        return removed

    # --- Internal helpers ---
    def _is_confirmation(self, text: str) -> bool:
        """Heuristic: detect short yes/no confirmations to avoid overwriting the question.

        Returns True for inputs like 'ja', 'nee', 'yes', 'no', 'klopt', 'correct',
        and short variants like 'ja, klopt'. This keeps the original tax question
        intact across the confirm → answer phase.
        """
        t = (text or "").strip().lower()
        if not t:
            return False
        keywords = {"ja", "nee", "yes", "no", "klopt", "correct"}
        if t in keywords:
            return True
        # Short affirmations containing a keyword (<= 3 words)
        words = [w.strip(",.!?") for w in t.split()]
        if len(words) <= 3 and any(w in keywords for w in words):
            return True
        return False
