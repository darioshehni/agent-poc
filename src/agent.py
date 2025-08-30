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

import logging
from typing import Dict, Any, List, Optional

from src.base import ToolManager
from src.sessions import SessionManager
from src.llm import LlmChat
from src.tools.legislation_tool import LegislationTool
from src.tools.case_law_tool import CaseLawTool
from src.tools.answer_tool import AnswerTool
from src.tools.remove_sources_tool import RemoveSourcesTool
from src.context import ContextBuilder
from src.tool_calls import ToolCallHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaxChatbot:
    """Orchestrates chat between the user, tools, and the LLM.

    Responsibilities:
    - Maintain per-dossier state via SessionManager
    - Issue LLM calls with function-calling tools available
    - Delegate tool-call execution and context construction to helpers
    - Return the assistant's final response as a string
    """
    
    def __init__(
        self,
        llm_client: Optional[LlmChat] = None,
        dossier_id: str = "default",
        model_name: str = "gpt-4o-mini",
    ):
        """
        Initialize the chatbot with clean architecture components.
        
        Args:
            dossier_id: Identifier for this dossier
        """
        
        # Core components
        self.llm_client = llm_client or LlmChat()
        self.session_manager = SessionManager()
        self.tool_manager = ToolManager()
        self.context_builder = ContextBuilder()
        self.tool_call_handler = ToolCallHandler(self.tool_manager)
        self.model_name = model_name
        
        # Current session
        self.dossier_id = dossier_id
        
        # Initialize system
        self._setup_tools()
        
        logger.info(f"TaxChatbot initialized for dossier: {dossier_id}")
    
    def _setup_tools(self) -> None:
        """Register all available tools."""
        
        # Create tool instances
        answer_tool = AnswerTool(
            llm_client=self.llm_client,
            session_manager=self.session_manager,
            dossier_id_getter=lambda: self.dossier_id,
            model_name_getter=lambda: self.model_name,
        )
        remove_tool = RemoveSourcesTool(
            llm_client=self.llm_client,
            session_manager=self.session_manager,
            dossier_id_getter=lambda: self.dossier_id,
            model_name_getter=lambda: self.model_name,
        )
        
        # Register tools (pass session for dossier updates and unified messaging)
        self.tool_manager.register(LegislationTool(
            session_manager=self.session_manager,
            dossier_id_getter=lambda: self.dossier_id,
        ))
        self.tool_manager.register(CaseLawTool(
            session_manager=self.session_manager,
            dossier_id_getter=lambda: self.dossier_id,
        ))
        self.tool_manager.register(answer_tool)
        self.tool_manager.register(remove_tool)
        
        # Validate all tools
        validation_errors = self.tool_manager.validate_tools()
        if validation_errors:
            logger.warning(f"Tool validation issues: {validation_errors}")
        
        logger.info(f"Registered {len(self.tool_manager.list_tools())} tools")
    
    
    async def process_message(self, user_input: str) -> str:
        """
        Main entry point for processing user messages.
        
        This method:
        1. Gets or creates dossier
        2. Checks for commands first
        3. Processes with AI if not a command
        4. Updates workflow state
        5. Returns appropriate response
        """
        
        try:
            # Get dossier
            dossier = self.session_manager.get_or_create_dossier(self.dossier_id)
            
            # Add user message to curated dossier conversation
            dossier.add_conversation_user(user_input)
            
            logger.info(f"Processing message for dossier {self.dossier_id}: {user_input[:50]}...")
            

            # Process with AI
            response = await self._process_with_ai(dossier)
            
            # Add response to curated dossier conversation
            dossier.add_conversation_assistant(response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            return f"Er is een onverwachte fout opgetreden: {str(e)}. Probeer het opnieuw."
    
    async def _process_with_ai(self, dossier) -> str:
        """Process one user turn using LLM + tools, returning assistant text."""

        # Build system prompt
        system_prompt = self.context_builder.build_system_prompt(dossier)
        
        # Prepare user-visible conversation (curated) from dossier
        conversation = [
            {"role": "system", "content": system_prompt}
        ]
        # Only include curated user-visible messages
        for msg in dossier.conversation:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                conversation.append({"role": msg["role"], "content": msg["content"]})
        
        # Get available tools
        tools = self.tool_manager.get_function_schemas()
        
        try:
            # Make initial AI request
            llm_answer = await self.llm_client.chat(
                messages=conversation,
                model_name=self.model_name,
                tools=tools,
                temperature=0.0,
            )
            response_message = {"content": llm_answer.answer, "tool_calls": llm_answer.tool_calls}
            
            # Handle function calls
            if response_message["tool_calls"]:
                # Execute tool calls, update dossier, extend conversation
                await self.tool_call_handler.handle(dossier, conversation, response_message)
                # Persist dossier snapshot (best-effort)
                try:
                    self.session_manager.save_dossier(dossier)
                except Exception:
                    pass

                # Refresh system prompt with updated dossier context
                conversation[0]["content"] = self.context_builder.build_system_prompt(dossier)

                # Get final response from the LLM
                final_answer = await self.llm_client.chat(
                    messages=conversation,
                    model_name=self.model_name,
                    temperature=0.0,
                )
                final_content = final_answer.answer
                return final_content or "Ik kon geen antwoord genereren op basis van de beschikbare informatie."
            else:
                # Direct response without function calls
                return response_message["content"] or "Ik kon geen passend antwoord genereren."
                
        except Exception as e:
            logger.error(f"Error in AI processing: {str(e)}", exc_info=True)
            return f"Er is een fout opgetreden bij het verwerken van uw vraag: {str(e)}"
    
    # Context building and tool-call execution are delegated to helpers
    
    
    def get_dossier_info(self) -> Dict[str, Any]:
        """Get information about the current dossier."""
        dossier = self.session_manager.get_dossier(self.dossier_id)
        if not dossier:
            return {"error": "No active session"}
        
        info = {
            "dossier_id": dossier.dossier_id,
            "message_count": len(dossier.conversation),
            "created_at": dossier.created_at.isoformat(),
            "updated_at": dossier.updated_at.isoformat(),
        }

        # Add selected vs unselected titles for quick confirmation UIs
        try:
            info["selected_titles"] = dossier.selected_titles()
            info["unselected_titles"] = dossier.unselected_titles()
        except Exception:
            info["selected_titles"] = []
            info["unselected_titles"] = []

        return info

    def reset_dossier(self) -> str:
        """Reset the current dossier."""
        self.session_manager.delete_dossier(self.dossier_id)
        logger.info(f"Reset dossier: {self.dossier_id}")
        return "Dossier is gereset. U kunt een nieuwe vraag stellen."

    def list_available_tools(self) -> List[str]:
        """Get list of available tools."""
        return self.tool_manager.list_tools()

    def cleanup_old_sessions(self, hours: int = 24) -> int:
        """Clean up old sessions."""
        removed = self.session_manager.cleanup_old_sessions(hours)
        logger.info(f"Cleaned up {removed} old sessions")
        return removed
