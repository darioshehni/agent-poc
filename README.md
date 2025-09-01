# TESS - Tax Assistant

A sophisticated Dutch tax advisory chatbot built with a clean, dossier-first architecture. TESS (Tax Expert Support System) helps users with Nederlandse belastingvragen through intelligent source retrieval, selection, and comprehensive answer generation.

## System Overview

### What is TESS?

TESS is a conversational AI system designed specifically for Dutch tax law. It combines:

- **Intelligent Source Retrieval**: Automatically finds relevant legislation and case law
- **Interactive Source Management**: Users can review and refine selected sources
- **Comprehensive Answer Generation**: Produces detailed, source-backed tax advice
- **Persistent Conversations**: Maintains context across multiple interactions

### Key Architectural Principles

1. **Dossier-First**: All conversation state and sources are maintained in a persistent `Dossier` object
2. **Tool-Driven**: Functionality is modular through a clean tool system with function calling
3. **Source-Backed**: All answers are explicitly grounded in retrieved legislation and case law  
4. **Clean Separation**: Clear boundaries between data models, business logic, and user interfaces
5. **Stateless Tools**: Tools return patches rather than mutating state directly

### Interfaces

- **WebSocket API** (`src/api/server.py`): Core backend service
- **Terminal Client** (`terminal_chat.py`): Command-line interface for testing
- **Streamlit UI** (`ui_streamlit.py`): Web-based graphical interface

---

## Complete System Flow

### Message Processing Pipeline

When a user sends a message, here's the complete flow:

```
1. WebSocket Server (server.py)
   ├── Receives user message + optional dossier_id
   ├── Creates TESS agent instance
   └── Calls agent.process_message()

2. TESS Agent (agent.py)
   ├── Loads/creates Dossier via SessionManager
   ├── Adds user message to dossier.conversation
   ├── Builds message list: [system_prompt] + conversation
   ├── Makes LLM call with function calling enabled
   └── Routes to tool execution or direct response

3. Tool Execution (tool_calls.py)
   ├── ToolCallHandler executes requested tools
   ├── Tools return DossierPatch objects or answer strings
   ├── Patches are applied to update dossier state
   └── Returns tool results to agent

4. Response Generation
   ├── Agent processes tool results via Presenter
   ├── Creates user-facing messages from tool outcomes
   ├── Adds assistant response to conversation
   └── Returns final response string

5. Persistence & Response
   ├── Server saves updated dossier to JSON
   ├── Sends response back to client
   └── Closes WebSocket connection
```

### Architecture Diagram

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client UI     │    │  WebSocket API   │    │  TESS Agent     │
│                 │◄──►│                  │◄──►│                 │
│ • Terminal      │    │ • FastAPI        │    │ • LLM calls     │
│ • Streamlit     │    │ • Per-connection │    │ • Tool orchestr.│
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                       ┌─────────────────┐              │
                       │ Session Manager │◄─────────────┤
                       │                 │              │
                       │ • Dossier CRUD  │              │
                       │ • JSON persist  │              │
                       └─────────────────┘              │
                                                         │
┌─────────────────┐    ┌──────────────────┐              │
│     Tools       │    │   Tool Handler   │◄─────────────┤
│                 │◄──►│                  │              │
│ • Legislation   │    │ • Execution      │              │
│ • Case Law      │    │ • Patch apply    │              │
│ • Answer Gen    │    │ • Result format  │              │
│ • Source Mgmt   │    └──────────────────┘              │
└─────────────────┘                                      │
                                                         │
┌─────────────────┐    ┌──────────────────┐              │
│    LLM Client   │    │   Data Models    │◄─────────────┘
│                 │◄──►│                  │
│ • OpenAI API    │    │ • Dossier        │
│ • Function call │    │ • DossierPatch   │
│ • Structured    │    │ • Legislation    │
└─────────────────┘    │ • CaseLaw        │
                       └──────────────────┘
```

---

## Core Components Deep Dive

### 1. Dossier System (`src/config/models.py`, `src/sessions.py`)

The **Dossier** is the heart of TESS - a persistent data structure containing:

```python
class Dossier(BaseModel):
    dossier_id: str                           # Unique identifier
    legislation: list[Legislation]            # Retrieved legislation sources
    case_law: list[CaseLaw]                  # Retrieved case law sources  
    selected_ids: list[str]                  # Currently selected source titles
    conversation: list[dict[str, str]]       # User-visible conversation history
```

**Key Features:**
- **Source Management**: Stores legislation and case law with deduplication by title
- **Selection Tracking**: Maintains which sources are currently selected for answers
- **Conversation History**: Only user-visible messages (no large source texts)
- **Persistence**: JSON serialization to `data/dossiers/{dossier_id}.json`

**Important Methods:**
- `add_conversation_user/assistant()`: Manage conversation flow
- `selected_titles()`, `unselected_titles()`: Get source selection state
- `get_selected_legislation/case_law()`: Retrieve sources for answer generation

### 2. TESS Agent (`src/agent.py`)

The **TESS** class orchestrates the complete conversation flow:

```python
class TESS:
    def __init__(self, dossier_id: str = ""):
        self.dossier = get_or_create_dossier(dossier_id)
        self.llm_client = LlmChat()
        self.tool_call_handler = self._setup_tool_call_handler()
```

**Core Responsibilities:**
- **Dossier Management**: Load/create dossiers per conversation
- **LLM Orchestration**: Make function-calling enabled LLM requests  
- **Tool Coordination**: Delegate tool execution to ToolCallHandler
- **Response Generation**: Convert tool results into user-facing messages
- **State Updates**: Apply patches and persist changes

**Key Method - `process_message()`:**
1. Add user input to dossier conversation
2. Build message list with system prompt
3. Call LLM with available tools
4. Execute any requested tool calls
5. Generate user-facing response
6. Persist updated dossier state

### 3. Tool System (`src/tools/`, `src/tool_calls.py`)

TESS uses a modular tool architecture where each tool:

- **Is Stateless**: Receives dossier + arguments, returns patches/data
- **Returns Patches**: `DossierPatch` objects that describe state changes
- **Has Clean Interface**: `name`, `description`, `parameters_schema`, `execute()`

**Available Tools:**

#### Retrieval Tools
- **`LegislationTool`**: Searches and returns relevant Dutch tax legislation
- **`CaseLawTool`**: Searches and returns relevant jurisprudence

#### Source Management Tools  
- **`RemoveSourcesTool`**: Removes sources from selection based on user input
- **`RestoreSourcesTool`**: Restores previously removed sources to selection

#### Answer Generation Tool
- **`AnswerTool`**: Generates comprehensive tax answers using selected sources

**Tool Execution Flow:**
1. `ToolCallHandler` receives tool calls from LLM
2. Maps tool names to registered callable functions
3. Executes each tool with dossier + parsed arguments
4. Collects `DossierPatch` objects from tools
5. Applies patches to update dossier state
6. Returns `ToolResult` objects for response generation

### 4. LLM Integration (`src/llm.py`)

The **LlmChat** class provides async OpenAI integration:

```python
class LlmChat:
    async def chat(messages, model_name, tools=None, tool_choice="auto", temperature=0.0)
    async def chat_structured(messages, model_name, response_format: Type[BaseModel])
```

**Features:**
- **Function Calling**: Enables LLM to request tool execution
- **Structured Output**: Parses responses into Pydantic models
- **Error Handling**: Robust error handling with fallbacks
- **Logging**: Detailed request/response logging for debugging

**Usage Patterns:**
- **Tool Selection**: LLM chooses which tools to call based on user input
- **Structured Parsing**: RemoveSourcesTool and RestoreSourcesTool use structured output
- **Answer Generation**: Direct text generation for final responses

### 5. Session Management (`src/sessions.py`)

**Session Management Functions:**
- `get_or_create_dossier(dossier_id)`: Load existing or create new dossier
- `save_dossier(dossier)`: Persist dossier to JSON file  
- `_load_dossier(dossier_id)`: Load dossier from filesystem
- `_create_dossier(dossier_id)`: Create new empty dossier

**Storage Details:**
- **Location**: `data/dossiers/{dossier_id}.json`
- **Format**: JSON serialization of Dossier model
- **Atomicity**: Simple file write (could be enhanced with atomic writes)

---

## Data Models & State Management

### Core Data Structures

```python
# Source Models
class Legislation(BaseModel):
    title: str    # Acts as unique identifier
    content: str  # Full text of legislation

class CaseLaw(BaseModel):  
    title: str    # ECLI identifier or case name
    content: str  # Case law content/summary

# State Change Model
class DossierPatch(BaseModel):
    add_legislation: list[Legislation] = []
    add_case_law: list[CaseLaw] = []  
    select_titles: list[str] = []
    unselect_titles: list[str] = []
    
    def apply(self, dossier: Dossier) -> Dossier:
        # Applies changes to dossier and returns updated version
```

### State Management Pattern

TESS uses a **patch-based state management** pattern:

1. **Tools Don't Mutate**: Tools return `DossierPatch` objects describing changes
2. **Centralized Application**: `ToolCallHandler` applies all patches atomically  
3. **Immutable Operations**: Each patch application returns a new dossier state
4. **Deduplication**: Sources are deduplicated by title during patch application

### Conversation Flow

```python
# Conversation structure in dossier
conversation: list[dict[str, str]] = [
    {"role": "user", "content": "What is the VAT rate on goods?"},
    {"role": "assistant", "content": "I found the following sources:\n\n- Wet op de omzetbelasting 1968, artikel 2\n\nAre these sources correct for your question?"},
    {"role": "user", "content": "Yes, please answer"},
    {"role": "assistant", "content": "## SOURCES\nWet op de omzetbelasting 1968, artikel 2\n\n## ANALYSIS\n... detailed analysis ..."}
]
```

**Key Principles:**
- **User-Visible Only**: No internal tool messages or large source texts
- **Curated Content**: Only meaningful exchanges are stored
- **Source References**: Sources referenced by title, not embedded
- **Structured Answers**: Final answers include source citations

---

## Tool Architecture & Extension Points

### Tool Interface

Every tool implements this interface:

```python
class BaseTool:
    @property
    def name(self) -> str:
        # Function name for LLM calling
        
    @property  
    def description(self) -> str:
        # Description for LLM to understand when to use tool
        
    @property
    def parameters_schema(self) -> dict[str, Any]:
        # JSON schema for function calling parameters
        
    async def execute(self, dossier: Dossier, **kwargs) -> dict:
        # Implementation that returns success/data/patch/message
```

### Tool Categories

**1. Retrieval Tools** (`LegislationTool`, `CaseLawTool`)
- **Input**: Search query from user
- **Output**: `DossierPatch` with `add_legislation/case_law` + `select_titles`
- **Purpose**: Find and add relevant sources to dossier

**2. Management Tools** (`RemoveSourcesTool`, `RestoreSourcesTool`)  
- **Input**: Natural language instruction (e.g., "remove article 13")
- **Processing**: Uses structured LLM call to map instruction to titles
- **Output**: `DossierPatch` with `select_titles` or `unselect_titles`

**3. Generation Tools** (`AnswerTool`)
- **Input**: User query for answer generation
- **Processing**: Uses selected sources to build context for LLM
- **Output**: Final answer string (no patch)

### Adding New Tools

1. **Create Tool Class**:
```python
class MyNewTool:
    @property
    def name(self) -> str:
        return "my_new_tool"
    
    @property
    def description(self) -> str:
        return "Description of what this tool does"
    
    @property  
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "..."}
            },
            "required": ["param1"]
        }
    
    async def execute(self, dossier: Dossier, param1: str, **kwargs) -> dict:
        # Implementation
        return {"success": True, "patch": DossierPatch(...)}
```

2. **Register in Agent** (`src/agent.py`):
```python
def _setup_tool_call_handler(self):
    my_tool = MyNewTool()
    tools = {
        # ... existing tools ...
        my_tool.name: my_tool.execute,
    }
    self.tool_schemas = [
        # ... existing schemas ...
        {"type": "function", "function": {
            "name": my_tool.name, 
            "description": my_tool.description, 
            "parameters": my_tool.parameters_schema
        }},
    ]
```

### Extension Patterns

**Data Model Extensions:**
- Add fields to `Legislation`, `CaseLaw`, or `Dossier`
- Extend `DossierPatch` for new state changes
- Update `apply()` method for new patch types

**New Source Types:**
- Create new source models (e.g., `Regulation`, `Directive`)
- Add corresponding fields to `Dossier` and `DossierPatch`
- Implement retrieval tools for new source types

**Custom Processing:**
- Add processing tools (e.g., document analysis, translation)
- Implement workflow tools (e.g., multi-step processes)
- Create integration tools (e.g., external API calls)

---

## API Specifications & Interfaces

### WebSocket API (`src/api/server.py`)

**Endpoint**: `ws://localhost:8000/ws`

**Request Format**:
```json
{
    "message": "What is the VAT rate on goods?",
    "dossier_id": "dos-a1b2c3d4"  // Optional, generated if omitted
}
```

**Response Format**:
```json
{
    "status": "success",
    "response": "I found the following sources:\n\n- Wet op de omzetbelasting 1968, artikel 2\n\nAre these sources correct for your question?",
    "dossier_id": "dos-a1b2c3d4"
}
```

**Error Response**:
```json
{
    "status": "error", 
    "error": "Error message description"
}
```

**Connection Model**:
- **One Message Per Connection**: Send request, receive response, connection closes
- **Stateless**: All state is maintained in the persisted dossier
- **Auto-Persistence**: Dossier is automatically saved after response

### Terminal Client (`terminal_chat.py`)

**Usage**:
```bash
# Start with new dossier
python terminal_chat.py

# Continue existing dossier  
python terminal_chat.py --dossier dos-a1b2c3d4

# Custom WebSocket URL
python terminal_chat.py --url ws://localhost:8000/ws
```

**Environment Variables**:
- `TAX_WS_URL`: WebSocket endpoint (default: `ws://localhost:8000/ws`)

**Features**:
- Interactive command-line conversation
- Persistent dossier across sessions
- Exit commands: `quit`, `exit`, `stop`, `bye`

### Streamlit UI (`ui_streamlit.py`)

**Usage**:
```bash
streamlit run ui_streamlit.py
```

**Features**:
- **Chat Interface**: Full conversation history with message bubbles
- **Dossier Management**: Switch between dossiers, create new sessions
- **Source Tracking**: Right sidebar shows currently selected sources
- **Session State**: Maintains UI state across interactions
- **Real-time Updates**: Selected sources update after each response

**Environment Variables**:
- `TAX_WS_URL`: WebSocket endpoint for backend communication

---

## Development & Deployment Guide

### Prerequisites

- **Python**: 3.11+ required
- **OpenAI API Key**: Required for LLM functionality
- **Dependencies**: See `requirements.txt`

### Environment Setup

1. **Clone Repository**:
```bash
git clone <repository-url>
cd agent-poc
```

2. **Create Virtual Environment**:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

3. **Install Dependencies**:
```bash
pip install -r requirements.txt
```

4. **Environment Configuration**:
Create `.env` file:
```env
OPENAI_API_KEY=your_openai_api_key_here
API_HOST=localhost
API_PORT=8000
LOG_LEVEL=INFO
```

### Running the System

1. **Start WebSocket Server**:
```bash
python src/api/server.py
```

2. **Terminal Client** (separate terminal):
```bash
python terminal_chat.py
```

3. **Streamlit UI** (alternative to terminal):
```bash
streamlit run ui_streamlit.py
```

### Development Workflow

**Adding New Functionality**:
1. **Data Model Changes**: Update `src/config/models.py`
2. **Tool Development**: Create tools in `src/tools/`
3. **Agent Integration**: Register tools in `src/agent.py`
4. **Testing**: Use terminal client for rapid iteration

**Debugging Tips**:
- **Logging**: Set `LOG_LEVEL=DEBUG` for detailed execution logs
- **Dossier Inspection**: Check `data/dossiers/` for saved state
- **Tool Testing**: Tools can be tested independently with mock dossiers

### Customization Points

**System Prompt** (`src/config/prompts.py`):
- `AGENT_SYSTEM_PROMPT`: Core agent behavior and tool usage guidelines
- `ANSWER_GENERATION_PROMPT`: Template for final answer generation

**Source Retrieval**:
- Replace dummy implementations in `LegislationTool` and `CaseLawTool`
- Add real search backends (elasticsearch, vector search, etc.)

**LLM Configuration**:
- Model selection in `src/config/config.py`
- Temperature and other parameters in tool implementations

### Production Considerations

**Scalability**:
- **Async Architecture**: Built for concurrent WebSocket connections
- **Stateless Design**: Easy to horizontally scale WebSocket servers
- **Persistent Storage**: Consider database backend for production

**Security**:
- **API Key Management**: Use secure secret management
- **Input Validation**: Add validation for user inputs
- **Rate Limiting**: Implement rate limiting for production use

**Monitoring**:
- **Structured Logging**: Comprehensive logging throughout system
- **Health Checks**: Add health check endpoints
- **Metrics**: Monitor tool usage, response times, error rates

### Testing Strategy

**Unit Testing**:
- **Tool Testing**: Mock dossiers for tool functionality
- **Model Testing**: Test patch application logic
- **LLM Testing**: Mock OpenAI responses for deterministic tests

**Integration Testing**:
- **End-to-End**: Full message flow testing
- **WebSocket Testing**: Client-server interaction testing
- **Persistence Testing**: Dossier save/load functionality

**User Testing**:
- **Terminal Client**: Quick manual testing
- **Streamlit UI**: User experience validation
- **Sample Conversations**: Predefined test scenarios

---

## Design Rationale & Best Practices

### Architectural Decisions

**Why Dossier-First?**
- **Single Source of Truth**: All conversation state in one place
- **Resumable Conversations**: Users can continue across sessions
- **Source Continuity**: Selected sources persist across turns
- **Testing & Debugging**: Easy to inspect and replay conversations

**Why Tool-Based Architecture?**
- **Modularity**: Each capability is independently testable
- **Extensibility**: Easy to add new functionality
- **LLM Integration**: Natural fit with function calling
- **Separation of Concerns**: Business logic separate from presentation

**Why Patch-Based Updates?**
- **Atomic Operations**: All changes applied together or not at all  
- **Conflict Resolution**: Clear semantics for concurrent modifications
- **Auditability**: Changes are explicit and traceable
- **Testability**: Easy to test state transitions

### Performance Considerations

**Token Efficiency**:
- **Minimal Transcripts**: Large source texts never enter conversation
- **Title-Based References**: Sources referenced by title only
- **Curated Messages**: Only user-visible content in conversation

**Memory Management**:
- **Stateless Tools**: No memory leaks from tool instances
- **JSON Serialization**: Efficient dossier storage
- **Connection-Per-Turn**: No long-lived WebSocket state

**Caching Opportunities**:
- **Source Retrieval**: Cache search results
- **LLM Responses**: Cache common answer patterns  
- **Dossier Loading**: In-memory caching for active dossiers

### Quality & Reliability

**Error Handling**:
- **Graceful Degradation**: System continues on tool failures
- **User-Friendly Errors**: Clear error messages for users
- **Detailed Logging**: Comprehensive error context for debugging

**Data Integrity**:
- **Model Validation**: Pydantic validation throughout
- **Deduplication**: Automatic source deduplication
- **Atomic Persistence**: Dossier saved after successful response

**User Experience**:
- **Progressive Disclosure**: Show sources before generating answers
- **User Control**: Allow source selection refinement
- **Context Preservation**: Maintain conversation context across turns

This comprehensive architecture provides a solid foundation for building sophisticated conversational AI systems with complex state management, tool integration, and user interaction patterns.