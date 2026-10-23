"""Value assignments without assuming vocabulary names denote distinct objects.

Semantics CRD 2026-09-24 §§7.1, 8, 9. Each branch normalizes both graph
terms AND the semantic vocabulary. Replacing only asserted terms would lose
the meaning of rdf:type when that name denotes a literal value. A branch
is accepted only by the guarded interpretation certificate; an unproved
branch stays unknown. Universal results require exhaustive assignments.
"""
from collections import defaultdict
from itertools import product

from . import _datatype_spaces as spaces
from .namespace import RDF, RDFS
from .term import BNode, Literal, TripleTerm, URIRef


def evaluate(source, target, regime, recognized):
    from . import semantics as sem
    from ._schema_reasoning import evaluate as schema
    from ._term_models import TermModel, ImpossibleModel

    bad_target = target is not None and sem._ill_typed(target, recognized)
    seed = source.copy()
    values = {t for g in (source, () if bad_target else target or ()) for row in g for root in row for t in sem._terms(root)
              if isinstance(t, Literal) and sem._literal_datatype(t) in recognized}
    for row in source:
        for root in row:
            for term in sem._terms(root):
                if isinstance(term, TripleTerm):
                    seed.add((term.predicate, RDF.type, RDF.Property))
    for datatype in recognized:
        sem._step()
        samples, _ = spaces.witnesses({datatype})
        values.update(samples)
    for value in values:
        key = sem._value(value)
        for datatype in recognized:
            sem._step()
            if spaces.contains(key, datatype):
                seed.add((value, RDF.type, datatype))
    if regime == 'rdfs':
        seed.update((d, RDF.type, RDFS.Datatype) for d in recognized)
    initial = sem._closure(seed, regime)
    constraints = defaultdict(set)
    for s, p, o in initial:
        sem._step()
        if p == RDF.type and o in recognized and not (
                isinstance(s, Literal) and sem._literal_datatype(s) in recognized):
            constraints[s].add(o)
    if not any(isinstance(s, TripleTerm) or isinstance(s, URIRef)
               and str(s).startswith((str(RDF), str(RDFS), spaces.XSD))
               for s in constraints):
        return None
    domains, complete = [], True
    occupied = {sem._value(value) for value in values}
    for node, types in constraints.items():
        if node in recognized:
            return None  # A fixed datatype object is not a freely assigned name.
        samples, exhaustive = spaces.witnesses(types, enumerate_finite=True)
        if not samples:
            return True
        if not exhaustive:
            samples += spaces.countermodel_witnesses(types, recognized, occupied, step=sem._step)
        domains.append((node, samples))
        complete &= exhaustive
    # Query existential variables have a separate scope from premise nodes.
    occupied_nodes = {t for g in (source, target or ()) for row in g for root in row for t in sem._terms(root)}
    query_variables = {}

    def rename(term):
        if isinstance(term, BNode):
            if term not in query_variables:
                node = BNode()
                while node in occupied_nodes:
                    sem._step()
                    node = BNode()
                occupied_nodes.add(node)
                query_variables[term] = node
            return query_variables[term]
        if isinstance(term, TripleTerm):
            return sem._InterpretedTriple(*(rename(c) for c in term))
        return term

    query = None if target is None or bad_target else {tuple(rename(t) for t in row) for row in target}
    all_proved = True
    for number, choices in enumerate(product(*(samples for _, samples in domains))):
        sem._step()
        if number >= 4096:
            raise sem.EntailmentResourceLimit('vocabulary value assignment limit (4096) exceeded')
        model = TermModel(initial, recognized)
        for (node, _), value in zip(domains, choices):
            model.assign(node, value)
        try:
            model.finish()
        except ImpossibleModel:
            continue
        with sem._interpreted_applications(model.applications):
            premise = {tuple(model.term(t) for t in row) for row in source}
            conclusion = None if query is None else {tuple(model.term(t) for t in row) for row in query}
            verdict = schema(premise, conclusion, regime, recognized,
                             aliases=model.aliases, applications=model.applications)
        if verdict is False:
            return False
        if verdict is not True:
            all_proved = False
    return True if complete and all_proved else None
