"""
Case law retrieval tool (dummy).

Returns a DossierPatch that adds the sample case law and selects their titles.
The agent is responsible for presenting user-facing messages.
"""

from typing import Any
import logging

from src.config.models import CaseLaw, DossierPatch

logger = logging.getLogger(__name__)


class CaseLawTool:
    """Tool for retrieving relevant Dutch tax case law and jurisprudence."""
    
    def __init__(self):
        """Initialize the case law tool with sample Dutch tax jurisprudence.
        
        Note: This is a dummy implementation with hardcoded sample data.
        Real implementations should replace this with actual case law search.
        """
        self._sample_case_law: list[CaseLaw] = [
            CaseLaw(
                title="ECLI:NL:HR:2020:123",
                content=(
                    "Geschil over btw-classificatie en tarieftoepassing. Het btw tarief op tandpasta is 0%"
                ),
            ),
            CaseLaw(
                title="ECLI:NL:RBAMS:2021:456",
                content=(
                    "Deelnemingsvrijstelling vereist een zakelijk motief."
                ),
            ),
        ]

    @property
    def name(self) -> str:
        return "get_case_law"
    
    @property
    def description(self) -> str:
        return "Retrieve relevant case law and jurisprudence for a query"
    
    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string", 
                    "description": "Tax question or topic to search case laws for. Should include any context that could be relevant or helpful in deciding what case law to return."
                }
            },
            "required": ["query"]
        }
    
    async def execute(self, query: str, dossier=None, **_: Any) -> dict:
        """Retrieve relevant Dutch tax case law based on the query.
        
        Currently returns hardcoded sample case law. Real implementations
        should perform actual search against case law databases.
        
        Args:
            query: Tax question or topic to search case law for
            dossier: Current dossier (unused in this implementation)
            **_: Additional arguments (ignored)
            
        Returns:
            Dictionary with 'success', 'data', and 'patch' keys. The patch
            contains case law to add and titles to select.
        """
        logger.debug("Case law tool called")
        try:
            items = list(self._sample_case_law)
            titles = [x.title for x in items]
            patch = DossierPatch(
                add_case_law=items,
                select_titles=titles,
            )
            return {"success": True, "data": None, "patch": patch}
        except Exception as e:
            logger.error(f"CaseLawTool failed: {e}", exc_info=True)
            message = ""
            return {"success": False, "data": None, "error_message": str(e)}
