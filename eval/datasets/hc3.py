"""HC3 (Human-ChatGPT Comparison Corpus) loader.

HC3 ships as JSONL with one record per question, each carrying both a
human answer and a ChatGPT answer. This loader yields labeled examples
suitable for AI-leakage rule evaluation.

The dataset itself is not bundled with this repo. Download from
https://huggingface.co/datasets/Hello-SimpleAI/HC3 (or the mirror of
your choice) and pass the path to the JSONL file in.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HC3Example:
    text: str
    is_ai: bool
    domain: str | None = None


def load_hc3(path: str | Path, limit: int | None = None) -> list[HC3Example]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"HC3 file not found at {p}. Download from "
            "https://huggingface.co/datasets/Hello-SimpleAI/HC3 and pass the path."
        )
    out: list[HC3Example] = []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            domain = row.get("source")
            for human in row.get("human_answers", []) or []:
                if human:
                    out.append(HC3Example(text=human, is_ai=False, domain=domain))
            for ai in row.get("chatgpt_answers", []) or []:
                if ai:
                    out.append(HC3Example(text=ai, is_ai=True, domain=domain))
            if limit is not None and len(out) >= limit:
                break
    return out[:limit] if limit else out
