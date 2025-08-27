"""
Session and state management for conversations.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from pathlib import Path
import json

try:
    from .base import WorkflowState, ToolResult
    from .models import Dossier, Legislation, CaseLaw
except ImportError:
    from base import WorkflowState, ToolResult
    from models import Dossier, Legislation, CaseLaw

logger = logging.getLogger(__name__)


@dataclass
class Conversation:
    """Manages the state of a single conversation session."""
    
    session_id: str
    current_question: str = ""
    state: WorkflowState = WorkflowState.IDLE  # Simplified: just IDLE or ACTIVE
    sources: Dict[str, ToolResult] = field(default_factory=dict)
    dossier: Dossier = field(default_factory=Dossier)
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def add_source(self, tool_name: str, result: ToolResult) -> None:
        """Add a tool result as a source and mirror into the dossier.

        This method updates in-memory state only. Persistence is handled by
        SessionManager to keep the data model free of I/O side effects.
        """
        self.sources[tool_name] = result
        # Mirror into dossier when possible
        try:
            if result and result.success and result.data:
                if tool_name == "get_legislation":
                    items: List[Any] = result.data if isinstance(result.data, list) else [result.data]
                    leg_items: List[Legislation] = [x for x in items if isinstance(x, Legislation)]
                    if leg_items:
                        self.dossier.add_legislation(leg_items)
                        # Default selection: newly added items are selected
                        for it in leg_items:
                            if it.id not in self.dossier.selected_ids:
                                self.dossier.selected_ids.append(it.id)
                elif tool_name == "get_case_law":
                    items = result.data if isinstance(result.data, list) else [result.data]
                    case_items: List[CaseLaw] = [x for x in items if isinstance(x, CaseLaw)]
                    if case_items:
                        self.dossier.add_case_law(case_items)
                        # Default selection: newly added items are selected
                        for it in case_items:
                            if it.id not in self.dossier.selected_ids:
                                self.dossier.selected_ids.append(it.id)
        except Exception:
            # Non-fatal: keep behavior compatible even if data shapes vary
            pass
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
        # Prefer dossier titles if available
        titles = self.dossier.titles()
        if titles:
            return titles

        source_names = []
        
        for tool_name, result in self.sources.items():
            if result.success and result.data:
                for item in result.data:
                    if isinstance(item, dict) and "source" in item:
                        source_names.append(item["source"])
                    elif hasattr(item, 'title'):
                        title = getattr(item, 'title', '')
                        if title:
                            source_names.append(title)
                    elif isinstance(item, str):
                        # Simple extraction - just take first line or reasonable length
                        first_line = item.split('\n')[0].strip()
                        if len(first_line) > 80:
                            first_line = first_line[:80] + "..."
                        source_names.append(first_line)

        return source_names
        
    def transition_to(self, new_state: WorkflowState) -> None:
        """Transition to a new workflow state."""
        self.state = new_state
        self.updated_at = datetime.now()


class SessionManager:
    """Manages multiple conversation sessions and simple dossier persistence.

    Responsibilities:
    - Create, retrieve, and cleanup in-memory sessions.
    - Persist the dossier for each session to a local JSON file (best-effort).
    - Lazily hydrate a session's dossier on first access if a saved file exists.
    """
    
    def __init__(self):
        self._sessions: Dict[str, Conversation] = {}
    
    def create_session(self, session_id: str) -> Conversation:
        """Create a new in-memory session with empty dossier and history."""
        session = Conversation(session_id=session_id)
        self._sessions[session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[Conversation]:
        """Get an existing session."""
        return self._sessions.get(session_id)
    
    def get_or_create_session(self, session_id: str) -> Conversation:
        """Get existing session or create one, hydrating dossier if available.

        If this is the first time we see the session_id and a dossier JSON
        exists on disk, we load it and mirror the dossier into sources.
        """
        if session_id in self._sessions:
            return self._sessions[session_id]

        # Try to load a persisted dossier
        loaded = self.load_session(session_id)
        if loaded:
            self._sessions[session_id] = loaded
            return loaded

        return self.create_session(session_id)
    
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

    # --- Persistence helpers ---
    def _base_dir(self) -> Path:
        return Path("data/dossiers")

    def _dossier_path(self, session_id: str) -> Path:
        return self._base_dir() / f"{session_id}.json"

    def save_session(self, session: Conversation) -> None:
        """Persist a session snapshot (dossier + summary) to local JSON."""
        try:
            base = self._base_dir()
            base.mkdir(parents=True, exist_ok=True)
            payload = {
                "session_id": session.session_id,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "state": session.state.value,
                "current_question": session.current_question,
                "dossier": session.dossier.to_dict(),
                # Keep history light; persist last N messages for context restore
                "conversation_history": session.conversation_history[-20:],
            }
            with self._dossier_path(session.session_id).open("w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save dossier for session {session.session_id}: {e}")

    def load_session(self, session_id: str) -> Optional[Conversation]:
        """Load a session from local JSON if available, else return None."""
        path = self._dossier_path(session_id)
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            session = Conversation(session_id=session_id)
            from .models import Dossier  # local import to avoid cycles at import time
            dossier = Dossier.from_dict(data.get("dossier", {}))
            session.dossier = dossier
            # Restore timestamps and state when present
            try:
                session.created_at = datetime.fromisoformat(data.get("created_at", session.created_at.isoformat()))
                session.updated_at = datetime.fromisoformat(data.get("updated_at", session.updated_at.isoformat()))
            except Exception:
                pass
            state_val = data.get("state")
            if state_val:
                try:
                    session.state = WorkflowState(state_val)
                except Exception:
                    pass
            session.current_question = data.get("current_question", "")
            # Restore recent conversation history if present
            history = data.get("conversation_history", [])
            if isinstance(history, list):
                session.conversation_history.extend(history)
            # Mirror dossier entries back into sources for prompt building
            self._mirror_dossier_to_sources(session)
            return session
        except Exception as e:
            logger.warning(f"Failed to load dossier for session {session_id}: {e}")
            return None

    def _mirror_dossier_to_sources(self, session: Conversation) -> None:
        """Reconstruct session.sources from the dossier contents.

        This provides a consistent view for context builders that rely on
        session.sources, even after a process restart.
        """
        from .base import ToolResult
        # Legislation
        if session.dossier.legislation:
            session.sources["get_legislation"] = ToolResult(
                success=True,
                data=list(session.dossier.legislation),
                metadata={"restored": True}
            )
        # Case law
        if session.dossier.case_law:
            session.sources["get_case_law"] = ToolResult(
                success=True,
                data=list(session.dossier.case_law),
                metadata={"restored": True}
            )


# WorkflowEngine removed - functionality moved directly to agent for simplicity
