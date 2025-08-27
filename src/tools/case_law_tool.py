"""
Case law retrieval tool with clean architecture.
"""

from typing import Dict, Any, List
import logging

try:
    from ..base import BaseTool, ToolResult
except ImportError:
    from base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class CaseLawTool(BaseTool):
    """Tool for retrieving relevant Dutch tax case law and jurisprudence."""
    
    def __init__(self):
        # Sample case law data - in reality this would be a proper database
        self._sample_case_law = [
            {
                "content": "uitspraak hoge raad ECLI:123: Op tandpasta wordt vrijgesteld van btw, omdat het geclassificeerd wordt als medicijn",
                "source": "Hoge Raad ECLI:NL:HR:2020:123",
                "court": "Hoge Raad",
                "date": "2020-01-15",
                "ecli": "ECLI:NL:HR:2020:123"
            },
            {
                "content": "rechtbank amsterdam ECLI:456:Er is alleen sprake van deelnemingsvrijstelling als de deelneming wordt gehouden met een zakelijk motief en niet alleen om te beleggen. Er is dus geen recht op deelnemingsvrijstelling als het dochterbedrijd een beleggingsdeelneming is.",
                "source": "Rechtbank Amsterdam ECLI:NL:RBAMS:2021:456", 
                "court": "Rechtbank Amsterdam",
                "date": "2021-03-10",
                "ecli": "ECLI:NL:RBAMS:2021:456"
            }
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
            
            # Format results
            formatted_results = [case["content"] for case in relevant_cases]
            source_names = [case["source"] for case in relevant_cases]
            
            result = ToolResult(
                success=True,
                data=formatted_results,
                metadata={
                    "source_names": source_names,
                    "query": query,
                    "result_count": len(formatted_results),
                    "courts": [case["court"] for case in relevant_cases],
                    "search_method": "keyword_matching"  # In real system: semantic + legal precedent
                }
            )
            
            logger.info(f"Found {len(formatted_results)} case law items")
            return result
            
        except Exception as e:
            logger.error(f"Error searching case law: {str(e)}", exc_info=True)
            return ToolResult(
                success=False,
                data=[],
                error_message=f"Fout bij het zoeken in jurisprudentie: {str(e)}"
            )
    
    def _search_case_law(self, query: str) -> List[Dict[str, Any]]:
        """
        Simple keyword-based search for case law.
        Production version would use legal search algorithms.
        """
        query_lower = query.lower()
        results = []
        
        for case in self._sample_case_law:
            content_lower = case["content"].lower()
            
            # Match based on tax topics
            if any(keyword in content_lower for keyword in ["btw", "vennootschap", "deelneming", "vrijstelling"]):
                results.append(case)
            elif any(keyword in query_lower for keyword in ["btw", "omzet"] if "btw" in content_lower):
                results.append(case)
            elif any(keyword in query_lower for keyword in ["vennootschap", "deelneming"] if "vennootschap" in content_lower):
                results.append(case)
        
        # Sort by court importance (Hoge Raad first)
        results.sort(key=lambda x: 0 if x["court"] == "Hoge Raad" else 1)
        
        return results
    
    def get_source_names(self) -> List[str]:
        """Get available source names (for backward compatibility)."""
        return [case["source"] for case in self._sample_case_law]
    
    def retrieve_case_law(self, query: str) -> List[str]:
        """Legacy method for backward compatibility."""
        result = self.execute(query)
        if result.success:
            return result.data
        return []