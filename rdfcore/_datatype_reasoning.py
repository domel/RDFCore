"""Explicit datatype constraints and finite-value case analysis.

Not a general RDF/RDFS decision procedure. Negative results require the
datatype-schema fragment below and a checked candidate interpretation.
No missing Horn proof is treated as a countermodel by itself.
"""

from collections import defaultdict
from itertools import product

from . import _datatype_spaces as spaces
from .namespace import RDF, RDFS
from .term import BNode, Literal, TripleTerm, URIRef

_MAX_ASSIGNMENTS = 4096


def _fragment(graph, recognized, regime):
    """Guard for extending a finite candidate to an RDF(S) interpretation.

    Unassigned ordinary names/blank-node witnesses get fresh resources.
    Datatype class extensions are fixed value spaces; source subclass links
    between them must be valid space inclusions. Property extensions contain
    the finitely asserted pairs plus required subproperty consequences.
    Disjoint domain/range constraints allow empty properties, not invented
    schema links. Checked assignments fix all required value denotations.
    Infinite datatype typing and the standard vocabulary can then be added
    without new ordinary edges. Targets outside these shapes cannot receive
    a negative certificate from this construction.
    """
    def ordinary(term):
        return (isinstance(term, BNode) or isinstance(term, URIRef)
                and not str(term).startswith((str(RDF), str(RDFS), spaces.XSD)))

    for s, p, o in graph:
        if p == RDF.type:
            if not ordinary(s) or o not in recognized | {RDF.Property}:
                return False
        elif regime == 'rdfs' and p in {RDFS.domain, RDFS.range}:
            if not ordinary(s) or o not in recognized:
                return False
        elif regime == 'rdfs' and p == RDFS.subClassOf:
            if s not in recognized or o not in recognized:
                return False
        elif regime == 'rdfs' and p == RDFS.subPropertyOf:
            if not ordinary(s) or not ordinary(o):
                return False
        elif not (ordinary(s) and isinstance(p, URIRef) and ordinary(p)
                  and (ordinary(o) or isinstance(o, Literal))):
            return False
    return True


def evaluate(source, target, regime, recognized):
    from . import semantics as sem

    # The caller already rejected recognized ill-typed premise literals.
    target_bad = target is not None and sem._ill_typed(target, recognized)
    interner = {}

    def canonical(term, assignments=None, *, conclusion=False):
        if assignments and not (conclusion and isinstance(term, BNode)):
            term = assignments.get(sem._key(term), term)
        if isinstance(term, TripleTerm):
            return TripleTerm(*(canonical(t, assignments, conclusion=conclusion) for t in term))
        if isinstance(term, Literal) and sem._literal_datatype(term) in recognized:
            return interner.setdefault(sem._key(term), term)
        return term

    def mapped(graph, assignments=None, *, conclusion=False):
        return {tuple(canonical(t, assignments, conclusion=conclusion) for t in triple)
                for triple in graph}

    literals = set()
    for graph in (source, () if target_bad or target is None else target):
        for triple in graph:
            for root in triple:
                for term in sem._terms(root):
                    if isinstance(term, Literal) and sem._literal_datatype(term) in recognized:
                        literals.add(canonical(term))
    for datatype in recognized:
        sem._step()
        samples, _ = spaces.witnesses({datatype})
        literals.update(map(canonical, samples))
    # A target-only intersection witness adds universally true type facts,
    # never an asserted ordinary edge from the conclusion.
    target_constraints = defaultdict(set)
    if target is not None and not target_bad:
        for s, p, o in target:
            if isinstance(s, BNode) and p == RDF.type and o in recognized:
                target_constraints[s].add(o)
        for types in target_constraints.values():
            samples, _ = spaces.witnesses(types)
            literals.update(map(canonical, samples))
    axioms = set()
    memberships = {}

    def type_facts(literal):
        if literal not in memberships:
            value = sem._value(literal)
            facts = set()
            for datatype in recognized:
                sem._step()
                if spaces.contains(value, datatype):
                    facts.add((literal, RDF.type, datatype))
            memberships[literal] = facts
        return memberships[literal]

    for literal in literals:
        axioms.update(type_facts(literal))
    if regime == 'rdfs':
        axioms.update((datatype, RDF.type, RDFS.Datatype) for datatype in recognized)
    supers = {datatype: {other for other in recognized if spaces.subset(datatype, other)}
              for datatype in recognized}

    def closure(graph):
        extra = set()
        for triple in graph:
            for root in triple:
                for term in sem._terms(root):
                    if isinstance(term, Literal) and sem._literal_datatype(term) in recognized:
                        extra.update(type_facts(term))
        result = sem._closure(graph | axioms | extra, regime)
        while True:
            implied = set()
            for s, p, o in result:
                sem._step()
                if p == RDF.type and o in supers:
                    implied.update((s, RDF.type, other) for other in supers[o])
            implied.difference_update(result)
            if not implied:
                return mapped(result)
            # Membership implication is not an asserted subClassOf relation.
            result = sem._closure(result | implied, regime)

    initial = closure(mapped(source))

    def constraints(graph):
        result = defaultdict(set)
        for s, p, o in graph:
            sem._step()
            if p == RDF.type and o in recognized:
                result[s].add(o)
        return result

    def contradiction(graph):
        for s, p, o in graph:
            sem._step()
            if (regime == 'rdfs' and p == RDFS.subClassOf and s in recognized
                    and o in recognized and not spaces.subset(s, o)):
                return True
        for node, types in constraints(graph).items():
            if isinstance(node, Literal) and sem._literal_datatype(node) in recognized:
                if any(not spaces.contains(sem._value(node), datatype) for datatype in types):
                    return True
            elif not isinstance(node, TripleTerm):
                samples, _ = spaces.witnesses(types)
                if not samples:
                    return True
        return False

    if contradiction(initial):
        return True
    if target is not None and not target_bad and sem._homomorphism(initial, mapped(target, conclusion=True)):
        return True
    variable_domains = []
    complete = True
    for node, types in constraints(initial).items():
        if isinstance(node, Literal) and sem._literal_datatype(node) in recognized:
            continue
        # Datatype IRIs denote fixed datatypes; propositions need T39's model.
        if (isinstance(node, TripleTerm) or isinstance(node, URIRef)
                and str(node).startswith((str(RDF), str(RDFS), spaces.XSD))):
            return None
        samples, exhaustive = spaces.witnesses(types, enumerate_finite=True)
        if not samples:
            return True
        if not exhaustive:
            samples += spaces.countermodel_witnesses(types, recognized,
                                                       {sem._value(t) for t in literals}, step=sem._step)
        variable_domains.append((sem._key(node), samples))
        complete &= exhaustive
    if variable_domains and any(isinstance(t, TripleTerm)
                                for graph in (source, target or ()) for row in graph for t in row):
        return None
    certified = _fragment(source, recognized, regime)
    target_fragment = target is None or target_bad or _fragment(target, recognized, regime)
    proof_in_every_branch = True
    for number, values in enumerate(product(*(domain for _, domain in variable_domains))):
        sem._step()
        if number >= _MAX_ASSIGNMENTS:
            raise sem.EntailmentResourceLimit(f'datatype assignment limit ({_MAX_ASSIGNMENTS}) exceeded')
        assignments = dict(zip((key for key, _ in variable_domains), values))
        branch = closure(mapped(source, assignments))
        if contradiction(branch):
            continue
        # Aliasing can activate further schema constraints. A branch is not a
        # countermodel until all its required values have actually been fixed.
        fixed = all(isinstance(node, Literal) and sem._literal_datatype(node) in recognized
                    for node in constraints(branch))
        if variable_domains and (not certified or not target_fragment):
            from ._schema_reasoning import evaluate as evaluate_schema
            branch_target = (None if target is None or target_bad
                             else mapped(target, assignments, conclusion=True))
            # Use the schema certificate on a concrete assignment, not on
            # unassigned names. It independently checks newly activated
            # constraints and may return unknown instead of a negative.
            verdict = evaluate_schema(branch, branch_target, regime, recognized)
            if verdict is False:
                return False
            if verdict is True:
                continue
        if target is None or target_bad:
            if certified and fixed:
                return False
            proof_in_every_branch = False
            continue
        target_branch = mapped(target, assignments, conclusion=True)
        proved = sem._homomorphism(branch, target_branch)
        if not proved:
            if certified and fixed and target_fragment:
                return False
            proof_in_every_branch = False
    if complete and proof_in_every_branch:
        return True
    return None
