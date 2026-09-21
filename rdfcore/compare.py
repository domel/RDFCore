"""Structural comparison helpers for RDF graphs and RDF 1.2 datasets."""

from __future__ import annotations

from .term import BNode, TripleTerm


def isomorphic(left, right) -> bool:
    """Return whether two graphs or datasets are equal up to blank-node names."""
    left_quads = _quads(left)
    right_quads = _quads(right)
    if len(left_quads) != len(right_quads):
        return False
    candidates = [
        (quad, [other for other in right_quads if _compatible(quad, other, {}, {})])
        for quad in left_quads
    ]
    candidates.sort(key=lambda item: len(item[1]))
    return _match(candidates, 0, {}, {}, set())


def _quads(value):
    if hasattr(value, "quads"):
        return list(value.quads())
    return [(*triple, None) for triple in value]


def _match(items, index, forward, reverse, used):
    if index == len(items):
        return True
    source, options = items[index]
    for target in options:
        if target in used:
            continue
        trial_forward = dict(forward)
        trial_reverse = dict(reverse)
        if _compatible(source, target, trial_forward, trial_reverse):
            used.add(target)
            if _match(items, index + 1, trial_forward, trial_reverse, used):
                return True
            used.remove(target)
    return False


def _compatible(left, right, forward, reverse):
    return all(
        _terms_equal(a, b, forward, reverse)
        for a, b in zip(left, right)
    )


def _terms_equal(left, right, forward, reverse):
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
        return True
    if isinstance(left, TripleTerm) or isinstance(right, TripleTerm):
        return (
            isinstance(left, TripleTerm)
            and isinstance(right, TripleTerm)
            and _terms_equal(left.subject, right.subject, forward, reverse)
            and _terms_equal(left.predicate, right.predicate, forward, reverse)
            and _terms_equal(left.object, right.object, forward, reverse)
        )
    return left == right

