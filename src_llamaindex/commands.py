"""
LlamaIndex-specific command system.
Demonstrates LlamaIndex's chat memory and agent management capabilities.
"""

import re
from typing import List, Optional
from abc import ABC, abstractmethod


class LlamaIndexBaseCommand(ABC):
    """Abstract base class for LlamaIndex-compatible commands."""
    
    @property
    @abstractmethod
    def pattern(self) -> str:
        """Regex pattern to match this command."""
        pass
    
    @abstractmethod
    def execute(self, chatbot, match_groups: List[str]) -> str:
        """Execute the command with LlamaIndex chatbot instance."""
        pass


class LlamaIndexResetCommand(LlamaIndexBaseCommand):
    """Command to reset LlamaIndex chat memory."""
    
    @property
    def pattern(self) -> str:
        return r"(?:clear|reset|opnieuw|nieuw.*gesprek|start.*over)"
    
    def execute(self, chatbot, match_groups: List[str]) -> str:
        """Reset LlamaIndex's chat memory buffer."""
        chatbot.memory.reset()
        return "🦙 LlamaIndex sessie is gereset. Chat memory buffer is gewist. U kunt een nieuwe vraag stellen."


class LlamaIndexStatusCommand(LlamaIndexBaseCommand):
    """Command to show LlamaIndex agent status and capabilities."""
    
    @property
    def pattern(self) -> str:
        return r"(?:status|info|session.*info|llamaindex.*status)"
    
    def execute(self, chatbot, match_groups: List[str]) -> str:
        """Show LlamaIndex-specific status and capabilities."""
        info = chatbot.get_session_info()
        
        response = "🦙 LlamaIndex Agent Status:\n"
        response += f"• Framework: {info.get('framework', 'LlamaIndex')}\n"
        response += f"• Agent Type: {info.get('agent_type', 'Unknown')}\n"
        response += f"• Memory Type: {info.get('memory_type', 'Unknown')}\n"
        response += f"• Memory Token Limit: {info.get('memory_token_limit', 'N/A')}\n"
        response += f"• Available Tools: {', '.join(info.get('available_tools', []))}\n"
        response += f"• LLM Model: {info.get('llm_model', 'Unknown')}\n"
        response += f"• Session ID: {info.get('session_id', 'Unknown')}\n"
        
        # Show LlamaIndex-specific features
        features = info.get('features', [])
        if features:
            response += f"• LlamaIndex Features: {', '.join(features)}\n"
        
        return response


class LlamaIndexMemoryCommand(LlamaIndexBaseCommand):
    """Command to show LlamaIndex chat memory content."""
    
    @property
    def pattern(self) -> str:
        return r"(?:memory|geschiedenis|history|chat.*buffer)"
    
    def execute(self, chatbot, match_groups: List[str]) -> str:
        """Show LlamaIndex chat memory buffer content."""
        if not hasattr(chatbot, 'memory'):
            return "LlamaIndex memory niet beschikbaar."
        
        # Get memory content (implementation depends on LlamaIndex version)
        try:
            # Try to get messages from memory
            if hasattr(chatbot.memory, 'get_all'):
                messages = chatbot.memory.get_all()
            elif hasattr(chatbot.memory, 'chat_store') and hasattr(chatbot.memory.chat_store, 'get_messages'):
                messages = chatbot.memory.chat_store.get_messages()
            else:
                return "🦙 LlamaIndex ChatMemoryBuffer is actief maar inhoud niet toegankelijk via dit commando."
            
            if not messages:
                return "🦙 LlamaIndex chat memory buffer is leeg."
            
            response = f"🦙 LlamaIndex Chat Memory ({len(messages)} berichten):\n\n"
            
            for i, message in enumerate(messages[-6:], 1):  # Show last 6 messages
                role = getattr(message, 'role', 'unknown')
                content = getattr(message, 'content', str(message))
                content = content[:100] + "..." if len(content) > 100 else content
                response += f"{i}. [{role.upper()}]: {content}\n"
            
            return response
            
        except Exception as e:
            return f"🦙 LlamaIndex memory inhoud: {str(e)}"


class LlamaIndexQueryCommand(LlamaIndexBaseCommand):
    """Command to show query processing capabilities."""
    
    @property
    def pattern(self) -> str:
        return r"(?:query|processing|transform|synthesis)"
    
    def execute(self, chatbot, match_groups: List[str]) -> str:
        """Show LlamaIndex query processing information."""
        return """🦙 LlamaIndex Query Processing Capabilities:

QUERY TRANSFORMATION:
• Intelligente herformulering van belastingvragen
• Context expansion voor betere source retrieval
• Entity extraction en concept identificatie

RESPONSE SYNTHESIS:
• Combinatie van multiple sources in coherent antwoord
• Structured information integration
• Citation tracking en source attribution

AGENT ORCHESTRATION:
• ReActAgent voor multi-step reasoning
• Tool selection en execution planning
• Context-aware decision making

MEMORY MANAGEMENT:
• ChatMemoryBuffer voor conversatie context
• Token-limited history management
• Relevance-based message filtering

Test deze features door een complexe belastingvraag te stellen!"""


class LlamaIndexHelpCommand(LlamaIndexBaseCommand):
    """Command to show LlamaIndex-specific help."""
    
    @property
    def pattern(self) -> str:
        return r"(?:help|hulp|commands|commando)"
    
    def execute(self, chatbot, match_groups: List[str]) -> str:
        """Show LlamaIndex chatbot help."""
        return """🦙 LlamaIndex Tax Chatbot - Beschikbare Commando's:

CONVERSATIE:
• reset/opnieuw - Reset ChatMemoryBuffer
• status - Toon agent capabilities en memory info
• memory/geschiedenis - Bekijk chat memory buffer
• query - Info over query processing features
• help/hulp - Deze hulp

BELASTINGVRAGEN:
Stel uw belastingvraag! De LlamaIndex ReActAgent zal:
1. Query Analysis: Vraag analyseren en transformeren
2. Retrieval: Intelligente source selection (wetgeving + jurisprudentie)
3. Synthesis Preparation: Information organization
4. User Confirmation: Bronnen tonen en bevestiging vragen  
5. Response Synthesis: Coherent antwoord genereren

LLAMAINDEX FEATURES:
• Query transformation voor betere begrip
• Response synthesis voor gestructureerde antwoorden
• ChatMemoryBuffer voor conversatie management
• ReActAgent met multi-step reasoning
• FunctionTool integration voor source retrieval"""


class LlamaIndexCommandProcessor:
    """Processes commands for LlamaIndex chatbot."""
    
    def __init__(self):
        self._commands: List[LlamaIndexBaseCommand] = [
            LlamaIndexResetCommand(),
            LlamaIndexStatusCommand(),
            LlamaIndexMemoryCommand(),
            LlamaIndexQueryCommand(),
            LlamaIndexHelpCommand()
        ]
    
    def add_command(self, command: LlamaIndexBaseCommand) -> None:
        """Add a new LlamaIndex command."""
        self._commands.append(command)
    
    def process_message(self, message: str, chatbot) -> Optional[str]:
        """
        Check if message matches any LlamaIndex command.
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
                    return f"Fout bij uitvoeren LlamaIndex commando: {str(e)}"
        
        return None
    
    def list_commands(self) -> List[str]:
        """Get list of available LlamaIndex command patterns."""
        return [type(cmd).__name__.replace('LlamaIndex', '').replace('Command', '') 
                for cmd in self._commands]