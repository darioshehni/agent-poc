"""
Presenter utilities for formatting user-facing assistant messages from tool outcomes.

This module keeps agent-facing logic simple by providing a single function that
inspects patches returned by tools and turns them into concise messages.

Rules:
- Retrieval: aggregate titles from all patches' add_legislation/add_case_law and
  render a single list plus a confirmation question.
- Removal: if any patch contains unselect_titles, render a single confirmation.
- Answer: handled separately by the agent (ToolResult.data from AnswerTool).
"""

from typing import Any, Dict, List
from src.prompts import build_retrieval_message, REMOVAL_CONFIRMATION


def present_outcomes(outcomes: List[Dict[str, Any]]) -> List[str]:
    """Aggregate patches across outcomes and produce assistant messages.

    Returns a list of messages (strings) for the agent to append to the dossier
    conversation and include in the in-flight conversation list.
    """
    retrieval_titles: List[str] = []
    removal_flag = False

    for out in outcomes:
        patch = out.get("patch")
        if patch is None:
            continue
        if hasattr(patch, "add_legislation") and patch.add_legislation:
            retrieval_titles.extend([x.title for x in patch.add_legislation if getattr(x, "title", "").strip()])
        if hasattr(patch, "add_case_law") and patch.add_case_law:
            retrieval_titles.extend([x.title for x in patch.add_case_law if getattr(x, "title", "").strip()])
        if hasattr(patch, "unselect_titles") and patch.unselect_titles:
            removal_flag = True

    messages: List[str] = []
    # De-duplicate titles but keep order
    if retrieval_titles:
        titles = list(dict.fromkeys(retrieval_titles))
        lines = ["Ik vond de volgende bronnen:"]
        for i, title in enumerate(titles, 1):
            lines.append(f"{i}. {title}")
        lines.append("Zijn deze bronnen correct voor uw vraag?")
        messages.append("\n".join(lines))

    if removal_flag:
        messages.append(REMOVAL_CONFIRMATION)

    return messages
