"""
Async LLM client used across the codebase.

Provides:
- `chat(messages, model_name, tools=...)` → `LlmAnswer(answer, tool_calls)` where
  `messages` can be a list of {role, content} or a single string. When `tools`
  (function schemas) are supplied, tool_calls contains the tool names chosen by
  the model for this turn.
- `chat_structured(messages, model_name, response_format)` to parse typed
  responses into Pydantic models (used by the removal tool).
"""

import os
import logging
from typing import Any, Dict, List, Optional, Type

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel

load_dotenv()

logger = logging.getLogger(__name__)


class LlmAnswer(BaseModel):
    """Unified LLM answer wrapper returned by LlmChat.chat.

    - answer: string form of the model output.
    - tool_calls: structured tool call requests with function name and arguments
      as provided by the model SDK (normalized to dicts).
    """
    answer: str
    tool_calls: List[Dict[str, Any]] = []


class LlmChat:
    """Handle LLM interaction: prompt formatting, chat (tools/structured)."""

    def __init__(self, logger_: Optional[logging.Logger] = None) -> None:
        """Initialize the LLM chat client.
        
        Args:
            logger_: Optional custom logger instance. Uses module logger if None.
        """
        self.logger = logger_ or logging.getLogger(__name__)
        self._openai_client = self._get_openai_client()

    def _get_openai_client(self) -> AsyncOpenAI:
        """Initialize and return AsyncOpenAI client.
        
        Returns:
            Configured AsyncOpenAI client instance
            
        Raises:
            Exception: If OPENAI_API_KEY environment variable is missing or client init fails
        """
        try:
            api_key = os.environ["OPENAI_API_KEY"]
            return AsyncOpenAI(api_key=api_key)
        except Exception as e:
            self.logger.error(f"Error initializing OpenAI client: {e}")
            raise

    @staticmethod
    def fill_prompt_template(prompt_template: str, prompt_kwargs: Dict[str, str]) -> str:
        """Fill template placeholders with provided values.
        
        Args:
            prompt_template: Template string with {key} placeholders
            prompt_kwargs: Dictionary of key-value pairs to substitute
            
        Returns:
            Template string with all placeholders replaced
        """
        for key, value in prompt_kwargs.items():
            prompt_template = prompt_template.replace(f"{{{key}}}", value)
        return prompt_template

    async def chat(
        self,
        messages: List[Dict[str, Any]] | str,
        model_name: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = "auto",
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> LlmAnswer:
        """Perform a chat completion with optional tool calling support.
        
        Args:
            messages: Either a list of message dicts with 'role' and 'content' keys,
                     or a single string that will be treated as a user message
            model_name: OpenAI model name (e.g., 'gpt-4o')
            tools: Optional list of tool/function schemas for function calling
            tool_choice: How the model should choose tools ('auto', 'none', or specific tool)
            temperature: Sampling temperature (0.0 for deterministic)
            **kwargs: Additional parameters passed to OpenAI API
            
        Returns:
            LlmAnswer containing the response text and any tool calls requested
            
        Raises:
            ValueError: If messages is empty
            Exception: If OpenAI API call fails
        """

        if not messages:
            raise ValueError ("messages cannot be empty")
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]

        params: Dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            **kwargs,
        }
        if tools:
            params["tools"] = tools
            if tool_choice is not None:
                params["tool_choice"] = tool_choice

        try:
            # Debug: summarize request
            try:
                msg_count = len(messages) if isinstance(messages, list) else 1
                tool_count = len(params.get("tools", []) or [])
                self.logger.info(f"LLM(Chat) start model={model_name} messages={msg_count} tools={tool_count}")
            except Exception:
                pass

            response = await self._openai_client.chat.completions.create(**params)
            msg = response.choices[0].message
            finish = getattr(response.choices[0], "finish_reason", None)
            tool_calls: List[Dict[str, Any]] = []
            for tool_call in (msg.tool_calls or []):
                try:
                    tool_calls.append({
                        "id": getattr(tool_call, "id", None),
                        "type": getattr(tool_call, "type", "function"),
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments or "{}",
                        },
                    })
                except Exception:
                    logger.warning("Error parsing tool call, using fallback minimal shape")
                    # Fallback minimal shape
                    tool_calls.append({
                        "function": {"name": getattr(getattr(tool_call, 'function', object()), 'name', ''), "arguments": getattr(getattr(tool_call, 'function', object()), 'arguments', '{}')}
                    })
            # Debug: log finish and tool call names
            try:
                names = [tc.get("function", {}).get("name") for tc in tool_calls if isinstance(tc, dict)]
                self.logger.info(f"LLM(Chat) done finish={finish} tool_calls={len(tool_calls)} names={names}")
            except Exception:
                pass

            # Content may be None when the model chooses tool_calls.
            # Ensure we always return a string to satisfy LlmAnswer.
            answer_text: str = msg.content if isinstance(getattr(msg, "content", None), str) else ""
            return LlmAnswer(answer=answer_text, tool_calls=tool_calls)
        except Exception as e:
            self.logger.error(f"Chat completion failed: {e}")
            raise

    async def chat_structured(
        self,
        messages: List[Dict[str, Any]] | str,
        model_name: str,
        response_format: Type[BaseModel],
    ) -> BaseModel:
        """Perform structured chat completion that returns a parsed Pydantic model.
        
        Uses OpenAI's Responses API if available for structured parsing, otherwise
        falls back to prompting for JSON and parsing locally.
        
        Args:
            messages: Either a list of message dicts or a single string
            model_name: OpenAI model name
            response_format: Pydantic model class to parse response into
            
        Returns:
            Instance of the specified Pydantic model with parsed response data
            
        Raises:
            Exception: If both structured API and fallback JSON parsing fail
        """
        # Try Responses API first (if available in installed SDK)
        try:
            client_has_responses = hasattr(self._openai_client, "responses")
            if client_has_responses:
                try:
                    msg_count = len(messages) if isinstance(messages, list) else 1
                    self.logger.info(f"LLM(Structured) start model={model_name} messages={msg_count} format={response_format.__name__}")
                except Exception:
                    pass
                if isinstance(messages, str):
                    messages = [{"role": "user", "content": messages}]
                resp = await self._openai_client.responses.parse(  # type: ignore[attr-defined]
                    model=model_name,
                    input=messages,
                    text_format=response_format,
                )
                out = resp.output_parsed
                try:
                    self.logger.info(f"LLM(Structured) done via ResponsesAPI output={out.model_dump_json()}")
                except Exception:
                    pass
                return out
        except Exception as e:
            # Log and continue to fallback
            self.logger.error(f"Structured chat parse failed: {e}")

        # Fallback to Chat Completions: ask for JSON only and parse
        import json
        try:
            user_content: str
            if isinstance(messages, str):
                user_content = messages
            else:
                # Extract last user content if a list was provided
                user_msgs = [m for m in messages if m.get("role") == "user"] if isinstance(messages, list) else []
                user_content = user_msgs[-1]["content"] if user_msgs else (messages[-1]["content"] if messages else "")  # type: ignore[index]

            sys_prompt = (
                "Je produceert uitsluitend geldige JSON die exact voldoet aan dit schema: "
                "{\"titles\": [string, ...]}. Geen extra tekst of uitleg."
            )
            cc_messages = [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_content},
            ]
            cc_resp = await self._openai_client.chat.completions.create(
                model=model_name,
                messages=cc_messages,
                temperature=0,
            )
            text = getattr(cc_resp.choices[0].message, "content", None) or "{}"
            try:
                preview = text[:500].replace("\n", " ")
                self.logger.info(f"LLM(Structured) fallback raw={preview}")
            except Exception:
                pass
            # Attempt direct JSON parse
            try:
                obj = json.loads(text)
            except json.JSONDecodeError:
                # Try to locate a JSON object substring
                start = text.find("{")
                end = text.rfind("}")
                if start != -1 and end != -1 and end > start:
                    obj = json.loads(text[start : end + 1])
                else:
                    raise
            out = response_format.model_validate(obj)
            try:
                self.logger.info(f"LLM(Structured) done via Fallback output={out.model_dump_json()}")
            except Exception:
                pass
            return out
        except Exception as e:
            self.logger.error(f"Structured chat (fallback) failed: {e}")
            raise
