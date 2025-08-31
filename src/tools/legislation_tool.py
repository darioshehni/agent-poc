"""
Legislation retrieval tool (dummy).

Returns a DossierPatch that adds the sample legislation and selects their titles.
The agent is responsible for presenting user-facing messages.
"""

from typing import Any
import logging

from src.config.models import DossierPatch, ToolResult, Legislation

logger = logging.getLogger(__name__)


class LegislationTool:
    """Tool for retrieving relevant Dutch tax legislation."""
    
    def __init__(self):
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
    
    async def execute(self, query: str, dossier=None, **_: Any) -> ToolResult:
        """Dummy implementation: always return the sample legislation as a patch.

        Real implementations will replace this with actual retrieval.
        """
        try:
            items = list(self._sample_legislation)
            titles = [x.title for x in items if (x.title or '').strip()]

            patch = DossierPatch(
                add_legislation=items,
                select_titles=[t for t in titles if t],
            )

            return ToolResult(success=True, data=None, message="", patch=patch)
        except Exception as e:
            logger.error(f"LegislationTool failed: {e}", exc_info=True)
            return ToolResult(success=False, data=None, error_message=str(e))
