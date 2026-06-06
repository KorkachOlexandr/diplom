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
    by_hash: dict[str, list[tuple[str, SubtreeHash]]] = defaultdict(list)
    counts: dict[str, int] = {}
    for sid, hashes in submissions:
        counts[sid] = len(hashes)
        for h in hashes:
            by_hash[h.hash_value].append((sid, h))

    shared: dict[tuple[str, str], list[SubtreeHash]] = defaultdict(list)
    for owners in by_hash.values():
        if len(owners) < 2:
            continue
        for i in range(len(owners)):
            for j in range(i + 1, len(owners)):
                if owners[i][0] == owners[j][0]:
                    continue
                key = tuple(sorted((owners[i][0], owners[j][0])))
                # We keep the bigger of the two as the evidence size — both
                # are equal in structural terms (same hash) so this is just
                # for display purposes.
                shared[key].append(owners[i][1] if owners[i][1].size >= owners[j][1].size else owners[j][1])

    out: list[tuple[str, str, AstMatch]] = []
    for (id_a, id_b), subtrees in shared.items():
        # Jaccard for the same reason as the winnowing channel: stable
        # against very different submission lengths.
        n_shared = len(subtrees)
        union = counts[id_a] + counts[id_b] - n_shared
        score = n_shared / union if union else 0.0
        if score < min_score:
            continue
        largest = max(s.size for s in subtrees)
        out.append(
            (
                id_a,
                id_b,
                AstMatch(
                    other_id=id_b,
                    score=score,
                    shared_subtrees=len(subtrees),
                    largest_subtree=largest,
                ),
            )
        )
    return out
