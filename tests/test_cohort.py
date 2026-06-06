from __future__ import annotations

from app.report.model import SubmissionReport
from app.signals.cohort.ast_hash import compare_subtrees, subtree_hashes
from app.signals.cohort.compare import find_matches
from app.signals.cohort.tokenize_code import (
    PythonTokenizer,
    detect_language,
    tokenize_source,
)
from app.signals.cohort.winnowing import compare_submissions, fingerprints


_BUBBLE = (
    "def bubble_sort(lst):\n"
    "    n = len(lst)\n"
    "    for i in range(n):\n"
    "        for j in range(n - i - 1):\n"
    "            if lst[j] > lst[j + 1]:\n"
    "                lst[j], lst[j + 1] = lst[j + 1], lst[j]\n"
    "    return lst\n"
)


_BUBBLE_RENAMED = (
    "def bubble_sort(arr):\n"
    "    length = len(arr)\n"
    "    for outer in range(length):\n"
    "        for inner in range(length - outer - 1):\n"
    "            if arr[inner] > arr[inner + 1]:\n"
    "                arr[inner], arr[inner + 1] = arr[inner + 1], arr[inner]\n"
    "    return arr\n"
)


_UNRELATED_FIB = (
    "def fib(n):\n"
    "    a, b = 0, 1\n"
    "    for _ in range(n):\n"
    "        a, b = b, a + b\n"
    "    return a\n"
)


# ---------- Tokenizer ----------

def test_python_tokenizer_normalizes_identifiers():
    tokens = PythonTokenizer().tokenize("def foo(): x = 1")
    kinds = [t.kind for t in tokens]
    assert "def" in kinds
    assert "IDENT" in kinds  # foo, x
    assert "NUM" in kinds    # 1
    assert "foo" not in kinds
    assert "x" not in kinds


def test_python_tokenizer_strips_comments_and_newlines():
    tokens = PythonTokenizer().tokenize("# a comment\ndef foo():\n    pass\n")
    raws = [t.raw for t in tokens]
    assert "# a comment" not in raws


def test_python_tokenizer_handles_broken_code_without_crashing():
    """Broken code shouldn't take the whole scan down — either the standard
    tokenizer eats it (it's surprisingly tolerant) or the regex fallback
    fires. We just verify some tokens come back either way."""
    # Unterminated string literal — guaranteed to fail the standard
    # tokenizer, forcing the fallback path.
    tokens = PythonTokenizer().tokenize('x = "unterminated\n')
    assert tokens  # fallback produced something


def test_detect_language_only_matches_known_extensions():
    assert detect_language("solution.py") == "python"
    assert detect_language("readme.md") is None
    assert detect_language("Main.java") is None  # explicitly not supported yet


# ---------- Winnowing ----------

def test_winnowing_identical_source_matches():
    fps_a = fingerprints(tokenize_source(_BUBBLE))
    fps_b = fingerprints(tokenize_source(_BUBBLE))
    matches = compare_submissions([("a", fps_a), ("b", fps_b)], min_score=0.5)
    assert matches
    _, _, m = matches[0]
    assert m.score >= 0.99


def test_winnowing_survives_identifier_renaming():
    """The key promise of token normalization: renames don't break detection."""
    fps_a = fingerprints(tokenize_source(_BUBBLE))
    fps_b = fingerprints(tokenize_source(_BUBBLE_RENAMED))
    matches = compare_submissions([("a", fps_a), ("b", fps_b)], min_score=0.5)
    assert matches
    _, _, m = matches[0]
    assert m.score >= 0.9


def test_winnowing_ignores_unrelated_pair():
    fps_a = fingerprints(tokenize_source(_BUBBLE))
    fps_b = fingerprints(tokenize_source(_UNRELATED_FIB))
    matches = compare_submissions([("a", fps_a), ("b", fps_b)], min_score=0.5)
    assert matches == []


# ---------- AST ----------

def test_ast_subtree_hashes_are_stable():
    a = subtree_hashes(_BUBBLE)
    b = subtree_hashes(_BUBBLE)
    assert len(a) == len(b)
    assert {h.hash_value for h in a} == {h.hash_value for h in b}


def test_ast_survives_identifier_renaming():
    """AST channel is the harder test of normalization — the structure is
    identical, so subtree hashes should match exactly."""
    a = subtree_hashes(_BUBBLE)
    b = subtree_hashes(_BUBBLE_RENAMED)
    matches = compare_subtrees([("a", a), ("b", b)], min_score=0.0)
    assert matches
    _, _, m = matches[0]
    assert m.score >= 0.99


def test_ast_returns_empty_for_unparseable_source():
    assert subtree_hashes("def def def( :::") == []


# ---------- compare.find_matches ----------

def test_find_matches_surfaces_winnowing_pair_on_renamed_copy():
    subs = [
        SubmissionReport(submission_id="s1", student_id="u1", student_name="Anna", text=_BUBBLE),
        SubmissionReport(submission_id="s2", student_id="u2", student_name="Daria", text=_BUBBLE_RENAMED),
        SubmissionReport(submission_id="s3", student_id="u3", student_name="Cyril", text=_UNRELATED_FIB),
    ]
    matches = find_matches(subs)
    s1_channels = {m.channel for m in matches["s1"]}
    s2_channels = {m.channel for m in matches["s2"]}
    assert "winnowing" in s1_channels
    assert "winnowing" in s2_channels
    assert matches["s3"] == []


def test_find_matches_handles_unparseable_code():
    """Winnowing channel works through the fallback tokenizer even when
    AST parsing fails. find_matches must not crash."""
    subs = [
        SubmissionReport(submission_id="s1", student_id="u1", student_name="A", text="def def def("),
        SubmissionReport(submission_id="s2", student_id="u2", student_name="B", text="def def def("),
    ]
    matches = find_matches(subs)  # must not raise
    assert "s1" in matches
    assert "s2" in matches
