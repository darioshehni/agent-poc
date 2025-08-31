"""
Answer generation tool with clean architecture.

This tool generates a comprehensive answer for a tax question using the current
dossier as its authoritative context. Large source texts never enter the chat
transcript; they remain solely in the dossier and are fed to the LLM only at
answer time via the prompt constructed here.
"""

from typing import Dict, Any, List
import logging

from src.models import ToolResult
from src.llm import LlmChat, LlmAnswer
from src.prompts import get_prompt_template, fill_prompt_template
from src.models import Dossier
from src.config import OpenAIModels

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
        self.llm_client = llm_client
    
    @property
    def name(self) -> str:
        return "generate_tax_answer"
    
    @property
    def description(self) -> str:
        return "Generate a comprehensive answer to a tax question using dossier sources (legislation and case law)"
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Original tax question from the user"
                }
            },
            "required": ["question"]
        }
    
    async def execute(self, question: str, dossier: Dossier) -> ToolResult:
        """
        Generate a comprehensive tax answer using sources from the session dossier.
        
        This tool:
        1. Validates input sources
        2. Creates a structured prompt with sources
        3. Uses LLM to generate comprehensive answer
        4. Validates and formats the response
        """
        
        try:
            logger.info(f"Generating answer for question: {question}...")
            
            # Require the model to pass the question explicitly
            question = question.strip()
            if not question:
                raise ValueError("Question cannot be empty")

            legislations = dossier.get_selected_legislation()
            case_laws = dossier.get_selected_case_law()

            # Format sources for the prompt
            legislation_context = self._format_sources(sources=legislations, category="WETGEVING")
            case_law_context = self._format_sources(sources=case_laws, category="JURISPRUDENTIE")
            
            # Create the prompt using template
            prompt = fill_prompt_template(
                get_prompt_template("answer_generation"),
                question=question,
                legislation=legislation_context,
                case_law=case_law_context
            )
            print(prompt)
            
            llm_answer: LlmAnswer = await self.llm_client.chat(
                messages=prompt,
                model_name=OpenAIModels.GPT_4O_MINI.value,
                temperature=0.0,
            )
            answer = llm_answer.answer
            print(answer)
            
            if not answer:
                raise ValueError("LLM generated empty response")
            
            # Return answer text; agent will append it to the conversation
            result = ToolResult(success=True, data=answer.strip())
            
            logger.info("Answer generated successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error generating answer: {str(e)}", exc_info=True)
            raise ValueError(f"Error generating answer: {str(e)}")


    def _format_sources(self, sources: List[any], category: str) -> str:
        """Format a list of source texts for inclusion in the prompt."""
        if not sources:
            return f"{category}:\nGeen {category.lower()} beschikbaar.\n"

        formatted_context = f"{category}:\n"
        for i, source in enumerate(sources, 1):
                formatted_context += f"{i}:\n{source.title}\n{source.content}\n\n"

        return formatted_context
