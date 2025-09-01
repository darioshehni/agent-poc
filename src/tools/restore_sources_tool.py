"""
Restore tool.

Maps a natural query (e.g., “herstel artikel 13” of “voeg ECLI toe”) naar
concrete titels in het dossier die op dit moment NIET geselecteerd zijn en
retourneert een DossierPatch met `select_titles` om deze weer te selecteren.
De agent verzorgt de user‑facing bevestiging.
"""

from typing import Any
import logging

from src.config.models import DocumentTitles, DossierPatch, Dossier
from src.llm import LlmChat
from src.config.prompts import RESTORE_PROMPT
from src.config.config import OpenAIModels

logger = logging.getLogger(__name__)


class RestoreSourcesTool:
    """Restore previously unselected sources back to the dossier selection.
    
    Uses natural language parsing to determine which document titles from the
    unselected list should be restored based on user queries.
    """

    def __init__(
        self,
        llm_client: LlmChat,
    ):
        """Initialize the source restoration tool.
        
        Args:
            llm_client: LLM client for parsing natural language restoration queries
        """
        self.llm_client = llm_client

    @property
    def name(self) -> str:
        return "restore_sources"

    @property
    def description(self) -> str:
        return "This tool determines which document titles from the unselected list should be restored based on a user query."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "A natural language query that explains which documents should be restored/selected. This should include specific to which titles and which types of document to restore."
                }
            },
            "required": ["query"]
        }

    async def execute(self, query: str, dossier: Dossier) -> dict:
        """Restore sources to dossier selection based on natural language query.
        
        Uses structured LLM parsing to map user language (e.g., "restore article 13")
        to specific source titles from the unselected sources in the dossier.
        
        Args:
            query: Natural language instruction for which sources to restore
            dossier: Current dossier with unselected sources available for restoration
            
        Returns:
            Dictionary with 'success', 'data', and 'patch' keys.
            The patch contains titles to select in the dossier.
            
        Raises:
            Exception: If LLM parsing fails or other execution errors occur
        """
        try:
            query = (query or "").strip()
            if not query:
                return {"success": False, "data": None, "message": "Query cannot be empty"}

            candidates: list[str] = dossier.unselected_titles()
            if not candidates:
                return {"success": False, "data": None, "message": "No unselected sources available to restore"}

            candidates_formatted = "\n".join(candidates)
            prompt = RESTORE_PROMPT.format(query=query, candidates=candidates_formatted)

            document_titles: DocumentTitles = await self.llm_client.chat_structured(
                messages=prompt,
                model_name=OpenAIModels.GPT_4O.value,
                response_format=DocumentTitles,
            )

            titles = list(document_titles.titles or [])
            if not titles:
                return {"success": False, "data": None, "message": "No titles selected for restoration"}

            patch = DossierPatch(select_titles=titles)
            return {"success": True, "data": document_titles, "patch": patch}

        except Exception as e:
            logger.error(f"restore_sources tool failed: {e}")
            raise e

