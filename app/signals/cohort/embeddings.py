"""Sentence-embedding channel for paraphrase detection.

Sentences are encoded with a multilingual sentence-transformer (default:
paraphrase-multilingual-MiniLM-L12-v2, chosen so the Ukrainian stretch goal
becomes a config flip). For class-size N submissions × ~10 sentences each,
brute-force cosine similarity is fast enough on CPU; FAISS is left as a
future optimization once we have a scaling problem to point at.

The whole module is import-guarded — if sentence-transformers isn't
installed, find_matches in compare.py degrades to MinHash-only without
crashing the scan.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np


_SENT_SPLIT = re.compile(r"[^.!?\n]+[.!?\n]?", re.UNICODE)


@dataclass(frozen=True)
class _Sentence:
    submission_id: str
    start: int
    end: int
    text: str


def split_sentences(text: str, min_chars: int = 20) -> list[_Sentence]:
    """Naive sentence split on terminal punctuation + newlines.

    Filters out fragments below min_chars to suppress noise from
    list-of-three style writing.
    """
    out: list[_Sentence] = []
    for m in _SENT_SPLIT.finditer(text):
        body = m.group(0)
        stripped = body.strip()
        if len(stripped) < min_chars:
            continue
        offset = body.find(stripped)
        start = m.start() + offset
        end = start + len(stripped)
        out.append(_Sentence(submission_id="", start=start, end=end, text=stripped))
    return out


class EmbeddingIndex:
    """Lazy-loads the sentence-transformer model on first use.

    Holds one float32 matrix of normalized vectors keyed back to (submission,
    sentence span) tuples. paraphrase_pairs() then runs brute-force cosine
    via a single matrix multiply.
    """

    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        self._model_name = model_name
        self._model = None
        self._sentences: list[_Sentence] = []
        self._vectors: np.ndarray | None = None

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
        return self._model

    def add(self, submission_id: str, text: str) -> None:
        sents = split_sentences(text)
        if not sents:
            return
        model = self._load_model()
        vectors = model.encode(
            [s.text for s in sents],
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        for s in sents:
            self._sentences.append(
                _Sentence(
                    submission_id=submission_id,
                    start=s.start,
                    end=s.end,
                    text=s.text,
                )
            )
        self._vectors = (
            np.asarray(vectors, dtype=np.float32)
            if self._vectors is None
            else np.vstack([self._vectors, np.asarray(vectors, dtype=np.float32)])
        )

    def paraphrase_pairs(
        self, threshold: float = 0.85
    ) -> list[tuple[str, str, tuple[int, int], tuple[int, int], str, str, float]]:
        if self._vectors is None or len(self._sentences) < 2:
            return []
        sims = self._vectors @ self._vectors.T
        np.fill_diagonal(sims, 0.0)
        out: list[tuple[str, str, tuple[int, int], tuple[int, int], str, str, float]] = []
        n = len(self._sentences)
        for i in range(n):
            si = self._sentences[i]
            row = sims[i]
            # Top candidates above threshold from different submissions.
            for j in range(i + 1, n):
                if row[j] < threshold:
                    continue
                sj = self._sentences[j]
                if si.submission_id == sj.submission_id:
                    continue
                out.append(
                    (
                        si.submission_id,
                        sj.submission_id,
                        (si.start, si.end),
                        (sj.start, sj.end),
                        si.text,
                        sj.text,
                        float(row[j]),
                    )
                )
        return out
