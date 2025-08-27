"""
Answer generation tool with clean architecture.
"""

from typing import Dict, Any, List
import logging

try:
    from ..base import BaseTool, ToolResult
    from ..llm import OpenAIClient
    from ..prompts import get_prompt_template, fill_prompt_template
except ImportError:
    from base import BaseTool, ToolResult
    from llm import OpenAIClient
    from prompts import get_prompt_template, fill_prompt_template

logger = logging.getLogger(__name__)


class AnswerTool(BaseTool):
    """Tool for generating comprehensive tax answers using retrieved sources."""
    
    def __init__(self, llm_client: OpenAIClient = None):
        self.llm_client = llm_client or OpenAIClient()
    
    @property
    def name(self) -> str:
        return "generate_tax_answer"
    
    @property
    def description(self) -> str:
        return "Generate a comprehensive answer to a tax question using provided legislation and case law sources"
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The original tax question from the user"
                },
                "legislation": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of relevant legislation sources to use in the answer"
                },
                "case_law": {
                    "type": "array", 
                    "items": {"type": "string"},
                    "description": "List of relevant case law sources to use in the answer"
                }
            },
            "required": ["question", "legislation", "case_law"]
        }
    
    def execute(self, question: str, legislation: List[str], case_law: List[str]) -> ToolResult:
        """
        Generate a comprehensive tax answer using the provided sources.
        
        This tool:
        1. Validates input sources
        2. Creates a structured prompt with sources
        3. Uses LLM to generate comprehensive answer
        4. Validates and formats the response
        """
        
        try:
            logger.info(f"Generating answer for question: {question[:100]}...")
            
            # Validate inputs
            if not question.strip():
                return ToolResult(
                    success=False,
                    data=None,
                    error_message="Question cannot be empty"
                )
            
            if not legislation and not case_law:
                return ToolResult(
                    success=False,
                    data=None,
                    error_message="At least one source (legislation or case law) is required"
                )
            
            # Format sources for the prompt
            legislation_text = self._format_sources(legislation, "WETGEVING")
            case_law_text = self._format_sources(case_law, "JURISPRUDENTIE")
            
            # Create the prompt using template
            prompt = fill_prompt_template(
                get_prompt_template("answer_generation"),
                question=question,
                legislation=legislation_text,
                case_law=case_law_text
            )
            
            # Generate answer using LLM
            response = self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=2000
            )
            
            answer = response["choices"][0]["message"]["content"]
            
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
                    "question": question,
                    "legislation_count": len(legislation),
                    "case_law_count": len(case_law),
                    "prompt_tokens": response.get("usage", {}).get("prompt_tokens", 0),
                    "completion_tokens": response.get("usage", {}).get("completion_tokens", 0),
                    "total_tokens": response.get("usage", {}).get("total_tokens", 0)
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
    
    def generate_answer_with_validation(
        self, 
        question: str, 
        legislation: List[str], 
        case_law: List[str]
    ) -> ToolResult:
        """Generate answer with additional validation step."""
        
        # Validate sources first
        validation_issues = self.validate_sources(legislation, case_law)
        
        if validation_issues:
            logger.warning(f"Source validation issues: {validation_issues}")
            # Could either fail or proceed with warning in metadata
        
        result = self.execute(question, legislation, case_law)
        
        # Add validation info to metadata
        if result.success and validation_issues:
            result.metadata["validation_warnings"] = validation_issues
        
        return result
    
    def generate_answer(self, question: str, legislation: List[str], case_law: List[str]) -> str:
        """Legacy method for backward compatibility."""
        result = self.execute(question, legislation, case_law)
        if result.success:
            return result.data
        return f"Error: {result.error_message}"