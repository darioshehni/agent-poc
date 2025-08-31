"""
Case law retrieval tool (dummy).

Returns a DossierPatch that adds the sample case law and selects their titles.
The agent is responsible for presenting user-facing messages.
"""

from typing import Dict, Any, List
import logging

from src.models import CaseLaw, DossierPatch, ToolResult

logger = logging.getLogger(__name__)


class CaseLawTool:
    """Tool for retrieving relevant Dutch tax case law and jurisprudence."""
    
    def __init__(self):
        self._sample_case_law: List[CaseLaw] = [
            CaseLaw(
                title="ECLI:NL:HR:2020:123",
                content=(
                    "Hoge Raad ECLI:NL:HR:2020:123: geschil over btw-classificatie en tarieftoepassing. Het btw tarief op tandpasta is 0%"
                ),
            ),
            CaseLaw(
                title="ECLI:NL:RBAMS:2021:456",
                content=(
                    "Rechtbank Amsterdam ECLI:NL:RBAMS:2021:456: deelnemingsvrijstelling vereist een zakelijk motief."
                ),
            ),
        ]
        # stateless
    
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
                    "description": "The tax question or topic to search case law for. This should also include all context that is relevant or helpfull for finding relevant case law. Including context where the user mentions which documents are relevant or not."
                }
            },
            "required": ["query"]
        }
    
    async def execute(self, query: str, dossier=None, **_: Any) -> ToolResult:
        """Dummy implementation: always return the sample case law as a patch."""
        logger.debug("Case law tool called")
        try:
            items = list(self._sample_case_law)
            titles = [x.title for x in items if (x.title or '').strip()]

            patch = DossierPatch(
                add_case_law=items,
                select_titles=[t for t in titles if t],
            )

            return ToolResult(success=True, data=None, message="", patch=patch)
        except Exception as e:
            logger.error(f"CaseLawTool failed: {e}", exc_info=True)
            return ToolResult(success=False, data=None, error_message=str(e))
    
    # No search helpers in dummy implementation
