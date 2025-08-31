"""
Removal tool.

Maps a natural instruction (e.g., “verwijder artikel 13”) to concrete titles in
the dossier and returns a DossierPatch with `unselect_titles`. The agent formats
the user-facing confirmation message.
"""

from typing import Any
import logging


from src.models import DocumentTitles, DossierPatch, Dossier, ToolResult
from src.llm import LlmChat
from src.prompts import REMOVE_PROMPT
from src.config import OpenAIModels

logger = logging.getLogger(__name__)




class RemoveSourcesTool:
    """Convert a removal instruction into a list of dossier source titles to unselect.

    This tool presents concise candidate names from the dossier to the
    LLM so it can map user language (e.g., "verwijder artikel 13") to exact
    entries. The agent applies the returned titles to update the dossier selection.
    """

    def __init__(
        self,
        llm_client: LlmChat,
    ):
        # Expect an async LlmChat client
        self.llm_client = llm_client

    @property
    def name(self) -> str:
        return "remove_sources"

    @property
    def description(self) -> str:
        return "Given a user message specifying which source have to be removed, this tool removes those tools from the dossier."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "instruction": {
                    "type": "string",
                    "description": "A natural language instruction that explains which documents should be removed, e.g., 'verwijder artikel 13 en ECLI:234:456 uit de selectie'. "
                }
            },
            "required": ["instruction"]
        }

    async def execute(self, instruction: str, dossier: Dossier) -> ToolResult:
        try:
            if not instruction.strip():
                return ToolResult(False, None, "Instruction cannot be empty")

            selected_titles: list[str] = dossier.selected_titles()
            if not selected_titles:
                return ToolResult(False, None, "No dossier sources available to remove")

            selected_titles_formatted = "\n".join(selected_titles)

            prompt = REMOVE_PROMPT.format(
                instruction=instruction,
                candidates=selected_titles_formatted
            )

            document_titles: DocumentTitles = await self.llm_client.chat_structured(
                messages=prompt,
                model_name=OpenAIModels.GPT_4O.value,
                response_format=DocumentTitles,
            )

            titles = list(document_titles.titles or [])
            if not titles:
                return ToolResult(False, None, "No titles selected for removal")

            patch = DossierPatch(unselect_titles=titles)

            return ToolResult(success=True,
                              data=document_titles,
                              message="",
                              patch=patch)

        except Exception as e:
            logger.error(f"remove_sources tool failed: {e}")
            return ToolResult(success=False, data=None, message=f"remove_sources failed: {e}")
