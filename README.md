# AI Agent Platform

A full-stack AI chat app with a React and Vite frontend, a FastAPI backend, Gemini
responses, and persistent conversation history in SQLite. The frontend reads and
writes conversations through the backend API; it does not use browser storage as
the source of truth.

## Features

- Create, list, open, and delete conversations.
- Persist user and assistant messages in SQLite.
- Send the new message to the backend; the backend supplies the stored history
  to Gemini.
- Gemini can answer directly or request one or more registered backend tools.
- Manual function-call validation and execution in a bounded multi-tool loop.
- The legacy `POST /chat` endpoint is retained for clients that send full
  message history.

## Architecture

```text
frontend/                         React + Vite UI
  src/
    components/chat/              Chat window, input, and message components
    features/conversations/       Conversation sidebar and API-backed hook
    hooks/useChat.js              Chat sending state
    services/                     Fetch client and API modules

backend/src/backend/
  api/routes/conversations.py     Conversation HTTP endpoints
  core/config.py                  Environment configuration
  database/                       SQLAlchemy engine, session, and base
  models/                         Conversation and message tables
  repositories/                   Database operations
  schemas/                        Request and response validation
  services/                       Conversation, Gemini, and tool logic
```

The SQLite database defaults to `backend/data/conversations.db`. Each message
belongs to one conversation; deleting a conversation cascades to its messages.
The backend creates the database and tables when it starts.

## Requirements

- Python 3.13 or newer, with [uv](https://docs.astral.sh/uv/) installed.
- Node.js and npm.
- A Gemini API key.

## Run locally

### 1. Configure and start the backend

From the repository root, open a terminal:

```powershell
cd backend
uv sync
```

Create `backend/.env` with your Gemini key. These settings are optional except
for `GEMINI_API_KEY`:

```dotenv
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-3.5-flash-lite
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
# Optional agent limits (defaults shown):
# AGENT_MAX_TOOL_ITERATIONS=5
# AGENT_MAX_TOOL_CALLS_PER_ROUND=4
# Optional database override:
# DATABASE_URL=sqlite:///./data/conversations.db
```

Start the API:

```powershell
uv run uvicorn backend.main:app --reload --app-dir src
```

The API runs at `http://localhost:8000`. Interactive API documentation is at
`http://localhost:8000/docs`.

### 2. Start the frontend

In a second terminal, from the repository root:

```powershell
cd frontend
npm install
npm run dev
```

Vite serves the app at `http://localhost:5173`. The frontend defaults to the
backend at `http://localhost:8000`. To use another backend URL, set
`VITE_API_URL` in `frontend/.env.local`, for example:

```dotenv
VITE_API_URL=http://localhost:8000
```

## Conversation API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/conversations` | Create a conversation |
| `GET` | `/conversations` | List conversations |
| `GET` | `/conversations/{id}` | Get a conversation and its messages |
| `GET` | `/conversations/{id}/messages` | List messages chronologically |
| `POST` | `/conversations/{id}/messages` | Send a message and receive Gemini's reply |
| `DELETE` | `/conversations/{id}` | Delete a conversation and its messages |

Create a conversation with an optional title:

```json
{"title":"A new chat"}
```

Send one new message (the client does not send the full history):

```json
{"content":"What time is it?"}
```

The response includes `user_message`, `assistant_message`, and a `response`
field containing the assistant text. If Gemini fails, the API returns HTTP 502;
the user message remains saved and no assistant message is fabricated. Unknown
conversation IDs return HTTP 404.

The compatibility endpoint `POST /chat` accepts the full history in a `messages`
array with `user` and `assistant` roles.

## Gemini tool behavior

The backend registers five allowlisted tools: `get_current_time`, `calculate`,
`convert_units`, `convert_temperature`, and `count_words`. Gemini receives their
declarations with the conversation history and chooses whether to call them.
The backend validates each name and argument schema before executing a batch,
then returns a matching function response for every call. It continues for up to
`AGENT_MAX_TOOL_ITERATIONS` rounds and accepts up to
`AGENT_MAX_TOOL_CALLS_PER_ROUND` calls in one round. Both limits have bounded
defaults. Arithmetic uses a restricted parser; length and temperature units are
explicitly enumerated, absolute-zero temperatures are rejected, and word-count
input is limited to 5,000 characters. Function responses use the Gemini `user`
role supported by the configured integration. Only the user message and final
assistant response are stored; intermediate calls and results are not persisted.

## Checks

Run backend tests from `backend`:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m unittest backend.test_gemini backend.test_conversations -v
```

Run frontend checks from `frontend`:

```powershell
npm run lint
npm run build
```

Backend tests mock Gemini and the clock, so they do not require live API calls.

## Roadmap and progress

This roadmap follows the companion architecture map. Status reflects the current
repository; future inspiration and project priorities can change the order or
scope of later stages.

| Stage | Status | Scope / completion goal |
| --- | --- | --- |
| 1. Current foundation | Complete | React + Vite, FastAPI, Gemini, SQLAlchemy models, SQLite persistence, conversation API, and offline tests. |
| Frontend persistence integration | Complete | React uses `/conversations`; conversation data is loaded from and saved to SQLite through the backend, not browser `localStorage`. |
| 2. Function calling + first tool | Complete | Manual Gemini function calling, allowlisted tool execution, and persisted final replies. |
| 3. Multi-tool agent loop | Complete | Five validated tools, bounded sequential rounds and parallel calls, safe failure handling, final-response-only persistence, and a successful configured-model tool round-trip using the `user` function-response role. |
| 4. Better tool architecture | Planned | Organize tool declarations, schemas, permissions, and execution so adding a tool stays predictable and disallowed tools are refused. |
| 5. LangGraph | Optional future stage | If orchestration needs grow, model stateful flows with nodes, conditional routing, checkpoints, and possible human approval. |
| 6. Retrieval-augmented generation (RAG) | Planned | Ingest documents, extract and chunk text, create embeddings, retrieve relevant passages, and have answers cite sources. No vector database has been selected. |
| 7. Evals and production readiness | Planned | Add automated quality and tool-use evaluations, tracing, latency/token/cost tracking, retries, security controls, rate limits, and reliability work. |

LangChain remains optional; the app currently calls Gemini directly through
`google-genai`. SQLite remains the conversation store. If RAG is added, document
embeddings and retrieval can use a separate vector store.
