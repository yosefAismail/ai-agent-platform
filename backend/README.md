# Backend

FastAPI backend for the chat app. Install dependencies with `uv sync`, then
start it from this directory with `uv run uvicorn backend.main:app --reload
--app-dir src`. Set `GEMINI_API_KEY` in `backend/.env`; `GEMINI_MODEL` and
comma-separated `CORS_ORIGINS` can also be configured there.

SQLite data is stored at `backend/data/conversations.db` by default. Set
`DATABASE_URL` to override the connection URL.

## Conversation API

- `POST /conversations` — create with optional `{"title":"..."}`.
- `GET /conversations` — list conversations.
- `GET /conversations/{id}` — get a conversation and its messages.
- `GET /conversations/{id}/messages` — list messages chronologically.
- `POST /conversations/{id}/messages` — send `{"content":"..."}`; returns
  the persisted user and assistant messages plus a `response` convenience field.
- `DELETE /conversations/{id}` — delete a conversation and its messages.

The legacy `POST /chat` endpoint remains available and accepts the full
`{"messages":[{"role":"user|assistant","content":"..."}]}` history.

Run the offline tests from this directory with:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m unittest backend.test_gemini backend.test_conversations -v
```
