"""Evaluation harness — Phase 5.

Phase 1: command-line skeleton only. The real implementations of the
`--signal cohort` (PAN), `--signal ai_leakage` (HC3 / M4), and `--system mixed`
runs land alongside the corresponding implementation phases.

Usage:
    python -m eval.run_eval --signal ai_leakage --dataset hc3
    python -m eval.run_eval --signal cohort --dataset pan
    python -m eval.run_eval --system mixed
"""
from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--signal", choices=["ai_leakage", "cohort", "webcheck"])
    parser.add_argument("--system", choices=["mixed"])
    parser.add_argument("--dataset", choices=["hc3", "m4", "pan"])
    args = parser.parse_args(argv)

    if args.signal == "ai_leakage":
        print("[Phase 3] AI-leakage rule evaluation on", args.dataset, "— not implemented yet.")
        return 1
    if args.signal == "cohort":
        print("[Phase 2] Cohort similarity evaluation on", args.dataset, "— not implemented yet.")
        return 1
    if args.system == "mixed":
        print("[Phase 5] Mixed-assignment ranker evaluation — not implemented yet.")
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
