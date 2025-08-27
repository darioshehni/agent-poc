# Framework Comparison Guide

This repository now includes three implementations of the same Dutch Tax Chatbot to demonstrate architectural differences and trade-offs between custom solutions and popular AI frameworks.

## Available Implementations

### 1. Original Custom Implementation (`src/`)
**Your clean, purpose-built solution**
- Custom tool registry with abstract base classes
- Direct OpenAI API integration with function calling
- Session management with conversation context
- Clean separation of concerns
- Minimal dependencies

### 2. LangChain Implementation (`src_langchain/`)
**Showcasing LangChain's agent patterns**
- ReAct agent with built-in reasoning
- Tool decorator system (`@tool`)
- ConversationBufferWindowMemory for automatic memory management
- Prompt template system
- Built-in error handling and retry logic

### 3. LlamaIndex Implementation (`src_llamaindex/`)
**Demonstrating LlamaIndex's query processing**
- ReActAgent with query transformation
- FunctionTool approach for tool integration
- ChatMemoryBuffer for conversation management
- Response synthesis capabilities
- Query processing pipeline

## Usage

Run any implementation using the terminal interface:

```bash
# Original implementation (default)
python terminal_chat.py
python terminal_chat.py --framework original

# LangChain implementation
python terminal_chat.py --framework langchain

# LlamaIndex implementation  
python terminal_chat.py --framework llamaindex
```


## Comparison Points

### Code Complexity
- **Original**: ~300 lines of clean, focused code
- **LangChain**: ~200 lines but relies heavily on framework abstractions
- **LlamaIndex**: ~200 lines with framework-specific patterns

### Learning Curve
- **Original**: Standard Python OOP, easy to understand and modify
- **LangChain**: Requires understanding of agents, memory, and chains
- **LlamaIndex**: Requires understanding of query engines and synthesis

### Control & Customization
- **Original**: Full control over every aspect of behavior
- **LangChain**: Some framework constraints but good customization options
- **LlamaIndex**: More opinionated about query processing and responses

### Dependencies & Bundle Size
- **Original**: 6 lightweight dependencies
- **LangChain**: 15+ dependencies with larger footprint
- **LlamaIndex**: 10+ dependencies with AI-focused utilities

### Maintenance & Debugging
- **Original**: Easy to debug, clear error traces
- **LangChain**: Framework abstractions can obscure issues
- **LlamaIndex**: Good debugging but framework-specific knowledge needed

## Key Architectural Differences

**Fair Comparison Note:** All implementations use the **same core system prompt** from the original `src/prompts.py` to ensure architectural comparison, not prompt differences.

### Tool Definition

**Original (BaseTool)**:
```python
class LegislationTool(BaseTool):
    def execute(self, **kwargs) -> ToolResult:
        # Custom implementation with full control
```

**LangChain (@tool decorator)**:
```python
@tool
def get_legislation(query: str) -> str:
    # Framework-managed function with automatic schema generation
```

**LlamaIndex (FunctionTool)**:
```python
legislation_tool = FunctionTool.from_defaults(
    fn=get_legislation_impl,
    name="get_legislation"
)
```

### Memory Management

**Original**: Custom session with conversation history
**LangChain**: `ConversationBufferWindowMemory`
**LlamaIndex**: `ChatMemoryBuffer`

### Agent Patterns

**Original**: Direct OpenAI function calling
**LangChain**: ReAct agent with built-in reasoning
**LlamaIndex**: ReActAgent with query processing

## When to Use Each Approach

### Choose Original When:
- You need full control over behavior
- Working with domain-specific requirements (like legal citations)
- Team prefers minimal dependencies
- Performance is critical
- You want to understand every piece of the system

### Choose LangChain When:
- Building complex multi-step reasoning workflows
- Need robust conversation memory management
- Want to leverage pre-built agent patterns
- Team is comfortable with framework abstractions
- Rapid prototyping of agent behaviors

### Choose LlamaIndex When:
- Working with document-heavy RAG applications
- Need advanced query processing and transformation
- Building knowledge base systems
- Want sophisticated response synthesis
- Primary focus is on information retrieval and synthesis

## Conclusion

For this specific Dutch tax chatbot use case, the **original custom implementation proves superior** because:

1. **Domain fit**: Legal/tax systems need precise control over citations and sources
2. **Simplicity**: The workflow is naturally conversation-driven, not complex multi-step
3. **Maintainability**: Clear, understandable code without framework magic
4. **Performance**: No framework overhead for this straightforward use case
5. **Control**: Full control over legal compliance and accuracy requirements

The framework implementations serve as valuable learning tools and might be beneficial for different use cases, but demonstrate that framework choice should always align with specific requirements rather than following trends.