"""
Base classes and core components for the tax chatbot.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json
import logging
from dataclasses import is_dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Result from a tool execution."""
    success: bool
    data: Any
    error_message: str = ""
    metadata: Dict[str, Any] = None
    message: str = ""
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseTool(ABC):
    """Abstract base class for all tools."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for the tool."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what the tool does."""
        pass
    
    @property
    @abstractmethod
    def parameters_schema(self) -> Dict[str, Any]:
        """JSON schema for the tool's parameters."""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters (async)."""
        pass
    
    def to_function_schema(self) -> Dict[str, Any]:
        """Convert tool to OpenAI function calling schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema
            }
        }


class LLMClient(ABC):
    """Abstract interface for LLM clients."""
    
    @abstractmethod
    def chat_completion(
        self, 
        conversation: List[Dict[str, str]],
        tools: List[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate a chat completion."""
        pass


class ToolManager:
    """Manages tools: registration, validation, execution, and schema generation."""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool) -> None:
        """Register a new tool."""
        if not isinstance(tool, BaseTool):
            raise TypeError(f"Tool must inherit from BaseTool, got {type(tool)}")
        
        if tool.name in self._tools:
            logger.warning(f"Tool {tool.name} already registered, overwriting")
        
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(tool_name)
    
    def list_tools(self) -> List[str]:
        """Get list of registered tool names."""
        return list(self._tools.keys())
    
    def get_function_schemas(self) -> List[Dict[str, Any]]:
        """Get OpenAI function schemas for all tools."""
        return [tool.to_function_schema() for tool in self._tools.values()]
    
    async def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a tool with given parameters (async)."""
        tool = self._tools.get(tool_name)
        
        if not tool:
            return ToolResult(
                success=False,
                data=None,
                error_message=f"Tool '{tool_name}' not found. Available tools: {list(self._tools.keys())}"
            )
        
        try:
            logger.debug(f"Executing tool {tool_name} with args: {kwargs}")
            result = await tool.execute(**kwargs)
            logger.debug(f"Tool {tool_name} completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Tool {tool_name} execution failed: {str(e)}", exc_info=True)
            return ToolResult(
                success=False,
                data=None,
                error_message=f"Tool execution failed: {str(e)}"
            )
    
    def execute_function_call(self, function_name: str, arguments: Dict[str, Any]) -> str:
        """
        Execute a function call from OpenAI and return result as JSON string.
        This is the interface between OpenAI function calling and our tool system.
        """
        try:
            # Parse arguments if they're a JSON string
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            
            # Execute the tool
            result = self.execute_tool(function_name, **arguments)
            
            return self.serialize_result_json(result)
                
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON arguments for {function_name}: {str(e)}"
            logger.error(error_msg)
            return json.dumps({"success": False, "error": error_msg}, ensure_ascii=False)
            
        except Exception as e:
            error_msg = f"Unexpected error executing {function_name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return json.dumps({"success": False, "error": error_msg}, ensure_ascii=False)

    def _serialize_data(self, data: Any) -> Any:
        """Convert tool result data to JSON-serializable form.
        - Dataclasses with to_dict or dataclass instances are converted to dicts
        - Lists are processed recursively
        - Other types are returned as-is
        """
        if data is None:
            return None
        # Pydantic model
        if hasattr(data, "model_dump") and callable(getattr(data, "model_dump")):
            try:
                return data.model_dump()
            except Exception:
                pass
        # Dataclass with custom to_dict
        if hasattr(data, "to_dict") and callable(getattr(data, "to_dict")):
            try:
                return data.to_dict()
            except Exception:
                pass
        # Generic dataclass
        if is_dataclass(data):
            return asdict(data)
        # List/tuple
        if isinstance(data, (list, tuple)):
            return [self._serialize_data(x) for x in data]
        # Dict
        if isinstance(data, dict):
            return {k: self._serialize_data(v) for k, v in data.items()}
        # Fallback
        return data

    def serialize_result(self, result: ToolResult) -> Dict[str, Any]:
        """Serialize ToolResult to a JSON-safe dict."""
        if result.success:
            return {
                "success": True,
                "data": self._serialize_data(result.data),
                "metadata": self._serialize_data(result.metadata or {}),
                "message": result.message or "",
            }
        else:
            return {
                "success": False,
                "error": result.error_message,
                "data": None,
            }

    def serialize_result_json(self, result: ToolResult) -> str:
        """Serialize ToolResult to a JSON string."""
        try:
            return json.dumps(self.serialize_result(result), ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to serialize ToolResult: {e}")
            # Fallback minimal error payload
            return json.dumps({"success": False, "error": "serialization_error"}, ensure_ascii=False)
    
    def validate_tools(self) -> List[str]:
        """Validate all registered tools. Returns list of validation errors."""
        errors = []
        
        for tool_name, tool in self._tools.items():
            try:
                # Basic validation
                if not tool.name:
                    errors.append(f"Tool {tool_name}: name is empty")
                
                if not tool.description:
                    errors.append(f"Tool {tool_name}: description is empty")
                
                if not tool.parameters_schema:
                    errors.append(f"Tool {tool_name}: parameters_schema is empty")
                
                # Test schema generation
                schema = tool.to_function_schema()
                if not isinstance(schema, dict):
                    errors.append(f"Tool {tool_name}: to_function_schema() must return dict")
                
            except Exception as e:
                errors.append(f"Tool {tool_name}: validation error - {str(e)}")
        
        return errors
