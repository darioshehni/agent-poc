"""
LLM client implementations for the tax chatbot.
"""

import os
import json
from typing import Dict, List, Any
import logging

from openai import OpenAI

try:
    from .base import LLMClient
except ImportError:
    from base import LLMClient

logger = logging.getLogger(__name__)


class OpenAIClient(LLMClient):
    """OpenAI client implementation."""
    
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = model
        self._client = None
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
    
    def _get_client(self) -> OpenAI:
        """Lazy initialization of OpenAI client."""
        if not self._client:
            self._client = OpenAI(api_key=self.api_key)
        return self._client
    
    def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        tools: List[Dict[str, Any]] = None,
        temperature: float = 0.0,
        max_tokens: int = 2000,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate a chat completion using OpenAI API."""
        
        client = self._get_client()
        
        # Prepare request parameters
        request_params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }
        
        # Add tools if provided
        if tools:
            request_params["tools"] = tools
            request_params["tool_choice"] = "auto"
        
        try:
            logger.debug(f"Making OpenAI request with {len(messages)} messages")
            
            response = client.chat.completions.create(**request_params)
            
            # Convert response to dict format
            result = {
                "choices": [
                    {
                        "message": {
                            "role": response.choices[0].message.role,
                            "content": response.choices[0].message.content,
                        }
                    }
                ],
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                }
            }
            
            # Add tool calls if present
            if response.choices[0].message.tool_calls:
                result["choices"][0]["message"]["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in response.choices[0].message.tool_calls
                ]
            
            logger.debug(f"OpenAI request completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}", exc_info=True)
            raise


class MockLLMClient(LLMClient):
    """Mock LLM client for testing."""
    
    def __init__(self, responses: List[str] = None):
        self.responses = responses or ["Mock response"]
        self.call_count = 0
    
    def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        tools: List[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Return a mock response."""
        
        response_text = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        
        result = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": response_text
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 10,
                "total_tokens": 20
            }
        }
        
        # Mock tool calls if tools are provided
        if tools and "get_legislation" in response_text:
            result["choices"][0]["message"]["tool_calls"] = [
                {
                    "id": "mock_call_1",
                    "type": "function",
                    "function": {
                        "name": "get_legislation",
                        "arguments": '{"query": "mock query"}'
                    }
                }
            ]
        
        return result


# Legacy ToolExecutor removed; tools are executed via ToolManager in src/base.py
