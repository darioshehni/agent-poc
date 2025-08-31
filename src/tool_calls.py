"""
Tool call execution and patch application.

What it does (in plain terms):
- Resolves and executes the tools requested by the model (function calling).
- Passes the current Dossier plus tool arguments to each tool.
- Collects DossierPatch objects from tools and applies them under a per‑dossier
  async lock (single writer per dossier).
- Appends a compact tool result to the messages for the model (no large content).
- Returns a tuple: (updated messages, outcomes), where outcomes is a list of
  {"function": str, "patch": DossierPatch | None} for the agent to present.

What it does NOT do:
- Format user‑visible messages (the agent presents patches to the user).
- Persist the dossier (the WebSocket server saves after sending the reply).
- Make additional LLM calls (the agent controls the LLM dialogue).
"""

from typing import Any, Dict, List
import json
import logging
import asyncio

from src.models import Dossier
from src.models import DossierPatch


class ToolCallHandler:
    """Run model tool calls, apply tool patches, and return outcomes.

    Simple contract: given a Dossier, the live message list, and the model's
    tool_calls, this handler executes the tools, applies their DossierPatch
    results under a per‑dossier lock, appends a compact tool observation to the
    messages, and returns (messages, outcomes) for the agent to present.
    """

    def __init__(self, tools_map: Dict[str, Any], logger: logging.Logger | None = None) -> None:
        self.tools_map = tools_map
        self.logger = logger or logging.getLogger(__name__)
        self._locks: Dict[str, asyncio.Lock] = {}

    def _get_lock(self, dossier_id: str) -> asyncio.Lock:
        if dossier_id not in self._locks:
            self._locks[dossier_id] = asyncio.Lock()
        return self._locks[dossier_id]

    async def handle(
        self,
        session: Dossier,
        messages: List[Dict[str, Any]],
        response_message: Dict[str, Any],
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Execute tool_calls, apply patches, and return (messages, outcomes).

        - Executes each tool exactly once with the current Dossier and its args.
        - Applies all returned DossierPatch objects under a per‑dossier lock.
        - Appends a compact observation message for the model (no large payloads).
        - Returns (updated messages, outcomes) where outcomes = [{"function", "patch"}].
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

        # Execute each tool, collect patches and messages
        tool_outcomes: List[Dict[str, Any]] = []
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

                # Execute tool and serialize for LLM
                tool_fn = self.tools_map.get(function_name)
                if not tool_fn:
                    raise ValueError(f"Unknown tool: {function_name}")
                tool_result = await tool_fn(dossier=session, **arguments)
                # For retrieval tools, avoid putting full content in the conversation.
                # Minimal payload back to the LLM; we do not expose full content
                result_payload = {"success": bool(getattr(tool_result, "success", True))}
                result_str = json.dumps(result_payload, ensure_ascii=False)

                # Mirror successful source-gathering results into the session (message only)
                success_flag = False
                if isinstance(result_payload, dict) and "success" in result_payload:
                    success_flag = bool(result_payload["success"])
                # Record outcome (patch + optional message) for later application
                if success_flag:
                    tool_outcomes.append({
                        "function": function_name,
                        "patch": tool_result.patch,
                        "message": tool_result.message,
                        "data": getattr(tool_result, "data", None),
                    })

                # Handle removal tool by updating selection (do not delete items)
                # remove_sources is handled via patches like others; nothing special here

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

        # Apply all patches/messages under a per‑dossier lock
        try:
            lock = self._get_lock(session.dossier_id)
        except Exception:
            lock = None

        async def _apply_all():
            for out in tool_outcomes:
                patch = out.get("patch")
                if isinstance(patch, DossierPatch):
                    patch.apply(session)
                # If a standalone message was returned, append it
                msg = (out.get("message") or "").strip()
                if msg:
                    session.add_conversation_assistant(msg)

        if lock is not None:
            async with lock:
                await _apply_all()
        else:
            await _apply_all()

        return messages, tool_outcomes

    # No per-tool injectors: context-aware tools should read from session/dossier directly
