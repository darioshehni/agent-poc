"""
Legislation retrieval tool with clean architecture.
Updates the dossier (when provided) and returns an assistant message.
"""

from typing import Dict, Any, List, Callable
import logging

from src.base import BaseTool, ToolResult
from src.sessions import SessionManager

logger = logging.getLogger(__name__)

from src.models import Legislation


class LegislationTool(BaseTool):
    """Tool for retrieving relevant Dutch tax legislation."""
    
    def __init__(self, session_manager: SessionManager | None = None, dossier_id_getter: Callable[[], str] | None = None):
        # In a real implementation, this would connect to a database or search system
        self._sample_legislation: List[Legislation] = [
            Legislation(
                title="Wet op de vennootschapsbelasting 1969, artikel 13",
                content=(
                    "Wet op de vennootschapsbelasting 1969, artikel 13:\n"
                    "De deelnemingsvrijstelling is een belangrijke fiscale regeling in de Nederlandse vennootschapsbelasting.\n"
                    "Kort gezegd betekent het dat een bedrijf (bijvoorbeeld een BV of NV) geen belasting hoeft te betalen over winst (dividenden of verkoopwinsten) die het ontvangt uit een kwalificerende deelneming. Zo wordt dubbele belasting voorkomen: de winst is namelijk al belast bij de dochtermaatschappij die de winst maakte.\n"
                    "Voorwaarden deelnemingsvrijstelling\n"
                    "De deelnemingsvrijstelling geldt meestal als:\n"
                    "Aandeelhouderschap: de moedermaatschappij minimaal 5% van de aandelen bezit in de dochtermaatschappij.\n"
                ),
            ),
            Legislation(
                title="Wet op de omzetbelasting 1968, artikel 2",
                content="Wet op de omzetbelasting 1968, artikel 2: het btw-tarief op goederen is 21%",
            ),
        ]
        self.session_manager = session_manager
        self.dossier_id_getter = dossier_id_getter or (lambda: "default")

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
    
    async def execute(self, query: str) -> ToolResult:
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
            
            # Update dossier if session manager is provided
            applied = False
            try:
                if self.session_manager is not None:
                    dos = self.session_manager.get_dossier(self.dossier_id_getter())
                    if dos is not None:
                        dos.add_legislation(relevant_legislation)
                        # Auto-select titles
                        for it in relevant_legislation:
                            t = (it.title or "").strip()
                            if t and t not in dos.selected_ids:
                                dos.selected_ids.append(t)
                        applied = True
            except Exception:
                applied = False

            # Prepare assistant message listing titles and confirmation question
            titles = [l.title for l in relevant_legislation if (l.title or '').strip()]
            lines = ["Ik vond de volgende bronnen:"]
            for i, t in enumerate(titles, 1):
                lines.append(f"{i}. {t}")
            lines.append("Zijn deze bronnen correct voor uw vraag?")
            assistant_msg = "\n".join(lines)

            # Return pydantic objects; metadata holds titles and flags
            formatted_results = relevant_legislation
            result = ToolResult(
                success=True,
                data=formatted_results,
                metadata={
                    "source_names": titles,
                    "query": query,
                    "result_count": len(formatted_results),
                    "search_method": "keyword_matching",
                    "dossier_updated": applied,
                },
                message=assistant_msg,
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
