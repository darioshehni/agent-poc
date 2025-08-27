# Tax Chatbot

Tax chatbot that leverages OpenAI's API and conversation context for workflow management.

## Features

- **Answer tax questions** with automatic source verification
- **Conversation-based workflow** without complex state management
- **Source confirmation** - shows sources and asks for user confirmation
- **Multi-interface support** - Terminal interface and REST API
- **Extensible tool system** for legislation and case law
- **Session management** for multi-user support
- **Command system** for advanced user interactions

## Architecture

This implementation uses a **stateless, conversation-context approach** where:

- ✅ **LLM understands workflow naturally** via conversation context
- ✅ **No complex state machines** - OpenAI handles flow naturally
- ✅ **Scalable API-first design** - perfect for microservices
- ✅ **Clean architecture** with clear separation of concerns

### Core Components

```
src/
├── agent.py           # Main chatbot logic
├── sessions.py        # Session and workflow management
├── prompts.py         # System prompts and templates
├── base.py           # Abstract base classes
├── llm.py            # OpenAI client abstraction
├── commands.py       # User commands
├── tools/            # Extensible toolset
│   ├── legislation_tool.py
│   ├── case_law_tool.py
│   └── answer_tool.py
└── api/
    └── server.py     # FastAPI REST interface
```

## Quick Start

### Requirements

- Python 3.8+
- OpenAI API key

### Installation

```bash
# Clone or download the project
cd agent-poc

# Install dependencies
pip install -r requirements.txt

# Create .env file
echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
```

### Terminal Interface

```bash
python terminal_chat.py
```

### REST API Server

```bash
# Start the server
python src/api/server.py

# Server runs on http://localhost:8000
# API documentation: http://localhost:8000/docs
```

## Usage

### Terminal Interface

```
💬 User: hoeveel procent btw moet ik betalen op tandpasta?

🤖 Bot: Ik vond de volgende bronnen:
1. Wet op de omzetbelasting 1968, artikel 2
2. ECLI:NL:HR:2020:123
Zijn deze bronnen correct voor uw vraag?

💬 User: ja

🤖 Bot: Op tandpasta geldt in Nederland een btw-tarief van 9%...
```

### REST API

```bash
# Chat endpoint
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "hoeveel procent btw moet ik betalen op tandpasta?",
    "session_id": "user123"
  }'

# Session info
curl -X GET "http://localhost:8000/session/user123"

# Health check
curl -X GET "http://localhost:8000/health"
```

## Workflow

The chatbot follows a **conversation-based workflow**:

1. **Gather sources**: For tax questions, automatically searches legislation and case law
2. **Show sources**: Only source titles are shown (not full content)
3. **Ask for confirmation**: "Are these sources correct for your question?"
4. **Generate answer**: After positive confirmation, generates comprehensive answer

### Supported Commands

- `reset` / `opnieuw` - Reset session
- `verwijder wetgeving` - Remove specific sources
- `toon bronnen` - Show current source status
- `herformuleer antwoord` - Regenerate answer

## Extending Tools

Easily add new tools:

```python
from src.base import BaseTool, ToolResult

class MyCustomTool(BaseTool):
    @property
    def name(self) -> str:
        return "my_tool"
    
    @property
    def description(self) -> str:
        return "Description of my tool"
    
    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            },
            "required": ["query"]
        }
    
    def execute(self, **kwargs) -> ToolResult:
        # Tool logic here
        return ToolResult(success=True, data="result")

# Register in agent.py
chatbot.add_tool(MyCustomTool())
```

## Configuration

### Environment Variables

```bash
# .env file
OPENAI_API_KEY=your_api_key_here
API_HOST=0.0.0.0          # Optional, default: 0.0.0.0
API_PORT=8000             # Optional, default: 8000
```

### Customize System Prompt

Edit `src/prompts.py` to modify chatbot behavior:

```python
AGENT_SYSTEM_PROMPT = """
Your custom instructions here...
"""
```

## Testing

```bash
# Test architecture
python test_architecture.py

# Test API endpoints (if server is running)
curl -X GET "http://localhost:8000/health"
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/chat` | POST | Send message to chatbot |
| `/session/{id}` | GET | Get session information |
| `/session/{id}` | DELETE | Reset specific session |
| `/health` | GET | Health check |
| `/tools` | GET | List available tools |
| `/commands` | GET | List available commands |
| `/admin/cleanup` | POST | Clean up old sessions |

## Design Principles

1. **Conversation Context over State Machines** - Let the LLM understand workflow naturally
2. **API-first Design** - Stateless, scalable, microservice-ready
3. **Clean Architecture** - Clear separation of responsibilities
4. **Extensibility** - Easy to add tools and commands
5. **Type Safety** - Using Pydantic models and type hints

