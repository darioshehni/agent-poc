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
                    "description": "The original tax question from the user. This should also contain all context from the conversation that is relevant or helpful for answering the question. Including context where the user mentions which documents are relevant or not."
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
            q = (question or "").strip()
            if not q:
                raise ValueError("Question cannot be empty")
                # return ToolResult(success=False, data=None, error_message="Question cannot be empty")
            # Require at least some sources available (selected preferred; else fallback below)
                # return ToolResult(
                #     success=False,
                #     data=None,
                #     error_message="No dossier sources available to generate an answer"
                # )

            # Gather source texts: prefer selected, else all
            selected = dossier.selected_texts()
            selection_present = (
                isinstance(selected, dict)
                and ((selected.get("legislation") or selected.get("case_law")))
            )
            if selection_present:
                legislation_texts = selected.get("legislation", [])
                case_law_texts = selected.get("case_law", [])
            else:
                all_texts = dossier.all_texts()
                legislation_texts = all_texts.get("legislation", [])
                case_law_texts = all_texts.get("case_law", [])

            # Format sources for the prompt
            legislation_context = self._format_sources(sources=legislation_texts, category="WETGEVING")
            case_law_context = self._format_sources(sources=case_law_texts, category="JURISPRUDENTIE")
            
            # Create the prompt using template
            prompt = fill_prompt_template(
                get_prompt_template("answer_generation"),
                question=q,
                legislation=legislation_context,
                case_law=case_law_context
            )
            
            llm_answer: LlmAnswer = await self.llm_client.chat(
                messages=prompt,
                model_name=OpenAIModels.GPT_4O_MINI.value,
                temperature=0.0,
            )
            answer = llm_answer.answer
            
            if not answer:
                raise ValueError("LLM generated empty response")
                # return ToolResult(
                #     success=False,
                #     data=None,
                #     error_message="LLM generated empty response"
                # )
            
            # Return answer text; agent will append it to the conversation
            result = ToolResult(success=True, data=answer.strip())
            
            logger.info("Answer generated successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error generating answer: {str(e)}", exc_info=True)
            return ToolResult(
                success=False,
                data=None,
                error_message=f"Fout bij het genereren van het antwoord: {str(e)}"
            )

    def _format_sources(self, sources: List[str], category: str) -> str:
        """Format a list of source texts for inclusion in the prompt."""
        if not sources:
            return f"{category}:\nGeen {category.lower()} beschikbaar.\n"

        lines = [f"{category}:"]
        for i, text in enumerate(sources, 1):
            text_clean = (text or "").strip()
            if text_clean:
                lines.append(f"{i}. {text_clean}")
        lines.append("")
        return "\n".join(lines)
