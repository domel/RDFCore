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
* T37 decision contract reviewed 2026-10-22 against the same published
  Semantics §§5, 7.1–7.2, 8–9 and the linked ED. No ED-only change is used.
  Schema WD 2026-10-22 is now published; its full rule audit belongs to T39.
* T38 value-space constraints use Semantics §§7–9, Concepts CR 2026-04-07
  §5/Appendix A and XSD 1.1 Part 2 REC 2012-04-05 §2.2.1/built-in types.
  Published Concepts/Semantics and linked EDs checked 2026-10-22. No
  ED-only lexical mapping or rule change is selected.

``entails(S, E)`` decides simple entailment by a blank-node homomorphism.
Matching descends into triple terms, with one mapping across the whole
conclusion; embedded triples are never asserted. Literal matching uses RDF
term identity, not Python value equality (implicit xsd:string is explicit).

In the default mode='proof', for regime='rdf' or 'rdfs', True is a sound proof,
but failure to find a proof raises UnsupportedEntailment, NEVER False.
Supported forward rules: RDF
property typing; RDFS domain/range, subclass/subproperty transitivity and
propagation, class/property typing and reflexivity, Resource typing,
ContainerMembershipProperty/Datatype consequences, and typing occurring
triple terms as Proposition. Generalized intermediate triples permit literal
and triple-term subjects and blank-node predicates. These are returned as
tuples, not inserted into Graph.

The finite RDF/RDFS axioms are included. Container membership axioms are
instantiated for IRIs occurring in the premise or conclusion, avoiding an
infinite materialization. No ordinary graph operation performs inference.

Explicit mode='decide' recognizes a supplied set of datatype IRIs through
datatypes.py (RDF/RDFS always include string/langString/dirLangString).
It validates literals even inside triple terms, proves explosion from an
ill-typed recognized premise literal and matches recognized literal values.
The literal False as conclusion asks whether the premise is inconsistent.
False decisions require a countermodel certificate. Certificates include
ordinary ground RDF(S) graphs without reserved vocabulary (RDF also permits
type/Property), the datatype-schema fragment below, and the simple-D fragment
without explicit recognized datatype IRIs in subject/predicate/object positions
or triple-term components. Simple-D matching descends through nested triple
terms without asserting their contents. Literal objects are allowed. Missing certificates raise
UnsupportedEntailment; no proof failure implies False.

Decision mode also checks supported datatype memberships and constraints,
including disjoint type/range/domain requirements and value-space inclusions.
It does not turn a space inclusion into an asserted subClassOf relation.
The datatype-schema countermodel fragment permits ordinary edges, type
assertions to recognized datatypes/Property, datatype domain/range, ordinary
subproperty links and recognized datatype subclass assertions. Fixed-vocabulary
aliasing and proposition constraints are excluded from that certificate.
Boolean and integer domains of at most 4096 values can be exhaustive;
larger spaces supply existence witnesses only. At most 4096 assignment
combinations are explored; exceeding this raises EntailmentResourceLimit.
New unresolved constraints prevent a countermodel certificate.

A separate guarded schema certificate covers intensional domain/range,
containers, class/property overlap and nonfunctional reification. It includes
nested triple-term predicate typing, proposition existence and selected
IT-totality witnesses, never assertions of embedded triples. An infinite
proposition extension cannot fit inside a finite recognized datatype; this
does not make individual propositions disjoint from literal values. General
fixed-vocabulary aliases, overlapping spaces and constructor/schema queries
can still be unsupported. Constructor witness search allows 4096 assignments.

NOT implemented: general RDF/RDFS decision procedures, exhaustive
proposition generation, dataset entailment, or complete RDF 1.2
Semantics conformance. In proof mode, ``datatypes`` remains reserved and any
supplied value still raises explicitly rather than being ignored.
The rules are monotonic and optional; no Graph methods or inputs are mutated.

Inputs must be finite RDF graphs (Graph or iterable of triples). Space is
proportional to the materialized input/closure; closure uses repeated joins,
and existential matching can take exponential time. Excessive nesting/search
depth raises EntailmentResourceLimit (an UnsupportedEntailment subclass)
instead of returning a negative result. Optional max_steps limits internal
validation, term traversal, matching and rule-join work. It is not a wall-clock
or memory bound; input iteration itself can block and individual terms can be
large. The default None leaves the work budget unlimited.
This module is a partial facility, not a full RDF 1.2 conformance claim.
"""

from __future__ import annotations

from collections.abc import Iterable
from collections import defaultdict
from contextlib import contextmanager
from contextvars import ContextVar
import re

from .dataset import ConjunctiveGraph, Dataset
from .namespace import RDF, RDFS
from .term import BNode, Literal, TripleTerm, URIRef

__all__ = ["UnsupportedEntailment", "EntailmentResourceLimit", "entails", "entailment_closure"]

Term = URIRef | BNode | Literal | TripleTerm
Triple = tuple[Term, Term, Term]
_XSD_STRING = URIRef("http://www.w3.org/2001/XMLSchema#string")


class UnsupportedEntailment(NotImplementedError):
    """The requested entailment cannot be decided by this partial facility."""


class EntailmentResourceLimit(UnsupportedEntailment):
    """Evaluation exhausted its work budget or Python recursion depth."""


_budget: ContextVar[list[int] | None] = ContextVar('entailment_budget', default=None)
_recognized: ContextVar[frozenset[URIRef] | None] = ContextVar('entailment_datatypes', default=None)


def _step() -> None:
    remaining = _budget.get()
    if remaining is not None:
        if remaining[0] == 0:
            raise EntailmentResourceLimit('entailment max_steps exceeded')
        remaining[0] -= 1


@contextmanager
def _limited(max_steps):
    if max_steps is not None:
        if type(max_steps) is not int:
            raise TypeError('max_steps must be an integer or None')
        if max_steps < 0:
            raise ValueError('max_steps must be non-negative')
    token = _budget.set(None if max_steps is None else [max_steps])
    try:
        yield
    except RecursionError as exc:
        raise EntailmentResourceLimit('entailment nesting/search limit exceeded') from exc
    finally:
        _budget.reset(token)


def _options(regime: str, datatypes: object) -> None:
    if regime not in ("simple", "rdf", "rdfs"):
        raise ValueError("regime must be 'simple', 'rdf', or 'rdfs'")
    if datatypes is not None:
        raise UnsupportedEntailment("custom datatype recognition is not implemented")


def _validate(triple: object) -> Triple:
    _step()
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
    _step()
    if isinstance(term, TripleTerm):
        return (TripleTerm, *(_key(component) for component in term))
    if isinstance(term, Literal):
        recognized = _recognized.get()
        if recognized is not None and _literal_datatype(term) in recognized:
            return ('datatype-value', _value(term))
        return (Literal, str(term), term.datatype or _XSD_STRING,
                (term.language or "").lower(), term.direction)
    return type(term), str(term)


def _literal_datatype(term: Literal) -> URIRef:
    if term.direction:
        return RDF.dirLangString
    if term.language:
        return RDF.langString
    return term.datatype or _XSD_STRING


def _value(literal: Literal):
    from .datatypes import datatype_value, DatatypeResourceLimit, UnsupportedDatatype
    try:
        return datatype_value(literal)
    except DatatypeResourceLimit as exc:
        raise EntailmentResourceLimit(str(exc)) from exc
    except UnsupportedDatatype as exc:
        raise UnsupportedEntailment(str(exc)) from exc


def _recognition(regime, datatypes) -> frozenset[URIRef]:
    from .datatypes import SUPPORTED_DATATYPES
    if isinstance(datatypes, str):
        raise TypeError('datatypes must be an iterable of URIRef terms or None')
    result = set()
    for datatype in (() if datatypes is None else datatypes):
        _step()
        if not isinstance(datatype, URIRef):
            raise TypeError('recognized datatype must be a URIRef')
        if str(datatype) not in SUPPORTED_DATATYPES:
            raise UnsupportedEntailment(f'unsupported recognized datatype: {datatype}')
        result.add(datatype)
    if regime != 'simple':
        result.update((_XSD_STRING, RDF.langString, RDF.dirLangString))
    return frozenset(result)


def _ill_typed(graph, recognized) -> bool:
    from .datatypes import InvalidLexicalForm
    for triple in graph:
        for root in triple:
            for term in _terms(root):
                if isinstance(term, Literal) and _literal_datatype(term) in recognized:
                    try:
                        _value(term)
                    except InvalidLexicalForm:
                        return True
    return False


def _literal_syntax(graph) -> None:
    """Invalid RDF input is not a D-inconsistency (Concepts §3.3)."""
    from ._language import well_formed_language_tag
    for triple in graph:
        for root in triple:
            for term in _terms(root):
                if not isinstance(term, Literal):
                    continue
                if any(0xD800 <= ord(char) <= 0xDFFF for char in str(term)):
                    raise TypeError('RDF literal strings must contain Unicode scalar values')
                if term.language and not well_formed_language_tag(term.language):
                    raise TypeError('RDF literal language tag must be BCP47 well-formed')
                if (term.datatype == RDF.langString and not term.language
                        or term.datatype == RDF.dirLangString and not (term.language and term.direction)):
                    raise TypeError('RDF language literal is missing language/direction components')


def _ordinary_ground(graph, regime) -> bool:
    """Certificate for a deliberately small countermodel fragment.

    Give ordinary IRIs distinct fresh nonliteral resources, recognized literal
    objects their fixed values, opaque literals fresh resources, and each
    ordinary predicate exactly its asserted pairs. Extend with the RDF(S)
    vocabulary, mandatory datatype value spaces and axioms. No input refers
    to those fixed resources, so a missing ordinary edge remains false.
    RDF additionally permits type/Property: its only applicable condition is
    property typing, which _closure already implements. RDFS does not get
    this exception (class/schema interactions require a stronger certificate).
    """
    allowed = {RDF.type, RDF.Property} if regime == 'rdf' else set()
    namespaces = (str(RDF), str(RDFS), 'http://www.w3.org/2001/XMLSchema#')
    for triple in graph:
        for term in triple:
            _step()
            if isinstance(term, Literal):
                continue
            if not isinstance(term, URIRef):
                return False
            if str(term).startswith(namespaces) and term not in allowed:
                return False
    return True


def _simple_value_fragment(graph, recognized) -> bool:
    # Quotient recognized literal values, then use a free triple-term algebra.
    # Datatype IRIs themselves denote fixed datatypes, not freely chosen names.
    for triple in graph:
        for root in triple:
            for term in _terms(root):
                if isinstance(term, URIRef) and term in recognized:
                    return False
    return True


def _decide(source, target, regime, recognized) -> bool:
    if _ill_typed(source, recognized):
        return True  # Includes the explicit False conclusion: ex falso.
    if regime != 'simple':
        from ._datatype_reasoning import evaluate
        from .datatypes import DatatypeResourceLimit, UnsupportedDatatype
        try:
            result = evaluate(source, target, regime, recognized)
            if result is None:
                from ._schema_reasoning import evaluate as evaluate_schema
                result = evaluate_schema(source, target, regime, recognized)
        except DatatypeResourceLimit as exc:
            raise EntailmentResourceLimit(str(exc)) from exc
        except UnsupportedDatatype as exc:
            raise UnsupportedEntailment(str(exc)) from exc
        if result is not None:
            return result
    consistent = regime == 'simple' or _ordinary_ground(source, regime)
    if target is None:
        if consistent:
            return False
        raise UnsupportedEntailment('premise consistency is not decided for this RDF/RDFS fragment')
    if _ill_typed(target, recognized):
        if consistent:
            return False
        raise UnsupportedEntailment('ill-typed conclusion but premise consistency is unknown')
    seed = source.copy()
    if regime != 'simple':
        for triple in source:
            for root in triple:
                for term in _terms(root):
                    if isinstance(term, Literal) and _literal_datatype(term) in recognized:
                        seed.add((term, RDF.type, _literal_datatype(term)))
    if _homomorphism(_closure(seed, regime, target), target):
        return True
    if regime == 'simple':
        if not recognized or (_simple_value_fragment(source, recognized)
                              and _simple_value_fragment(target, recognized)):
            return False
    elif consistent and _ordinary_ground(target, regime):
        return False
    raise UnsupportedEntailment('no proof or countermodel certificate for this entailment fragment')


def _match(pattern: Term, value: Term, bindings: dict) -> bool:
    _step()
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
        _step()
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
    _step()
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
            _step()
            by_predicate[b].append((a, b, c))
            by_subject_predicate[(a, b)].append(c)
            by_predicate_object[(b, c)].append(a)
        for s, p, o in result:
            _step()
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
                    _step()
                    if p == RDFS.domain:
                        additions.add((a, RDF.type, o))
                    elif p == RDFS.range:
                        additions.add((c, RDF.type, o))
                    else:
                        additions.add((a, o, c))
            if p in (RDFS.subPropertyOf, RDFS.subClassOf):
                for c in by_subject_predicate.get((o, p), ()):
                    _step()
                    additions.add((s, p, c))
            if p == RDFS.subClassOf:
                for a in by_predicate_object.get((RDF.type, s), ()):
                    _step()
                    additions.add((a, RDF.type, o))
        additions.difference_update(result)
        if not additions:
            return result
        result.update(additions)


def entailment_closure(
    graph: Iterable[Triple], *, regime: str = "rdfs", datatypes: object = None,
    max_steps: int | None = None,
) -> frozenset[Triple]:
    """Return a finite, sound but incomplete rule closure, including input.

    The immutable result may contain generalized triples (literal/triple-term
    subjects or blank-node predicates), unsuitable for ``Graph.add``. Absence
    from this partial closure does NOT establish non-entailment. No datatype
    recognition or full axiomatic closure is performed.

    ``max_steps`` is an optional non-negative internal work budget, not a
    time/memory limit. Exhaustion raises EntailmentResourceLimit.
    """
    _options(regime, datatypes)
    with _limited(max_steps):
        return frozenset(_closure(_snapshot(graph), regime))


def entails(
    premise: Iterable[Triple], conclusion: Iterable[Triple] | bool, *,
    regime: str = "simple", datatypes: object = None,
    max_steps: int | None = None,
    mode: str = 'proof',
) -> bool:
    """Decide simple entailment, or prove a supported RDF/RDFS entailment.

    Default proof mode RDF/RDFS return only True or raise
    UnsupportedEntailment; a failed proof is unknown, not False.
    Blank nodes in conclusion are existential and have
    an independent scope from premise, even when their labels coincide.
    Invalid RDF input raises TypeError; unknown regimes raise ValueError.
    ``max_steps`` limits internal work, not time or memory. Exhaustion raises
    EntailmentResourceLimit, never False. None preserves unlimited work.

    Explicit mode='decide' supports datatype value matching, recognized
    ill-typed premise inconsistency and countermodel-certified negatives in
    the module's documented fragments. datatypes is an iterable of URIRef;
    None/empty means no additional recognized types (RDF/RDFS add mandatory
    types). Unknown requested types raise UnsupportedEntailment; unrecognized
    literal types remain opaque. conclusion=False asks about inconsistency,
    not the empty graph. Outside supported fragments the result is unknown,
    never an assumed False. This is not a complete RDF/RDFS decision mode.
    Supported value-space constraints include incompatible types and datatype
    ranges/domains; see the module's datatype-schema fragment and assignment
    limits. An empty property extension does not assert subPropertyOf.
    Malformed RDF literal components raise TypeError in decision mode, not an
    inconsistency verdict. Constructors and the legacy proof path are unchanged.
    """
    if mode not in ('proof', 'decide'):
        raise ValueError("mode must be 'proof' or 'decide'")
    _options(regime, datatypes if mode == 'proof' else None)
    with _limited(max_steps):
        if mode == 'decide':
            recognized = _recognition(regime, datatypes)
            source = _snapshot(premise)
            target = None if conclusion is False else _snapshot(conclusion)
            _literal_syntax(source)
            if target is not None:
                _literal_syntax(target)
            token = _recognized.set(recognized)
            try:
                return _decide(source, target, regime, recognized)
            finally:
                _recognized.reset(token)
        source, target = _snapshot(premise), _snapshot(conclusion)
        if _homomorphism(_closure(source, regime, target), target):
            return True
        if regime == "simple":
            return False
    raise UnsupportedEntailment(
        f"{regime} proof not found: datatype, axiomatic, proposition and "
        "inconsistency reasoning are incomplete; non-entailment is unknown"
    )
