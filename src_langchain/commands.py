"""
LangChain-specific command system.
Demonstrates how LangChain's agent memory management compares to custom session handling.
"""

import re
from typing import List, Optional
from abc import ABC, abstractmethod


class LangChainBaseCommand(ABC):
    """Abstract base class for LangChain-compatible commands."""
    
    @property
    @abstractmethod
    def pattern(self) -> str:
        """Regex pattern to match this command."""
        pass
    
    @abstractmethod
    def execute(self, chatbot, match_groups: List[str]) -> str:
        """Execute the command with LangChain chatbot instance."""
        pass


class LangChainClearCommand(LangChainBaseCommand):
    """Command to clear LangChain memory."""
    
    @property
    def pattern(self) -> str:
        return r"(?:clear|reset|opnieuw|nieuw.*gesprek|start.*over)"
    
    def execute(self, chatbot, match_groups: List[str]) -> str:
        """Clear LangChain's conversation memory."""
        chatbot.memory.clear()
        return "LangChain sessie is gewist. Conversation memory is gereset. U kunt een nieuwe vraag stellen."


class LangChainStatusCommand(LangChainBaseCommand):
    """Command to show LangChain agent status."""
    
    @property
    def pattern(self) -> str:
        return r"(?:status|info|session.*info|langchain.*status)"
    
    def execute(self, chatbot, match_groups: List[str]) -> str:
        """Show LangChain-specific status information."""
        info = chatbot.get_session_info()
        
        response = "🔗 LangChain Agent Status:\n"
        response += f"• Framework: {info.get('framework', 'LangChain')}\n"
        response += f"• Agent Type: {info.get('agent_type', 'Unknown')}\n"
        response += f"• Memory Type: {info.get('memory_type', 'Unknown')}\n"
        response += f"• Memory Window: {info.get('memory_window', 'N/A')} exchanges\n"
        response += f"• Available Tools: {', '.join(info.get('available_tools', []))}\n"
        response += f"• Session ID: {info.get('session_id', 'Unknown')}\n"
        
        # Show memory content if available
        if hasattr(chatbot, 'memory') and chatbot.memory.chat_memory.messages:
            message_count = len(chatbot.memory.chat_memory.messages)
            response += f"• Messages in Memory: {message_count}\n"
        
        return response


class LangChainMemoryCommand(LangChainBaseCommand):
    """Command to show LangChain memory content."""
    
    @property
    def pattern(self) -> str:
        return r"(?:memory|geschiedenis|history|conversatie.*history)"
    
    def execute(self, chatbot, match_groups: List[str]) -> str:
        """Show LangChain conversation memory."""
        if not hasattr(chatbot, 'memory') or not chatbot.memory.chat_memory.messages:
            return "LangChain memory is leeg. Nog geen conversatiegeschiedenis."
        
        messages = chatbot.memory.chat_memory.messages
        response = f"🧠 LangChain Conversation Memory ({len(messages)} berichten):\n\n"
        
        for i, message in enumerate(messages[-6:], 1):  # Show last 6 messages
            role = message.type if hasattr(message, 'type') else 'unknown'
            content = message.content[:100] + "..." if len(message.content) > 100 else message.content
            response += f"{i}. [{role.upper()}]: {content}\n"
        
        return response


class LangChainHelpCommand(LangChainBaseCommand):
    """Command to show LangChain-specific help."""
    
    @property
    def pattern(self) -> str:
        return r"(?:help|hulp|commands|commando)"
    
    def execute(self, chatbot, match_groups: List[str]) -> str:
        """Show LangChain agent help."""
        return """🔗 LangChain Tax Chatbot - Beschikbare Commando's:

CONVERSATIE:
• reset/opnieuw - Reset LangChain memory
• status - Toon agent en memory informatie
• memory/geschiedenis - Bekijk conversation history
• help/hulp - Deze hulp

BELASTINGVRAGEN:
Stel gewoon uw belastingvraag! De LangChain ReAct agent zal:
1. Reasoning: Uw vraag analyseren
2. Action: Relevante bronnen zoeken (wetgeving + jurisprudentie)  
3. Observation: Resultaten evalueren
4. Action: Bronnen tonen en om bevestiging vragen
5. Action: Na bevestiging, uitgebreid antwoord genereren

LANGCHAIN FEATURES:
• ReAct agent pattern voor gestructureerde reasoning
• Automatische conversation memory management
• Tool orchestration via built-in agent executor
• Error handling en retry logic"""


class LangChainCommandProcessor:
    """Processes commands for LangChain chatbot."""
    
    def __init__(self):
        self._commands: List[LangChainBaseCommand] = [
            LangChainClearCommand(),
            LangChainStatusCommand(),
            LangChainMemoryCommand(),
            LangChainHelpCommand()
        ]
    
    def add_command(self, command: LangChainBaseCommand) -> None:
        """Add a new LangChain command."""
        self._commands.append(command)
    
    def process_message(self, message: str, chatbot) -> Optional[str]:
        """
        Check if message matches any LangChain command.
        Returns command response if matched, None otherwise.
        """
        message_lower = message.lower().strip()
        
        for command in self._commands:
            pattern = command.pattern
            match = re.search(pattern, message_lower)
            
            if match:
                match_groups = [match.group(0)] + list(match.groups())
                try:
                    return command.execute(chatbot, match_groups)
                except Exception as e:
                    return f"Fout bij uitvoeren LangChain commando: {str(e)}"
        
        return None
    
    def list_commands(self) -> List[str]:
        """Get list of available LangChain command patterns."""
        return [type(cmd).__name__.replace('LangChain', '').replace('Command', '') 
                for cmd in self._commands]