# diplom — code-plagiarism screening for Google Classroom

Instructor-facing tool that fetches submissions from a Google Classroom
programming assignment and runs them through two signals:

1. **Multi-channel code similarity** — winnowing fingerprints over a
   normalized token sequence (Moss-style) plus AST subtree hashing for
   structural similarity that survives variable renaming and statement
   reordering.
2. **Explainable AI-leakage taxonomy** — high-precision rules detecting
   specific failure modes of careless LLM use in source code (pasted
   ChatGPT preambles inside comments, leftover markdown ``` fences,
   knowledge-cutoff disclosures in docstrings, Ukrainian-localized
   equivalents, and more). Each rule surfaces the quoted evidence and
   the tool deliberately does not produce an "AI score" or verdict.

External web plagiarism (Moss/JPlag-equivalent) is left as a stubbed
interface; the production counterpart is a CLI-based service, which is
called out as a deployment concern in the thesis rather than a
methodological gap.

## Setup

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows / Git Bash
# source .venv/bin/activate     # macOS / Linux
pip install -e .[dev]
```

Phase 1 of the cohort signal uses only the Python standard library
(`tokenize`, `ast`, `difflib`). There are no NLP or ML dependencies for
the core algorithm.

## Google Classroom credentials

1. In Google Cloud Console, create a project and enable the **Classroom API** and **Drive API**.
2. Create OAuth client credentials of type **Desktop app**.
3. Download the JSON and save it as `credentials.json` at the repo root (gitignored).
4. First run opens a browser for consent; the resulting token is cached to `token.json` (also gitignored).

The OAuth scopes requested are read-only — see `app/classroom/oauth.py`.

## Run the teacher UI

```bash
python -m streamlit run app/ui/home.py
```

If `credentials.json` is missing, the UI loads in **demo mode** with a
synthetic CS101 course containing three assignments
(bubble_sort, false-positive showcase, fibonacci) so you can exercise the
pipeline end-to-end without Google credentials.

## Run tests

```bash
pytest
```

## Evaluation harness (Phase 5)

```bash
python -m eval.run_eval --signal ai_leakage --synthetic
python -m eval.run_eval --signal cohort --synthetic
python -m app.signals.ai_leakage.taxonomy > app/signals/ai_leakage/taxonomy.md
```

Reports land in `eval/reports/` as JSON for thesis tables.

## Project layout

```
app/
├── ui/                Streamlit teacher dashboard
├── classroom/         Google Classroom + Drive integration
├── pipeline/          Scan orchestration + SQLite store
├── signals/
│   ├── webcheck/      External web plagiarism — stubbed interface
│   ├── cohort/        Code similarity
│   │   ├── tokenize_code.py   Python lexer + identifier normalization
│   │   ├── winnowing.py       Karp–Rabin + winnowing (Moss algorithm)
│   │   ├── ast_hash.py        AST subtree hashing
│   │   └── compare.py         Fuse channels into CohortMatch objects
│   └── ai_leakage/    Explainable rule taxonomy
│       ├── engine.py          Auto-loading rule registry
│       ├── rules/             One file per family
│       └── taxonomy.py        Auto-generated taxonomy doc
└── report/            Report model + ranker
eval/                  Synthetic dataset + harness + metrics
tests/                 pytest suite
```

## Status

All five thesis phases are wired end-to-end:

- Foundation (Classroom OAuth, extraction, store, UI)
- Cohort similarity (winnowing + AST, Jaccard scoring)
- AI-leakage taxonomy (19 rules, 4 families, EN + UA)
- Web plagiarism (stub interface, documented Moss/JPlag deployment path)
- Evaluation (synthetic per-rule P/R/F1, cohort AUC by relation)
