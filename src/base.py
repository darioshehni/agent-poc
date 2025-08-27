"""
Base classes and core components for the tax chatbot.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class WorkflowState(Enum):
    """Simple states for conversation workflow."""
    IDLE = "idle"
    ACTIVE = "active"  # Simplified: either idle or actively working


@dataclass
class ToolResult:
    """Result from a tool execution."""
    success: bool
    data: Any
    error_message: str = ""
    metadata: Dict[str, Any] = None
    
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
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
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
        messages: List[Dict[str, str]], 
        tools: List[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate a chat completion."""
        pass


class ToolRegistry:
    """Registry for managing available tools."""
    
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
    
    def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a tool with given parameters."""
        tool = self._tools.get(tool_name)
        
        if not tool:
            return ToolResult(
                success=False,
                data=None,
                error_message=f"Tool '{tool_name}' not found. Available tools: {list(self._tools.keys())}"
            )
        
        try:
            logger.debug(f"Executing tool {tool_name} with args: {kwargs}")
            result = tool.execute(**kwargs)
            logger.debug(f"Tool {tool_name} completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Tool {tool_name} execution failed: {str(e)}", exc_info=True)
            return ToolResult(
                success=False,
                data=None,
                error_message=f"Tool execution failed: {str(e)}"
            )
    
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