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
    assert math.isclose(s.recall, 2 / 3, rel_tol=1e-6)


def test_roc_auc_perfect_classifier():
    y_true = [True, True, False, False]
    y_score = [0.9, 0.8, 0.2, 0.1]
    assert math.isclose(roc_auc(y_true, y_score), 1.0, rel_tol=1e-6)


def test_roc_auc_random_classifier_is_half():
    y_true = [True, False, True, False, True, False]
    y_score = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
    assert math.isclose(roc_auc(y_true, y_score), 0.5, rel_tol=1e-6)


def test_ndcg_perfect_order():
    assert math.isclose(ndcg_at_k([1, 1, 0, 0], k=4), 1.0, rel_tol=1e-6)


def test_precision_at_k():
    assert precision_at_k([True, True, False, True], k=2) == 1.0
    assert precision_at_k([False, True, True, True], k=2) == 0.5


def test_synthetic_ai_leakage_dataset_is_reproducible():
    a = generate_ai_leakage(seed=7)
    b = generate_ai_leakage(seed=7)
    assert [e.text for e in a] == [e.text for e in b]


def test_synthetic_cohort_dataset_has_expected_relations():
    examples = generate_cohort(n_unrelated=5, n_exact=5, n_paraphrase=5, seed=0)
    relations = {e.relation for e in examples}
    assert relations == {"unrelated", "exact_copy", "paraphrase"}


def test_eval_ai_leakage_synthetic_runs_end_to_end():
    """The injected positives should drive overall recall well above
    random. Exact numbers depend on the dataset and may shift as rules
    evolve — we just want a sanity floor."""
    result = eval_ai_leakage_synthetic(seed=0)
    assert result["n_examples"] > 0
    assert "per_rule" in result
    # Overall recall — does *any* rule fire on positive examples?
    assert result["overall"]["recall"] > 0.5
    # Overall precision — false-positive rate on negatives should be low.
    assert result["overall"]["precision"] > 0.5


def test_eval_cohort_synthetic_detects_exact_copies():
    result = eval_cohort_synthetic(seed=0)
    # MinHash should catch the vast majority of exact copies.
    assert result["exact_copy_detected_at_0.5"] >= int(result["n_exact_copy"] * 0.9)
    # AUC should clearly beat random.
    assert result["auc"] > 0.7
