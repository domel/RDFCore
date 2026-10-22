"""Structural comparison helpers for RDF graphs and RDF 1.2 datasets."""

from __future__ import annotations

from .term import BNode, TripleTerm


def isomorphic(left, right) -> bool:
    """Return whether two graphs or datasets are equal up to blank-node names."""
    if hasattr(left, 'quads') != hasattr(right, 'quads'):
        return False
    left_quads = set(_quads(left))
    right_quads = set(_quads(right))
    if len(left_quads) != len(right_quads):
        return False
    # Ground statements need no search or recursion. Keep graph declarations
    # as records too: quads alone cannot describe empty named graphs.
    left_ground = {row for row in left_quads if not any(_has_bnode(t) for t in row)}
    right_ground = {row for row in right_quads if not any(_has_bnode(t) for t in row)}
    if left_ground != right_ground:
        return False
    left_quads -= left_ground
    right_quads -= right_ground
    by_shape = {}
    for row in right_quads:
        by_shape.setdefault(tuple(_shape(t) for t in row), []).append(row)
    candidates = [
        (quad, [other for other in by_shape.get(tuple(_shape(t) for t in quad), ())
                if _compatible(quad, other, {}, {})])
        for quad in left_quads
    ]
    candidates.sort(key=lambda item: len(item[1]))
    return _match(candidates)


def _quads(value):
    from .dataset import Dataset
    if isinstance(value, Dataset):
        # Dataset.graph() deliberately follows RDFLib's base-reset behavior.
        # Neither quads() nor graphs() is therefore a read-only snapshot API.
        # Read existing store contexts directly, without creating graph views
        # or registering contexts as a side effect of comparison.
        default = value.default_graph.identifier
        contexts = list(dict.fromkeys(value.store.contexts()))
        rows = [(*triple, None if context == default else context)
                for context in contexts
                for triple, _ in value.store.triples((None, None, None), context)]
        return rows + [(None if context == default else context,)
                       for context in dict.fromkeys([*contexts, default])]
    if hasattr(value, "quads"):
        default = value.default_graph.identifier
        return [(*row[:3], None if row[3] == default else row[3]) for row in value.quads()] + [
            (None if graph.identifier == default else graph.identifier,) for graph in value.graphs()]
    return [(*triple, None) for triple in value]


def _has_bnode(term):
    return isinstance(term, BNode) or isinstance(term, TripleTerm) and any(_has_bnode(t) for t in term)


def _shape(term):
    if isinstance(term, BNode):
        return (BNode,)
    if isinstance(term, TripleTerm):
        return (TripleTerm, *(_shape(t) for t in term))
    return (term,)


def _match(items):
    if not items:
        return True
    forward, reverse, used = {}, {}, set()
    # Explicit DFS frames and reversible bindings keep stack space linear,
    # without Python recursion or a full mapping copy for every statement.
    stack = [(iter(items[0][1]), None, [])]
    while stack:
        options, previous, bindings = stack[-1]
        try:
            target = next(options)
        except StopIteration:
            stack.pop()
            if previous is not None:
                used.remove(previous)
            for a, b in bindings:
                del forward[a]
                del reverse[b]
            continue
        if target in used:
            continue
        added = []
        if _compatible(items[len(stack) - 1][0], target, forward, reverse, added):
            if len(stack) == len(items):
                return True
            used.add(target)
            stack.append((iter(items[len(stack)][1]), target, added))
        else:
            for a, b in added:
                del forward[a]
                del reverse[b]
    return False


def _compatible(left, right, forward, reverse, added=None):
    return len(left) == len(right) and all(
        _terms_equal(a, b, forward, reverse, added)
        for a, b in zip(left, right)
    )


def _terms_equal(left, right, forward, reverse, added=None):
    if isinstance(left, BNode) or isinstance(right, BNode):
        if not isinstance(left, BNode) or not isinstance(right, BNode):
            return False
        mapped = forward.get(left)
        if mapped is not None:
            return mapped == right
        mapped_back = reverse.get(right)
        if mapped_back is not None:
            return mapped_back == left
        forward[left] = right
        reverse[right] = left
        if added is not None:
            added.append((left, right))
        return True
    if isinstance(left, TripleTerm) or isinstance(right, TripleTerm):
        return (
            isinstance(left, TripleTerm)
            and isinstance(right, TripleTerm)
            and _terms_equal(left.subject, right.subject, forward, reverse, added)
            and _terms_equal(left.predicate, right.predicate, forward, reverse, added)
            and _terms_equal(left.object, right.object, forward, reverse, added)
        )
    return left == right

