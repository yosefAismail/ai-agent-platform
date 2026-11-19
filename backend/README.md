# Backend

FastAPI backend for the chat app. Install dependencies with `uv sync`, then
start it from the `backend` directory:

```powershell
uv run uvicorn backend.main:app --reload --app-dir src
```

Set `GEMINI_API_KEY` in `backend/.env`. The `GEMINI_MODEL` and comma-separated
`CORS_ORIGINS` settings can also be configured there.

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

The LLM service offers Gemini one backend tool: `get_current_time`. It returns
an ISO 8601 timestamp in UTC, with the timezone labeled as `UTC`.

Function calling is handled manually. The backend validates the requested
function name and arguments against an allowlist, executes the tool, and sends
the result back to Gemini for a final answer. A request supports one tool
round-trip only. Direct Gemini text responses continue to work without running
the tool. Intermediate tool calls and results are not stored as conversation
messages; only the user's message and the final assistant response are
persisted.

## Tests

Run the backend's offline tests from the `backend` directory. Gemini calls and
the clock are mocked; these tests do not call the live Gemini API.

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m unittest backend.test_gemini backend.test_conversations -v
```
