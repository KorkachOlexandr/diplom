from __future__ import annotations

import importlib
import pkgutil
import re
from dataclasses import dataclass, field
from typing import Callable

from app.report.model import LeakageHit


@dataclass(frozen=True)
class Rule:
    """A high-precision detector for one LLM-leakage failure mode.

    The taxonomy framing: each rule targets a specific, named failure mode of
    careless LLM use, NOT general AI authorship. Rules are intentionally
    high-precision and low-recall. Per-rule precision/recall on HC3 / M4 will
    be measured in Phase 3 and stored in `measured_precision` / `measured_recall`.
    """

    id: str
    name: str
    family: str
    description: str
    detector: Callable[[str], list[tuple[int, int, str]]]
    measured_precision: float | None = None
    measured_recall: float | None = None


_RULES: dict[str, Rule] = {}


def register(rule: Rule) -> Rule:
    if rule.id in _RULES:
        raise ValueError(f"Duplicate rule id: {rule.id}")
    _RULES[rule.id] = rule
    return rule


def registered_rules() -> list[Rule]:
    _autoload()
    return list(_RULES.values())


def detect(text: str) -> list[LeakageHit]:
    _autoload()
    hits: list[LeakageHit] = []
    for rule in _RULES.values():
        for start, end, evidence in rule.detector(text):
            hits.append(
                LeakageHit(
                    rule_id=rule.id,
                    rule_family=rule.family,
                    description=rule.description,
                    start=start,
                    end=end,
                    evidence=evidence,
                )
            )
    hits.sort(key=lambda h: (h.start, h.rule_id))
    return hits


def regex_detector(pattern: str, flags: int = re.IGNORECASE | re.MULTILINE) -> Callable[[str], list[tuple[int, int, str]]]:
    """Helper: build a detector function from a regex pattern."""
    compiled = re.compile(pattern, flags)

    def _run(text: str) -> list[tuple[int, int, str]]:
        return [(m.start(), m.end(), m.group(0)) for m in compiled.finditer(text)]

    return _run


_AUTOLOADED = False


def _autoload() -> None:
    global _AUTOLOADED
    if _AUTOLOADED:
        return
    from app.signals.ai_leakage import rules as rules_pkg

    for _, name, _ in pkgutil.iter_modules(rules_pkg.__path__):
        importlib.import_module(f"{rules_pkg.__name__}.{name}")
    _AUTOLOADED = True
