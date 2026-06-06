"""Evaluation harness for the thesis.

Usage:
    # Synthetic-only — runs immediately, no external downloads.
    python -m eval.run_eval --signal ai_leakage --synthetic
    python -m eval.run_eval --signal cohort --synthetic
    python -m eval.run_eval --system mixed --synthetic

    # External datasets (download separately).
    python -m eval.run_eval --signal ai_leakage --dataset hc3 --hc3-path data/hc3.jsonl
    python -m eval.run_eval --signal cohort --dataset pan --pan-dir data/pan/

Reports are written to eval/reports/ as JSON for the thesis.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from app.signals.ai_leakage import detect, registered_rules
from app.signals.cohort.shingles import (
    longest_matching_span,
    near_duplicate_pairs,
)
from eval.datasets.synthetic import (
    generate_ai_leakage,
    generate_cohort,
)
from eval.metrics import PRFScore, prf, roc_auc


REPORTS_DIR = Path(__file__).resolve().parent / "reports"


def _write_report(name: str, payload: dict) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = REPORTS_DIR / f"{name}-{ts}.json"
    out.write_text(json.dumps(payload, indent=2, default=str))
    return out


# ---------- AI-leakage evaluation ----------

def eval_ai_leakage_synthetic(seed: int = 0) -> dict:
    examples = generate_ai_leakage(seed=seed)
    rules = registered_rules()
    rule_ids = {r.id for r in rules}

    per_rule_tp = defaultdict(int)
    per_rule_fp = defaultdict(int)
    per_rule_fn = defaultdict(int)
    overall_y_true: list[bool] = []
    overall_y_pred: list[bool] = []

    for ex in examples:
        hits = detect(ex.text)
        fired = {h.rule_id for h in hits}
        any_fired = bool(fired)
        overall_y_true.append(ex.is_positive)
        overall_y_pred.append(any_fired)

        # Per-rule book-keeping. A rule's "positive class" is the synthetic
        # examples labeled with its rule_id.
        for rid in rule_ids:
            is_target = ex.expected_rule_id == rid
            fired_here = rid in fired
            if is_target and fired_here:
                per_rule_tp[rid] += 1
            elif is_target and not fired_here:
                per_rule_fn[rid] += 1
            elif not is_target and fired_here:
                per_rule_fp[rid] += 1

    per_rule: dict[str, dict] = {}
    for r in rules:
        score = PRFScore.from_counts(
            tp=per_rule_tp[r.id],
            fp=per_rule_fp[r.id],
            fn=per_rule_fn[r.id],
        )
        per_rule[r.id] = {
            "name": r.name,
            "family": r.family,
            "precision": score.precision,
            "recall": score.recall,
            "f1": score.f1,
            "tp": score.tp,
            "fp": score.fp,
            "fn": score.fn,
        }

    overall = prf(overall_y_true, overall_y_pred)
    return {
        "n_examples": len(examples),
        "n_positive": sum(1 for e in examples if e.is_positive),
        "overall": {
            "precision": overall.precision,
            "recall": overall.recall,
            "f1": overall.f1,
        },
        "per_rule": per_rule,
    }


def eval_ai_leakage_hc3(path: str, limit: int | None = None) -> dict:
    from eval.datasets.hc3 import load_hc3

    examples = load_hc3(path, limit=limit)
    y_true: list[bool] = []
    y_score: list[float] = []
    y_pred: list[bool] = []
    for ex in examples:
        hits = detect(ex.text)
        y_true.append(ex.is_ai)
        y_score.append(float(len(hits)))
        y_pred.append(bool(hits))
    score = prf(y_true, y_pred)
    return {
        "n_examples": len(examples),
        "n_ai": sum(y_true),
        "precision": score.precision,
        "recall": score.recall,
        "f1": score.f1,
        "auc": roc_auc(y_true, y_score),
    }


# ---------- Cohort evaluation ----------

def eval_cohort_synthetic(seed: int = 0) -> dict:
    examples = generate_cohort(seed=seed)
    # For each example pair, run the MinHash channel directly.
    y_true: list[bool] = []  # whether the pair is exact_copy or paraphrase
    y_score: list[float] = []  # estimated jaccard from MinHash

    minhash_pairs_lookup: dict[tuple[str, str], float] = {}
    submissions = []
    for ex in examples:
        submissions.append((ex.id_a, ex.text_a))
        submissions.append((ex.id_b, ex.text_b))

    pairs = near_duplicate_pairs(submissions, threshold=0.1)
    for id_a, id_b, jaccard in pairs:
        key = tuple(sorted((id_a, id_b)))
        minhash_pairs_lookup[key] = max(minhash_pairs_lookup.get(key, 0.0), jaccard)

    n_copy_detected = 0
    n_paraphrase_detected = 0
    for ex in examples:
        key = tuple(sorted((ex.id_a, ex.id_b)))
        score = minhash_pairs_lookup.get(key, 0.0)
        is_related = ex.relation in ("exact_copy", "paraphrase")
        y_true.append(is_related)
        y_score.append(score)
        if score > 0.5:
            if ex.relation == "exact_copy":
                n_copy_detected += 1
            elif ex.relation == "paraphrase":
                n_paraphrase_detected += 1

    return {
        "n_examples": len(examples),
        "n_exact_copy": sum(1 for e in examples if e.relation == "exact_copy"),
        "n_paraphrase": sum(1 for e in examples if e.relation == "paraphrase"),
        "n_unrelated": sum(1 for e in examples if e.relation == "unrelated"),
        "exact_copy_detected_at_0.5": n_copy_detected,
        "paraphrase_detected_at_0.5": n_paraphrase_detected,
        "auc": roc_auc(y_true, y_score),
        "note": (
            "AUC reflects MinHash channel only. Embedding channel (Phase 2) "
            "would dominate the paraphrase column; left to a future run with "
            "sentence-transformers installed."
        ),
    }


# ---------- System-level (mixed) ----------

def eval_system_mixed(seed: int = 0) -> dict:
    """Build a simulated assignment with mixed-suspicion submissions and
    check that the ranker places the truly suspicious ones at the top."""
    # Currently uses synthetic AI-leakage examples only; cohort fusion goes
    # in once we wire the runner into this harness directly.
    examples = generate_ai_leakage(seed=seed)
    y_true: list[bool] = []
    y_score: list[float] = []
    for ex in examples:
        hits = detect(ex.text)
        y_true.append(ex.is_positive)
        y_score.append(float(len(hits)))
    return {
        "n_examples": len(examples),
        "auc": roc_auc(y_true, y_score),
    }


# ---------- CLI ----------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--signal", choices=["ai_leakage", "cohort"])
    parser.add_argument("--system", choices=["mixed"])
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--dataset", choices=["hc3", "pan"])
    parser.add_argument("--hc3-path", type=str)
    parser.add_argument("--pan-dir", type=str)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    if args.signal == "ai_leakage":
        if args.synthetic:
            payload = eval_ai_leakage_synthetic(seed=args.seed)
            name = "ai_leakage-synthetic"
        elif args.dataset == "hc3":
            if not args.hc3_path:
                parser.error("--hc3-path required with --dataset hc3")
            payload = eval_ai_leakage_hc3(args.hc3_path, limit=args.limit)
            name = "ai_leakage-hc3"
        else:
            parser.error("provide --synthetic or --dataset")
        out_path = _write_report(name, payload)
        _print_summary(name, payload)
        print(f"\nWritten: {out_path}")
        return 0

    if args.signal == "cohort":
        if args.synthetic:
            payload = eval_cohort_synthetic(seed=args.seed)
            name = "cohort-synthetic"
        else:
            parser.error("cohort eval currently supports --synthetic only")
        out_path = _write_report(name, payload)
        _print_summary(name, payload)
        print(f"\nWritten: {out_path}")
        return 0

    if args.system == "mixed":
        payload = eval_system_mixed(seed=args.seed)
        name = "system-mixed"
        out_path = _write_report(name, payload)
        _print_summary(name, payload)
        print(f"\nWritten: {out_path}")
        return 0

    parser.print_help()
    return 1


def _print_summary(name: str, payload: dict) -> None:
    print(f"\n=== {name} ===\n")
    if "per_rule" in payload:
        print(f"{'rule_id':<45} {'family':<15} {'P':>6} {'R':>6} {'F1':>6}")
        print("-" * 80)
        for rid, m in sorted(payload["per_rule"].items()):
            print(
                f"{rid:<45} {m['family']:<15} "
                f"{m['precision']:>6.3f} {m['recall']:>6.3f} {m['f1']:>6.3f}"
            )
        o = payload["overall"]
        print("-" * 80)
        print(
            f"{'OVERALL':<45} {'(any rule)':<15} "
            f"{o['precision']:>6.3f} {o['recall']:>6.3f} {o['f1']:>6.3f}"
        )
    else:
        for k, v in payload.items():
            print(f"  {k}: {v}")


if __name__ == "__main__":
    sys.exit(main())
