
"""TESS Chatbot Agent (dossier‑first orchestration).

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

from src.sessions import get_or_create_dossier, save_dossier
from src.llm import LlmChat, LlmAnswer
from src.tools.legislation_tool import LegislationTool
from src.tools.case_law_tool import CaseLawTool
from src.tools.answer_tool import AnswerTool
from src.tools.remove_sources_tool import RemoveSourcesTool
from src.tools.restore_sources_tool import RestoreSourcesTool
from src.presenter import present_outcomes
from src.tool_calls import ToolCallHandler
from src.config.models import Dossier, DossierPatch, ToolResult
from src.config.prompts import AGENT_SYSTEM_PROMPT
from src.config.config import OpenAIModels


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _apply_patches_to_in_memory_dossier(dossier: Dossier, tool_results: list[ToolResult]) -> Dossier:
    """Apply all DossierPatch objects from tool results to update the dossier.
    
    Args:
        dossier: The dossier to update
        tool_results: List of tool execution results that may contain patches
        
    Returns:
        Updated dossier with all patches applied
    """
    for output in tool_results:
        patch = output.patch
        if not patch:
            continue
        if isinstance(patch, DossierPatch):
            dossier = patch.apply(dossier=dossier)
    return dossier


class TESS:
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
        """Initialize the TESS agent with a specific dossier.
        
        Creates or loads the dossier, initializes the LLM client, and sets up
        all available tools for the conversation.
        
        Args:
            dossier_id: Unique identifier for the dossier. If empty, loads/creates
                       a dossier with this ID, or generates new ID if not found.
        """
        self.dossier = get_or_create_dossier(dossier_id=dossier_id)
        self.dossier_id = self.dossier.dossier_id

        self.llm_client = LlmChat()
        self.tool_call_handler = self._setup_tool_call_handler()

        logger.info(f"Initialized TESS for dossier {self.dossier_id}")

    def _setup_tool_call_handler(self) -> ToolCallHandler:
        """Initialize and register all available tools for the agent.
        
        Creates instances of all tools, builds the tools mapping for execution,
        and constructs function calling schemas for the LLM.
        
        Returns:
            Configured ToolCallHandler with all tools registered
        """

        # Create tool instances
        answer_tool = AnswerTool(llm_client=self.llm_client)
        remove_tool = RemoveSourcesTool(llm_client=self.llm_client)
        restore_tool = RestoreSourcesTool(llm_client=self.llm_client)
        leg_tool = LegislationTool()
        case_tool = CaseLawTool()

        tools = {
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
        logger.info(f"Registered {len(tools)} tools")
        return ToolCallHandler(tools)


    async def process_message(self, user_input: str) -> str:
        """Main entry point for processing user messages.
        
        Processes a user message through the complete TESS pipeline:
        1. Adds user message to dossier conversation
        2. Calls LLM with available tools 
        3. Executes any requested tool calls
        4. Applies patches to update dossier state
        5. Generates user-facing response
        6. Persists updated dossier
        
        Args:
            user_input: The user's message to process
            
        Returns:
            Assistant's response string
            
        Raises:
            ValueError: If message processing fails
        """

        try:
            dossier = self.dossier
            dossier.add_conversation_user(content=user_input)

            logger.info(f"Processing message for dossier {self.dossier_id}: {user_input[:50]}...")
            response = await self._process_with_ai(dossier=dossier)
            return response
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            raise ValueError(f"Error processing message: {str(e)}")
            # return f"Er is een onverwachte fout opgetreden: {str(e)}. Probeer het opnieuw."

    async def _process_with_ai(self, dossier: Dossier) -> str:
        """Process one conversation turn using LLM with tool calling support.
        
        Builds the message context from dossier conversation, calls LLM with
        available tools, executes any tool calls, and generates the final response.
        
        Args:
            dossier: Current dossier with conversation and sources
            
        Returns:
            Generated assistant response text
        """

        system_prompt = [{"role": "system", "content": AGENT_SYSTEM_PROMPT}]
        conversation = dossier.conversation

        logger.info(f"AGENT: last_msg={conversation[-1]['content'][:60]}")

        logger.info("AGENT: chat request")
        llm_answer: LlmAnswer = await self.llm_client.chat(
            messages=system_prompt + conversation,
            model_name=OpenAIModels.GPT_4O.value,
            tools=self.tool_schemas,
            temperature=0.0,
        )

        # Handle function calls
        if llm_answer.tool_calls:
            logger.info(f"AGENT: tool_calls: {[tool['function']['name'] for tool in llm_answer.tool_calls]}")
            # Execute tool calls.
            tool_results = await self.tool_call_handler.run(
                dossier=dossier,
                tool_calls=llm_answer.tool_calls,
            )
            dossier = _apply_patches_to_in_memory_dossier(dossier=dossier, tool_results=tool_results)

            # Explain tool outcomes to the user.
            assistant_response = present_outcomes(tool_results=tool_results)
        else:
            # Direct response without function calls
            logger.info("AGENT: no tool_calls: returning direct content.")
            assistant_response = llm_answer.answer

        dossier.add_conversation_assistant(content=assistant_response)
        save_dossier(dossier=dossier)
        return assistant_response
