"""
Tool call orchestration for the agent.

Purpose
-------
This module is the glue between the LLM's function-calling output and the
chatbot's internal execution/runtime state. The LLM decides which tools to
call (and with what arguments) based on the system prompt and conversation.
The handler executes those tool calls via the ToolManager, updates the
dossier accordingly, and appends compact tool results back into the
conversation messages so the LLM can produce a final response.


Interactions with other components
----------------------------------
- ToolManager: Used to execute tools and to serialize ToolResult payloads.
- QuerySession/SessionManager: Tools update the dossier directly; the handler
  only appends compact tool observations/messages for the LLM. Persisting to
  disk is performed by the server after a turn completes.
- AnswerTool: Not called here directly. When the LLM later calls the answer
  tool, it reads context from the dossier to compose its prompt.

This module does not:
- Call the LLM for follow-up content (the Agent does that after handling tools).
- Inject large text into the conversation history.
- Perform persistence (the Agent triggers persistence in SessionManager).
"""

from typing import Any, Dict, List
import json
import logging

from src.models import Dossier
from src.base import ToolManager


class ToolCallHandler:
    """Execute tool_calls via ToolManager and update the session dossier.

    Adds compact tool observations to messages; retrieval tools include
    metadata only. No persistence or final LLM call here.
    """

    def __init__(self, tool_manager: ToolManager, logger: logging.Logger | None = None) -> None:
        self.tool_manager = tool_manager
        self.logger = logger or logging.getLogger(__name__)

    async def handle(
        self,
        session: Dossier,
        messages: List[Dict[str, Any]],
        response_message: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Run tool_calls, update dossier, append tool observations.

        - Retrieval: include metadata-only output and append a user-facing message.
        - Removal: tools should unselect titles in the dossier; handler appends message.
        """
        # Add assistant message with tool calls
        # Normalize tool_calls to a list of dicts
        raw_calls = response_message["tool_calls"]
        if not isinstance(raw_calls, list):
            self.logger.error("tool_calls must be a list; got %s", type(raw_calls).__name__)
            return messages

        normalized_calls: List[Dict[str, Any]] = []
        for raw in raw_calls:
            if isinstance(raw, dict):
                normalized_calls.append(raw)
            elif isinstance(raw, str):
                try:
                    normalized_calls.append(json.loads(raw))
                except Exception:
                    self.logger.error("Failed to parse tool_call string; skipping")
            else:
                self.logger.error("Invalid tool_call entry type: %s", type(raw).__name__)

        assistant_msg: Dict[str, Any] = {
            "role": "assistant",
            "content": response_message["content"] or "",
        }
        if normalized_calls:
            assistant_msg["tool_calls"] = normalized_calls
        messages.append(assistant_msg)

        # Execute each tool exactly once and add the serialized result
        for tool_call in normalized_calls:
            try:
                if not isinstance(tool_call, dict):
                    # Sometimes SDK objects or strings slip through; try to coerce JSON strings
                    if isinstance(tool_call, str):
                        tool_call = json.loads(tool_call)
                    else:
                        raise TypeError("Invalid tool_call entry type")
                function = tool_call["function"]
                function_name = function["name"]
                arguments = function["arguments"] if "arguments" in function else {}
                if isinstance(arguments, str):
                    if arguments.strip():
                        arguments = json.loads(arguments)
                    else:
                        arguments = {}
                elif not isinstance(arguments, dict):
                    arguments = {}

                self.logger.info(f"Executing tool: {function_name}")

                # If the model attempts to call the final answer tool, override
                # arguments with authoritative data from the session dossier.
                # No argument injection: tools obtain context from the session/dossier

                # Execute tool and serialize for LLM
                tool_result = await self.tool_manager.execute_tool(function_name, **arguments)
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

                # Mirror successful source-gathering results into the session (message only)
                success_flag = False
                if isinstance(result_payload, dict) and "success" in result_payload:
                    success_flag = bool(result_payload["success"])
                if function_name in ["get_legislation", "get_case_law"] and success_flag:
                    md = tool_result.metadata or {}
                    # Prefer a tool-provided message; otherwise curate titles prompt
                    if (tool_result.message or "").strip():
                        session.add_conversation_assistant(tool_result.message.strip())
                    else:
                        titles = []
                        if isinstance(md, dict) and "source_names" in md and md["source_names"]:
                            titles = list(md["source_names"])[:5]
                        if titles:
                            lines = ["Ik vond de volgende bronnen:"]
                            for i, t in enumerate(titles, 1):
                                lines.append(f"{i}. {t}")
                            lines.append("Zijn deze bronnen correct voor uw vraag?")
                            session.add_conversation_assistant("\n".join(lines))

                # Handle removal tool by updating selection (do not delete items)
                if function_name == "remove_sources" and success_flag:
                    try:
                        # Result data may be a Pydantic model or a plain dict
                        decision = tool_result.data
                        remove_ids: list[str] = []
                        # New structured output: DocumentTitles.titles
                        if hasattr(decision, 'titles'):
                            remove_ids = list(getattr(decision, 'titles') or [])
                        elif isinstance(decision, dict):
                            if 'titles' in decision and decision['titles']:
                                remove_ids = list(decision['titles'])
                            elif 'remove_ids' in decision and decision['remove_ids']:
                                # Backward compatibility
                                remove_ids = list(decision['remove_ids'])

                        # If the tool already applied changes, it should set the metadata flag.
                        md = tool_result.metadata or {}
                        if not (isinstance(md, dict) and md.get("dossier_updated")):
                            if remove_ids:
                                before_sel = len(session.dossier.selected_ids)
                                session.dossier.selected_ids = [sid for sid in session.dossier.selected_ids if sid not in remove_ids]
                                removed_count = before_sel - len(session.dossier.selected_ids)
                                self.logger.info(f"Unselected {removed_count} sources via remove_sources tool (handler applied)")
                                if removed_count > 0:
                                    session.add_conversation_assistant("Ik heb de genoemde bronnen uit de selectie gehaald.")
                            # No workflow state machine; rely on conversation

                        # Append any tool-provided assistant message
                        if (tool_result.message or "").strip():
                            session.add_conversation_assistant(tool_result.message.strip())
                    except Exception as e:
                        self.logger.warning(f"Failed to apply remove_sources decision: {e}")

                # Append tool message for the LLM to consume
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"] if "id" in tool_call else "unknown",
                    "content": result_str,
                })

            except Exception as e:
                self.logger.error(f"Error executing tool call: {e}")
                error_result = json.dumps({"success": False, "error": str(e)})
                tool_call_id = "unknown"
                if isinstance(tool_call, dict) and "id" in tool_call:
                    tool_call_id = tool_call["id"]
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": error_result,
                })

        return messages

    # No per-tool injectors: context-aware tools should read from session/dossier directly
