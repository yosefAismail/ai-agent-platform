# Backend

FastAPI backend for the chat app. Install dependencies with `uv sync`, then
start it from the `backend` directory:

```powershell
uv run uvicorn backend.main:app --reload --app-dir src
```

Set `GEMINI_API_KEY` in `backend/.env`. The `GEMINI_MODEL` and comma-separated
`CORS_ORIGINS` settings can also be configured there. Agent limits may be set
with `AGENT_MAX_TOOL_ITERATIONS` (default 5, max 20) and
`AGENT_MAX_TOOL_CALLS_PER_ROUND` (default 4, max 10).

SQLite data is stored in `backend/data/conversations.db` by default. Set
`DATABASE_URL` to override the database connection URL.

## Conversation API

- `POST /conversations` - create a conversation with an optional
  `{"title":"..."}` body.
- `GET /conversations` - list conversations.
- `GET /conversations/{id}` - get a conversation and its messages.
- `GET /conversations/{id}/messages` - list messages chronologically.
- `POST /conversations/{id}/messages` - send a new message with
  `{"content":"..."}`. The response includes the persisted user message,
  assistant message, and a `response` convenience field.
- `DELETE /conversations/{id}` - delete a conversation and its messages.

The legacy `POST /chat` endpoint remains available. It accepts the full history:

```json
{
  "messages": [
    {"role": "user", "content": "Hi"},
    {"role": "assistant", "content": "Hello"}
  ]
}
```

## Gemini Function Calling

The LLM service offers five backend tools: `get_current_time` (ISO 8601 UTC
timestamp), `calculate` (restricted arithmetic), `convert_units` (supported
length units), `convert_temperature` (C/F/K, rejecting temperatures below
absolute zero), and `count_words` (text limited to 5,000 characters).

Function calling is handled manually. Gemini may answer directly or request
tools; the backend validates every requested name and argument against an
allowlist before executing any call in a batch. It returns one matching
function response for each call, using the `user` role supported by the
configured integration, and continues up to the configured iteration and
per-round call limits. Automatic function calling is disabled. Intermediate
tool calls and results are not stored as conversation messages; only the
user's message and final assistant response are persisted.

## Tests

Run the backend's offline tests from the `backend` directory. Gemini calls and
the clock are mocked; these tests do not call the live Gemini API.

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m unittest backend.test_gemini backend.test_conversations -v
```
