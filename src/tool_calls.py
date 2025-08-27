"""
Tool call orchestration for the agent.

This module encapsulates execution of LLM tool calls, bridging between the
OpenAI function-calling results and the internal tool system. It updates the
session/dossier, appends tool outputs to the LLM message list, and leaves the
agent free to focus on high-level flow.
"""

from typing import Any, Dict, List
import json
import logging

from sessions import Conversation
from base import ToolManager, WorkflowState


class ToolCallHandler:
    """Executes LLM tool calls and updates session state.

    Responsibilities:
    - Append the assistant tool_calls message to the transcript.
    - Execute each tool via ToolManager exactly once.
    - Serialize and append tool results as tool messages for the LLM.
    - Mirror source-collection results into the session (and dossier).

    This class performs no I/O other than mutating the in-memory messages and
    session. It does not perform the follow-up LLM call; the agent remains in
    control of that step.
    """

    def __init__(self, tool_manager: ToolManager, logger: logging.Logger | None = None) -> None:
        self.tool_manager = tool_manager
        self.logger = logger or logging.getLogger(__name__)

    def handle(self,
               session: Conversation,
               messages: List[Dict[str, Any]],
               response_message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process tool calls from an assistant response and extend messages.

        Args:
            session: The active QuerySession to update.
            messages: The running list of chat messages (will be mutated).
            response_message: The assistant response that includes tool_calls.

        Returns:
            The updated messages list (same object for convenience).
        """
        # Add assistant message with tool calls
        messages.append({
            "role": "assistant",
            "content": response_message.get("content"),
            "tool_calls": response_message["tool_calls"],
        })

        # Execute each tool exactly once and add the serialized result
        for tool_call in response_message["tool_calls"]:
            try:
                function_name = tool_call["function"]["name"]
                arguments = tool_call["function"].get("arguments", "{}")
                if isinstance(arguments, str):
                    arguments = json.loads(arguments)

                self.logger.info(f"Executing tool: {function_name}")

                # If the model attempts to call the final answer tool, override
                # arguments with authoritative data from the session dossier.
                # No argument injection: tools obtain context from the session/dossier

                # Execute tool and serialize for LLM
                tool_result = self.tool_manager.execute_tool(function_name, **arguments)
                # For retrieval tools, avoid putting full content in the conversation.
                if function_name in ["get_legislation", "get_case_law"]:
                    result_payload = {
                        "success": tool_result.success,
                        "data": None,  # prevent large content from entering the transcript
                        "metadata": {
                            **(tool_result.metadata or {}),
                            "note": "content stored in session dossier; titles only in convo"
                        },
                    }
                    result_str = json.dumps(result_payload, ensure_ascii=False)
                else:
                    result_str = self.tool_manager.serialize_result_json(tool_result)
                    result_payload = json.loads(result_str)

                # Mirror successful source-gathering results into the session
                if function_name in ["get_legislation", "get_case_law"] and result_payload.get("success"):
                    session.add_source(function_name, tool_result)
                    session.transition_to(WorkflowState.ACTIVE)

                # Handle removal tool by updating selection (do not delete items)
                if function_name == "remove_sources" and result_payload.get("success"):
                    try:
                        # Result data may be a Pydantic model or a plain dict
                        decision = tool_result.data
                        remove_ids = []
                        if hasattr(decision, 'remove_ids'):
                            remove_ids = list(getattr(decision, 'remove_ids') or [])
                        elif isinstance(decision, dict):
                            remove_ids = list(decision.get('remove_ids') or [])

                        if remove_ids:
                            # Update selection: mark these IDs as unselected
                            before_sel = len(session.dossier.selected_ids)
                            session.dossier.selected_ids = [sid for sid in session.dossier.selected_ids if sid not in remove_ids]
                            removed_count = before_sel - len(session.dossier.selected_ids)
                            self.logger.info(f"Unselected {removed_count} sources via remove_sources tool")
                            session.transition_to(WorkflowState.ACTIVE)
                    except Exception as e:
                        self.logger.warning(f"Failed to apply remove_sources decision: {e}")

                # Append tool message for the LLM to consume
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": result_str,
                })

            except Exception as e:
                self.logger.error(f"Error executing tool call: {e}")
                error_result = json.dumps({"success": False, "error": str(e)})
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get("id", "unknown"),
                    "content": error_result,
                })

        return messages

    # No per-tool injectors: context-aware tools should read from session/dossier directly
