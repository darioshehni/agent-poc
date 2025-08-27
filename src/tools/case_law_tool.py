"""
Case law retrieval tool with clean architecture.
Returns CaseLaw Pydantic models so each source has a stable ID and title.
"""

from typing import Dict, Any, List
import logging

try:
    from ..base import BaseTool, ToolResult
    from ..models import CaseLaw
except ImportError:
    from base import BaseTool, ToolResult
    from models import CaseLaw

logger = logging.getLogger(__name__)


class CaseLawTool(BaseTool):
    """Tool for retrieving relevant Dutch tax case law and jurisprudence."""
    
    def __init__(self):
        # Sample case law data (Pydantic models)
        self._sample_case_law: List[CaseLaw] = [
            CaseLaw(
                title="Hoge Raad ECLI:NL:HR:2020:123",
                court="Hoge Raad",
                ecli="ECLI:NL:HR:2020:123",
                date="2020-01-15",
                content=(
                    "Uitspraak Hoge Raad ECLI:NL:HR:2020:123: Op tandpasta wordt vrijgesteld van btw, "
                    "omdat het geclassificeerd wordt als medicijn."
                ),
            ),
            CaseLaw(
                title="Rechtbank Amsterdam ECLI:NL:RBAMS:2021:456",
                court="Rechtbank Amsterdam",
                ecli="ECLI:NL:RBAMS:2021:456",
                date="2021-03-10",
                content=(
                    "Rechtbank Amsterdam: Er is alleen sprake van deelnemingsvrijstelling als de deelneming "
                    "wordt gehouden met een zakelijk motief en niet alleen om te beleggen."
                ),
            ),
        ]
    
    @property
    def name(self) -> str:
        return "get_case_law"
    
    @property
    def description(self) -> str:
        return "Retrieve relevant Dutch tax case law and jurisprudence for a query"
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string", 
                    "description": "The tax question or topic to search case law for"
                }
            },
            "required": ["query"]
        }
    
    def execute(self, query: str) -> ToolResult:
        """
        Retrieve case law based on the query.
        
        In a real implementation, this would:
        1. Connect to legal databases (Rechtspraak.nl, commercial databases)
        2. Use advanced search with legal terminology
        3. Apply relevance scoring based on legal precedent importance
        4. Filter by court hierarchy and recency
        """
        
        try:
            logger.info(f"Searching case law for query: {query}")

            relevant_cases = self._search_case_law(query)

            if not relevant_cases:
                return ToolResult(
                    success=False,
                    data=[],
                    error_message="Geen relevante jurisprudentie gevonden voor deze vraag."
                )

            titles = [c.title for c in relevant_cases]
            result = ToolResult(
                success=True,
                data=relevant_cases,
                metadata={
                    "source_names": titles,
                    "query": query,
                    "result_count": len(relevant_cases),
                    "courts": [c.court for c in relevant_cases],
                    "search_method": "keyword_matching",  # Demo
                }
            )

            logger.info(f"Found {len(relevant_cases)} case law items")
            return result

        except Exception as e:
            logger.error(f"Error searching case law: {str(e)}", exc_info=True)
            return ToolResult(
                success=False,
                data=[],
                error_message=f"Fout bij het zoeken in jurisprudentie: {str(e)}"
            )
    
    def _search_case_law(self, query: str) -> List[CaseLaw]:
        """Simple keyword-based search for case law (demo)."""
        query_lower = query.lower()
        results: List[CaseLaw] = []

        for case in self._sample_case_law:
            content_lower = (case.content or "").lower()
            title_lower = (case.title or "").lower()

            if any(keyword in content_lower for keyword in ["btw", "vennootschap", "deelneming", "vrijstelling"]):
                results.append(case)
            elif any(keyword in query_lower for keyword in ["btw", "omzet"]) and "btw" in content_lower:
                results.append(case)
            elif any(keyword in query_lower for keyword in ["vennootschap", "deelneming"]) and ("vennootschap" in content_lower or "rechtbank" in title_lower or "hoge raad" in title_lower):
                results.append(case)

        return results
    
    # Legacy accessors removed; use execute() and session/dossier instead
