"""Query-local RDF/RDFS proofs and a guarded free-extension countermodel.

Semantics CRD 2026-09-24 §§5, 8, 9; Schema WD 2026-10-23.
Published documents and linked EDs inspected 2026-10-24. The non-normative
appendix is NOT assumed to prove completeness of arbitrary RDF 1.2 reasoning.

For a negative certificate, ordinary names and source blank nodes denote
distinct resources, apart from recognized literal value identity. The finite
diagram is extended with fresh resources/properties/classes, the three
mandatory infinite datatype spaces, all container properties, and injective
triple denotations. Representatives below record their forced type profiles.
Class/property overlap is allowed. Additional proposition members get fresh
preimages with predicates outside the finite query vocabulary, not invented
assertions or a functional rdf:reifies relation.

Overlapping supported spaces are partitioned by exact datatype membership.
Value assignments and constructor equations are checked by the companion
datatype/alias evaluators. An infinite eligible value region can supply the
constructor image; that model choice is never used as a universal proof.
The guard still rejects unhandled vocabulary links. Constructor queries are
negative-certified only on finite property extensions, not on arbitrary
infinite typing/subclass/subproperty relations. Unsupported diagrams remain
unknown even if a Horn proof is absent. This is not a claim of complete
RDF/RDFS decision support. A separate free-class interpretation also refutes
a restricted recursive constructor query, without forbidding IT cycles in
other interpretations.
"""
from . import _datatype_spaces as spaces
from .namespace import RDF, RDFS, XSD
from .term import BNode, Literal, TripleTerm, URIRef
from .term import _INTEGER_BOUNDS, _INTEGER_DATATYPES

_MANDATORY = frozenset((XSD.string, RDF.langString, RDF.dirLangString))
_SCHEMA = frozenset((RDFS.domain, RDFS.range, RDFS.subClassOf, RDFS.subPropertyOf))
_INFINITE = (RDF.type, RDFS.subClassOf, RDFS.subPropertyOf)


def _separate_spaces(recognized):
    """Disjoint spaces need no additional membership-region partition."""
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


def _schema_guard(model, standard, step, canonical=None, recognized=frozenset()):
    from .semantics import _Vocabulary
    rdf = RDF if canonical is None else _Vocabulary(RDF, canonical)
    rdfs = RDFS if canonical is None else _Vocabulary(RDFS, canonical)
    schema = _SCHEMA if canonical is None else set(map(canonical, _SCHEMA))
    for s, p, o in model:
        step()
        if p not in schema or _ordinary(s) or (s, p, o) in standard:
            continue
        if p == rdfs.subClassOf and o in (s, rdfs.Resource, rdfs.Literal):
            # Reflexivity, the universal superclass, and datatype->Literal.
            if o != rdfs.Literal or (s, rdf.type, rdfs.Datatype) in model:
                continue
        if p == rdfs.subClassOf and o in {
                rdfs.Class, rdf.Property, rdfs.Literal, rdfs.Proposition} and (
                s == rdfs.Resource or (rdfs.Resource, rdfs.subClassOf, o) in model):
            # Lift Resource's cluster together with its added unary role.
            continue
        if p == rdfs.subClassOf and s == rdfs.Proposition and o in recognized:
            # The model phase separately supplies an infinite value region
            # for the constructor image; a finite sample cannot certify this.
            continue
        if p == rdfs.subClassOf and s == rdfs.Proposition and o == rdfs.Literal and any(
                (s, rdfs.subClassOf, d) in model for d in recognized):
            continue
        if p == rdfs.subPropertyOf and (s == o or o == rdfs.member
                and (s, rdf.type, rdfs.ContainerMembershipProperty) in model):
            continue
        if s == rdf.type and p in (rdfs.domain, rdfs.range) and _ordinary(o):
            continue
        if s == rdf.type and p == rdfs.subPropertyOf and _ordinary(o):
            continue
        return False
    return True


def _constructor_proof(proof, query, regime, recognized, fresh, sem):
    """Sound IT-totality witnesses; lack of a witness is still unknown.

    Only already proven properties can be constructor predicates. Correlated
    variables use one mapping from the nonconstructor part of the query.
    No constructed triple is asserted. Interpreted applications admit literal
    and proposition resources without changing public TripleTerm grammar.
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
            value = sem._InterpretedTriple(s, p, o)
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


def _free_class_cycle(source, query, recognized):
    """A free interpretation refutes this recursive subclass query.

    Semantics CRD 2026-09-24 §§5, 9: choose distinct vocabulary resources
    and a free, injective IT whose image excludes those resources. Make all
    resources classes, with Resource and Class universal. Give the other
    vocabulary classes their required extensions. The subclass relation is
    the axiomatic hierarchy, reflexivity and edges to the two universal
    classes. A constructed superclass can therefore only be the subject
    itself. A finite free term cannot equal a term properly containing it.

    This is ONE admissible countermodel, not an occurs check on every RDF
    interpretation: IT cycles remain legal in other models. Restrict the
    premise and datatype map so no extra constraint invalidates this model.
    """
    from .semantics import _step
    if (recognized != _MANDATORY or len(query) != 1
            or not source <= {(RDFS.Resource, RDFS.subClassOf, RDFS.Class)}):
        return False
    node, predicate, term = next(iter(query))
    if not isinstance(node, BNode) or predicate != RDFS.subClassOf:
        return False
    depth = 0
    while isinstance(term, TripleTerm):
        _step()
        if term.subject != node or term.predicate != RDF.type:
            return False
        depth += 1
        term = term.object
    return depth > 0 and term == node


def evaluate(source, target, regime, recognized, *, aliases=None, applications=()):
    from . import semantics as sem

    if (regime == 'rdfs' and target is not None and not aliases and not applications
            and _free_class_cycle(source, target, recognized)):
        return False
    target_bad = target is not None and sem._ill_typed(target, recognized)
    valid_target = () if target_bad or target is None else target
    interner = {}
    vocabulary = source | set(valid_target)
    if aliases:
        vocabulary |= {(name, RDF.type, RDF.Property) for name in aliases}

    def canonical(term):
        if aliases and isinstance(term, URIRef):
            term = aliases.get(term, term)
        if isinstance(term, TripleTerm):
            term = sem._application_value(sem._InterpretedTriple(*(canonical(t) for t in term)))
        if isinstance(term, Literal) and sem._literal_datatype(term) in recognized:
            return interner.setdefault(sem._key(term), term)
        return term

    def mapped(graph):
        return {tuple(canonical(t) for t in row) for row in graph}

    rdf = RDF if not aliases else sem._Vocabulary(RDF, canonical)
    rdfs = RDFS if not aliases else sem._Vocabulary(RDFS, canonical)

    def close(graph):
        return sem._closure(graph, regime, vocabulary, canonical=canonical if aliases else None)

    source, query = mapped(source), mapped(valid_target)
    terms = {t for graph in (source, query) for row in graph for root in row for t in sem._terms(root)}
    terms.update(canonical(t) for value, components in applications for t in (value, *components))
    occupied = set(terms)

    def fresh():
        while True:
            sem._step()
            node = BNode()
            if node not in occupied:
                occupied.add(node)
                return node

    property_witness = fresh()
    proposition_witness = fresh() if regime == 'rdfs' else None
    axioms = {(property_witness, rdf.type, rdf.Property)}
    if regime == 'rdfs':
        axioms.update(((fresh(), rdf.type, rdfs.Class),
                       (fresh(), rdf.type, rdfs.Resource),
                       (proposition_witness, rdf.type, rdfs.Proposition)))
        # One unmentioned member represents the remaining infinite family.
        number = 1
        while rdf['_'+str(number)] in occupied:
            sem._step()
            number += 1
        axioms.add((rdf['_'+str(number)], rdf.type, rdfs.ContainerMembershipProperty))
        axioms.update((datatype, rdf.type, rdfs.Datatype) for datatype in recognized)
        # IRIs always denote resources; target-only opaque literals need not
        # denote in every interpretation and are added only to the model.
        axioms.update((term, rdf.type, rdfs.Resource) for term in terms if isinstance(term, URIRef))

    values = {term for term in terms if isinstance(term, Literal)
              and sem._literal_datatype(term) in recognized}
    regions = ()
    if not _separate_spaces(recognized):
        regions = spaces.membership_regions(recognized, step=sem._step)
        values.update(canonical(sample) for _, sample in regions)
    for datatype in recognized:
        sem._step()
        samples, _ = spaces.witnesses({datatype})
        values.update(map(canonical, samples))
    for value in values:
        for datatype in recognized:
            sem._step()
            if spaces.contains(sem._value(value), datatype):
                axioms.add((value, rdf.type, datatype))
    seed = source | axioms
    for value, components in applications:
        seed.add((canonical(components[1]), rdf.type, rdf.Property))
        if regime == 'rdfs':
            seed.add((canonical(value), rdf.type, rdfs.Proposition))
    for row in source:
        for root in row:
            for term in sem._terms(root):
                if isinstance(term, TripleTerm):
                    seed.add((term.predicate, rdf.type, rdf.Property))
                    if regime == 'rdfs':
                        seed.add((term, rdf.type, rdfs.Proposition))
    proof = close(seed)

    if regime == 'rdfs':
        # IR includes three mandatory infinite spaces and IP is nonempty.
        # Injective IT therefore has an infinite image, even if the graph is
        # finite. This is a cardinality argument, not finite sample coverage.
        for cls in _MANDATORY | {rdfs.Resource, rdfs.Proposition}:
            types = {d for d in recognized if (cls, rdfs.subClassOf, d) in proof}
            if types and _finite_intersection(types):
                return True

    # A known value forced outside its space is a genuine inconsistency.
    # A named resource forced into a space is NOT such a proof: it may alias
    # a literal value. Likewise, propositions are not disjoint from values.
    for node, p, datatype in proof:
        sem._step()
        if p == rdf.type and datatype in recognized and node in recognized:
            return True
        if (p == rdf.type and datatype in recognized and isinstance(node, Literal)
                and sem._literal_datatype(node) in recognized
                and not spaces.contains(sem._value(node), datatype)):
            return True
    if target is not None and not target_bad and sem._homomorphism(proof, query):
        return True
    if regime == 'rdfs' and any(isinstance(o, TripleTerm) and p in _SCHEMA | {rdf.type}
                               for _, p, o in query):
        if _constructor_proof(proof, query, regime, recognized, fresh, sem):
            return True

    # Only a candidate interpretation is allowed to choose particular literal
    # values for propositions. Such a choice must never prove that literal
    # is necessarily a proposition. The image needs an INFINITE eligible
    # region, even if one finite space happens to contain the sample value.
    model_seed = proof
    image_types = {d for d in recognized if (proposition_witness, rdf.type, d) in proof}
    if image_types:
        if _finite_intersection(image_types):
            return True
        regions = regions or spaces.membership_regions(recognized, step=sem._step)
        distinguished = {sem._value(t) for t in terms if isinstance(t, Literal)
                         and sem._literal_datatype(t) in recognized}
        sample = spaces.fresh_image_witness(image_types, recognized, distinguished, step=sem._step)
        if sample is None:
            return None
        selected = canonical(sample)
        model_seed = {tuple(selected if t == proposition_witness else t for t in row) for row in proof}
        model_seed |= {(selected, rdf.type, d) for d in recognized
                       if spaces.contains(sem._value(selected), d)}
        model_seed = close(model_seed)

    standard = close(axioms)
    if not _schema_guard(model_seed, standard, sem._step, canonical if aliases else None, recognized):
        return None
    for profile, _ in regions:
        # A fresh symbol is universally instantiable with any member of this
        # nonempty region. Check the entire profile, not just a sample value.
        marker = fresh()
        virtual = close(proof | {(marker, rdf.type, URIRef(d)) for d in profile})
        if any(s == marker and p == rdf.type and o in recognized and str(o) not in profile
               for s, p, o in virtual):
            return True
        if not _schema_guard(virtual, standard, sem._step, canonical if aliases else None, recognized):
            return None
    for node, p, datatype in model_seed:
        sem._step()
        if p == rdf.type and datatype in recognized:
            if not isinstance(node, Literal) or sem._literal_datatype(node) not in recognized:
                return None
            if not spaces.contains(sem._value(node), datatype):
                return None  # A failed candidate choice is not an inconsistency proof.

    model = model_seed
    if regime == 'rdfs':
        model = close(model_seed | {(t, rdf.type, rdfs.Resource) for t in terms
                               if isinstance(t, Literal)})
        if not _schema_guard(model, standard, sem._step, canonical if aliases else None, recognized):
            return None
        # Opaque target literals can be assigned fresh nonliteral resources,
        # but not assumed to have arbitrary fixed datatype values.
        if any(p == rdf.type and o in recognized and (not isinstance(s, Literal)
               or sem._literal_datatype(s) not in recognized
               or not spaces.contains(sem._value(s), o)) for s, p, o in model):
            return None
    if target is None or target_bad:
        return False
    for _, p, obj in query:
        sem._step()
        if isinstance(obj, TripleTerm) and (p in _SCHEMA or p == rdf.type
                or any((q, rdfs.subPropertyOf, p) in model for q in _INFINITE)):
            return None
    return None if sem._homomorphism(model, query) else False
