"""
Conversation context builders for the agent.

Note: We intentionally keep the system prompt static. We do not append dynamic
context information here; sources are provided only to tools at call time.
"""

from typing import Callable

from src.models import Dossier
from src.prompts import get_prompt_template


class ContextBuilder:
    """Builds the static system prompt (no dynamic session context)."""

    def __init__(self, prompt_getter: Callable[[str], str] = get_prompt_template) -> None:
        self._get_prompt = prompt_getter

    def build_system_prompt(self, dossier: Dossier) -> str:
        """Return only the base system prompt (no appended context)."""
        return self._get_prompt("agent_system")
