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

## 2026-07-31 — Module 6: AI Consulting Chat

- Combines Module 2 (retrieval) and Module 3's Claude-calling pattern into a grounded, multi-turn RAG chat. "Grounded" = the system prompt instructs Claude to answer ONLY from retrieved excerpts and say so explicitly when something isn't covered, rather than falling back to general knowledge — this is what makes it a consulting-copilot answer instead of a generic chatbot answer.
- Design: retrieved context goes in the **system prompt** (rebuilt fresh every turn, based only on the latest question), while conversation memory lives entirely in the **messages list** (accumulated turn by turn). These two update independently, which is what let a "what would you recommend to fix **it**?" follow-up resolve correctly in the Colab test — Claude only knows "it" refers to machine downtime because the prior turns are in `messages`, not because retrieval re-ran on the pronoun.
- Proved three things at once in Colab with three questions: a grounded factual answer, a multi-turn follow-up requiring conversation memory, and — most important — a correct refusal ("I don't have that information in the uploaded documents") on an out-of-scope question about marketing budget, instead of a hallucinated answer.
- Ported into the repo:
  - `backend/ai/chat.py` — `build_context()` (same retrieval as Module 2's search, plus tracks which source filenames were used) and `answer_question()`
  - `backend/schemas/chat.py` — `ChatRequest`/`ChatResponse`. Deliberately **stateless**: the caller sends the full conversation history each request; the backend doesn't persist chat sessions. Reason: no frontend exists yet to know what a real session data model needs to look like, so this avoids guessing — Streamlit will hold `messages` in its own session state later, same as the Colab `history` list did.
  - `backend/api/routes/chat.py` — `POST /workspaces/{workspace_id}/chat`
- Verified: 8 pytest cases pass (up from 6), including sources coming back correctly attributed to the uploaded filename and a 404 on an unknown workspace. Used the same mocked-Anthropic-client approach as Module 3 (no real API cost in tests).

## 2026-07-31 — Streamlit frontend (Home, Documents, Interview Analyzer, Chat)

- Built directly in the repo, not Colab-first like the AI modules — Streamlit needs a persistent local server to click around in, which is the exact thing Colab struggles with. Verified in a real browser instead (Claude Code's preview tooling), not just described.
- Structure: `app/main.py` (workspace create/select — everything else depends on having a `workspace_id`, stored in `st.session_state`) + `app/pages/1_Documents.py`, `2_Interview_Analyzer.py`, `3_Chat.py` (Streamlit's numeric-prefix convention drives sidebar order/naming automatically) + `app/services/api_client.py` (thin `requests` wrapper — the frontend never touches the DB or Claude directly, only the FastAPI backend).
- Import mechanics worth remembering: pages import as `from services.api_client import ...`, not `from app.services...`. Streamlit inserts the *main script's own directory* (`app/`) into `sys.path` once at startup, and that entry persists for the whole session including page navigations — so `app/` acts as the import root, not the project root.
- `.claude/launch.json` (both the one at the actual working-directory root and the one inside the repo, for standalone clones) got a `frontend` entry alongside `backend`, with `--server.headless true` passed explicitly since the launcher's working directory doesn't reliably pick up `.streamlit/config.toml`.
- Bugs found by actually clicking through it, not just reading the code:
  - Coordinate-based clicks on Streamlit buttons were unreliable right after a rerun (DOM shifts under fixed pixel coordinates); clicking by element ref instead fixed it. Not an app bug, a browser-automation lesson.
  - Direct URL navigation to a page (vs. clicking a sidebar link) opens a new browser session/websocket, which resets `st.session_state` — confirmed this is expected Streamlit behavior, not a bug, by seeing the "select a workspace first" guard correctly re-trigger.
  - Real bug: an API failure (tested by hitting Chat with no `ANTHROPIC_API_KEY` configured locally) surfaced as a raw Python traceback with local file paths dumped into the UI — `requests`' `raise_for_status()` was uncaught. Fixed by wrapping the AI-calling pages (Chat, Interview Analyzer) in `try/except requests.exceptions.RequestException` with a plain-language `st.error()` instead. Worth remembering for a demo: this is exactly the kind of thing that only shows up when you actually break the happy path, not when you only test it working.
- Known gap: browser automation here can't drive an OS-native file-picker dialog, so the file upload widget's happy path wasn't click-tested end-to-end in the browser — the upload *endpoint* itself was already proven separately (pytest + a live `curl` round-trip back in Module 2), so this is a UI-wiring gap, not a functionality gap. Worth manually testing once by hand.

## 2026-07-31 — Real API key wired up locally

- Two bugs found getting the local `.env` working, neither in the app's actual logic:
  - The `.env` file got saved as `.env.txt` by the text editor — a classic Windows gotcha (editors/File Explorer silently appending `.txt`). Renamed it; worth double-checking the exact filename (no extension) whenever a "why isn't my env var loading" mystery shows up.
  - `backend/ai/client.py`'s `load_dotenv()` (no arguments) relies on searching from the calling file's location, which got tripped up by the same cwd mismatch that `.claude/launch.json` needed workarounds for earlier (the actual server process's working directory is the parent folder, not the repo root). Fixed by passing an explicit path computed from `Path(__file__)`, independent of cwd.
- Verified for real: sent a live chat question with zero documents uploaded to that workspace — got back a genuine Claude response correctly saying it had no material to reference, rather than guessing. Confirms both the real API connection and the grounding behavior together, this time without the mocked client.

## 2026-07-31 — Module 7: SWOT Generator

- New retrieval shape: `collection.get()` with no filter, no query — pulls back *every* chunk from *every* document in a workspace, ordered by `(document_id, chunk_index)`. Different from Module 3 (one document) and Module 6 (top-k similarity search for one question) — a SWOT needs the whole picture, there's no single query to search by.
- Tool schema: four arrays (`strengths`/`weaknesses`/`opportunities`/`threats`), each item a `{item, explanation}` pair so every claim traces back to a one-sentence reason, not a floating label.
- Enriched the Colab demo transcript with one positive line (experienced workforce) specifically so Strengths wouldn't be empty — worth noting the *original* transcript correctly would have produced an empty Strengths quadrant, which is the grounding working correctly, just not a useful demo.
- Proved the interesting part: Opportunities and Threats were never stated in the transcript — Claude had to infer them (predictive maintenance as an opportunity, production capacity loss as a threat) while still keeping every explanation traceable to something actually said. Grounded doesn't mean "verbatim only," it means "no claim without a real source."
- Ported into the repo: `backend/ai/swot.py`, `backend/schemas/swot.py`, `backend/api/routes/swot.py` (`POST /workspaces/{workspace_id}/swot`, 400 if no documents uploaded yet), `app/pages/5_SWOT.py` — rendered as a classic 2×2 quadrant matrix (`st.columns` twice), not a flat list, since that's the actual visual consultants use.
- **Real bug found and fixed**, not just a false alarm this time: `chromadb.EphemeralClient()` instances created in the same Python process share their underlying in-memory store — it's cached internally by settings, not truly isolated per instance. Confirmed empirically (`tests/conftest.py` documents the repro) before trusting it as the cause. Every test file's `workspace_id` fixture creates a fresh SQLite DB where autoincrement restarts at 1, so every test file was accidentally sharing one Chroma collection named `workspace_1_docs` — a document uploaded in `test_documents.py` was silently visible to `test_swot.py`. First attempt at a fix (call `.reset()` inside the FastAPI dependency override itself) overcorrected: that runs once *per request*, so it wiped a test's own data between its own upload and search calls. Real fix: reset exactly once per test (in fixture setup, before any requests), with a separate no-reset function used as the actual per-request dependency override — both using identical `Settings` objects, since chromadb also refuses to share its "ephemeral" identifier across mismatched settings. Applied consistently across all four affected test files via a shared `tests/conftest.py` helper, so a fifth test file can't reintroduce the same bug.
- Verified for real: live `curl` round-trip against the real server with a real uploaded transcript and a real Claude call, plus visual confirmation of the 2×2 quadrant layout in the browser.

## 2026-07-31 — Module 8: Roadmap Generator

- First **chained AI pipeline** in this project: the roadmap endpoint doesn't re-read raw documents — it calls `generate_swot()` (Module 7's function) first, formats that structured result back into plain text, and feeds *that* into a second Claude call as the roadmap's actual input. One step's structured output becomes the next step's context. This is the seed of what "agentic workflows" actually are, and it's also just how a real consultant works — you build the roadmap from your findings, not by re-reading every transcript from scratch each time.
- **Real, reproducible bug found in Colab**, not a fluke: `tool_choice` forces Claude to *call* the tool, but doesn't guarantee every `required` field in the schema comes back with the exact key name. Claude has such a strong prior toward capitalizing "ROI" as an acronym that it emitted `expected_ROI` instead of the schema's `expected_roi` — consistently, across nearly every item in the response, not a one-off fluke. Confirmed by inspecting the actual malformed dict rather than guessing.
- Two-part fix, one specific and one general:
  1. Renamed the field to `expected_return` (`backend/ai/roadmap.py`) — avoiding acronym-shaped field names in tool schemas sidesteps this specific capitalization instinct. Confirmed fixed against the real API afterward (every item came back correctly keyed).
  2. Made every field except `initiative` `Optional` in `backend/schemas/roadmap.py` regardless — the general lesson is that `tool_choice`-forced structured output is far more reliable than free-text parsing, but still not a 100% guarantee the way validating an *incoming* request is. Any future mismatch now degrades to a blank field instead of a 500.
- `tests/test_roadmap.py` includes a **regression test that reproduces the exact bug** (a fake response with `expected_ROI` instead of `expected_return`) and asserts the endpoint still returns 200 with the field simply empty — this is deliberately testing the *defense*, not just the happy path.
- Verified for real against the live server: two genuine sequential Claude calls, and the resulting roadmap's dependencies meaningfully chain across horizons (a Medium-Term item correctly named a specific Quick Win as its prerequisite) — not just three disconnected lists. Confirmed the Streamlit page renders all three horizons with cost/complexity/ROI badges and dependency notes.

## 2026-07-31 — Refactor + Module 5: Digital Maturity Assessment

- Refactor first: SWOT, Roadmap, and now Digital Maturity all needed "every chunk from every document in a workspace" (as opposed to Chat's top-k similarity search). Third occurrence of the same logic, so extracted it into `get_full_workspace_context()` in `backend/rag/vector_store.py` and updated the SWOT/Roadmap routes to use it instead of their own copies — three near-identical blocks earned the abstraction; two wouldn't have.
- Same "don't trust the LLM with arithmetic" decision as Module 4: Claude scores the 9 individual dimensions (Leadership, Operations, Technology, Data, Supply Chain, Automation, Sustainability, Cybersecurity, Workforce), 1-5 each — but the `overall` average is computed by our own Python code, never asked of Claude.
- Handled the "zero evidence for a dimension" case explicitly rather than leaving it ambiguous: the system prompt instructs Claude to score an unevidenced dimension a neutral 3 and say so ("Insufficient evidence in provided documents") rather than either inventing detail or leaving it blank — confirmed in the Colab run that Sustainability and Cybersecurity (genuinely absent from our fictional transcript) got exactly this treatment.
- Extended the defensive-schema lesson from Module 8 one step further: normalization now happens in the **route**, not just the Pydantic schema — a missing category, a missing score, or a score outside 1-5 all fall back to the same neutral 3, unifying "Claude honestly flagged this as unknown" and "Claude's response was malformed" into one code path instead of two.
- `tests/test_digital_maturity.py` includes a fake response with an **entire category key omitted** (`cybersecurity`, not just a field) and asserts the endpoint still returns 200 with that dimension defaulted to 3 — plus an exact numeric assertion on the computed `overall` (2,2,2,2,2,2,3,3,3 → 2.3).
- Verified for real: live `curl` round-trip (overall computed correctly as 2.4 for that run) and visual confirmation of the Streamlit page — metric, bar chart, and all 9 star ratings with justifications. Noted the overall differed slightly between the `curl` run and the browser run (2.4 vs 2.3) — expected LLM non-determinism between two independent calls, not a bug.

## 2026-07-31 — Module 9: Technology Recommendation Engine

- Third module chained off the SWOT (`generate_swot()`), but narrower than Roadmap: only the **Weaknesses** quadrant is used (`format_weaknesses_as_text()`, new in `backend/ai/swot.py`), since the spec's Problem → Recommendation → Technology → Platform → ROI format is a direct 1:1 mapping from problems to fixes, not a phased synthesis.
- Explicit, worth-articulating distinction from every prior AI module: grounding (never answer from outside the client's documents) applies to **client-specific facts** — but recommending "Azure IoT" vs "AWS IoT Core" isn't a client fact, it's general technology knowledge, exactly what an LLM's training is suited for. So this module deliberately grounds the *problem* side in the SWOT while letting Claude use its own knowledge for the *solution* side (real, current vendor/platform names). Confirmed it named specific real products (Azure IoT, PTC ThingWorx, project44) rather than generic categories.
- Applied Module 8's lesson **proactively** this time instead of reactively: the field was named `expected_return` from the very first draft, not `expected_roi` — confirmed via the Colab run that it came back correctly keyed on the first try, no capitalization drift.
- Small cost-saving decision: if the SWOT step finds zero weaknesses, the route returns an empty recommendation list immediately instead of spending a second Claude call recommending technology for nothing. `tests/test_technology.py` proves this actually happens (not just that the output looks right) by making the fake client's technology-tool branch raise if it's ever called when weaknesses is empty.
- Verified for real: live `curl` round-trip against the actual server produced four grounded problem→platform mappings with real vendor names, and the Streamlit table rendered (confirmed via the dataframe toolbar controls appearing, since a visual screenshot wasn't available this session).

## 2026-07-31 — Module 4: KPI Dashboard

- Deliberately **no Claude call** in this module — OEE/MTBF/MTTR are well-defined formulas, not a reasoning task. An LLM would be slower, cost money, and add non-determinism for zero benefit. Worth being able to articulate this "when NOT to use AI" judgment call, not just "when to use it."
- Domain content: OEE (Overall Equipment Effectiveness) = Availability × Performance × Quality, the single number consultants actually report to plant managers (world-class ≈ 85%, most real factories run 60-75%). Plus MTBF (reliability) and MTTR (repair speed), both derived from operating time / downtime / failure count.
- Computed from **raw** operational data (planned time, downtime, units produced, good units, ideal cycle time, failure count, energy) rather than accepting pre-computed ratios — more realistic, and the only way MTBF/MTTR can be derived at all. Verified the formulas by hand before running any code, then confirmed the Colab pandas output matched exactly.
- Deliberately made "Line 3" in the sample data worse (more downtime, more failures) to match the "machine failures happen almost every week" complaint from the Module 3 interview transcript — same fictional Acme engagement, consistent numbers across every module telling one coherent story.
- Pandas concept: vectorized column operations (`df["oee"] = df["availability"] * df["performance"] * df["quality"]`) instead of a per-row Python loop — the core reason pandas is fast, and a common interview question.
- Ported into the repo:
  - `backend/kpi/calculations.py` — `compute_kpis()`, pure pandas, validates required columns are present and raises `ValueError` (→ HTTP 400) if not
  - `backend/api/routes/kpi.py` — `POST /workspaces/{workspace_id}/kpi`, parses an uploaded CSV with `pd.read_csv`
  - `app/pages/4_KPI_Dashboard.py` — upload + `st.dataframe` table + `st.bar_chart` of OEE by machine
  - `datasets/sample_kpi.csv` — sample data matching the Colab numbers, for manually testing the upload widget by hand (still the one browser-automation gap)
- This module was fully verifiable without any mocking — deterministic math, no external API, so pytest asserts *exact* numeric values (not just "status 200") for the first time in this project. Also confirmed via a live `curl` round-trip that matched the hand-calculated numbers to the decimal.
- Bug hit while verifying in the browser (not a real app bug): the Streamlit frontend process had been running since before `upload_kpi_csv` was added to `api_client.py` — Python caches already-imported modules in memory, so the running process didn't see the new function until restarted. Lesson: adding a function to a module already imported by a long-running process needs a process restart, not just a page refresh.
