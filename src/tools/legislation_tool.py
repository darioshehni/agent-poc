"""
Legislation retrieval tool (dummy).

Returns a DossierPatch that adds the sample legislation and selects their titles.
The agent is responsible for presenting user-facing messages.
"""

from typing import Any
import logging

from src.config.models import DossierPatch, Legislation

logger = logging.getLogger(__name__)


class LegislationTool:
    """Tool for retrieving relevant Dutch tax legislation."""
    
    def __init__(self):
        """Initialize the legislation tool with sample Dutch tax legislation.
        
        Note: This is a dummy implementation with hardcoded sample data.
        Real implementations should replace this with actual search functionality.
        """
        self._sample_legislation: list[Legislation] = [
            Legislation(
                title="Wet op de vennootschapsbelasting 1969, artikel 13",
                content=(
                    "De deelnemingsvrijstelling is een belangrijke fiscale regeling in de Nederlandse vennootschapsbelasting.\n"
                    "Kort gezegd betekent het dat een bedrijf (bijvoorbeeld een BV of NV) geen belasting hoeft te betalen over winst (dividenden of verkoopwinsten) die het ontvangt uit een kwalificerende deelneming. Zo wordt dubbele belasting voorkomen: de winst is namelijk al belast bij de dochtermaatschappij die de winst maakte.\n"
                    "Voorwaarden deelnemingsvrijstelling\n"
                    "De deelnemingsvrijstelling geldt meestal als:\n"
                    "Aandeelhouderschap: de moedermaatschappij minimaal 5% van de aandelen bezit in de dochtermaatschappij.\n"
                ),
            ),
            Legislation(
                title="Wet op de omzetbelasting 1968, artikel 2",
                content="Het btw-tarief op goederen is 21%",
            ),
        ]
        # stateless

    @property
    def name(self) -> str:
        return "get_legislation"
    
    @property
    def description(self) -> str:
        return "Retrieve relevant legislation for a query."
    
    @property 
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Tax question or topic to search legislation for. Should include any context that could be relevant or helpful in deciding what legislation to return."
                }
            },
            "required": ["query"]
        }
    
    async def execute(self, query: str, dossier=None, **_: Any) -> dict:
        """Retrieve relevant Dutch tax legislation based on the query.
        
        Currently returns hardcoded sample legislation. Real implementations
        should perform actual search against legislation databases.
        
        Args:
            query: Tax question or topic to search legislation for
            dossier: Current dossier (unused in this implementation)
            **_: Additional arguments (ignored)
            
        Returns:
            Dictionary with 'success', 'data', and 'patch' keys. The patch
            contains legislation to add and titles to select.
        """
        try:
            items = list(self._sample_legislation)
            titles = [x.title for x in items if (x.title or '').strip()]
            patch = DossierPatch(
                add_legislation=items,
                select_titles=titles,
            )
            return {"success":True, "data": None, "patch": patch}
        except Exception as e:
            logger.error(f"LegislationTool failed: {e}", exc_info=True)
            return {"success": False, "data": None, "error_message": str(e)}
