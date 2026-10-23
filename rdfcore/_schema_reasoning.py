"""Query-local RDF/RDFS proofs and a guarded free-extension countermodel.

Semantics CRD 2026-09-24 §§5, 8, 9; Schema WD 2026-10-22.
Published documents and linked EDs inspected 2026-10-23. The non-normative
appendix is NOT assumed to prove completeness of arbitrary RDF 1.2 reasoning.

For a negative certificate, ordinary names and source blank nodes denote
distinct resources, apart from recognized literal value identity. The finite
diagram is extended with fresh resources/properties/classes, the three
mandatory infinite datatype spaces, all container properties, and injective
triple denotations. Representatives below record their forced type profiles.
Class/property overlap is allowed. Additional proposition members get fresh
preimages with predicates outside the finite query vocabulary, not invented
assertions or a functional rdf:reifies relation.

The guard rejects new fixed-vocabulary schema links (except ordinary domains
and ranges of rdf:type), forced named/constructor datatype values and
overlapping recognized datatype spaces. Finite datatype assignments belong to T38. Constructor
queries are negative-certified only on finite property extensions, never on
the infinite typing/subclass/subproperty relations. Unsupported diagrams
remain unknown even if a Horn proof is absent. These restrictions are part
of the certificate, NOT a claim of complete RDF/RDFS decision support.
"""
from . import _datatype_spaces as spaces
from .namespace import RDF, RDFS, XSD
from .term import BNode, Literal, TripleTerm, URIRef
from .term import _INTEGER_BOUNDS, _INTEGER_DATATYPES

_MANDATORY = frozenset((XSD.string, RDF.langString, RDF.dirLangString))
_SCHEMA = frozenset((RDFS.domain, RDFS.range, RDFS.subClassOf, RDFS.subPropertyOf))
_INFINITE = (RDF.type, RDFS.subClassOf, RDFS.subPropertyOf)


def _separate_spaces(recognized):
    """The representative model supports disjoint value families only.

    Overlapping numeric facets, strings and JSON still use T38's guarded
    assignments. Merely finding a witness for an intersection is insufficient.
    """
    types = list(recognized)
    return all(not spaces.families(a) & spaces.families(b)
               for i, a in enumerate(types) for b in types[i+1:])


def _finite_intersection(types):
    common = set.intersection(*(spaces.families(t) for t in types))
    if not common or common <= {'boolean', 'float', 'double', 'temporal-gMonth',
                                 'temporal-gDay', 'temporal-gMonthDay'}:
        return True
    if common == {'numeric'}:
        bounds = [_INTEGER_BOUNDS.get(str(t), (None, None)) for t in types
                  if str(t) in _INTEGER_DATATYPES]
        return any(lo is not None for lo, _ in bounds) and any(hi is not None for _, hi in bounds)
    return {XSD.yearMonthDuration, XSD.dayTimeDuration} <= types


def _ordinary(term):
    return isinstance(term, BNode) or isinstance(term, URIRef) and not str(term).startswith(
        (str(RDF), str(RDFS), str(XSD)))


def _schema_guard(model, standard, step):
    for s, p, o in model:
        step()
        if p not in _SCHEMA or _ordinary(s) or (s, p, o) in standard:
            continue
        if p == RDFS.subClassOf and o in (s, RDFS.Resource, RDFS.Literal):
            # Reflexivity, the universal superclass, and datatype->Literal.
            if o != RDFS.Literal or (s, RDF.type, RDFS.Datatype) in model:
                continue
        if p == RDFS.subPropertyOf and (s == o or o == RDFS.member
                and (s, RDF.type, RDFS.ContainerMembershipProperty) in model):
            continue
        if s == RDF.type and p in (RDFS.domain, RDFS.range) and _ordinary(o):
            continue
        return False
    return True


def _constructor_proof(proof, query, regime, recognized, fresh, sem):
    """Sound IT-totality witnesses; lack of a witness is still unknown.

    Only already proven properties can be constructor predicates. Correlated
    variables use one mapping from the nonconstructor part of the query.
    No constructed triple is asserted. Public TripleTerm cannot represent
    literal/proposition subjects after substitution; those cases are skipped,
    not treated as negative entailments.
    """
    patterns = [row for row in query if not any(isinstance(t, TripleTerm) for t in row)]
    choices = [(row, [candidate for candidate in proof if all(sem._match(p, v, {})
                for p, v in zip(row, candidate))]) for row in patterns]
    choices.sort(key=lambda pair: len(pair[1]))
    lookup = {sem._key(t): t for row in proof for root in row for t in sem._terms(root)}
    properties = {s for s, p, o in proof if p == RDF.type and o == RDF.Property}
    known = set(lookup)

    def bindings(index, current):
        sem._step()
        if index == len(choices):
            yield current
            return
        row, candidates = choices[index]
        for candidate in candidates:
            extended = current.copy()
            if all(sem._match(p, v, extended) for p, v in zip(row, candidate)):
                yield from bindings(index+1, extended)

    for number, bound in enumerate(bindings(0, {})):
        sem._step()
        if number >= 4096:
            raise sem.EntailmentResourceLimit('constructor witness assignment limit (4096) exceeded')
        variables = {node: lookup[key] for node, key in bound.items()}
        additions = set()

        def instantiate(term):
            if isinstance(term, BNode):
                if term not in variables:
                    variables[term] = fresh()
                return variables[term]
            if isinstance(term, Literal):
                if sem._literal_datatype(term) not in recognized and sem._key(term) not in known:
                    raise ValueError('an opaque query literal need not denote')
            if not isinstance(term, TripleTerm):
                return term
            if term.predicate not in properties:
                raise ValueError('constructor predicate is not known to be a property')
            s, p, o = (instantiate(t) for t in term)
            if not isinstance(s, (URIRef, BNode)):
                raise ValueError('generalized constructor subject requires a separate representation')
            value = TripleTerm(s, p, o)
            additions.add((value, RDF.type, RDFS.Proposition))
            return value

        for row in query:
            for term in row:
                if isinstance(term, TripleTerm):
                    try:
                        instantiate(term)
                    except ValueError:
                        pass
        if additions and sem._homomorphism(sem._closure(proof | additions, regime, query), query):
            return True
    return False


def evaluate(source, target, regime, recognized):
    from . import semantics as sem

    target_bad = target is not None and sem._ill_typed(target, recognized)
    valid_target = () if target_bad or target is None else target
    interner = {}

    def canonical(term):
        if isinstance(term, TripleTerm):
            return TripleTerm(*(canonical(t) for t in term))
        if isinstance(term, Literal) and sem._literal_datatype(term) in recognized:
            return interner.setdefault(sem._key(term), term)
        return term

    def mapped(graph):
        return {tuple(canonical(t) for t in row) for row in graph}

    source, query = mapped(source), mapped(valid_target)
    terms = {t for graph in (source, query) for row in graph for root in row for t in sem._terms(root)}
    occupied = set(terms)

    def fresh():
        while True:
            sem._step()
            node = BNode()
            if node not in occupied:
                occupied.add(node)
                return node

    axioms = {(fresh(), RDF.type, RDF.Property)}
    if regime == 'rdfs':
        axioms.update(((fresh(), RDF.type, RDFS.Class),
                       (fresh(), RDF.type, RDFS.Resource),
                       (fresh(), RDF.type, RDFS.Proposition)))
        # One unmentioned member represents the remaining infinite family.
        number = 1
        while RDF['_'+str(number)] in occupied:
            sem._step()
            number += 1
        axioms.add((RDF['_'+str(number)], RDF.type, RDFS.ContainerMembershipProperty))
        axioms.update((datatype, RDF.type, RDFS.Datatype) for datatype in recognized)
        # IRIs always denote resources; target-only opaque literals need not
        # denote in every interpretation and are added only to the model.
        axioms.update((term, RDF.type, RDFS.Resource) for term in terms if isinstance(term, URIRef))

    values = {term for term in terms if isinstance(term, Literal)
              and sem._literal_datatype(term) in recognized}
    for datatype in recognized:
        sem._step()
        samples, _ = spaces.witnesses({datatype})
        values.update(map(canonical, samples))
    for value in values:
        for datatype in recognized:
            sem._step()
            if spaces.contains(sem._value(value), datatype):
                axioms.add((value, RDF.type, datatype))
    seed = source | axioms
    for row in source:
        for root in row:
            for term in sem._terms(root):
                if isinstance(term, TripleTerm):
                    seed.add((term.predicate, RDF.type, RDF.Property))
                    if regime == 'rdfs':
                        seed.add((term, RDF.type, RDFS.Proposition))
    proof = sem._closure(seed, regime, query)

    if regime == 'rdfs':
        # IR includes three mandatory infinite spaces and IP is nonempty.
        # Injective IT therefore has an infinite image, even if the graph is
        # finite. This is a cardinality argument, not finite sample coverage.
        for cls in _MANDATORY | {RDFS.Resource, RDFS.Proposition}:
            types = {d for d in recognized if (cls, RDFS.subClassOf, d) in proof}
            if types and _finite_intersection(types):
                return True

    # A known value forced outside its space is a genuine inconsistency.
    # A named resource forced into a space is NOT such a proof: it may alias
    # a literal value. Likewise, propositions are not disjoint from values.
    for node, p, datatype in proof:
        sem._step()
        if (p == RDF.type and datatype in recognized and isinstance(node, Literal)
                and sem._literal_datatype(node) in recognized
                and not spaces.contains(sem._value(node), datatype)):
            return True
    if target is not None and not target_bad and sem._homomorphism(proof, query):
        return True
    if regime == 'rdfs' and any(isinstance(o, TripleTerm) and p in _SCHEMA | {RDF.type}
                               for _, p, o in query):
        if _constructor_proof(proof, query, regime, recognized, fresh, sem):
            return True

    if not _separate_spaces(recognized):
        return None
    standard = sem._closure(axioms, regime, query)
    if not _schema_guard(proof, standard, sem._step):
        return None
    for node, p, datatype in proof:
        sem._step()
        if p == RDF.type and datatype in recognized:
            if not isinstance(node, Literal) or sem._literal_datatype(node) not in recognized:
                return None

    model = proof
    if regime == 'rdfs':
        model = sem._closure(proof | {(t, RDF.type, RDFS.Resource) for t in terms
                                     if isinstance(t, Literal)}, regime, query)
        if not _schema_guard(model, standard, sem._step):
            return None
        # Opaque target literals can be assigned fresh nonliteral resources,
        # but not assumed to have arbitrary fixed datatype values.
        if any(p == RDF.type and o in recognized and (not isinstance(s, Literal)
               or sem._literal_datatype(s) not in recognized) for s, p, o in model):
            return None
    if target is None or target_bad:
        return False
    for _, p, obj in query:
        sem._step()
        if isinstance(obj, TripleTerm) and (p in _SCHEMA or p == RDF.type
                or any((q, RDFS.subPropertyOf, p) in model for q in _INFINITE)):
            return None
    return None if sem._homomorphism(model, query) else False
