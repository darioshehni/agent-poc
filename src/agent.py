
"""Tax Chatbot Agent (dossier‑first orchestration).

Responsibilities (simple and explicit):
- Build the message list as [system] + full `dossier.conversation`.
- Call the LLM with function calling enabled and the tool schemas.
- Use ToolCallHandler to run tools and apply DossierPatch changes.
- Present tool outcomes to the user by composing assistant messages
  (titles list for retrieval, confirmation for removal).
- If the AnswerTool produced an answer, append it and return immediately.
- Otherwise, make a final LLM call for a natural assistant reply.

Tools are stateless and return DossierPatch (or answer text for AnswerTool).
The agent owns all user‑visible wording and conversation management.
Persistence is handled by the WebSocket server after sending the reply.
"""

import logging
from typing import Dict, Any, List

from src.config import OpenAIModels
from src.sessions import SessionManager
from src.llm import LlmChat
from src.tools.legislation_tool import LegislationTool
from src.tools.case_law_tool import CaseLawTool
from src.tools.answer_tool import AnswerTool
from src.tools.remove_sources_tool import RemoveSourcesTool
from src.context import ContextBuilder
from src.presenter import present_outcomes
from src.tool_calls import ToolCallHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaxAssistant:
    """Orchestrates chat between the user, tools, and the LLM.

    Responsibilities:
    - Maintain per-dossier state via SessionManager
    - Issue LLM calls with function-calling tools available
    - Delegate tool-call execution and context construction to helpers
    - Return the assistant's final response as a string
    """
    
    def __init__(
        self,
        dossier_id: str = "default",
    ):
        """
        Initialize the chatbot with clean architecture components.
        
        Args:
            dossier_id: Identifier for this dossier
        """
        
        # Core components
        self.llm_client = LlmChat()
        self.session_manager = SessionManager()
        # tools map and their schemas for function-calling
        self.tools: Dict[str, Any] = {}
        self.context_builder = ContextBuilder()
        self.tool_call_handler = None  # will be set after tools map is ready

        # Current session
        self.dossier_id = dossier_id
        
        # Initialize system
        self._setup_tools()
        
        logger.info(f"TaxChatbot initialized for dossier: {dossier_id}")
    
    def _setup_tools(self, leg_tool=None) -> None:
        """Register all available tools."""
        
        # Create tool instances
        answer_tool = AnswerTool(llm_client=self.llm_client)
        remove_tool = RemoveSourcesTool(llm_client=self.llm_client)
        leg_tool = LegislationTool()
        case_tool = CaseLawTool()

        self.tools = {
            leg_tool.name: leg_tool.execute,
            case_tool.name: case_tool.execute,
            answer_tool.name: answer_tool.execute,
            remove_tool.name: remove_tool.execute,
        }
        # Build function-calling schemas
        self.tool_schemas = [
            {"type": "function", "function": {"name": leg_tool.name, "description": leg_tool.description, "parameters": leg_tool.parameters_schema}},
            {"type": "function", "function": {"name": case_tool.name, "description": case_tool.description, "parameters": case_tool.parameters_schema}},
            {"type": "function", "function": {"name": answer_tool.name, "description": answer_tool.description, "parameters": answer_tool.parameters_schema}},
            {"type": "function", "function": {"name": remove_tool.name, "description": remove_tool.description, "parameters": remove_tool.parameters_schema}},
        ]
                # Initialize the handler once tools map is ready
        self.tool_call_handler = ToolCallHandler(self.tools)
        logger.info(f"Registered {len(self.tools)} tools")
    
    
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
            raise ValueError(f"Error processing message: {str(e)}")
            # return f"Er is een onverwachte fout opgetreden: {str(e)}. Probeer het opnieuw."
    
    async def _process_with_ai(self, dossier) -> str:
        """Process one user turn using LLM + tools, returning assistant text."""

        # Build system prompt
        system_prompt = self.context_builder.build_system_prompt(dossier)
        
        # Prepare user-visible conversation (curated) from dossier
        conversation = [
            {"role": "system", "content": system_prompt}
        ]
        conversation.extend(dossier.conversation)

        # Get available tools
        tools = self.tool_schemas
        
        try:
            # Make initial AI request
            llm_answer = await self.llm_client.chat(
                messages=conversation,
                model_name=OpenAIModels.GPT_4O.value,
                tools=tools,
                temperature=0.0,
            )
            response_message = {"content": llm_answer.answer, "tool_calls": llm_answer.tool_calls}
            
            # Handle function calls
            if response_message["tool_calls"]:
                # Execute tool calls and apply patches; handler returns list of outcomes
                conversation, outcomes = await self.tool_call_handler.handle(dossier, conversation, response_message)

                # Formulate user-visible assistant messages at the agent level (aggregate across patches)
                for msg in present_outcomes(outcomes):
                    dossier.add_conversation_assistant(msg)
                    conversation.append({"role": "assistant", "content": msg})

                # If AnswerTool produced an answer, append and return it directly
                answer_texts: List[str] = [
                    (out.get("data") or "").strip()
                    for out in outcomes
                    if out.get("function") == "generate_tax_answer" and isinstance(out.get("data"), str)
                ]
                answer_texts = [x for x in answer_texts if x]
                if answer_texts:
                    final_answer_text = answer_texts[-1]
                    dossier.add_conversation_assistant(final_answer_text)
                    return final_answer_text

                # Persist happens in the WebSocket server after sending the reply

                # Refresh system prompt with updated dossier context
                conversation[0]["content"] = self.context_builder.build_system_prompt(dossier)

                # Get final response from the LLM
                final_answer = await self.llm_client.chat(
                    messages=conversation,
                    model_name=OpenAIModels.GPT_4O.value,
                    temperature=0.0,
                )
                final_content = final_answer.answer
                return final_content or "Ik kon geen antwoord genereren op basis van de beschikbare informatie."
            else:
                # Direct response without function calls
                return response_message["content"] or "Ik kon geen passend antwoord genereren."
                
        except Exception as e:
            logger.error(f"Error in AI processing: {str(e)}", exc_info=True)
            raise ValueError(f"Error in AI processing: {str(e)}")
            #return f"Er is een fout opgetreden bij het verwerken van uw vraag: {str(e)}"
    
    # Context building and tool-call execution are delegated to helpers
    
    
    def get_dossier_info(self) -> Dict[str, Any]:
        """Get information about the current dossier."""
        dossier = self.session_manager.get_dossier(self.dossier_id)
        if not dossier:
            return {"error": "No active session"}
        
        info = {"dossier_id": dossier.dossier_id,
                "message_count": len(dossier.conversation),
                "selected_titles": dossier.selected_titles(),
                "unselected_titles": dossier.unselected_titles()}

        # Add selected vs unselected titles for quick confirmation UIs

        return info

    def reset_dossier(self) -> str:
        """Reset the current dossier."""
        self.session_manager.delete_dossier(self.dossier_id)
        logger.info(f"Reset dossier: {self.dossier_id}")
        return "Dossier is gereset. U kunt een nieuwe vraag stellen."

    def list_available_tools(self) -> List[str]:
        """Get list of available tools."""
        return list(self.tools.keys())

    
    # presenter moved to src/presenter.py
