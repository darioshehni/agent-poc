"""
Answer generation tool with clean architecture.

This tool generates a comprehensive answer for a tax query using the current
dossier as its authoritative context. Large source texts never enter the chat
transcript; they remain solely in the dossier and are fed to the LLM only at
answer time via the prompt constructed here.
"""

from typing import Any
import logging

from src.llm import LlmChat, LlmAnswer
from src.config.prompts import get_prompt_template, fill_prompt_template
from src.config.models import Dossier
from src.config.config import OpenAIModels

logger = logging.getLogger(__name__)


class AnswerTool:
    """Generate comprehensive tax answers using the session dossier.

    The tool pulls its context (legislation and case law) from the dossier
    associated with the active session. Large source texts never enter the chat
    transcript; they remain solely in the dossier and are fed to the LLM only
    at answer time via the prompt constructed here.
    """

    def __init__(
        self,
        llm_client: LlmChat
    ):
        """Initialize the answer generation tool.
        
        Args:
            llm_client: LLM client for generating comprehensive tax answers
        """
        self.llm_client = llm_client
    
    @property
    def name(self) -> str:
        return "generate_tax_answer"
    
    @property
    def description(self) -> str:
        return "Generate an answer to a tax query using dossier sources (legislation and case law)"
    
    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Original tax query from the user. Include any context that could be relevant or helpful for answering correctly."
                }
            },
            "required": ["query"]
        }
    
    async def execute(self, query: str, dossier: Dossier) -> dict:
        """Generate a comprehensive tax answer using selected sources from the dossier.
        
        Uses the currently selected legislation and case law to build a structured
        prompt for comprehensive answer generation. Sources are formatted and fed
        to the LLM only at answer time, keeping them out of the conversation transcript.
        
        Args:
            query: Original tax question from the user
            dossier: Current dossier containing selected sources
            
        Returns:
            Dictionary with 'success' and 'message' keys. The message contains
            the generated comprehensive answer.
            
        Raises:
            ValueError: If query is empty or LLM generation fails
        """
        
        try:
            logger.info(f"Generating answer for query: {query}...")
            
            # Require the model to pass the query explicitly
            query = query.strip()
            if not query:
                raise ValueError("Query cannot be empty")

            legislations = dossier.get_selected_legislation()
            case_laws = dossier.get_selected_case_law()

            # Format sources for the prompt
            legislation_context = self._format_sources(sources=legislations)
            case_law_context = self._format_sources(sources=case_laws)
            
            # Create the prompt using template
            prompt = fill_prompt_template(
                get_prompt_template("answer_generation"),
                query=query,
                legislation=legislation_context,
                case_law=case_law_context
            )

            llm_answer: LlmAnswer = await self.llm_client.chat(
                messages=prompt,
                model_name=OpenAIModels.GPT_4O.value,
                temperature=0.0,
            )
            answer = llm_answer.answer

            if not answer:
                raise ValueError("LLM generated empty response")
            
            # Return answer text. Agent will append it to the conversation
            logger.info("Answer generated successfully")
            return {"success": True, "message": answer.strip()}

            
        except Exception as e:
            logger.error(f"Error generating answer: {str(e)}", exc_info=True)
            raise ValueError(f"Error generating answer: {str(e)}")


    def _format_sources(self, sources: list[any]) -> str:
        """Format source list for inclusion in the answer generation prompt.
        
        Args:
            sources: List of Legislation or CaseLaw objects
            
        Returns:
            Formatted string with numbered sources, or default message if empty
        """
        if not sources:
            return "Geen bronnen beschikbaar.\n"

        formatted_context = ""
        for i, source in enumerate(sources, 1):
                formatted_context += f"{i}:\n{source.title}\n{source.content}\n\n"

        return formatted_context
