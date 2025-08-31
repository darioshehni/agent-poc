
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
import re
import json
from typing import Any

from src.config.config import OpenAIModels
from src.sessions import get_or_create_dossier, save_dossier
from src.llm import LlmChat, LlmAnswer
from src.tools.legislation_tool import LegislationTool
from src.tools.case_law_tool import CaseLawTool
from src.tools.answer_tool import AnswerTool
from src.tools.remove_sources_tool import RemoveSourcesTool
from src.tools.restore_sources_tool import RestoreSourcesTool
from src.presenter import present_outcomes
from src.tool_calls import ToolCallHandler
from src.config.models import Dossier
from src.config.prompts import AGENT_SYSTEM_PROMPT

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaxAssistant:
    """Orchestrates chat between the user, tools, and the LLM.

    Responsibilities:
    - Maintain per-dossier state via Dossier object
    - Issue LLM calls with function-calling tools available
    - Delegate tool-call execution and context construction to helpers
    - Return the assistant's final response as a string
    """
    
    def __init__(
        self,
        dossier_id: str = "",
    ):
        """
        Initialize the chatbot with clean architecture components.
        
        Args:
            dossier_id: Identifier for this dossier
        """
        self.dossier_id = dossier_id
        self.dossier: Dossier = get_or_create_dossier(dossier_id=dossier_id)
        self.llm_client = LlmChat()

        self.tools: dict[str, Any] = {}
        self.tool_call_handler = None  # will be set after tools map is ready
        self._setup_tools()
        
        logger.info(f"TESS initialized for dossier: {dossier_id}")
    
    def _setup_tools(self) -> None:
        """Register all available tools."""
        
        # Create tool instances
        answer_tool = AnswerTool(llm_client=self.llm_client)
        remove_tool = RemoveSourcesTool(llm_client=self.llm_client)
        restore_tool = RestoreSourcesTool(llm_client=self.llm_client)
        leg_tool = LegislationTool()
        case_tool = CaseLawTool()

        self.tools = {
            leg_tool.name: leg_tool.execute,
            case_tool.name: case_tool.execute,
            answer_tool.name: answer_tool.execute,
            remove_tool.name: remove_tool.execute,
            restore_tool.name: restore_tool.execute,
        }
        # Build function-calling schemas
        self.tool_schemas = [
            {"type": "function", "function": {"name": leg_tool.name, "description": leg_tool.description, "parameters": leg_tool.parameters_schema}},
            {"type": "function", "function": {"name": case_tool.name, "description": case_tool.description, "parameters": case_tool.parameters_schema}},
            {"type": "function", "function": {"name": answer_tool.name, "description": answer_tool.description, "parameters": answer_tool.parameters_schema}},
            {"type": "function", "function": {"name": remove_tool.name, "description": remove_tool.description, "parameters": remove_tool.parameters_schema}},
            {"type": "function", "function": {"name": restore_tool.name, "description": restore_tool.description, "parameters": restore_tool.parameters_schema}},
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
            self.dossier.add_conversation_user(content=user_input)
            
            logger.info(f"Processing message for dossier {self.dossier_id}: {user_input[:50]}...")

            response = await self._process_with_ai(dossier=self.dossier)
            
            # Add assistant response to dossier conversation
            self.dossier.add_conversation_assistant(response)
            save_dossier(dossier=self.dossier)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            raise ValueError(f"Error processing message: {str(e)}")
            # return f"Er is een onverwachte fout opgetreden: {str(e)}. Probeer het opnieuw."
    
    async def _process_with_ai(self, dossier: Dossier) -> str:
        """Process one user turn using LLM + tools, returning assistant text."""

        system_prompt = [{"role": "system", "content": AGENT_SYSTEM_PROMPT}]
        conversation = dossier.conversation

        tools = self.tool_schemas
        logger.info(f"AGENT: conversation_len={len(conversation)} last_user={(conversation[-1]['content'][:60] if conversation else '')}")

        # Agent-level routing: detect explicit removal request and call tool directly
        try:
            last_user = (conversation[-1]["content"] if conversation else "").strip().lower()
        except Exception:
            last_user = ""
        removal_patterns = [
            r"\bverwijder\b",
            r"\bniet nodig\b",
            r"\bhaal (het|de|die)?\s*weg\b",
            r"\bgeen\s+(ecli|jurisprudentie|rechtspraak)\b",
        ]
        is_removal_intent = bool(last_user and any(re.search(p, last_user) for p in removal_patterns))
        if is_removal_intent and dossier.selected_titles():
            logger.info("AGENT: direct removal intent detected; invoking remove_sources tool")
            synthetic_calls = [{
                "function": {"name": "remove_sources", "arguments": json.dumps({"query": last_user})}
            }]
            tool_calls = await self.tool_call_handler.run(dossier=dossier, tool_calls=synthetic_calls)
            outcome_messages = present_outcomes(tool_calls, dossier=dossier)
            if outcome_messages:
                return "\n\n".join(outcome_messages)
            return "Ik heb uw selectie aangepast. Wilt u de huidige bronnen controleren?"

        try:
            logger.info("AGENT: chat request (tools enabled)")
            llm_answer: LlmAnswer = await self.llm_client.chat(
                messages=system_prompt + conversation,
                model_name=OpenAIModels.GPT_4O.value,
                tools=tools,
                temperature=0.0,
            )
            response_message = {"content": llm_answer.answer, "tool_calls": llm_answer.tool_calls}
            
            # Handle function calls
            if response_message["tool_calls"]:
                logger.info(f"AGENT: tool_calls received: {[c.get('function',{}).get('name') for c in llm_answer.tool_calls]}")
                # Execute tool calls with parsed arguments from the model
                tool_calls = await self.tool_call_handler.run(
                    dossier=dossier,
                    tool_calls=llm_answer.tool_calls,
                )

                # Formulate user-visible assistant message(s) (retrieval/removal confirmations)
                outcome_messages = present_outcomes(tool_calls, dossier=dossier)
                if outcome_messages:
                    # Return these to the user now; do not proceed to final LLM answer
                    # The WebSocket server expects a single string, so join if multiple
                    combined = "\n\n".join(outcome_messages)
                    logger.info("AGENT: returning presenter messages (retrieval/removal)")
                    return combined

                # If AnswerTool produced an answer, return it directly
                for tool_call in tool_calls:
                    if tool_call["function"] == "generate_tax_answer":
                        return tool_call["data"]

                # If no outcome messages and no AnswerTool, provide a safe fallback
                logger.info("AGENT: tools executed but no presenter messages; returning fallback")
                return "Ik heb bronnen verzameld, maar kon geen titels presenteren. Kunt u uw vraag iets aanscherpen?"
            else:
                # Direct response without function calls
                logger.info("AGENT: no tool_calls; returning direct content")
                return response_message["content"] or "Ik kon geen passend antwoord genereren."

        except Exception as e:
            logger.error(f"Error in AI processing: {str(e)}")
            raise ValueError(f"Error in AI processing: {str(e)}")
            #return f"Er is een fout opgetreden bij het verwerken van uw vraag: {str(e)}"
