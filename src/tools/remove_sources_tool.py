"""
Tool to map a natural user instruction (e.g., "remove article 13") to
concrete dossier entries, returning a structured list of titles to remove.

This tool reads the current dossier (legislation and case law),
presents short candidate names to the LLM along with the user's removal
instruction, and asks for a strict JSON result listing the titles to remove.

The agent will then deterministically unselect those titles from the dossier.
"""

from typing import Dict, Any, Callable
import json
import logging


from src.base import BaseTool, ToolResult
from src.models import DocumentTitles
from src.sessions import SessionManager


logger = logging.getLogger(__name__)


REMOVE_PROMPT = """
Je krijgt een lijst met bronnen (wetgeving en/of jurisprudentie) uit een dossier
en een gebruikersinstructie om bepaalde bron(nen) te verwijderen. Kies uitsluitend
de bronnen die het beste overeenkomen met de instructie. Geef als uitvoer STRIKT
het volgende JSON-formaat, en niets anders:

{"titles": ["Titel 1", "Titel 2", ...]}

Waarbij elke ID exact overeenkomt met een titel in de kandidatenlijst hieronder
(de titel fungeert als ID; gebruik de titeltekst exact zoals getoond).
Geef GEEN toelichting buiten dit JSON.

INSTRUCTIE:
{instruction}

KANDIDATEN (Titel; gebruik exact de titel als ID):
{candidates}
"""


class RemoveSourcesTool(BaseTool):
    """Convert a removal instruction into a list of dossier source titles to unselect.

    This tool presents concise candidate names from the dossier to the
    LLM so it can map user language (e.g., "verwijder artikel 13") to exact
    entries. The agent applies the returned titles to update the dossier selection.
    """

    def __init__(
        self,
        llm_client: Any = None,
        session_manager: 'SessionManager' = None,
        dossier_id_getter: Callable[[], str] | None = None,
        model_name_getter: Callable[[], str] | None = None,
    ):
        # Expect an async LlmChat client
        self.llm_client = llm_client
        self.session_manager = session_manager
        self.dossier_id_getter = dossier_id_getter or (lambda: "default")
        self.model_name_getter = model_name_getter or (lambda: "gpt-4o-mini")

    @property
    def name(self) -> str:
        return "remove_sources"

    @property
    def description(self) -> str:
        return "Map a removal instruction to exact dossier source titles to unselect"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "instruction": {
                    "type": "string",
                    "description": "User instruction specifying which sources to remove"
                }
            },
            "required": ["instruction"]
        }

    async def execute(self, instruction: str) -> ToolResult:
        try:
            if not instruction.strip():
                return ToolResult(False, None, "Instruction cannot be empty")

            # Build candidate list from dossier (titles act as IDs)
            candidates_display = []
            try:
                dossier = None
                if self.session_manager is not None:
                    dossier = self.session_manager.get_dossier(self.dossier_id_getter())
                if dossier:
                    for l in dossier.legislation:
                        if getattr(l, 'title', '').strip():
                            candidates_display.append(l.title)
                    for c in dossier.case_law:
                        if getattr(c, 'title', '').strip():
                            candidates_display.append(c.title)
            except Exception as e:
                logger.warning(f"remove_sources: could not build candidates: {e}")

            if not candidates_display:
                return ToolResult(False, None, "No dossier sources available to remove")

            prompt = REMOVE_PROMPT.format(
                instruction=instruction,
                candidates="\n".join(candidates_display)
            )

            # Ask the LLM to return structured titles list
            parsed: DocumentTitles = await self.llm_client.chat_structured(
                messages=prompt,
                model_name=self.model_name_getter(),
                response_format=DocumentTitles,
            )

            titles = list(parsed.titles or [])
            if not titles:
                return ToolResult(False, None, "No titles selected for removal")

            # Apply unselection directly to the dossier
            removed_count = 0
            try:
                if self.session_manager is not None:
                    dossier = self.session_manager.get_dossier(self.dossier_id_getter())
                    if dossier:
                        before_sel = list(dossier.selected_ids)
                        dossier.selected_ids = [sid for sid in dossier.selected_ids if sid not in titles]
                        removed_count = len(before_sel) - len(dossier.selected_ids)
            except Exception as e:
                logger.warning(f"remove_sources: failed to apply unselection: {e}")

            message = "Ik heb de genoemde bronnen uit de selectie gehaald." if removed_count > 0 else "Er was geen overeenkomst met de huidige selectie."

            return ToolResult(True, parsed, metadata={"dossier_updated": True, "removed_count": removed_count}, message=message)

        except Exception as e:
            logger.error(f"remove_sources tool failed: {e}")
            return ToolResult(False, None, f"remove_sources failed: {e}")
