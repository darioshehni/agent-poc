# Tax Chatbot (Code-Oriented Guide)

This repository implements a Dutch tax chatbot (“TESS”) with a clean, tool-driven architecture. This README explains how the code works: the modules, classes, and the end-to-end flow through the system.

**Goal:** Understand the codebase structure and how a single user turn is handled, from input → tool calls → final answer, including how sessions and sources are managed.

## Code Map

- `src/agent.py`: Orchestrates one chat turn. Builds prompts, calls the LLM, delegates tool-call execution, persists state, and returns the assistant’s text.
- `src/base.py`: Core abstractions. `BaseTool` (async tools), `ToolResult`, `LLMClient` interface, and `ToolManager` (register/execute/serialize tools).
- `src/sessions.py`: In-memory dossiers (no wrapper). Handles persistence to `data/dossiers/<dossier_id>.json` and hydration on first access.
- `src/models.py`: Pydantic models: `Legislation`, `CaseLaw`, `Dossier`, `RemovalDecision` used across tools and session state.
- `src/tool_calls.py`: Bridges LLM function calls to tools. Executes tools via `ToolManager`, updates the session/dossier, appends compact tool results back into the conversation.
- `src/context.py`: Builds the static system prompt. Intentionally does not inject large dynamic context into messages.
- `src/prompts.py`: System prompt and answer-generation template, plus simple helpers for retrieval.
- `src/llm.py`: Async OpenAI wrapper. `LlmChat.chat()` returns `LlmAnswer` with `answer` and `tool_calls` (function call names).
- `src/tools/`: Tool implementations.
  - `legislation_tool.py`: Demo search for legislation.
  - `case_law_tool.py`: Demo search for case law.
  - `answer_tool.py`: Generates the final answer using sources from the dossier.
  - `remove_sources_tool.py`: Maps a natural instruction to IDs to unselect from the dossier.
- `src/api/server.py`: FastAPI WebSocket server that proxies a single-turn chat to the agent and persists the dossier.
- `terminal_chat.py`: Minimal WebSocket client for manual testing.

## End-to-End Flow (One User Turn)

The main flow lives in `TaxChatbot.process_message()`:

1. Dossier: Fetch or create a `Dossier` (`SessionManager.get_or_create_dossier`). Add the user turn to the curated, user-visible `dossier.conversation`.
2. System Prompt: `ContextBuilder.build_system_prompt()` returns the static system policy from `prompts.py`.
3. Conversation: Build a conversation array consisting of `[system_prompt] + dossier.conversation`. No large source text is injected here.
4. Tools: Provide function schemas from `ToolManager.get_function_schemas()` so the model can invoke tools.
5. First LLM Call: `LlmChat.chat(messages, tools=..., model_name=...)` returns an `LlmAnswer` with `answer` and optional `tool_calls`.
6. Tool Calls (if any): `ToolCallHandler.handle()` executes each tool via `ToolManager.execute_tool()` and updates the session:
   - Retrieval tools (`get_legislation`, `get_case_law`): add sources to the dossier and return a short assistant message that is appended to the conversation.
   - Removal tool (`remove_sources`): unselects titles in `dossier.selected_ids` and returns a short assistant message.
   - For retrieval tools, only metadata goes back into the conversation to avoid large content in the transcript; full content lives only in the dossier.
7. Persistence: The server persists the dossier snapshot (`SessionManager.save_dossier`) after sending the reply.
8. Final LLM Call: Rebuild the system prompt (now reflecting updated state) and call the LLM again without tools to produce the final answer text.
9. Record + Return: Append the assistant’s final text to `dossier.conversation` and return it.

Notes:
- For non-tax small talk, the LLM may answer directly without tools.
- For tax questions, the policy encourages “sources → confirmation → final answer”. The answer tool reads source content from the dossier at call time.

## Key Classes and Responsibilities

**`TaxChatbot` (src/agent.py):**
- Orchestrates the flow described above.
- Holds `SessionManager`, `ToolManager`, `LlmChat`, `ContextBuilder`, and `ToolCallHandler`.
- Registers tools in `_setup_tools()` and exposes helpers like `get_session_info()`, `list_available_tools()`, and `cleanup_old_sessions()`.

**`Dossier` and `SessionManager` (src/sessions.py):**
- `Dossier`: single source of truth containing sources and curated conversation; includes `dossier_id`, `created_at`, `updated_at`.
- `SessionManager`: CRUD for dossiers (`get_dossier`, `get_or_create_dossier`, `save_dossier`) with JSON snapshots in `data/dossiers/<dossier_id>.json`.

**`Dossier` (src/models.py):**
- Aggregates sources collected during a session: `legislation`, `case_law`, `selected_ids`, `conversation` (user-visible chat subset).
- Selection helpers: `select_by_ids`, `selected_texts()`, `all_texts()`, `selected_titles()`, `unselected_titles()`.
- Answer tool behavior: if nothing is selected, all collected texts are used; if some IDs are selected, only those texts are used.

**`ToolManager`, `BaseTool`, `ToolResult` (src/base.py):**
- `BaseTool`: contract for tools. Properties `name`, `description`, `parameters_schema` and async `execute(**kwargs)`.
- `ToolManager`: registers tools, lists schemas for function calling, executes a tool by name, and serializes results for chat messages.
- `ToolResult`: normalized result with `success`, `data`, `error_message`, `metadata`. Includes safe serialization of dataclasses, dicts, lists, and Pydantic models.

**`ToolCallHandler` (src/tool_calls.py):**
- Normalizes `tool_calls` coming from the LLM, executes tools via `ToolManager`, updates the session/dossier, and appends a compact tool result message back into the conversation.
- Special handling for retrieval tools to avoid putting large content into the conversation (titles only, full content in dossier).

**`LlmChat` and `LlmAnswer` (src/llm.py):**
- Async thin wrapper around OpenAI. `chat()` accepts either a message list or a single user string. When tools are provided, function-calling is enabled and `tool_calls` are extracted.
- `LlmAnswer`: Pydantic model with `answer: str` and `tool_calls: list[str]` (function names).

**Prompts and Context (src/prompts.py, src/context.py):**
- `AGENT_SYSTEM_PROMPT`: policy that enforces the “sources → confirmation → answer” workflow for tax questions while allowing direct, natural responses for small talk.
- `ANSWER_GENERATION_PROMPT`: template used by the answer tool to produce a detailed answer using only dossier sources.
- `ContextBuilder`: returns the static system prompt; dynamic session data stays out of the chat transcript.

## Tools in Detail (src/tools/)

- `LegislationTool` (`name: get_legislation`): Keyword-based demo search returning `Legislation` items. Metadata includes `source_names` for user display. Results are mirrored into the dossier and auto-selected.
- `CaseLawTool` (`name: get_case_law`): Keyword-based demo search returning `CaseLaw` items. Metadata includes `source_names` only.
- `AnswerTool` (`name: generate_tax_answer`): Reads source texts from the active session’s dossier (selected first, otherwise all). Builds a prompt using the answer template and calls `LlmChat` to generate the final answer.
- `RemoveSourcesTool` (`name: remove_sources`): Presents the dossier’s sources as concise candidates and asks the LLM to return strict JSON (`DocumentTitles.titles`) via a structured call; the agent unselects matching titles from `dossier.selected_ids`.

Tool interface expectations:
- Async `execute(**kwargs)` that returns a `ToolResult`.
- `parameters_schema` is used to expose the tool to the LLM function-calling API.

## Data Models (src/models.py)

- `Legislation`: fields `title`, `content`.
- `CaseLaw`: fields `title`, `content`.
- `Dossier`: aggregates `legislation`, `case_law`, `selected_ids`, `conversation` with helpers for titles and text extraction.
- `DocumentTitles`: simple structure used by the removal tool (`titles: list[str]`).

Important note:
- Titles function as identifiers for selection and removal. If you need stable IDs or fields like ECLI/article numbers in future, extend the models and adjust selection accordingly.

## Reading Order (Suggested)

- `src/agent.py`: top-level orchestration and turn lifecycle.
- `src/tool_calls.py`: how function calls are executed and how results affect the session.
- `src/sessions.py` and `src/models.py`: dossier structure and persistence.
- `src/tools/*.py`: concrete tools and their expected inputs/outputs.
- `src/llm.py`, `src/prompts.py`, `src/context.py`: LLM plumbing and prompts.
- `src/api/server.py` and `terminal_chat.py`: entry points.

## Behavior Guarantees and Rationale

- Sources stay out of the conversation transcript: Large texts are only stored in the dossier; the conversation uses titles/metadata to keep tokens low and privacy high.
- Confirmation-before-answer workflow: The agent encourages showing sources and asking for confirmation. The final answer (via `generate_tax_answer`) uses dossier content only.
- Async-first: Tool execution and LLM calls are async to compose well with the FastAPI server and terminal runner.

## Notable Implementation Details

- `TaxChatbot._is_confirmation()`: prevents short “ja/nee/klopt/correct” messages from polluting the last user question logic; the answer tool falls back to the last user message in the dossier when needed.
- `SessionManager.save_dossier/load_dossier`: persists and restores the dossier snapshot.
- `ToolCallHandler`: for retrieval tools, appends a curated assistant message listing the found titles and asking for confirmation.
- Legacy surfaces: there are a few synchronous helpers (e.g., `AnswerTool.generate_answer`) that wrap async behavior; treat them as legacy/unused in the current async flow.
- `ToolManager.execute_function_call()` exists but is not used by the agent; it assumes sync execution and would need awaiting to use with async tools.

## Running Locally

- Requirements: Python `3.12+`, `.env` with `OPENAI_API_KEY`.
- Install: `pip install -r requirements.txt`.
- Terminal: `python terminal_chat.py`.
- API: `python src/api/server.py` (FastAPI at `http://localhost:8000`, docs at `/docs`).

## Extending the System

- Add a tool: implement `BaseTool` with async `execute`, define a `parameters_schema`, and register it in `TaxChatbot._setup_tools()` (or dynamically via `add_tool`).
- Change prompts/policy: edit `src/prompts.py` (system prompt and answer template).
- Evolve models: extend `Legislation`/`CaseLaw` if you need stable IDs or extra metadata (e.g., ECLI, article identifiers) across the app.

## API Surface (Server)

- `GET /`: API info.
- WebSocket: connect to `/ws`, send `{message, dossier_id?}`, receive `{status, response, dossier_id}`.
- `GET /tools`: list tool names.
- `GET /health`: liveness plus a count of registered tools.
- `POST /admin/cleanup`: remove dossiers older than N hours.

## Caveats and TODOs

- Some tests and legacy scripts reference APIs that no longer exist (e.g., synchronous flows, command lists). Treat them as historical. Use the terminal app or FastAPI server to exercise the current async flow.
- If you adopt stable per-source IDs or richer metadata, extend the Pydantic models and thread those fields through dossier helpers and tools.
- If you expose `ToolManager.execute_function_call()` in future, make it async or ensure proper awaiting.
