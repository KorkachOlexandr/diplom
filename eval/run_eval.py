"""Evaluation harness for the thesis (code-plagiarism edition).

Usage:
    # Synthetic-only — runs immediately, stdlib only.
    python -m eval.run_eval --signal ai_leakage --synthetic
    python -m eval.run_eval --signal cohort --synthetic
    python -m eval.run_eval --system mixed --synthetic

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
from app.signals.cohort.ast_hash import compare_subtrees, subtree_hashes
from app.signals.cohort.tokenize_code import tokenize_source
from app.signals.cohort.winnowing import compare_submissions, fingerprints
from eval.datasets.synthetic import generate_ai_leakage, generate_cohort
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
        fired = {h.rule_id for h in detect(ex.text)}
        overall_y_true.append(ex.is_positive)
        overall_y_pred.append(bool(fired))

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
            tp=per_rule_tp[r.id], fp=per_rule_fp[r.id], fn=per_rule_fn[r.id]
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


# ---------- Cohort evaluation ----------

def eval_cohort_synthetic(seed: int = 0) -> dict:
    examples = generate_cohort(seed=seed)

    # Build a flat (id, text) list and pairwise lookup of the relation.
    submissions: list[tuple[str, str]] = []
    relation_by_pair: dict[tuple[str, str], str] = {}
    for ex in examples:
        submissions.append((ex.id_a, ex.text_a))
        submissions.append((ex.id_b, ex.text_b))
        key = tuple(sorted((ex.id_a, ex.id_b)))
        relation_by_pair[key] = ex.relation

    # Winnowing channel.
    fps_by_sub = []
    for sid, text in submissions:
        try:
            tokens = tokenize_source(text)
        except Exception:
            tokens = []
        fps_by_sub.append((sid, fingerprints(tokens)))
    winnow_pairs = {
        tuple(sorted((a, b))): m.score
        for a, b, m in compare_submissions(fps_by_sub, min_score=0.0)
    }

    # AST channel.
    ast_by_sub = [(sid, subtree_hashes(text)) for sid, text in submissions]
    ast_pairs = {
        tuple(sorted((a, b))): m.score
        for a, b, m in compare_subtrees(ast_by_sub, min_score=0.0)
    }

    rows: list[dict] = []
    y_true_related: list[bool] = []
    y_winnow: list[float] = []
    y_ast: list[float] = []
    y_combined: list[float] = []

    for ex in examples:
        key = tuple(sorted((ex.id_a, ex.id_b)))
        w_score = winnow_pairs.get(key, 0.0)
        a_score = ast_pairs.get(key, 0.0)
        combined = max(w_score, a_score)
        is_related = ex.relation in ("exact_copy", "renamed", "reordered")
        y_true_related.append(is_related)
        y_winnow.append(w_score)
        y_ast.append(a_score)
        y_combined.append(combined)
        rows.append(
            {
                "relation": ex.relation,
                "winnow": w_score,
                "ast": a_score,
                "combined": combined,
            }
        )

    by_rel: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_rel[r["relation"]].append(r)

    relation_summary = {}
    for rel, items in by_rel.items():
        w_detected = sum(1 for it in items if it["winnow"] > 0.3)
        a_detected = sum(1 for it in items if it["ast"] > 0.3)
        c_detected = sum(1 for it in items if it["combined"] > 0.3)
        relation_summary[rel] = {
            "n": len(items),
            "winnow_detected_at_0.3": w_detected,
            "ast_detected_at_0.3": a_detected,
            "combined_detected_at_0.3": c_detected,
        }

    return {
        "n_examples": len(examples),
        "by_relation": relation_summary,
        "auc_winnow": roc_auc(y_true_related, y_winnow),
        "auc_ast": roc_auc(y_true_related, y_ast),
        "auc_combined": roc_auc(y_true_related, y_combined),
    }


# ---------- System-level ----------

def eval_system_mixed(seed: int = 0) -> dict:
    """Combine AI-leakage detection scores with cohort scores into a single
    ranking, then check that suspicious submissions land at the top."""
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
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    if args.signal == "ai_leakage":
        if not args.synthetic:
            parser.error("only --synthetic mode is implemented for now")
        payload = eval_ai_leakage_synthetic(seed=args.seed)
        name = "ai_leakage-synthetic"
    elif args.signal == "cohort":
        if not args.synthetic:
            parser.error("only --synthetic mode is implemented for now")
        payload = eval_cohort_synthetic(seed=args.seed)
        name = "cohort-synthetic"
    elif args.system == "mixed":
        payload = eval_system_mixed(seed=args.seed)
        name = "system-mixed"
    else:
        parser.print_help()
        return 1

    out_path = _write_report(name, payload)
    _print_summary(name, payload)
    print(f"\nWritten: {out_path}")
    return 0


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
    elif "by_relation" in payload:
        print(f"{'relation':<15} {'n':>5} {'winnow':>8} {'ast':>6} {'combined':>10}")
        print("-" * 50)
        for rel in ("exact_copy", "renamed", "reordered", "unrelated"):
            if rel in payload["by_relation"]:
                d = payload["by_relation"][rel]
                print(
                    f"{rel:<15} {d['n']:>5} "
                    f"{d['winnow_detected_at_0.3']:>8} "
                    f"{d['ast_detected_at_0.3']:>6} "
                    f"{d['combined_detected_at_0.3']:>10}"
                )
        print(f"\nAUC (winnow): {payload['auc_winnow']:.3f}")
        print(f"AUC (ast):    {payload['auc_ast']:.3f}")
        print(f"AUC (max):    {payload['auc_combined']:.3f}")
    else:
        for k, v in payload.items():
            print(f"  {k}: {v}")


if __name__ == "__main__":
    sys.exit(main())
