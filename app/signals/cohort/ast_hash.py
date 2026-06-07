"""AST subtree hashing for structural similarity.

Token-based winnowing handles cosmetic edits (renames, reformatting,
literal changes) but is sensitive to deeper refactoring like statement
reordering or function extraction. Hashing AST subtrees gives us a
second channel that survives those edits — two functions with the
same control-flow shape produce overlapping subtree hashes even when
the textual fingerprints diverge.

Method: walk the Python AST, emit a deterministic hash per non-trivial
subtree (any node with ≥ MIN_SUBTREE_SIZE descendants). Compare two
submissions by counting shared subtree hashes, normalized by the
smaller submission's hash count.
"""
from __future__ import annotations

import ast
import hashlib
from collections import defaultdict
from dataclasses import dataclass


# Don't waste cycles on tiny shared subtrees — they're statistical noise
# (every Python file has `Name`, `Load`, `Store` nodes). Empirically ~6
# is the floor below which precision tanks; tunable in Phase 5.
MIN_SUBTREE_SIZE = 6


@dataclass(frozen=True)
class SubtreeHash:
    hash_value: str
    node_type: str
    size: int                    # number of nodes in the subtree
    lineno: int                  # source line where the subtree starts (1-based)
    end_lineno: int | None       # source line where it ends


def _ast_signature(node: ast.AST) -> tuple:
    """Recursive structural signature. Identifiers, numeric, and string
    constants are abstracted away so renames don't disturb the hash."""
    if isinstance(node, ast.Name):
        return ("Name", "IDENT")
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, complex)):
            return ("Constant", "NUM")
        if isinstance(node.value, str):
            return ("Constant", "STR")
        if isinstance(node.value, bytes):
            return ("Constant", "BYTES")
        return ("Constant", type(node.value).__name__)
    if isinstance(node, ast.arg):
        return ("arg",)
    parts: list = [type(node).__name__]
    for field_name in node._fields:
        value = getattr(node, field_name, None)
        if isinstance(value, ast.AST):
            parts.append(_ast_signature(value))
        elif isinstance(value, list):
            parts.append(tuple(_ast_signature(v) if isinstance(v, ast.AST) else None for v in value))
        elif isinstance(value, str) and field_name in {"name", "id", "attr", "module", "asname", "arg"}:
            parts.append(("IDENT",))
        elif isinstance(value, (int, float, complex)) and field_name == "value":
            parts.append(("NUM",))
        else:
            parts.append(value)
    return tuple(parts)


def _count_nodes(node: ast.AST) -> int:
    return 1 + sum(_count_nodes(c) for c in ast.iter_child_nodes(node))


def subtree_hashes(source: str) -> list[SubtreeHash]:
    """Return one SubtreeHash per non-trivial subtree in the source.

    If the source doesn't parse, returns []. The token-winnowing channel
    still runs on unparseable code, so we don't lose the submission.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    out: list[SubtreeHash] = []
    for node in ast.walk(tree):
        size = _count_nodes(node)
        if size < MIN_SUBTREE_SIZE:
            continue
        sig = _ast_signature(node)
        h = hashlib.sha256(repr(sig).encode("utf-8")).hexdigest()[:16]
        out.append(
            SubtreeHash(
                hash_value=h,
                node_type=type(node).__name__,
                size=size,
                lineno=getattr(node, "lineno", 0) or 0,
                end_lineno=getattr(node, "end_lineno", None),
            )
        )
    return out


@dataclass(frozen=True)
class AstMatch:
    other_id: str
    score: float
    shared_subtrees: int
    largest_subtree: int


def compare_subtrees(
    submissions: list[tuple[str, list[SubtreeHash]]],
    min_score: float = 0.15,
) -> list[tuple[str, str, AstMatch]]:
    # Per-submission multiset of subtree hashes — count, not list, so a
    # repeated structural pattern (e.g. two calls of `fib(n - NUM)` after
    # normalization) doesn't get squared into the shared count via Cartesian
    # product across owners. The shared count is multiset intersection.
    counts: dict[str, int] = {sid: len(hs) for sid, hs in submissions}
    hash_multiset: dict[str, dict[str, int]] = {sid: {} for sid, _ in submissions}
    largest_seen: dict[str, dict[str, int]] = {sid: {} for sid, _ in submissions}
    for sid, hashes in submissions:
        for h in hashes:
            hash_multiset[sid][h.hash_value] = hash_multiset[sid].get(h.hash_value, 0) + 1
            prev = largest_seen[sid].get(h.hash_value, 0)
            if h.size > prev:
                largest_seen[sid][h.hash_value] = h.size

    # All hashes that appear in at least two submissions.
    all_hashes: set[str] = set()
    for ms in hash_multiset.values():
        all_hashes.update(ms.keys())

    sub_ids = [sid for sid, _ in submissions]
    shared_count: dict[tuple[str, str], int] = {}
    largest_subtree: dict[tuple[str, str], int] = {}
    for h in all_hashes:
        owners = [sid for sid in sub_ids if h in hash_multiset[sid]]
        if len(owners) < 2:
            continue
        for i in range(len(owners)):
            for j in range(i + 1, len(owners)):
                a, b = owners[i], owners[j]
                key = tuple(sorted((a, b)))
                contribution = min(hash_multiset[a][h], hash_multiset[b][h])
                shared_count[key] = shared_count.get(key, 0) + contribution
                size = max(largest_seen[a][h], largest_seen[b][h])
                if size > largest_subtree.get(key, 0):
                    largest_subtree[key] = size

    out: list[tuple[str, str, AstMatch]] = []
    for (id_a, id_b), n_shared in shared_count.items():
        # Jaccard for the same reason as the winnowing channel: stable
        # against very different submission lengths.
        union = counts[id_a] + counts[id_b] - n_shared
        score = n_shared / union if union else 0.0
        if score < min_score:
            continue
        out.append(
            (
                id_a,
                id_b,
                AstMatch(
                    other_id=id_b,
                    score=score,
                    shared_subtrees=n_shared,
                    largest_subtree=largest_subtree[(id_a, id_b)],
                ),
            )
        )
    return out
