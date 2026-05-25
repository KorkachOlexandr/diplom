# diplom — anti-plagiarism screening for Google Classroom

Instructor-facing tool that fetches submissions from a Google Classroom assignment and runs them through three signals:

1. **External web plagiarism** (CopyLeaks wrapper — stubbed in Phase 1).
2. **Paraphrase-aware intra-cohort similarity** (Phase 2 — MinHash + sentence-embedding channels with side-by-side evidence).
3. **Explainable AI-leakage taxonomy** (Phase 3 — high-precision rules for careless LLM use, each with quoted evidence and measured precision/recall).

The full plan, novelty framing, and evaluation methodology live in the thesis plan file. This README is just for getting the foundation running.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .[dev]
```

Phase 2 (cohort similarity) and the evaluation harness have their own optional extras:

```bash
pip install -e .[cohort,eval,dev]
```

## Google Classroom credentials

1. In Google Cloud Console, create a project and enable the **Classroom API** and **Drive API**.
2. Create OAuth client credentials of type **Desktop app**.
3. Download the JSON and save it as `credentials.json` at the repo root (gitignored).
4. First run opens a browser for consent; the resulting token is cached to `token.json` (also gitignored).

The OAuth scopes requested are read-only — see `app/classroom/oauth.py`.

## Run the teacher UI

```bash
streamlit run app/ui/home.py
```

If `credentials.json` is missing, the UI loads in **demo mode** with a synthetic course/assignment so you can exercise the pipeline end-to-end without Google credentials.

## Run tests

```bash
pytest
```

## Project layout

```
app/
├── ui/              # Streamlit teacher dashboard
├── classroom/       # Google Classroom + Drive integration
├── pipeline/        # Scan orchestration + SQLite store
├── signals/
│   ├── webcheck/    # External web plagiarism (Phase 4)
│   ├── cohort/      # Intra-cohort similarity (Phase 2)
│   └── ai_leakage/  # Explainable rule taxonomy (Phase 3)
└── report/          # Report model + ranker
eval/                # Evaluation harness (Phase 5)
tests/
```

## Status

Phase 1 (foundation) is implemented. Signals are stubbed except for a handful of obvious AI-leakage rules wired in to demonstrate the engine. See the thesis plan file for the phase roadmap.
