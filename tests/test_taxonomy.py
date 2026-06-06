from __future__ import annotations

from app.signals.ai_leakage import registered_rules
from app.signals.ai_leakage.taxonomy import generate_taxonomy_md


def test_taxonomy_includes_every_registered_rule():
    md = generate_taxonomy_md()
    for rule in registered_rules():
        assert f"`{rule.id}`" in md, f"missing rule {rule.id} in taxonomy"


def test_taxonomy_groups_by_family():
    md = generate_taxonomy_md()
    families = {r.family for r in registered_rules()}
    for family in families:
        assert f"Family: `{family}`" in md


def test_taxonomy_includes_unmeasured_note_when_no_metrics():
    md = generate_taxonomy_md()
    # Phase 1 ships without measured precision/recall; the eval harness fills
    # them in. Every rule should currently be marked "not yet measured".
    assert "not yet measured" in md
