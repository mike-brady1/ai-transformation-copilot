# AI Industry Transformation Consultant

[![CI](https://github.com/mike-brady1/ai-transformation-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/mike-brady1/ai-transformation-copilot/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An AI-powered digital transformation copilot for strategy consultants — analyzes client documents and operational data, then generates the deliverables a consulting engagement actually produces: SWOT, digital maturity score, technology roadmap, sustainability estimate, and an exportable executive report and slide deck.

> Portfolio project inspired by Capgemini Invent's Intelligent Industry practice. Built module by module — see [`docs/progress.md`](docs/progress.md) for the full engineering journal: every architecture decision, every bug found, and why, in the order it actually happened.

## Status

All 12 modules from the original spec are complete, tested, and verified end-to-end against the real Claude API.

| # | Module | Backend | Frontend |
|---|--------|---------|----------|
| 1 | Company Workspace | [`workspaces.py`](backend/api/routes/workspaces.py) | [`main.py`](app/main.py) |
| 2 | Document Upload + RAG | [`documents.py`](backend/api/routes/documents.py) | [`1_Documents.py`](app/pages/1_Documents.py) |
| 3 | Interview Analyzer | [`documents.py`](backend/api/routes/documents.py) (`/analyze`) | [`2_Interview_Analyzer.py`](app/pages/2_Interview_Analyzer.py) |
| 4 | Operational KPI Dashboard | [`kpi.py`](backend/api/routes/kpi.py) | [`4_KPI_Dashboard.py`](app/pages/4_KPI_Dashboard.py) |
| 5 | Digital Maturity Assessment | [`digital_maturity.py`](backend/api/routes/digital_maturity.py) | [`7_Digital_Maturity.py`](app/pages/7_Digital_Maturity.py) |
| 6 | AI Consulting Chat | [`chat.py`](backend/api/routes/chat.py) | [`3_Chat.py`](app/pages/3_Chat.py) |
| 7 | SWOT Generator | [`swot.py`](backend/api/routes/swot.py) | [`5_SWOT.py`](app/pages/5_SWOT.py) |
| 8 | Transformation Roadmap | [`roadmap.py`](backend/api/routes/roadmap.py) | [`6_Roadmap.py`](app/pages/6_Roadmap.py) |
| 9 | Technology Recommendations | [`technology.py`](backend/api/routes/technology.py) | [`8_Technology_Recommendations.py`](app/pages/8_Technology_Recommendations.py) |
| 10 | Sustainability Analyzer | [`sustainability.py`](backend/api/routes/sustainability.py) | [`9_Sustainability.py`](app/pages/9_Sustainability.py) |
| 11 | Executive Report Generator | [`executive_report.py`](backend/api/routes/executive_report.py) | [`10_Executive_Report.py`](app/pages/10_Executive_Report.py) |
| 12 | PowerPoint Generator | *(reuses Module 11's endpoint)* | [`11_PowerPoint.py`](app/pages/11_PowerPoint.py) |

## How the AI is actually used

Not every module calls an LLM, and the ones that do don't all use it the same way — worth being explicit about, since "just call Claude" isn't a design:

- **Pure computation, no LLM**: KPI Dashboard (OEE/MTBF/MTTR are exact formulas; an LLM would be slower, costlier, and non-deterministic for zero benefit).
- **Grounded in client documents**: Interview Analyzer, SWOT, Digital Maturity, Chat. These are instructed to answer only from what's actually in the uploaded documents, and to say so explicitly when evidence is missing rather than invent it (Chat refuses out-of-scope questions; Digital Maturity scores an unevidenced dimension a neutral 3 and states "insufficient evidence").
- **Grounded problem + general knowledge solution**: Technology Recommendations. The *problem* (a SWOT weakness) is grounded in the client's documents; the *solution* (which vendor platform — Azure IoT vs. PTC ThingWorx) is general technology knowledge no client document could contain, so the LLM is deliberately allowed to use its own training there.
- **LLM supplies judgment, code does the math**: Sustainability Analyzer. Claude proposes a plausible grid emissions factor with a stated assumption; the actual CO2 arithmetic (`energy_kwh × factor`) happens in Python, never in the model.
- **Chained pipelines**: Roadmap and Technology Recommendations both build on the SWOT's *output*, not on raw documents again — one call's structured result becomes the next call's input, the same idea reused for the Executive Report and PowerPoint, which reuse the SWOT/Roadmap/Maturity/Technology results already sitting in the Streamlit session rather than regenerating them a second time.

## Architecture

```
                     +----------------------+
                     |    Streamlit UI      |
                     +----------+-----------+
                                |  HTTP (requests)
                                v
                     +----------------------+
                     |   FastAPI backend    |
                     +----------------------+
                     /          |           \
                    v           v            v
              SQLite/Postgres  ChromaDB   Anthropic (Claude)
              (workspaces,     (embedded    (chat, SWOT,
               documents       chunks,      roadmap, maturity,
               metadata)       per-        technology,
                                workspace)   sustainability,
                                             executive report)
```

The frontend never touches the database, the vector store, or Claude directly — every AI call and every piece of persistence lives in the backend, reached only over HTTP. Document chunks are embedded locally (`sentence-transformers` via ChromaDB's default embedding function — no embeddings API key needed) since Anthropic doesn't serve an embeddings endpoint.

## Getting Started

### 1. Clone and install

```bash
git clone https://github.com/mike-brady1/ai-transformation-copilot.git
cd ai-transformation-copilot
python -m venv .venv
.venv\Scripts\activate   # source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
```

### 2. Configure your API key

```bash
cp .env.example .env
```

Edit `.env` and set `ANTHROPIC_API_KEY` (get one at [console.anthropic.com](https://console.anthropic.com)). This is a pay-as-you-go key, separate from any Claude.ai subscription.

### 3. Run it

```bash
# Terminal 1 — backend
python -m uvicorn backend.api.main:app --reload

# Terminal 2 — frontend
python -m streamlit run app/main.py
```

Backend docs (interactive Swagger UI): http://localhost:8000/docs
Frontend: http://localhost:8501

A sample KPI CSV is included at [`datasets/sample_kpi.csv`](datasets/sample_kpi.csv) for testing the KPI Dashboard and Sustainability Analyzer without needing real operational data.

### 4. Run the tests

```bash
pytest
```

No API key required to run the test suite — every test that would call Claude substitutes a fake client (see [`tests/conftest.py`](tests/conftest.py)), so the suite is free, fast, and deterministic. CI runs this on every push via [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

## Folder Structure

```
ai-transformation-copilot/
├── app/                  # Streamlit frontend
│   ├── pages/             # one page per module (numeric prefix = sidebar order)
│   ├── services/          # thin HTTP client wrapping the backend API
│   └── main.py            # workspace creation/selection
├── backend/
│   ├── ai/                 # Claude prompts, tool schemas, one file per module
│   ├── api/routes/         # one FastAPI router per module
│   ├── kpi/                # OEE/MTBF/MTTR calculations (pandas, no LLM)
│   ├── rag/                # chunking, document loaders, ChromaDB access
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/              # Pydantic request/response schemas
│   └── database.py
├── datasets/               # sample data for manual testing
├── docs/progress.md        # the engineering journal — every decision and bug, in order
├── tests/                  # pytest, one file per module, all Claude calls mocked
├── .streamlit/config.toml
└── requirements.txt
```

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy (SQLite by default, Postgres-ready via `DATABASE_URL`)
- **Frontend**: Streamlit
- **AI**: Anthropic Claude (`claude-sonnet-4-5`), tool use for structured output, ChromaDB for vector search, `sentence-transformers` for local embeddings
- **Data**: pandas
- **Exports**: `python-docx` (Word), `fpdf2` (PDF), `python-pptx` (PowerPoint)
- **Testing**: pytest, FastAPI's `TestClient`, dependency injection for fully mocked Claude/ChromaDB in tests
- **CI**: GitHub Actions

## Notable engineering decisions (see [`docs/progress.md`](docs/progress.md) for the full story on each)

- **Structured output isn't a guarantee.** Claude's `tool_choice` forces a tool call, but not that every field arrives under its exact schema name — found in practice when Claude silently emitted `expected_ROI` instead of the schema's `expected_roi` (a strong prior toward capitalizing "ROI" as an acronym). Fixed by avoiding acronym-shaped field names *and* making every non-critical field `Optional` with a safe default, so a future mismatch degrades gracefully instead of 500ing.
- **Shared in-memory test doubles can leak state.** `chromadb.EphemeralClient()` instances in the same process share their underlying store — confirmed with a two-line repro before trusting it as the cause of a cross-test-file bug — fixed by resetting the shared store once per test, not once per request.
- **Test with real content, not two-line placeholders.** Two separate PDF-export crashes (a Unicode/Latin-1 font limitation, and a cursor-position bug in `fpdf2`'s `multi_cell`) only appeared with genuinely long, real Claude-generated prose — a short synthetic test string didn't trigger either.

## Skills Demonstrated

**Consulting**: business analysis, digital transformation methodology, SWOT/roadmap/maturity frameworks, executive communication.
**AI Engineering**: RAG, vector databases, prompt engineering, structured output via tool use, chained multi-step LLM pipelines, grounding/anti-hallucination design, when *not* to use an LLM.
**Software Engineering**: FastAPI, REST API design, SQLAlchemy, Pydantic, dependency injection for testability, pytest, CI/CD, Streamlit, defensive handling of unreliable external (LLM) responses.

## Deployment (not yet deployed)

Designed for a free-tier deployment: [Streamlit Community Cloud](https://streamlit.io/cloud) for the frontend, [Render](https://render.com) for the FastAPI backend, [Neon](https://neon.tech) for a hosted Postgres (swap `DATABASE_URL`, no code changes needed — that's the point of using an ORM). Both platforms deploy directly from this GitHub repo.
