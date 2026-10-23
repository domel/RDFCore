"""Congruence and injectivity of the interpretation's IT mapping.

Names need not be distinct. Equal constructor results force equal arguments,
and equal arguments force equal results. Cycles are allowed by the formal IT
conditions; an occurs check would incorrectly reject some D-interpretations.
Fixed datatype objects and distinct recognized literal values cannot merge.
"""
from .term import BNode, Literal, TripleTerm, URIRef
from dataclasses import dataclass


@dataclass(frozen=True)
class _Resource:
    """A semantic constant; unlike a BNode it is never a query variable."""
    identifier: str

    def __str__(self):
        return self.identifier


class ImpossibleModel(Exception):
    pass


class TermModel:
    def __init__(self, graph, recognized):
        from . import semantics as sem
        self.sem, self.recognized = sem, recognized
        self.terms, self.parents, self.apps = {}, {}, {}
        for row in graph:
            for root in row:
                for term in sem._terms(root):
                    self.add(term)

    def add(self, term):
        key = self.sem._key(term)
        if key not in self.parents:
            self.parents[key] = key
            self.terms[key] = term
            if isinstance(term, TripleTerm):
                self.apps[key] = tuple(self.add(c) for c in term)
        return key

    def find(self, key):
        self.sem._step()
        root = key
        while self.parents[root] != root:
            root = self.parents[root]
        while key != root:
            parent = self.parents[key]
            self.parents[key] = root
            key = parent
        return root

    def union(self, a, b):
        a, b = self.find(a), self.find(b)
        if a == b:
            return False
        self.parents[b] = a
        return True

    def assign(self, term, value):
        self.union(self.add(term), self.add(value))

    def finish(self):
        while True:
            forward, inverse, changed = {}, {}, False
            for result, components in self.apps.items():
                self.sem._step()
                signature = tuple(self.find(c) for c in components)
                root = self.find(result)
                if signature in forward:
                    changed |= self.union(root, forward[signature])
                else:
                    forward[signature] = root
                if root in inverse:
                    for left, right in zip(components, inverse[root]):
                        changed |= self.union(left, right)
                else:
                    inverse[root] = components
            if not changed:
                break
        groups = {}
        for key, term in self.terms.items():
            groups.setdefault(self.find(key), []).append(term)
        self.representatives = {}
        occupied = {term for terms in groups.values() for term in terms}
        for root, terms in groups.items():
            values = [t for t in terms if isinstance(t, Literal)
                      and self.sem._literal_datatype(t) in self.recognized]
            datatypes = [t for t in terms if isinstance(t, URIRef) and t in self.recognized]
            if (len({self.sem._key(t) for t in values}) > 1 or len(set(datatypes)) > 1
                    or values and datatypes):
                raise ImpossibleModel('incompatible fixed denotations')
            names = sorted((t for t in terms if isinstance(t, URIRef)), key=str)
            opaque = [t for t in terms if isinstance(t, Literal)]
            nodes = [t for t in terms if isinstance(t, BNode)]
            if values or datatypes or names or opaque:
                representative = (values or datatypes or names or opaque)[0]
            elif nodes and not any(isinstance(t, TripleTerm) for t in terms):
                representative = nodes[0]
            else:
                representative = _Resource(str(BNode()))
                while representative in occupied:
                    self.sem._step()
                    representative = _Resource(str(BNode()))
                occupied.add(representative)
            self.representatives[root] = representative
        self.aliases = {t: self.representatives[self.find(k)] for k, t in self.terms.items()
                        if isinstance(t, URIRef)}
        self.applications = tuple((self.representatives[self.find(k)],
                                   tuple(self.representatives[self.find(c)] for c in components))
                                  for k, components in self.apps.items())

    def term(self, term):
        key = self.sem._key(term)
        if key in self.parents:
            return self.representatives[self.find(key)]
        if isinstance(term, TripleTerm):
            return self.sem._application_value(self.sem._InterpretedTriple(*(self.term(c) for c in term)))
        return term
