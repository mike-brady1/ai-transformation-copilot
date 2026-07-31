# Progress Log

A running record of what's been built, in what order, and *why* — the reasoning, not just the diff. Useful for interview prep: this is the "defend your decisions" cheat sheet.

## 2026-07-31 — Environment setup

- Started fresh: archived the old all-at-once scaffold, decided to build module by module instead.
- Workflow: prototype each module in a Colab notebook first (understand every line), then port working code into this repo.
- Chose GitHub for version control + as the deploy source for Streamlit Community Cloud / Render.
- Planned free hosting for later: Streamlit Community Cloud (frontend), Render (FastAPI backend), Neon (Postgres). ChromaDB persists to a local file, no separate host needed.
- Repo pushed to GitHub: https://github.com/mike-brady1/ai-transformation-copilot
- LLM provider: **Anthropic (Claude)** instead of the original spec's OpenAI. Reason: already working with Claude in this build process, consistent story for interviews. Functionally interchangeable for RAG/consulting-copilot purposes — same concepts (chat completions, embeddings via a separate embedding model since Anthropic doesn't serve one, tool use) apply either way.
- Verified the Colab → Secrets → Anthropic API round trip works (`claude-sonnet-4-5`, `messages.create`).

## 2026-07-31 — Module 1: Company Workspace

- Prototyped in Colab first: Pydantic model for validation → SQLAlchemy ORM model + SQLite for persistence → FastAPI endpoints → verified with `TestClient`, all in-notebook, no server needed.
- Ported into the repo as separate concerns instead of one script, since real projects split by responsibility:
  - `backend/database.py` — engine + session + `get_db` dependency
  - `backend/models/workspace.py` — SQLAlchemy ORM model (the DB table)
  - `backend/schemas/workspace.py` — Pydantic request/response shapes (the API contract)
  - `backend/api/routes/workspaces.py` — the actual endpoints
  - `backend/api/main.py` — assembles the FastAPI app
- Persistence: SQLite file for now (`sqlite:///./workspaces.db`), zero setup. Swapping to Postgres later is a one-line change to `DATABASE_URL` because SQLAlchemy is an ORM — the rest of the code doesn't know or care which database it's talking to.
- Added `tests/test_workspaces.py` using FastAPI's `dependency_overrides` to swap in a throwaway per-test SQLite file, so tests never touch the real database or each other.
- Verified for real, not just assumed: ran `pytest` (1 passed) and briefly started the actual `uvicorn` server and hit `/health` and `/workspaces` with `curl` before committing.
