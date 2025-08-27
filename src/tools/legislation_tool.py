"""
Legislation retrieval tool with clean architecture.
"""

from typing import Dict, Any, List
import logging

try:
    from ..base import BaseTool, ToolResult
except ImportError:
    from base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

try:
    from ..models import Legislation
except ImportError:
    from models import Legislation


class LegislationTool(BaseTool):
    """Tool for retrieving relevant Dutch tax legislation."""
    
    def __init__(self):
        # In a real implementation, this would connect to a database or search system
        self._sample_legislation: List[Legislation] = [
            Legislation(
                title="Wet op de vennootschapsbelasting 1969, artikel 13",
                law="Wet VPB",
                article="artikel 13",
                content=(
                    "Wet op de vennootschapsbelasting 1969, artikel 13:\n"
                    "De deelnemingsvrijstelling is een belangrijke fiscale regeling in de Nederlandse vennootschapsbelasting.\n"
                    "Kort gezegd betekent het dat een bedrijf (bijvoorbeeld een BV of NV) geen belasting hoeft te betalen over winst (dividenden of verkoopwinsten) die het ontvangt uit een kwalificerende deelneming. Zo wordt dubbele belasting voorkomen: de winst is namelijk al belast bij de dochtermaatschappij die de winst maakte.\n"
                    "Voorwaarden deelnemingsvrijstelling\n"
                    "De deelnemingsvrijstelling geldt meestal als:\n"
                    "Aandeelhouderschap: de moedermaatschappij minimaal 5% van de aandelen bezit in de dochtermaatschappij.\n"
                ),
                citation="Wet VPB 1969 art. 13",
            ),
            Legislation(
                title="Wet op de omzetbelasting 1968, artikel 2",
                law="Wet OB",
                article="artikel 2",
                content="Wet op de omzetbelasting 1968, artikel 2: het btw-tarief op goederen is 21%",
                citation="Wet OB 1968 art. 2",
            ),
        ]
    
    @property
    def name(self) -> str:
        return "get_legislation"
    
    @property
    def description(self) -> str:
        return "Retrieve relevant Dutch tax legislation for a query"
    
    @property 
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The tax question or topic to search legislation for"
                }
            },
            "required": ["query"]
        }
    
    def execute(self, query: str) -> ToolResult:
        """
        Retrieve legislation based on the query.
        
        In a real implementation, this would:
        1. Parse the query for tax-related keywords
        2. Search a legislation database
        3. Rank results by relevance
        4. Return the most relevant articles
        """
        
        try:
            logger.info(f"Searching legislation for query: {query}")
            
            # Simple keyword matching for demonstration
            # In reality, you'd use semantic search, embeddings, etc.
            relevant_legislation = self._search_legislation(query)
            
            if not relevant_legislation:
                return ToolResult(
                    success=False,
                    data=[],
                    error_message="Geen relevante wetgeving gevonden voor deze vraag."
                )
            
            # Return dataclass objects; metadata holds titles for quick display
            formatted_results = relevant_legislation
            source_names = [item.title for item in relevant_legislation]
            
            result = ToolResult(
                success=True,
                data=formatted_results,
                metadata={
                    "source_names": source_names,
                    "query": query,
                    "result_count": len(formatted_results),
                    "search_method": "keyword_matching"  # In real system: "semantic_search"
                }
            )
            
            logger.info(f"Found {len(formatted_results)} legislation items")
            return result
            
        except Exception as e:
            logger.error(f"Error searching legislation: {str(e)}", exc_info=True)
            return ToolResult(
                success=False,
                data=[],
                error_message=f"Fout bij het zoeken in wetgeving: {str(e)}"
            )
    
    def _search_legislation(self, query: str) -> List[Legislation]:
        """
        Simple keyword-based search.
        In production, this would be much more sophisticated.
        """
        query_lower = query.lower()
        results: List[Legislation] = []

        # Simple keyword matching using sample dataclasses
        for item in self._sample_legislation:
            content_lower = (item.content or "").lower()
            title_lower = (item.title or "").lower()

            if any(keyword in content_lower for keyword in ["btw", "vpb", "belasting", "deelneming", "tarief"]):
                results.append(item)
                continue
            if any(keyword in query_lower for keyword in ["btw", "omzet"] ) and "btw" in content_lower:
                results.append(item)
                continue
            if any(keyword in query_lower for keyword in ["vennootschap", "deelneming"] ) and ("vpb" in content_lower or "vennootschaps" in title_lower):
                results.append(item)

        # If generic tax terms present but nothing matched, return all as demo
        if not results and any(t in query_lower for t in ["belasting", "tarief"]):
            results = list(self._sample_legislation)

        return results
    
    # Legacy accessors removed; use execute() and session/dossier instead
