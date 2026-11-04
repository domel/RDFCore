"""Structural comparison helpers for RDF graphs and RDF 1.2 datasets."""

from __future__ import annotations

from collections import Counter, deque

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
    left_parts, right_parts = _components(left_quads), _components(right_quads)
    if Counter(key for key, _ in left_parts) != Counter(key for key, _ in right_parts):
        return False
    available = {}
    for key, rows in right_parts:
        available.setdefault(key, []).append(rows)
    # Blank-node components are independent. Greedily pair isomorphic
    # components within an invariant bucket; equivalence makes this safe.
    for key, rows in left_parts:
        choices = available[key]
        for index, other in enumerate(choices):
            if _component_match(rows, other):
                choices.pop(index)
                break
        else:
            return False
    return True


def _nodes(row):
    stack = list(row)
    nodes = set()
    while stack:
        term = stack.pop()
        if isinstance(term, BNode):
            nodes.add(term)
        elif isinstance(term, TripleTerm):
            stack.extend(term)
    return nodes


def _components(rows):
    parents, records = {}, []

    def root(node):
        while parents[node] != node:
            parents[node] = parents[parents[node]]
            node = parents[node]
        return node

    for row in rows:
        nodes = _nodes(row)
        first = next(iter(nodes))
        for node in nodes:
            parents.setdefault(node, node)
        for node in nodes:
            parents[root(node)] = root(first)
        records.append((row, first))
    groups, counts = {}, Counter()
    for node in parents:
        counts[root(node)] += 1
    for row, node in records:
        groups.setdefault(root(node), []).append(row)
    return [((counts[node], frozenset(Counter(tuple(_shape(t) for t in row) for row in group).items())), group)
            for node, group in groups.items()]


def _component_match(left_quads, right_quads):
    by_shape = {}
    for row in right_quads:
        by_shape.setdefault(tuple(_shape(t) for t in row), []).append(row)
    candidates = [
        (quad, [other for other in by_shape.get(tuple(_shape(t) for t in quad), ())
                if _compatible(quad, other, {}, {})])
        for quad in left_quads
    ]
    if any(not options for _, options in candidates):
        return False
    # Keep a connected prefix of source rows, so each next assignment can
    # reuse bindings instead of speculatively mapping distant cycle edges.
    incidence = {}
    for index, (row, _) in enumerate(candidates):
        for node in _nodes(row):
            incidence.setdefault(node, []).append(index)
    first = min(range(len(candidates)), key=lambda index: len(candidates[index][1]))
    pending, seen, ordered = deque([first]), {first}, []
    while pending:
        index = pending.popleft()
        row, options = candidates[index]
        ordered.append((row, options))
        for node in _nodes(row):
            for neighbor in incidence[node]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    pending.append(neighbor)
    return _match(ordered)


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

