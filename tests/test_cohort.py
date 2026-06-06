from __future__ import annotations

from app.report.model import SubmissionReport
from app.signals.cohort.compare import find_matches
from app.signals.cohort.shingles import (
    longest_matching_span,
    near_duplicate_pairs,
    shingle,
)


def test_shingle_produces_kgrams():
    text = "the quick brown fox jumps over the lazy dog"
    sh = shingle(text, k=3)
    assert "the quick brown" in sh
    assert "quick brown fox" in sh
    assert len(sh) == 7


def test_minhash_finds_identical_pair():
    text = (
        "Climate change refers to long-term shifts in temperatures and "
        "weather patterns. Human activities have been the dominant driver."
    )
    pairs = near_duplicate_pairs(
        [("a", text), ("b", text), ("c", "Completely unrelated topic about cats.")],
        threshold=0.3,
    )
    pair_ids = {tuple(sorted((id_a, id_b))) for id_a, id_b, _ in pairs}
    assert ("a", "b") in pair_ids
    assert ("a", "c") not in pair_ids


def test_minhash_finds_partial_reuse():
    shared = (
        "Photosynthesis is the process by which plants convert sunlight into "
        "chemical energy stored in glucose."
    )
    text_a = "Some opening sentence. " + shared + " Some closing sentence."
    text_b = "A different intro. " + shared + " Different conclusion entirely."
    pairs = near_duplicate_pairs(
        [("a", text_a), ("b", text_b), ("c", "Lorem ipsum dolor sit amet.")],
        threshold=0.3,
    )
    pair_ids = {tuple(sorted((id_a, id_b))) for id_a, id_b, _ in pairs}
    assert ("a", "b") in pair_ids


def test_longest_matching_span():
    shared = "the mitochondrion is the powerhouse of the cell"
    text_a = "Earlier text. " + shared + " later text."
    text_b = "Different earlier. " + shared + " different later."
    out = longest_matching_span(text_a, text_b, min_chars=20)
    assert out is not None
    (_, _), (_, _), excerpt_a, excerpt_b = out
    assert shared in excerpt_a
    assert shared in excerpt_b


def test_longest_matching_span_returns_none_for_short_match():
    out = longest_matching_span("abc xyz", "def xyz", min_chars=60)
    assert out is None


def test_find_matches_surfaces_cohort_pair():
    shared = (
        "Climate change refers to long-term shifts in temperatures and weather "
        "patterns. Human activities have been the dominant driver since the "
        "industrial revolution."
    )
    subs = [
        SubmissionReport(submission_id="s1", student_id="u1", student_name="Anna", text=shared),
        SubmissionReport(submission_id="s2", student_id="u2", student_name="Daria", text=shared),
        SubmissionReport(
            submission_id="s3",
            student_id="u3",
            student_name="Cyril",
            text="Newton's three laws describe forces and motion.",
        ),
    ]
    matches = find_matches(subs)
    assert any(m.other_submission_id == "s2" and m.channel == "minhash" for m in matches["s1"])
    assert any(m.other_submission_id == "s1" and m.channel == "minhash" for m in matches["s2"])
    assert matches["s3"] == []


def test_find_matches_handles_empty_submissions():
    subs = [
        SubmissionReport(submission_id="s1", student_id="u1", student_name="A", text=""),
        SubmissionReport(submission_id="s2", student_id="u2", student_name="B", text=""),
    ]
    matches = find_matches(subs)
    assert matches == {"s1": [], "s2": []}
