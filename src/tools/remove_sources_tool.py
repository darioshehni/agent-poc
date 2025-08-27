"""
Tool to map a natural user instruction (e.g., "remove article 13") to
concrete dossier entries, returning a structured list of IDs to remove.

This tool reads the current session's dossier (legislation and case law),
presents short candidate names to the LLM along with the user's removal
instruction, and asks for a strict JSON result listing the IDs to remove.

The agent will then deterministically remove those IDs from the dossier.
"""

from typing import Dict, Any, List, Callable
import json
import logging

try:
    from ..base import BaseTool, ToolResult
    from ..llm import OpenAIClient
    from ..prompts import fill_prompt_template
    from ..models import RemovalDecision
    from ..sessions import SessionManager
except ImportError:
    from base import BaseTool, ToolResult
    from llm import OpenAIClient
    from prompts import fill_prompt_template
    from models import RemovalDecision
    from sessions import SessionManager


logger = logging.getLogger(__name__)


REMOVE_PROMPT = """
Je krijgt een lijst met bronnen (wetgeving en/of jurisprudentie) uit een dossier
en een gebruikersinstructie om bepaalde bron(nen) te verwijderen. Kies uitsluitend
de bronnen die het beste overeenkomen met de instructie. Geef als uitvoer STRIKT
het volgende JSON-formaat, en niets anders:

{
  "remove_ids": ["ID1", "ID2", ...]
}

Waarbij elke ID exact overeenkomt met een ID in de kandidatenlijst hieronder.
Geef GEEN toelichting buiten dit JSON.

INSTRUCTIE:
{instruction}

KANDIDATEN (ID — Titel):
{candidates}
"""


class RemoveSourcesTool(BaseTool):
    """Convert a removal instruction into a list of dossier source IDs to remove.

    This tool presents concise candidate names from the session dossier to the
    LLM so it can map user language (e.g., "verwijder artikel 13") to exact
    entries. The agent applies the returned IDs to update the dossier.
    """

    def __init__(
        self,
        llm_client: OpenAIClient = None,
        session_manager: 'SessionManager' = None,
        session_id_getter: Callable[[], str] | None = None,
    ):
        self.llm_client = llm_client or OpenAIClient()
        self.session_manager = session_manager
        self.session_id_getter = session_id_getter or (lambda: "default")

    @property
    def name(self) -> str:
        return "remove_sources"

    @property
    def description(self) -> str:
        return "Map a removal instruction to exact dossier source IDs to remove"

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

    def execute(self, instruction: str) -> ToolResult:
        try:
            if not instruction.strip():
                return ToolResult(False, None, "Instruction cannot be empty")

            # Build candidate list from dossier
            candidates_display = []
            try:
                session = None
                if self.session_manager is not None:
                    session = self.session_manager.get_session(self.session_id_getter())
                if session and session.dossier:
                    for l in session.dossier.legislation:
                        candidates_display.append(f"{l.id} — {l.title or l.law or ''}")
                    for c in session.dossier.case_law:
                        candidates_display.append(f"{c.id} — {c.title or c.ecli or ''}")
            except Exception as e:
                logger.warning(f"remove_sources: could not build candidates: {e}")

            if not candidates_display:
                return ToolResult(False, None, "No dossier sources available to remove")

            prompt = REMOVE_PROMPT.format(
                instruction=instruction,
                candidates="\n".join(candidates_display)
            )

            response = self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=500
            )

            text = response["choices"][0]["message"].get("content", "").strip()
            # Attempt to parse strict JSON
            try:
                data = json.loads(text)
                decision = RemovalDecision.model_validate(data)
            except Exception as e:
                logger.warning(f"remove_sources: JSON parse/validate issue: {e}; text={text[:200]}")
                return ToolResult(False, None, "Invalid JSON returned for removal decision")

            return ToolResult(True, decision, metadata={
                "prompt_tokens": response.get("usage", {}).get("prompt_tokens", 0),
                "completion_tokens": response.get("usage", {}).get("completion_tokens", 0),
            })

        except Exception as e:
            logger.error(f"remove_sources tool failed: {e}")
            return ToolResult(False, None, f"remove_sources failed: {e}")

