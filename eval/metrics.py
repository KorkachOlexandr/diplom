"""Lightweight metrics for the evaluation chapter.

Implements precision/recall/F1, ROC-AUC, and NDCG@k from numpy without
pulling sklearn. Keeps the eval harness runnable with only the base
install when sklearn-based extras aren't available.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class PRFScore:
    precision: float
    recall: float
    f1: float
    tp: int
    fp: int
    fn: int

    @classmethod
    def from_counts(cls, tp: int, fp: int, fn: int) -> "PRFScore":
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        return cls(precision=precision, recall=recall, f1=f1, tp=tp, fp=fp, fn=fn)


def prf(y_true: list[bool], y_pred: list[bool]) -> PRFScore:
    tp = sum(1 for t, p in zip(y_true, y_pred) if t and p)
    fp = sum(1 for t, p in zip(y_true, y_pred) if not t and p)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t and not p)
    return PRFScore.from_counts(tp, fp, fn)


def roc_auc(y_true: list[bool], y_score: list[float]) -> float:
    """Mann-Whitney U formulation. O(n log n)."""
    pairs = sorted(zip(y_score, y_true), key=lambda x: x[0])
    ranks: dict[int, float] = {}
    i = 0
    n = len(pairs)
    while i < n:
        j = i
        while j < n and pairs[j][0] == pairs[i][0]:
            j += 1
        avg = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[k] = avg
        i = j
    sum_pos_ranks = sum(ranks[k] for k, (_, t) in enumerate(pairs) if t)
    n_pos = sum(1 for _, t in pairs if t)
    n_neg = n - n_pos
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    u = sum_pos_ranks - n_pos * (n_pos + 1) / 2
    return u / (n_pos * n_neg)


def ndcg_at_k(relevances: list[float], k: int) -> float:
    """Normalized discounted cumulative gain at k. relevances is the
    sequence of true relevances in the ranked order produced by the system.
    """
    def dcg(rs):
        return sum(r / math.log2(i + 2) for i, r in enumerate(rs))

    actual = dcg(relevances[:k])
    ideal = dcg(sorted(relevances, reverse=True)[:k])
    return actual / ideal if ideal else 0.0


def precision_at_k(ranking: list[bool], k: int) -> float:
    if k == 0:
        return 0.0
    top = ranking[:k]
    return sum(top) / k
