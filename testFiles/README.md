# Test files for live Classroom demo

Twelve `.py` files (plus one empty-submission note) organized by assignment.
Upload each file via the corresponding student account to the corresponding
Google Classroom assignment.

## Expected results when you scan

### Assignment 1 — Bubble sort
| Account | File | Phase 1 expectation |
|---|---|---|
| 1 | `account1-original.py` | clean — nothing fires |
| 2 | `account2-web-copy.py` | nothing fires (Phase 4 web-check is a stub — Moss/JPlag would catch this) |
| 3 | `account3-ai-pasted.py` | **~6 leakage rules fire** (preamble, sign-off, time complexity, fences, example usage) |
| 4 | `account4-renamed-copy.py` | **cohort match with Account 1** — both winnowing and AST channels |

### Assignment 2 — Known limitations (false-positive showcase)
Each submission is honest code that trips one rule on purpose.
| Account | File | Rule that fires |
|---|---|---|
| 1 | `account1-docs-tutorial.py` | `comment.explanation_block` |
| 2 | `account2-ml-essay.py` | `comment.as_an_ai` |
| 3 | `account3-markdown-parser.py` | `markdown.code_fence_in_source` |
| 4 | `account4-stats-with-notes.py` | `boilerplate.note_blocks_repeated` |

### Assignment 3 — Fibonacci (all clean)
| Account | File | Phase 1 expectation |
|---|---|---|
| 1 | `account1-iterative.py` | clean |
| 2 | `account2-recursive.py` | clean |
| 3 | `account3-memoized.py` | clean |
| 4 | (no attachment) | extraction-error path — see `account4-EMPTY.md` |

## Phase status

Implemented and live:
- Phase 1 (Classroom OAuth, ingestion, extraction)
- Phase 2 cohort similarity (winnowing + AST, Jaccard scoring)
- Phase 3 AI-leakage taxonomy (19 rules across 4 families, EN + UA)
- Phase 5 evaluation harness (synthetic dataset + JSON reports)

Intentionally stubbed:
- Phase 4 web plagiarism — the code-plagiarism equivalents (Moss, JPlag)
  are CLI tools rather than REST APIs; integration is documented as a
  deployment slot, not a methodological gap.
