"""Explicit, partial RDF 1.2 entailment facilities (no runtime dependencies).

Baseline, inspected 2026-10-17:
* Semantics CRD 2026-09-24:
  https://www.w3.org/TR/2026/CRD-rdf12-semantics-20260924/
  Sections #simpleinterpretations, #rdf-interpretations, #rdfs-interpretations.
* Schema WD 2026-10-10:
  https://www.w3.org/TR/2026/WD-rdf12-schema-20261010/
  Sections on subClassOf, subPropertyOf, domain and range.
* Linked EDs https://w3c.github.io/rdf-semantics/spec/ and
  https://w3c.github.io/rdf-schema/spec/ inspected on the same date. Their
  source has no fixed publishDate (previousPublishDate is 2014-02-25).
  The inspected simple interpretation/instance and hierarchy/domain/range
  conditions agree with the published baseline; no ED-only rule is selected.
  The ED contains two rdfD2 presentations; normative conditions, rather than
  a presumed complete appendix algorithm, are the basis of this subset.
* https://w3c.github.io/rdf-tests/rdf/rdf12/rdf-semantics/ inspected, including
  transparency, shared blank node, non-assertion and inconsistency cases.

``entails(S, E)`` decides simple entailment by a blank-node homomorphism.
Matching descends into triple terms, with one mapping across the whole
conclusion; embedded triples are never asserted. Literal matching uses RDF
term identity, not Python value equality (implicit xsd:string is explicit).

For regime='rdf' or 'rdfs', True is a sound proof, but failure to find a proof
raises UnsupportedEntailment, NEVER False. Supported forward rules: RDF
property typing; RDFS domain/range, subclass/subproperty transitivity and
propagation, class/property typing and reflexivity, Resource typing,
ContainerMembershipProperty/Datatype consequences, and typing occurring
triple terms as Proposition. Generalized intermediate triples permit literal
and triple-term subjects and blank-node predicates. These are returned as
tuples, not inserted into Graph.

The finite RDF/RDFS axioms are included. Container membership axioms are
instantiated for IRIs occurring in the premise or conclusion, avoiding an
infinite materialization. No ordinary graph operation performs inference.

NOT implemented: datatype value entailment/recognition, inconsistency
detection or explosion, exhaustive proposition generation, dataset entailment,
or a complete official W3C manifest run. Positive proofs remain valid even
for inconsistent premises; no consistency conclusion is drawn. ``datatypes``
is reserved: any supplied value raises explicitly rather than being ignored.
The rules are monotonic and optional; no Graph methods or inputs are mutated.

Inputs must be finite RDF graphs (Graph or iterable of triples). Space is
proportional to the materialized input/closure; closure uses repeated joins,
and existential matching can take exponential time. Excessive nesting/search
depth raises UnsupportedEntailment instead of returning a negative result.
This module is a partial facility, not a full RDF 1.2 conformance claim.
"""

from __future__ import annotations

from collections.abc import Iterable
from collections import defaultdict
import re

from .dataset import ConjunctiveGraph, Dataset
from .namespace import RDF, RDFS
from .term import BNode, Literal, TripleTerm, URIRef

__all__ = ["UnsupportedEntailment", "entails", "entailment_closure"]

Term = URIRef | BNode | Literal | TripleTerm
Triple = tuple[Term, Term, Term]
_XSD_STRING = URIRef("http://www.w3.org/2001/XMLSchema#string")


class UnsupportedEntailment(NotImplementedError):
    """The requested entailment cannot be decided by this partial facility."""


def _options(regime: str, datatypes: object) -> None:
    if regime not in ("simple", "rdf", "rdfs"):
        raise ValueError("regime must be 'simple', 'rdf', or 'rdfs'")
    if datatypes is not None:
        raise UnsupportedEntailment("custom datatype recognition is not implemented")


def _validate(triple: object) -> Triple:
    if not isinstance(triple, (tuple, list)) or len(triple) != 3:
        raise TypeError("expected an RDF triple of three terms")
    s, p, o = triple
    if not isinstance(s, (URIRef, BNode)) or not isinstance(p, URIRef):
        raise TypeError("RDF subjects must be IRIs/blank nodes and predicates IRIs")
    if not isinstance(o, (URIRef, BNode, Literal, TripleTerm)):
        raise TypeError("RDF object must be an RDF term")
    if isinstance(o, TripleTerm):
        _validate(tuple(o))
    return s, p, o


def _snapshot(graph: Iterable[Triple]) -> set[Triple]:
    if isinstance(graph, (Dataset, ConjunctiveGraph)):
        raise UnsupportedEntailment("select an explicit graph; dataset entailment is unsupported")
    return {_validate(triple) for triple in graph}


def _key(term: Term) -> tuple:
    if isinstance(term, TripleTerm):
        return (TripleTerm, *(_key(component) for component in term))
    if isinstance(term, Literal):
        return (Literal, str(term), term.datatype or _XSD_STRING,
                (term.language or "").lower(), term.direction)
    return type(term), str(term)


def _match(pattern: Term, value: Term, bindings: dict) -> bool:
    if isinstance(pattern, BNode):
        key = _key(value)
        if pattern in bindings:
            return bindings[pattern] == key
        bindings[pattern] = key
        return True
    if isinstance(pattern, TripleTerm):
        return isinstance(value, TripleTerm) and all(
            _match(p, v, bindings) for p, v in zip(pattern, value)
        )
    return _key(pattern) == _key(value)


def _homomorphism(source: set[Triple], target: set[Triple]) -> bool:
    # Ground positions prune candidates without modifying the shared mapping.
    choices = []
    for pattern in target:
        candidates = [triple for triple in source if all(
            _match(p, v, {}) for p, v in zip(pattern, triple)
        )]
        if not candidates:
            return False
        choices.append((pattern, candidates))
    choices.sort(key=lambda entry: len(entry[1]))

    def search(index: int, bindings: dict) -> bool:
        if index == len(choices):
            return True
        pattern, candidates = choices[index]
        for triple in candidates:
            extended = bindings.copy()
            if all(_match(p, v, extended) for p, v in zip(pattern, triple)):
                if search(index + 1, extended):
                    return True
        return False

    return search(0, {})


def _terms(term: Term):
    yield term
    if isinstance(term, TripleTerm):
        for component in term:
            yield from _terms(component)


def _axioms(regime: str, vocabulary: set[Term]) -> set[Triple]:
    """Published Semantics sections 8 and 9, restricted to finite vocabulary."""
    result = {(RDF[name], RDF.type, RDF.Property) for name in
              ('type', 'subject', 'predicate', 'object', 'reifies', 'first', 'rest', 'value')}
    result.add((RDF.nil, RDF.type, RDF.List))
    containers = {term for term in vocabulary if isinstance(term, URIRef)
                  and re.fullmatch(re.escape(str(RDF)) + r'_[1-9][0-9]*', str(term))}
    for term in containers:
        result.add((term, RDF.type, RDF.Property))
        if regime == 'rdfs':
            result.update(((term, RDF.type, RDFS.ContainerMembershipProperty),
                           (term, RDFS.domain, RDFS.Resource),
                           (term, RDFS.range, RDFS.Resource)))
    if regime != 'rdfs':
        return result
    domains = {
        RDF.type: RDFS.Resource, RDF.reifies: RDFS.Resource,
        RDFS.domain: RDF.Property, RDFS.range: RDF.Property,
        RDFS.subPropertyOf: RDF.Property, RDFS.subClassOf: RDFS.Class,
        RDF.subject: RDF.Statement, RDF.predicate: RDF.Statement, RDF.object: RDF.Statement,
        RDFS.member: RDFS.Resource, RDF.first: RDF.List, RDF.rest: RDF.List,
        RDFS.seeAlso: RDFS.Resource, RDFS.isDefinedBy: RDFS.Resource,
        RDFS.comment: RDFS.Resource, RDFS.label: RDFS.Resource, RDF.value: RDFS.Resource,
    }
    ranges = {
        RDF.type: RDFS.Class, RDF.reifies: RDFS.Proposition,
        RDFS.domain: RDFS.Class, RDFS.range: RDFS.Class,
        RDFS.subPropertyOf: RDF.Property, RDFS.subClassOf: RDFS.Class,
        RDF.subject: RDFS.Resource, RDF.predicate: RDFS.Resource, RDF.object: RDFS.Resource,
        RDFS.member: RDFS.Resource, RDF.first: RDFS.Resource, RDF.rest: RDF.List,
        RDFS.seeAlso: RDFS.Resource, RDFS.isDefinedBy: RDFS.Resource,
        RDFS.comment: RDFS.Literal, RDFS.label: RDFS.Literal, RDF.value: RDFS.Resource,
    }
    result.update((p, RDFS.domain, c) for p, c in domains.items())
    result.update((p, RDFS.range, c) for p, c in ranges.items())
    result.update((term, RDFS.subClassOf, RDFS.Container) for term in (RDF.Alt, RDF.Bag, RDF.Seq))
    result.update(((RDFS.ContainerMembershipProperty, RDFS.subClassOf, RDF.Property),
                   (RDFS.Proposition, RDFS.subClassOf, RDFS.Resource),
                   (RDFS.Datatype, RDFS.subClassOf, RDFS.Class),
                   (RDFS.isDefinedBy, RDFS.subPropertyOf, RDFS.seeAlso)))
    return result


def _closure(source: set[Triple], regime: str, vocabulary=()) -> set[Triple]:
    result = source.copy()
    if regime == "simple":
        return result
    terms = {term for triple in (*source, *vocabulary) for root in triple for term in _terms(root)}
    result.update(_axioms(regime, terms))
    while True:
        additions = set()
        by_predicate = defaultdict(list)
        by_subject_predicate = defaultdict(list)
        by_predicate_object = defaultdict(list)
        for a, b, c in result:
            by_predicate[b].append((a, b, c))
            by_subject_predicate[(a, b)].append(c)
            by_predicate_object[(b, c)].append(a)
        for s, p, o in result:
            additions.add((p, RDF.type, RDF.Property))
            if regime != "rdfs":
                continue
            for root in (s, p, o):
                for term in _terms(root):
                    additions.add((term, RDF.type, RDFS.Resource))
                    if isinstance(term, TripleTerm):
                        additions.add((term, RDF.type, RDFS.Proposition))
            if p == RDF.type:
                additions.add((o, RDF.type, RDFS.Class))
                if o == RDF.Property:
                    additions.add((s, RDFS.subPropertyOf, s))
                if o == RDFS.Class:
                    additions.update(((s, RDFS.subClassOf, s),
                                      (s, RDFS.subClassOf, RDFS.Resource)))
                if o == RDFS.ContainerMembershipProperty:
                    additions.add((s, RDFS.subPropertyOf, RDFS.member))
                if o == RDFS.Datatype:
                    additions.add((s, RDFS.subClassOf, RDFS.Literal))
            if p == RDFS.subClassOf:
                additions.update(((s, RDF.type, RDFS.Class), (o, RDF.type, RDFS.Class)))
            if p == RDFS.subPropertyOf:
                additions.update(((s, RDF.type, RDF.Property), (o, RDF.type, RDF.Property)))
            if p in (RDFS.domain, RDFS.range):
                additions.update(((s, RDF.type, RDF.Property), (o, RDF.type, RDFS.Class)))
            if p in (RDFS.domain, RDFS.range, RDFS.subPropertyOf):
                for a, b, c in by_predicate.get(s, ()):
                    if p == RDFS.domain:
                        additions.add((a, RDF.type, o))
                    elif p == RDFS.range:
                        additions.add((c, RDF.type, o))
                    else:
                        additions.add((a, o, c))
            if p in (RDFS.subPropertyOf, RDFS.subClassOf):
                for c in by_subject_predicate.get((o, p), ()):
                    additions.add((s, p, c))
            if p == RDFS.subClassOf:
                for a in by_predicate_object.get((RDF.type, s), ()):
                    additions.add((a, RDF.type, o))
        additions.difference_update(result)
        if not additions:
            return result
        result.update(additions)


def entailment_closure(
    graph: Iterable[Triple], *, regime: str = "rdfs", datatypes: object = None,
) -> frozenset[Triple]:
    """Return a finite, sound but incomplete rule closure, including input.

    The immutable result may contain generalized triples (literal/triple-term
    subjects or blank-node predicates), unsuitable for ``Graph.add``. Absence
    from this partial closure does NOT establish non-entailment. No datatype
    recognition or full axiomatic closure is performed.
    """
    _options(regime, datatypes)
    try:
        return frozenset(_closure(_snapshot(graph), regime))
    except RecursionError as exc:
        raise UnsupportedEntailment("entailment nesting limit exceeded") from exc


def entails(
    premise: Iterable[Triple], conclusion: Iterable[Triple], *,
    regime: str = "simple", datatypes: object = None,
) -> bool:
    """Decide simple entailment, or prove a supported RDF/RDFS entailment.

    RDF/RDFS return only True or raise UnsupportedEntailment; a failed proof
    is unknown, not False. Blank nodes in conclusion are existential and have
    an independent scope from premise, even when their labels coincide.
    Invalid RDF input raises TypeError; unknown regimes raise ValueError.
    """
    _options(regime, datatypes)
    try:
        source, target = _snapshot(premise), _snapshot(conclusion)
        if _homomorphism(_closure(source, regime, target), target):
            return True
        if regime == "simple":
            return False
    except RecursionError as exc:
        raise UnsupportedEntailment("entailment nesting/search limit exceeded") from exc
    raise UnsupportedEntailment(
        f"{regime} proof not found: datatype, axiomatic, proposition and "
        "inconsistency reasoning are incomplete; non-entailment is unknown"
    )
