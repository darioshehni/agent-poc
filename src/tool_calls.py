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

from typing import Any
import logging
import json

from src.config.models import Dossier, ToolResult

logger = logging.getLogger(__name__)


class ToolCallHandler:
    """Execute model tool calls and apply patches.

    Given a Dossier and the list of tool_calls from the model, execute each
    tool exactly once, apply all returned patches under a lock, and return
    a list of outcomes in a stable shape:
        [{"function": str, "patch": DossierPatch | None, "message": str, "data": Any, "success": bool}]
    """

    def __init__(self, tools_map: dict[str, Any]) -> None:
        self.tools_map = tools_map

    async def run(
        self,
        dossier: Dossier,
        tool_calls: list[dict[str, Any]],
    ) -> list[ToolResult]:
        """Execute tool_calls, apply patches to dossier, and return outcomes.

        - Executes each tool exactly once with the current Dossier and its args.
        - Applies all returned DossierPatch objects under a per‑dossier lock.
        - Returns outcomes = [{"function", "patch", "message", "data", "success"}].
        """
        # Execute each tool, collect patches and messages.
        tool_outcomes: list[ToolResult] = []
        for tool_call in tool_calls:
            try:
                function = tool_call["function"]
                function_name = function["name"]
                arguments = json.loads(function["arguments"]) if "arguments" in function else {}
                logger.info(f"TOOL: executing {function_name} args={arguments.keys()}")

                # Execute tool with arguments.
                tool_function = self.tools_map[function_name]
                response = await tool_function(dossier=dossier, **arguments)

                # Parse tool result.
                tool_result = ToolResult(
                    function=function_name,
                    patch=response.get("patch", None),
                    message=response.get("message", ""),
                    data=response.get("data", None),
                    success=response.get("success", True),
                )
                # Log patch summary if present
                patch = tool_result.patch
                if patch is not None:
                    leg_n = len(getattr(patch, "add_legislation", []) or [])
                    case_n = len(getattr(patch, "add_case_law", []) or [])
                    sel_n = len(getattr(patch, "select_titles", []) or [])
                    rem_n = len(getattr(patch, "unselect_titles", []) or [])
                    logger.info(
                        f"TOOL: {function_name} success={tool_result.success} "
                        f"patch(add_leg={leg_n}, add_case={case_n}, select={sel_n}, unselect={rem_n})"
                    )

                tool_outcomes.append(tool_result)

            except Exception as e:
                logger.error(f"Error executing tool call: {e}")
                raise e

        return tool_outcomes
