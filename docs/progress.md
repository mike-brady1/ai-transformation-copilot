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

## 2026-07-31 — Module 2: Document Upload + RAG foundations

- Prototyped in Colab first: chunked a sample interview transcript with `RecursiveCharacterTextSplitter`, embedded it with ChromaDB's default local model (`all-MiniLM-L6-v2`, 384-dim vectors, no API key needed), stored it in a `PersistentClient` collection, and proved semantic search works — a query with zero literal word overlap ("equipment reliable") still matched the "machine failures" chunk with the lowest distance.
- Embedding provider decision: local via ChromaDB's default (free, offline, no extra account) rather than Voyage AI. Anthropic doesn't serve embeddings itself, so this is a separate, deliberately free/simple choice — revisit if retrieval quality becomes a problem at larger scale.
- Ported into the repo:
  - `backend/models/document.py` — `Document` row per upload, with a `ForeignKey` to `workspaces.id` (first use of a relational foreign key in this project — the DB enforces "every document belongs to a real workspace")
  - `backend/rag/loaders.py` — extracts plain text from raw file bytes by extension. Only `.txt` and `.pdf` implemented so far; DOCX/PPTX/XLSX/CSV from the original spec are a follow-up, added the same way when a module actually needs them
  - `backend/rag/chunking.py` — same splitter as Colab, but `chunk_size=800` instead of the demo's `300` (300 was only small to force multiple chunks out of a tiny example; 800 chars is a more realistic real-document default)
  - `backend/rag/vector_store.py` — Chroma client + per-workspace collection (`workspace_{id}_docs`), exposed as a FastAPI dependency (`get_chroma_client`) so tests can swap in an in-memory client, mirroring how `get_db` already worked for the SQL side
  - `backend/api/routes/documents.py` — `POST .../documents` (upload, chunk, embed, store), `GET .../documents` (list), `GET .../documents/search` (semantic search — this is the exact machinery Module 6's chat will sit on top of later)
- New dependency snag: `chromadb` install produced a scary-looking `opentelemetry` version-conflict warning in Colab (from an unrelated pre-installed package, `google-adk`) that looked fatal but wasn't — and separately, a real `ModuleNotFoundError` when the Colab runtime silently restarted mid-session and lost the earlier `pip install`. Lesson: a scary red pip warning and an actual missing-module error are different things; check which one you actually have before reacting.
- Verified for real: 4 pytest cases pass (upload, 404 on unknown workspace, semantic search finds the right chunk, plus the workspace fixture), and a live `uvicorn` server round-tripped an upload + search via `curl`.

## 2026-07-31 — Module 3: Interview Analyzer

- First module that calls Claude to reason, not just search. Core concept: **structured output via tool use** — describe a JSON schema as a "tool," force Claude to call it (`tool_choice={"type": "tool", "name": ...}`), get back a real dict instead of prose to regex-parse.
- Prototyped in Colab: extracted 3 distinct pain points (with severity, business impact, named recommendation) from the sample transcript, one per interview segment — confirmed non-generic recommendations (e.g. "Predictive Maintenance Program" not "improve maintenance").
- Hit a Colab-specific bug worth remembering: reused the variable name `client` for both the Anthropic client (Module 0) and `TestClient(app)` (Module 1) in the same notebook session — the second assignment silently shadowed the first, causing `AttributeError: 'TestClient' object has no attribute 'messages'`. Fixed by using distinct names (`anthropic_client` vs `client`). This is a Colab/notebook-specific risk (one shared global namespace across all cells) that a fresh Python process per run doesn't have.
- Discussed Colab vs. local Jupyter: recommended local going forward since nothing in this project needs Colab's main draw (free GPU), and local lets Claude Code run/verify cells directly instead of relying on copy-pasted output — decision deferred, still using Colab for now.
- Ported into the repo:
  - `backend/ai/client.py` — `get_anthropic_client()` FastAPI dependency, reads `ANTHROPIC_API_KEY` from a local `.env` (via `python-dotenv`) — the local equivalent of Colab's Secrets panel
  - `backend/ai/interview_analysis.py` — the tool schema + system prompt + `analyze_transcript()`
  - `backend/schemas/interview.py` — `PainPoint` response schema
  - `documents.py` — added `chunk_index` to chunk metadata at upload time (needed to reassemble a document's chunks in original order later) and a new `POST .../documents/{document_id}/analyze` endpoint that uses `collection.get(where=...)` — an exact metadata lookup, different from the similarity-search `.query()` used for search — to pull all of one document's chunks, sorts by `chunk_index`, rejoins into full text, and sends that to `analyze_transcript()`
- Testing note: mocked the Anthropic client in tests (`_FakeAnthropicClient`, shaped like the real SDK's response) instead of calling the real API — no cost, no network dependency, no non-determinism in CI. Skipped a live-server `curl` smoke test this time for the same cost reason; the Colab run + mocked tests together cover it.
- Verified: 6 pytest cases pass (up from 4), including the new analyze endpoint and its 404 case.
