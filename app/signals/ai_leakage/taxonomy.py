"""Auto-generate the AI-leakage rule taxonomy document.

The taxonomy is part of the thesis — it documents *what* the tool detects
and the operating point of each rule. Generating it from the live registry
keeps the doc and the code from drifting.

Usage:
    python -m app.signals.ai_leakage.taxonomy > taxonomy.md
"""
from __future__ import annotations

from collections import defaultdict

from app.signals.ai_leakage.engine import Rule, registered_rules


_HEADER = """# AI-Leakage Rule Taxonomy

This document is auto-generated from the rules registered in
`app/signals/ai_leakage/rules/`. Each rule targets one specific failure
mode of careless LLM use. Rules are intentionally high-precision and
low-recall — the tool surfaces evidence, not verdicts.

Per-rule precision and recall are measured on the synthetic and HC3
evaluation sets (see Chapter B of the thesis). Rules without measured
operating points have not yet been evaluated; this is tracked as work
in progress.
"""


def _format_rule(r: Rule) -> str:
    lines = [
        f"### `{r.id}` — {r.name}",
        "",
        r.description,
        "",
    ]
    if r.measured_precision is not None or r.measured_recall is not None:
        prec = f"{r.measured_precision:.3f}" if r.measured_precision is not None else "—"
        rec = f"{r.measured_recall:.3f}" if r.measured_recall is not None else "—"
        lines.extend(
            [
                f"- Measured precision: **{prec}**",
                f"- Measured recall: **{rec}**",
                "",
            ]
        )
    else:
        lines.extend(["- Operating point: not yet measured.", ""])
    return "\n".join(lines)


def generate_taxonomy_md() -> str:
    rules = registered_rules()
    by_family: dict[str, list[Rule]] = defaultdict(list)
    for r in rules:
        by_family[r.family].append(r)

    parts = [_HEADER]
    parts.append(f"**Total rules registered:** {len(rules)} across {len(by_family)} families.\n")

    for family in sorted(by_family):
        family_rules = sorted(by_family[family], key=lambda r: r.id)
        parts.append(f"## Family: `{family}` ({len(family_rules)} rules)\n")
        for r in family_rules:
            parts.append(_format_rule(r))

    return "\n".join(parts)


def main() -> None:
    print(generate_taxonomy_md())


if __name__ == "__main__":
    main()
