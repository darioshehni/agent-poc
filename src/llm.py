"""
Async LLM client used across the codebase (prompt formatting + OpenAI calls).
"""

import os
import logging
from typing import Any, Dict, List, Optional, Type

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel

load_dotenv()


class LlmAnswer(BaseModel):
    """Unified LLM answer wrapper returned by LlmChat.chat.

    - answer: string form of the model output.
    - tool_calls: names of tools the model decided to call in this turn.
    """
    answer: str
    tool_calls: List[str] = []


class LlmChat:
    """Handle LLM interaction: prompt formatting, chat (tools/structured)."""

    def __init__(self, logger_: Optional[logging.Logger] = None) -> None:
        self.logger = logger_ or logging.getLogger(__name__)
        self._openai_client = self._get_openai_client()

    def _get_openai_client(self) -> AsyncOpenAI:
        """Initialize and return AsyncOpenAI client."""
        try:
            api_key = os.environ["OPENAI_API_KEY"]
            return AsyncOpenAI(api_key=api_key)
        except Exception as e:
            self.logger.error(f"Error initializing OpenAI client: {e}")
            raise

    @staticmethod
    def fill_prompt_template(prompt_template: str, prompt_kwargs: Dict[str, str]) -> str:
        """Fill placeholders like {name} with values from prompt_kwargs."""
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
        """Chat; `messages` may be a full list or a single user string."""

        # Accept a single string or a full message list
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
        if not isinstance(messages, list) or not messages:
            raise ValueError("messages must be a non-empty list or a string")

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
            resp = await self._openai_client.chat.completions.create(**params)
            msg = resp.choices[0].message
            tool_calls = [tc.function.name for tc in (msg.tool_calls or [])]
            return LlmAnswer(answer=msg.content or "", tool_calls=tool_calls)
        except Exception as e:
            self.logger.error(f"Chat completion failed: {e}")
            raise

    async def chat_structured(
        self,
        messages: List[Dict[str, Any]] | str,
        model_name: str,
        response_format: Type[BaseModel],
    ) -> BaseModel:
        """Structured call that returns a parsed Pydantic model (no tools)."""
        try:
            if isinstance(messages, str):
                messages = [{"role": "user", "content": messages}]
            resp = await self._openai_client.responses.parse(  # type: ignore[attr-defined]
                model=model_name,
                input=messages,
                text_format=response_format,
            )
            return resp.output_parsed
        except Exception as e:
            self.logger.error(f"Structured chat parse failed: {e}")
            raise
