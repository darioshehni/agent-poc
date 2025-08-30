"""
Answer generation tool with clean architecture.

This tool generates a comprehensive answer for a tax question using the current
session's dossier as its authoritative context. It does not rely on large
source texts being present in the conversation. Instead, it retrieves the
legislation and case law content directly from the SessionManager using the
current dossier_id supplied by the agent at runtime.
"""

from typing import Dict, Any, List, Callable
import logging

from src.base import BaseTool, ToolResult
from src.llm import LlmChat
from src.prompts import get_prompt_template, fill_prompt_template
from src.sessions import SessionManager

logger = logging.getLogger(__name__)


class AnswerTool(BaseTool):
    """Generate comprehensive tax answers using the session dossier.

    The tool pulls its context (legislation and case law) from the dossier
    associated with the active session. Large source texts never enter the chat
    transcript; they remain solely in the dossier and are fed to the LLM only
    at answer time via the prompt constructed here.
    """

    def __init__(
        self,
        llm_client: Any = None,
        session_manager: 'SessionManager' = None,
        dossier_id_getter: Callable[[], str] | None = None,
        model_name_getter: Callable[[], str] | None = None,
    ):
        # Expect an async LlmChat client
        self.llm_client = llm_client
        # Session access for dossier retrieval
        self.session_manager = session_manager
        self.dossier_id_getter = dossier_id_getter or (lambda: "default")
        self.model_name_getter = model_name_getter or (lambda: "gpt-4o-mini")
    
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
                    "description": "The original tax question from the user"
                }
            },
            "required": ["question"]
        }
    
    async def execute(self, question: str, legislation: List[str] = None, case_law: List[str] = None, **_: Any) -> ToolResult:
        """
        Generate a comprehensive tax answer using sources from the session dossier.
        
        This tool:
        1. Validates input sources
        2. Creates a structured prompt with sources
        3. Uses LLM to generate comprehensive answer
        4. Validates and formats the response
        """
        
        try:
            logger.info(f"Generating answer for question: {question[:100]}...")
            
            # If question not provided by the LLM tool call, fall back to last user message
            q = (question or "").strip()
            if not q and self.session_manager is not None:
                try:
                    dossier_id = self.dossier_id_getter()
                    dossier = self.session_manager.get_dossier(dossier_id)
                    if dossier and dossier.conversation:
                        for msg in reversed(dossier.conversation):
                            if isinstance(msg, dict) and msg.get("role") == "user":
                                content = (msg.get("content") or "").strip()
                                if content:
                                    q = content
                                    break
                except Exception:
                    pass
            if not q:
                return ToolResult(False, None, "Question cannot be empty")

            # Retrieve dossier-based sources
            legislation_texts: List[str] = []
            case_law_texts: List[str] = []
            try:
                if self.session_manager is not None:
                    dossier_id = self.dossier_id_getter()
                    dossier = self.session_manager.get_dossier(dossier_id)
                    if dossier:
                        # Prefer selected items if any, else use all collected
                        sel = dossier.selected_texts()
                        has_sel = (
                            isinstance(sel, dict)
                            and (
                                ("legislation" in sel and sel["legislation"]) or
                                ("case_law" in sel and sel["case_law"])
                            )
                        )
                        if has_sel:
                            legislation_texts = sel["legislation"] if "legislation" in sel else []
                            case_law_texts = sel["case_law"] if "case_law" in sel else []
                        else:
                            all_tx = dossier.all_texts()
                            legislation_texts = all_tx["legislation"] if "legislation" in all_tx else []
                            case_law_texts = all_tx["case_law"] if "case_law" in all_tx else []
            except Exception as e:
                logger.warning(f"Could not retrieve dossier for answer tool: {e}")

            if not legislation_texts and not case_law_texts:
                return ToolResult(
                    success=False,
                    data=None,
                    error_message="No dossier sources available to generate an answer"
                )
            
            # Format sources for the prompt
            legislation_text = self._format_sources(legislation_texts, "WETGEVING")
            case_law_text = self._format_sources(case_law_texts, "JURISPRUDENTIE")
            
            # Create the prompt using template
            prompt = fill_prompt_template(
                get_prompt_template("answer_generation"),
                question=q,
                legislation=legislation_text,
                case_law=case_law_text
            )
            
            # Generate answer using async LLM client
            answer_obj = await self.llm_client.chat(
                messages=prompt,
                model_name=self.model_name_getter(),
                temperature=0.0,
            )
            answer = answer_obj.answer
            
            if not answer or not answer.strip():
                return ToolResult(
                    success=False,
                    data=None,
                    error_message="LLM generated empty response"
                )
            
            # Create successful result with metadata
            result = ToolResult(
                success=True,
                data=answer.strip(),
                metadata={
                    "question": q,
                    "legislation_count": len(legislation_texts),
                    "case_law_count": len(case_law_texts),
                }
            )
            
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
        """Format a list of sources for inclusion in the prompt."""
        if not sources:
            return f"{category}:\nGeen {category.lower()} beschikbaar.\n"
        
        formatted = f"{category}:\n"
        for i, source in enumerate(sources, 1):
            # Clean up the source text
            source_clean = source.strip()
            if source_clean:
                formatted += f"{i}. {source_clean}\n"
        
        return formatted
    
    def validate_sources(self, legislation: List[str], case_law: List[str]) -> List[str]:
        """Validate source quality and return list of issues."""
        issues = []
        
        # Check for empty sources
        if not legislation and not case_law:
            issues.append("No sources provided")
        
        # Check for very short sources (likely incomplete)
        for i, leg in enumerate(legislation):
            if len(leg.strip()) < 10:
                issues.append(f"Legislation source {i+1} is too short")
        
        for i, case in enumerate(case_law):
            if len(case.strip()) < 10:
                issues.append(f"Case law source {i+1} is too short")
        
        return issues
    
    def generate_answer_with_validation(self, question: str) -> ToolResult:
        """Generate answer with a basic validation check using dossier sources."""
        # Pull sources from dossier then validate and execute
        leg: List[str] = []
        cas: List[str] = []
        try:
            if self.session_manager is not None:
                dossier_id = self.dossier_id_getter()
                dossier = self.session_manager.get_dossier(dossier_id)
                if dossier:
                    leg = [getattr(x, 'content', str(x)) for x in dossier.legislation]
                    cas = [getattr(x, 'content', str(x)) for x in dossier.case_law]
        except Exception as e:
            logger.warning(f"Validation: could not read dossier: {e}")

        validation_issues = self.validate_sources(leg, cas)
        if validation_issues:
            logger.warning(f"Source validation issues: {validation_issues}")
        result = self.execute(question)
        if result.success and validation_issues:
            result.metadata["validation_warnings"] = validation_issues
        return result
    
    def generate_answer(self, question: str) -> str:
        """Legacy helper to generate an answer using dossier context."""
        result = self.execute(question)
        if result.success:
            return result.data
        return f"Error: {result.error_message}"
