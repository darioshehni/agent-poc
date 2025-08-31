"""
Tool call execution and patch application (simplified).

Responsibilities:
- Resolve and execute the tools requested by the model (function calling).
- Pass the current Dossier plus parsed tool arguments to each tool.
- Collect DossierPatch objects from tools and apply them under a per‑dossier
  async lock (single writer per dossier).
- Return a list of outcomes for the agent/presenter to turn into user messages.

This handler does NOT mutate the LLM message list or make follow‑up LLM calls.
"""

from typing import Any, Dict, List
import json
import logging
import asyncio

from src.models import Dossier, DossierPatch


class ToolCallHandler:
    """Execute model tool calls and apply patches.

    Given a Dossier and the list of tool_calls from the model, execute each
    tool exactly once, apply all returned patches under a lock, and return
    a list of outcomes in a stable shape:
        [{"function": str, "patch": DossierPatch | None, "message": str, "data": Any, "success": bool}]
    """

    def __init__(self, tools_map: Dict[str, Any], logger: logging.Logger | None = None) -> None:
        self.tools_map = tools_map
        self.logger = logger or logging.getLogger(__name__)

    async def run(
        self,
        dossier: Dossier,
        tool_calls: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Execute tool_calls, apply patches, and return outcomes.

        - Executes each tool exactly once with the current Dossier and its args.
        - Applies all returned DossierPatch objects under a per‑dossier lock.
        - Returns outcomes = [{"function", "patch", "message", "data", "success"}].
        """
        # Normalize tool_calls to a list of dicts
        if not isinstance(tool_calls, list):
            self.logger.error("tool_calls must be a list; got %s", type(tool_calls).__name__)
            raise ValueError("tool_calls must be a list")

        normalized_calls: List[Dict[str, Any]] = []
        for raw in tool_calls:
            if isinstance(raw, dict):
                normalized_calls.append(raw)
            elif isinstance(raw, str):
                try:
                    normalized_calls.append(json.loads(raw))
                except Exception:
                    self.logger.error("Failed to parse tool_call string; skipping")
                    continue
            else:
                self.logger.error("Invalid tool_call entry type: %s", type(raw).__name__)

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

                # Strict argument contract: tools must receive 'query'
                fname = (function_name or "").strip()
                if fname in {"remove_sources", "generate_tax_answer", "restore_sources"}:
                    q = arguments.get("query")
                    if not isinstance(q, str) or not q.strip():
                        raise ValueError(f"{fname} requires a non-empty 'query' parameter")

                self.logger.info(f"TOOL: executing {function_name} args={arguments}")

                # Execute tool and serialize for LLM
                tool_function = self.tools_map.get(function_name)
                if not tool_function:
                    raise ValueError(f"Unknown tool: {function_name}")
                tool_result = await tool_function(dossier=dossier, **arguments)
                # Record outcome (patch + optional message) for later application
                out = {
                    "function": function_name,
                    "patch": getattr(tool_result, "patch", None),
                    "message": getattr(tool_result, "message", ""),
                    "data": getattr(tool_result, "data", None),
                    "success": bool(getattr(tool_result, "success", True)),
                }
                # Log patch summary if present
                patch = out["patch"]
                if patch is not None:
                    try:
                        leg_n = len(getattr(patch, "add_legislation", []) or [])
                        case_n = len(getattr(patch, "add_case_law", []) or [])
                        rem_n = len(getattr(patch, "unselect_titles", []) or [])
                        self.logger.info(f"TOOL: {function_name} success={out['success']} patch(add_leg={leg_n}, add_case={case_n}, unselect={rem_n})")
                    except Exception:
                        pass
                tool_outcomes.append(out)

            except Exception as e:
                self.logger.error(f"Error executing tool call: {e}")
                tool_outcomes.append({
                    "function": (tool_call.get("function", {}) or {}).get("name", "unknown") if isinstance(tool_call, dict) else "unknown",
                    "patch": None,
                    "message": f"Error: {e}",
                    "data": None,
                    "success": False,
                })


        # Apply all patches/messages under a per‑dossier lock
        # We don't keep explicit locks here; ToolCallHandler is per-assistant.
        for output in tool_outcomes:
            patch = output.get("patch")
            if isinstance(patch, DossierPatch):
                patch.apply(dossier)
            # If a standalone message was returned, append it
            msg = (output.get("message") or "").strip()
            if msg:
                dossier.add_conversation_assistant(msg)

        return tool_outcomes
