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

from src.config.models import ToolResult
from src.config.prompts import RETRIEVAL_TITLES_HEADER, SELECTED_CONFIRMATION, SELECT_TITLES_HEADER, UNSELECT_TITLES_HEADER


def present_outcomes(tool_results: list[ToolResult]) -> str:
    """Generate user-facing messages from tool execution results.
    
    Analyzes patches from tool results and creates formatted messages that inform
    the user about source retrievals, selections, and unselections. Handles:
    - New source retrievals (legislation and case law)
    - Source selections and unselections  
    - Direct tool messages (e.g., from AnswerTool)
    
    Args:
        tool_results: List of tool execution results with patches and messages
        
    Returns:
        Formatted assistant message string for the user, or a default message
        if no changes were made
    """
    retrieved_titles: list[str] = []
    selected_titles: list[str] = []
    unselected_titles: list[str] = []

    message = ""
    for result in tool_results:
        patch = result.patch
        if patch is None:
            continue
        # Newly retrieved sources (titles only)
        retrieved_titles.extend([x.title for x in getattr(patch, 'add_legislation', [])])
        retrieved_titles.extend([x.title for x in getattr(patch, 'add_case_law', [])])
        # Selection changes
        selected_titles.extend([t for t in getattr(patch, 'select_titles', [])])
        unselected_titles.extend([t for t in getattr(patch, 'unselect_titles', [])])

    if retrieved_titles:
        message += f"{RETRIEVAL_TITLES_HEADER}\n\n\n- "
        message += "\n- ".join(retrieved_titles)
        message += "\n\n\n"

    if unselected_titles:
        message += f"{UNSELECT_TITLES_HEADER}\n\n\n- "
        message += "\n- ".join(unselected_titles)
        message += "\n\n\n"

    if selected_titles and not retrieved_titles:
        message += f"{SELECT_TITLES_HEADER}\n\n\n- "
        message += "\n- ".join(selected_titles)
        message += "\n\n\n"

    if message:
        message += f"{SELECTED_CONFIRMATION}\n\n\n\n"

    # Append any direct messages from tools.
    for result in tool_results:
        if result.message:
            message += f"{result.message}\n\n\n\n"

    if not message:
        message = "Ik heb geen wijzigingen aangebracht."

    return message
