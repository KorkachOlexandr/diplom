from __future__ import annotations

import math

from eval.datasets.synthetic import generate_ai_leakage, generate_cohort
from eval.metrics import ndcg_at_k, precision_at_k, prf, roc_auc
from eval.run_eval import eval_ai_leakage_synthetic, eval_cohort_synthetic


def test_prf_basic():
    y_true = [True, True, True, False, False]
    y_pred = [True, False, True, True, False]
    s = prf(y_true, y_pred)
    assert s.tp == 2
    assert s.fp == 1
    assert s.fn == 1
    assert math.isclose(s.precision, 2 / 3, rel_tol=1e-6)


def test_roc_auc_perfect_classifier():
    assert math.isclose(roc_auc([True, True, False, False], [0.9, 0.8, 0.2, 0.1]), 1.0)


def test_roc_auc_random_classifier_is_half():
    assert math.isclose(roc_auc([True, False, True, False], [0.5, 0.5, 0.5, 0.5]), 0.5)


def test_ndcg_perfect_order():
    assert math.isclose(ndcg_at_k([1, 1, 0, 0], k=4), 1.0)


def test_precision_at_k():
    assert precision_at_k([True, True, False, True], k=2) == 1.0
    assert precision_at_k([False, True, True, True], k=2) == 0.5


def test_synthetic_ai_leakage_is_reproducible():
    a = generate_ai_leakage(seed=7)
    b = generate_ai_leakage(seed=7)
    assert [e.text for e in a] == [e.text for e in b]


def test_synthetic_cohort_includes_code_transformations():
    examples = generate_cohort(n_unrelated=3, n_exact=3, n_renamed=3, n_reordered=3, seed=0)
    relations = {e.relation for e in examples}
    assert relations == {"unrelated", "exact_copy", "renamed", "reordered"}


def test_eval_ai_leakage_synthetic_runs_and_has_decent_recall():
    """Aggregate floor: with the injected positives, *some* rule should fire
    on a strong majority of them, and clean negatives should mostly be
    quiet."""
    result = eval_ai_leakage_synthetic(seed=0)
    assert result["n_examples"] > 0
    assert "per_rule" in result
    assert result["overall"]["recall"] > 0.7
    assert result["overall"]["precision"] > 0.7


def test_eval_cohort_synthetic_detects_exact_copies_and_renames():
    """The winnowing channel should catch exact copies; the AST channel
    should catch the renamed-but-structurally-identical pairs."""
    result = eval_cohort_synthetic(seed=0)
    rel = result["by_relation"]
    assert rel["exact_copy"]["winnow_detected_at_0.3"] >= int(rel["exact_copy"]["n"] * 0.9)
    assert rel["renamed"]["winnow_detected_at_0.3"] >= int(rel["renamed"]["n"] * 0.9)
    assert rel["renamed"]["ast_detected_at_0.3"] >= int(rel["renamed"]["n"] * 0.9)
    # Combined ranker should beat random.
    assert result["auc_combined"] > 0.7
