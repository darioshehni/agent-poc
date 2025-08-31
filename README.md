# Tax Chatbot (Dossier‑First Architecture)

This repository implements a Dutch tax chatbot (“TESS”) with a clean, tool‑driven, dossier‑first architecture. This README explains the codebase so you can understand how messages flow through the system, how data is modeled, and where to change things.

## How One Turn Works

1) Dossier: TaxChatbot fetches or creates a `Dossier` via `SessionManager.get_or_create_dossier(dossier_id)` and appends the user message to `dossier.conversation`.
2) System Prompt: `ContextBuilder.build_system_prompt(dossier)` returns the static policy (no dynamic context injected).
3) Messages: The agent builds `[system, ...dossier.conversation]` as the message list (no large source texts in the transcript).
4) First LLM Call: `LlmChat.chat(messages, tools=function_schemas)` lets the model decide if it needs tools.
5) Tool Calls: `ToolCallHandler.handle(...)` executes tools via a tools map.
   - Tools receive the dossier and return a DossierPatch (no side effects) or answer text (for AnswerTool).
   - The handler applies all patches under a per‑dossier lock and appends a compact tool observation to the transcript (no large source content).
6) Final LLM Call: The agent refreshes the system prompt and asks the LLM for the final answer based on the curated conversation.
7) Persist: The WebSocket server sends the reply, then persists the updated `Dossier` JSON and closes the connection.

## Code Map (Where Things Live)

- `src/agent.py`: Orchestrates one chat turn. Builds the prompt, calls the LLM, executes tools via the handler, and returns assistant text.
- `src/models.py`: Pydantic models:
  - `Legislation(title, content)` and `CaseLaw(title, content)`.
  - `DocumentTitles(titles: list[str])` for structured tool output.
  - `Dossier(dossier_id, legislation, case_law, selected_ids, conversation)` including helpers for selection and conversation.
- `src/models.py`: Core data models, including `ToolResult` and `DossierPatch`.
- `src/tool_calls.py`: Resolves/executes model tool calls, applies DossierPatch objects under a per‑dossier lock, and returns outcomes (no user-facing formatting).
- `src/sessions.py`: Dossier manager in memory:
  - `get_dossier`, `get_or_create_dossier`, `save_dossier`, `load_dossier`, `delete_dossier`, `list_dossiers`.
- `src/prompts.py`: System policy and answer template.
- `src/context.py`: Builds the static system prompt (no dynamic context injection).
- `src/llm.py`: Thin async OpenAI wrapper; returns `LlmAnswer` with `answer` and `tool_calls`.
- `src/tools/`: Tool implementations (stateless; return DossierPatch or answer text):
  - `legislation_tool.py`: dummy legislation retrieval → returns a patch (add_legislation + select_titles).
  - `case_law_tool.py`: dummy case law retrieval → returns a patch (add_case_law + select_titles).
  - `remove_sources_tool.py`: maps a removal instruction to titles and returns a patch (unselect_titles) via a structured call.
  - `answer_tool.py`: builds and returns the final answer text from dossier sources.
- `src/api/server.py`: Minimal FastAPI WebSocket server; proxies one message per connection and persists the dossier at the end.
- `terminal_chat.py`: Minimal WebSocket client for local testing.

## Data Model: Dossier

`Dossier` is the single source of truth per user conversation.

- Identity: `dossier_id: str`/
- Sources: `legislation: list[Legislation]`, `case_law: list[CaseLaw]`.
- Selection: `selected_ids: list[str]` (titles act as IDs).
- Conversation: `conversation: list[{"role","content"}]` — only user‑visible, curated turns are stored.
- Helpers:
  - `add_conversation_user`, `add_conversation_assistant`.
  - `selected_texts()`, `all_texts()`, `selected_titles()`, `unselected_titles()`.

Important: large source texts never enter the chat transcript; they stay in the dossier only. The conversation shows short, human‑readable assistant messages and lists of titles.

## Tools and Tool Results

- Each tool exposes: `name`, `description`, `parameters_schema` (for LLM function-calling), and async `execute(...)`.
- Tools are stateless and do not mutate the dossier. They return:
  - `DossierPatch` (retrieval/removal) to be applied by the handler under a lock; or
  - `ToolResult.data` as the final answer string (AnswerTool).
- The agent is responsible for composing user-visible messages from patches (e.g., titles list / confirmation) and for appending the final answer to the conversation.

## Orchestration (Agent + Handler)

- Agent (`TaxAssistant`):
  - Builds the messages from the dossier, calls the LLM, delegates tool execution, presents patches as user-facing assistant messages, and returns the final answer.
  - If AnswerTool produced an answer, the agent appends it to the conversation and returns it directly (no extra LLM call).
- ToolCallHandler:
  - Resolves and executes tool callables from a tools map, passes the dossier and args.
  - Applies all returned DossierPatch objects under a per‑dossier lock and appends compact observations to the messages for the model.
  - Returns both (updated messages, outcomes) so the agent can present patches.

## WebSocket API

- Endpoint: `GET /` (info) and `WS /ws` (single‑turn chat)
- Request JSON (one per connection):
  - `{ "message": "text", "dossier_id"?: "id" }` — if `dossier_id` is omitted, the server generates one.
- Response JSON:
  - `{ "status": "success", "response": "text", "dossier_id": "id" }`
- The server persists the dossier after sending the response and then closes the socket.

## Running Locally

- Requirements: Python 3.12+, `.env` with `OPENAI_API_KEY`.
- Install: `pip install -r requirements.txt`.
- Server: `python src/api/server.py` (FastAPI + WebSocket at `ws://localhost:8000/ws`).
- Client: `python terminal_chat.py --dossier dos-xyz` (or omit to auto‑generate).

## Extending the System

- Add a tool:
  - Create a small class with `name`, `description`, `parameters_schema`, and `async def execute(self, dossier: Dossier, **kwargs)` (return DossierPatch or an answer string).
  - Register it in the agent tools map: `agent.tools[tool.name] = tool.execute`, and add its schema to `agent.tool_schemas`.
- Change the policy or answer template: edit `src/prompts.py`.
- Evolve the data model: extend `Legislation`/`CaseLaw` or `Dossier` if you need more metadata (e.g., article numbers, ECLI) — titles are used as identifiers by default.

## Design Rationale

- Dossier‑first: a single, durable object holds sources and the curated conversation.
- Tools are pure domain logic: they return patches or an answer; they don’t perform file I/O or format user messages.
- Persistence once per turn: the server persists a snapshot after the reply to ensure atomic, user‑visible states.
- Minimal transcripts: titles and short messages keep tokens low and avoid leaking large texts into the chat.

