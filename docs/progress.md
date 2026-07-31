# Progress Log

A running record of what's been built, in what order, and *why* — the reasoning, not just the diff. Useful for interview prep: this is the "defend your decisions" cheat sheet.

## 2026-07-31 — Environment setup

- Started fresh: archived the old all-at-once scaffold, decided to build module by module instead.
- Workflow: prototype each module in a Colab notebook first (understand every line), then port working code into this repo.
- Chose GitHub for version control + as the deploy source for Streamlit Community Cloud / Render.
- Planned free hosting for later: Streamlit Community Cloud (frontend), Render (FastAPI backend), Neon (Postgres). ChromaDB persists to a local file, no separate host needed.
