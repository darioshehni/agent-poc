"""
Session and state management for conversations.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

try:
    from .base import WorkflowState, ToolResult
except ImportError:
    from base import WorkflowState, ToolResult

logger = logging.getLogger(__name__)


@dataclass
class QuerySession:
    """Manages the state of a single conversation session."""
    
    session_id: str
    current_question: str = ""
    state: WorkflowState = WorkflowState.IDLE  # Simplified: just IDLE or ACTIVE
    sources: Dict[str, ToolResult] = field(default_factory=dict)
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def add_source(self, tool_name: str, result: ToolResult) -> None:
        """Add a tool result as a source."""
        self.sources[tool_name] = result
        self.updated_at = datetime.now()
        
    def remove_source(self, tool_name: str) -> bool:
        """Remove a source. Returns True if source existed."""
        removed = self.sources.pop(tool_name, None) is not None
        if removed:
            self.updated_at = datetime.now()
        return removed
        
    def get_source(self, tool_name: str) -> Optional[ToolResult]:
        """Get a specific source."""
        return self.sources.get(tool_name)
        
    def has_sources(self, tool_names: List[str]) -> bool:
        """Check if all specified tools have been executed successfully."""
        return all(
            tool_name in self.sources and self.sources[tool_name].success
            for tool_name in tool_names
        )
        
    def clear_sources(self) -> None:
        """Clear all sources."""
        self.sources.clear()
        self.updated_at = datetime.now()
        
    def add_message(self, role: str, content: str) -> None:
        """Add a message to conversation history."""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.updated_at = datetime.now()
        
    def get_source_summary(self) -> Dict[str, str]:
        """Get a summary of available sources."""
        summary = {}
        for tool_name, result in self.sources.items():
            if result.success:
                summary[tool_name] = "✓ Available"
            else:
                summary[tool_name] = f"✗ Failed: {result.error_message}"
        return summary
    
    def get_source_names_for_display(self) -> List[str]:
        """Get source names/titles for display to user (not full content)."""
        source_names = []
        
        for tool_name, result in self.sources.items():
            if result.success and result.data:
                # Extract source names based on tool type
                if tool_name == "get_legislation":
                    for item in result.data:
                        if isinstance(item, dict) and "source" in item:
                            source_names.append(item["source"])
                        elif isinstance(item, str):
                            # For backward compatibility, extract from content
                            if ":" in item:
                                source_names.append(item.split(":")[0].strip())
                            else:
                                source_names.append(item[:100] + "..." if len(item) > 100 else item)
                
                elif tool_name == "get_case_law":
                    for item in result.data:
                        if isinstance(item, dict) and "source" in item:
                            source_names.append(item["source"])
                        elif isinstance(item, str):
                            # Extract ECLI number or court case reference
                            if "ECLI:" in item:
                                # Extract ECLI reference
                                ecli_start = item.find("ECLI:")
                                ecli_end = item.find(" ", ecli_start)
                                if ecli_end == -1:
                                    ecli_end = ecli_start + 50  # fallback
                                source_names.append(item[ecli_start:ecli_end])
                            else:
                                source_names.append(item[:100] + "..." if len(item) > 100 else item)
        
        return source_names
        
    def transition_to(self, new_state: WorkflowState) -> None:
        """Transition to a new workflow state."""
        self.state = new_state
        self.updated_at = datetime.now()


class SessionManager:
    """Manages multiple conversation sessions."""
    
    def __init__(self):
        self._sessions: Dict[str, QuerySession] = {}
    
    def create_session(self, session_id: str) -> QuerySession:
        """Create a new session."""
        session = QuerySession(session_id=session_id)
        self._sessions[session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[QuerySession]:
        """Get an existing session."""
        return self._sessions.get(session_id)
    
    def get_or_create_session(self, session_id: str) -> QuerySession:
        """Get existing session or create new one."""
        if session_id not in self._sessions:
            return self.create_session(session_id)
        return self._sessions[session_id]
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session. Returns True if session existed."""
        return self._sessions.pop(session_id, None) is not None
    
    def list_sessions(self) -> List[str]:
        """Get list of all session IDs."""
        return list(self._sessions.keys())
    
    def cleanup_old_sessions(self, hours_old: int = 24) -> int:
        """Remove sessions older than specified hours. Returns count removed."""
        cutoff_time = datetime.now().timestamp() - (hours_old * 3600)
        to_remove = [
            session_id for session_id, session in self._sessions.items()
            if session.updated_at.timestamp() < cutoff_time
        ]
        
        for session_id in to_remove:
            del self._sessions[session_id]
            
        return len(to_remove)


class WorkflowEngine:
    """Simplified workflow management - just tracks source collection."""
    
    def __init__(self):
        self.required_tools = ["get_legislation", "get_case_law"]
    
    def process_tool_result(
        self, 
        session: QuerySession, 
        tool_name: str, 
        result: ToolResult
    ) -> WorkflowState:
        """
        Process a tool result. Just add to session and mark as active.
        The LLM handles all workflow logic through conversation context.
        """
        # Add result to session
        session.add_source(tool_name, result)
        
        # Return ACTIVE when working with tools
        return WorkflowState.ACTIVE