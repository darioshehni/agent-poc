"""
Conversation context builders for the agent.

Note: We intentionally keep the system prompt static. We do not append dynamic
session/source information here; sources are provided only to tools at call time.
"""

from typing import Callable

from sessions import Conversation
from prompts import get_prompt_template


class ContextBuilder:
    """Builds the static system prompt (no dynamic session context)."""

    def __init__(self, prompt_getter: Callable[[str], str] = get_prompt_template) -> None:
        self._get_prompt = prompt_getter

    def build_system_prompt(self, session: Conversation) -> str:
        """Return only the base system prompt (no appended context)."""
        return self._get_prompt("agent_system")
