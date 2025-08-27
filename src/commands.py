"""
Command system for handling user actions like "remove sources", "reformulate", etc.
"""

import re
from typing import List, Optional
from abc import ABC, abstractmethod

try:
    from .base import WorkflowState
    from .sessions import QuerySession
except ImportError:
    from base import WorkflowState
    from sessions import QuerySession


class BaseCommand(ABC):
    """Abstract base class for user commands."""
    
    @property
    @abstractmethod
    def pattern(self) -> str:
        """Regex pattern to match this command."""
        pass
    
    @abstractmethod
    def execute(self, session: QuerySession, match_groups: List[str]) -> str:
        """Execute the command with matched groups from regex."""
        pass


class RemoveSourceCommand(BaseCommand):
    """Command to remove specific sources."""
    
    @property
    def pattern(self) -> str:
        return r"(?:verwijder|remove|ignore).+(?:wetgeving|legislation|jurisprudentie|case.*law)"
    
    def execute(self, session: QuerySession, match_groups: List[str]) -> str:
        match_text = match_groups[0] if match_groups else ""
        
        removed_sources = []
        
        if "wetgeving" in match_text.lower() or "legislation" in match_text.lower():
            if session.remove_source("get_legislation"):
                removed_sources.append("wetgeving")
                
        if "jurisprudentie" in match_text.lower() or "case" in match_text.lower():
            if session.remove_source("get_case_law"):
                removed_sources.append("jurisprudentie")
        
        if removed_sources:
            session.transition_to(WorkflowState.ACTIVE)
            sources_text = " en ".join(removed_sources)
            return f"Ik heb de {sources_text} bronnen verwijderd. U kunt nu nieuwe instructies geven."
        else:
            return "Er waren geen bronnen om te verwijderen."


class ReformulateCommand(BaseCommand):
    """Command to reformulate answer with different approach."""
    
    @property 
    def pattern(self) -> str:
        return r"(?:herformuleer|reformulate|anders|different|opnieuw).*(?:antwoord|answer)"
    
    def execute(self, session: QuerySession, match_groups: List[str]) -> str:
        if not session.sources:
            return "Er zijn nog geen bronnen om mee te herformuleren. Stel eerst een belastingvraag."
        
        # No need to change state - LLM handles reformulation naturally
        return "Ik ga het antwoord herformuleren met de beschikbare bronnen."


class ClearSessionCommand(BaseCommand):
    """Command to clear the current session."""
    
    @property
    def pattern(self) -> str:
        return r"(?:clear|reset|opnieuw|nieuw.*gesprek|start.*over)"
    
    def execute(self, session: QuerySession, match_groups: List[str]) -> str:
        session.clear_sources()
        session.conversation_history.clear()
        session.current_question = ""
        session.transition_to(WorkflowState.IDLE)
        return "Sessie is gewist. U kunt een nieuwe vraag stellen."


class ShowSourcesCommand(BaseCommand):
    """Command to show available sources."""
    
    @property
    def pattern(self) -> str:
        return r"(?:toon|show|wat.*bronnen|which.*sources|status)"
    
    def execute(self, session: QuerySession, match_groups: List[str]) -> str:
        if not session.sources:
            return "Er zijn nog geen bronnen beschikbaar."
        
        summary = session.get_source_summary()
        response = "Beschikbare bronnen:\n"
        for tool_name, status in summary.items():
            display_name = {
                "get_legislation": "Wetgeving",
                "get_case_law": "Jurisprudentie"
            }.get(tool_name, tool_name)
            response += f"• {display_name}: {status}\n"
            
        return response.strip()


class CommandProcessor:
    """Processes and executes user commands."""
    
    def __init__(self):
        self._commands: List[BaseCommand] = [
            RemoveSourceCommand(),
            ReformulateCommand(), 
            ClearSessionCommand(),
            ShowSourcesCommand()
        ]
    
    def add_command(self, command: BaseCommand) -> None:
        """Add a new command to the processor."""
        self._commands.append(command)
    
    def process_message(self, message: str, session: QuerySession) -> Optional[str]:
        """
        Check if message matches any command and execute it.
        Returns command response if matched, None otherwise.
        """
        message_lower = message.lower().strip()
        
        for command in self._commands:
            pattern = command.pattern
            match = re.search(pattern, message_lower)
            
            if match:
                match_groups = [match.group(0)] + list(match.groups())
                try:
                    return command.execute(session, match_groups)
                except Exception as e:
                    return f"Fout bij uitvoeren commando: {str(e)}"
        
        return None
    
    def list_commands(self) -> List[str]:
        """Get list of available command patterns."""
        return [cmd.pattern for cmd in self._commands]