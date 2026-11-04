"""Explicit transformations following Interop DNOTE 2026-07-23 §§3.1–3.3.

This informative Note's Full/Basic mapping preserves information on its
supported input domain, not RDF entailment. Directional i18n mapping to 1.1
is a separate RDFCore extension. ED reviewed 2026-11-04.
"""

from __future__ import annotations

import re

from .namespace import RDF
from .term import BNode, Literal, TripleTerm, URIRef

I18N_BASE = "https://www.w3.org/ns/i18n#"
_I18N = re.compile(r"^https://www\.w3\.org/ns/i18n#([a-z0-9]+(?:-[a-z0-9]+)*)_(ltr|rtl)$")


def _copy_graph_names(source, result):
    if hasattr(source, 'quads'):
        for identifier in source.store.contexts():
            if identifier != source.default_graph.identifier:
                if identifier == result.default_graph.identifier:
                    raise ValueError('named graph collides with target default graph identifier')
                result.graph(identifier)


def _statements(value):
    if not hasattr(value, 'quads'):
        return [(*triple, None) for triple in value]
    default = value.default_graph.identifier
    return [(*triple, None if context == default else context)
            for context in value.store.contexts()
            for triple, _ in value.store.triples((None, None, None), context)]


def _bnodes(term):
    if isinstance(term, BNode):
        yield term
    elif isinstance(term, TripleTerm):
        for component in term:
            yield from _bnodes(component)


def _check_hybrid(quads):
    if any(isinstance(s, BNode) and p == RDF.type and o == RDF.PropositionForm
           for s, p, o, _ in quads) and any(isinstance(o, TripleTerm) for _, _, o, _ in quads):
        raise ValueError('cannot transform mixed triple terms and existing PropositionForm nodes')


def encode_direction_i18n(literal: Literal) -> Literal:
    if not isinstance(literal, Literal) or literal.direction is None or literal.language is None:
        raise ValueError("expected a directional language literal")
    datatype = URIRef(I18N_BASE + f"{literal.language.lower()}_{literal.direction}")
    return Literal(str(literal), datatype=datatype, normalize=False)


def decode_direction_i18n(literal: Literal) -> Literal:
    if not isinstance(literal, Literal) or literal.datatype is None:
        raise ValueError("expected an i18n directional literal")
    match = _I18N.fullmatch(str(literal.datatype))
    if match is None:
        raise ValueError("literal does not use an RDF i18n direction datatype")
    language, direction = match.groups()
    return Literal(str(literal), lang=language, direction=direction, normalize=False)


def basic_encode(value):
    """Encode RDF 1.2 triple terms as RDF 1.2 Basic proposition forms."""
    from .dataset import Dataset
    from .graph import Graph

    is_dataset = hasattr(value, "quads")
    result = Dataset() if is_dataset else Graph()
    _copy_graph_names(value, result)
    mapping = {}
    quads = _statements(value)
    occupied = {node for quad in quads for term in quad for node in _bnodes(term)}
    if is_dataset:
        occupied.update(node for context in value.store.contexts() for node in _bnodes(context))
    _check_hybrid(quads)
    for quad in quads:
        subject, predicate, obj, graph = quad
        converted = _encode_term(obj, mapping, result, graph, occupied)
        _add_quad(result, (subject, predicate, converted, graph))
    return result


def basic_decode(value):
    from .dataset import Dataset
    from .graph import Graph

    is_dataset = hasattr(value, "quads")
    result = Dataset() if is_dataset else Graph()
    _copy_graph_names(value, result)
    quads = _statements(value)
    _check_hybrid(quads)
    forms = _proposition_forms(quads)
    if is_dataset:
        names = set(value.store.contexts())
        if any(node in names for _, node in forms):
            raise ValueError('proposition form cannot replace a graph name')
    for subject, predicate, obj, graph in quads:
        if _is_form_triple(subject, predicate, obj, forms, graph):
            continue
        if (graph, subject) in forms or (graph, predicate) in forms:
            raise ValueError('proposition form cannot replace an asserted subject or predicate')
        converted = _decode_term(obj, forms, graph)
        _add_quad(result, (subject, predicate, converted, graph))
    return result


def _encode_term(term, mapping, result, graph, occupied):
    if not isinstance(term, TripleTerm):
        return term
    key = (graph, term)
    if key in mapping:
        return mapping[key]
    node = BNode()
    while node in occupied:
        node = BNode()
    occupied.add(node)
    mapping[key] = node
    subject = _encode_term(term.subject, mapping, result, graph, occupied)
    predicate = _encode_term(term.predicate, mapping, result, graph, occupied)
    obj = _encode_term(term.object, mapping, result, graph, occupied)
    _add_quad(result, (node, RDF.type, RDF.PropositionForm, graph))
    _add_quad(result, (node, RDF.propositionFormSubject, subject, graph))
    _add_quad(result, (node, RDF.propositionFormPredicate, predicate, graph))
    _add_quad(result, (node, RDF.propositionFormObject, obj, graph))
    return node


def _add_quad(result, quad):
    subject, predicate, obj, graph = quad
    if graph is None:
        result.add((subject, predicate, obj))
    else:
        result.add((subject, predicate, obj, graph))


def _proposition_forms(quads):
    forms = {(graph, subject): {} for subject, predicate, obj, graph in quads
             if isinstance(subject, BNode) and predicate == RDF.type and obj == RDF.PropositionForm}
    for subject, predicate, obj, graph in quads:
        key = (graph, subject)
        if key in forms and predicate in (
            RDF.propositionFormSubject,
            RDF.propositionFormPredicate,
            RDF.propositionFormObject,
        ):
            fields = forms[key]
            if predicate in fields and fields[predicate] != obj:
                raise ValueError('ambiguous proposition form component')
            fields[predicate] = obj
    fields_order = (RDF.propositionFormSubject, RDF.propositionFormPredicate, RDF.propositionFormObject)
    if any(not all(field in fields for field in fields_order) for fields in forms.values()):
        raise ValueError('incomplete proposition form')
    resolved, active = {}, set()
    for key in forms:
        stack = [(key, False)]
        while stack:
            current, finish = stack.pop()
            if current in resolved:
                continue
            graph, _ = current
            s, p, o = (forms[current][field] for field in fields_order)
            dependency = (graph, o)
            if finish:
                if (graph, s) in forms or (graph, p) in forms:
                    raise ValueError('proposition form cannot replace a triple-term subject or predicate')
                try:
                    resolved[current] = TripleTerm(s, p, resolved.get(dependency, o))
                except (TypeError, ValueError) as exc:
                    raise ValueError('invalid proposition form components') from exc
                active.remove(current)
            else:
                if current in active:
                    raise ValueError('cyclic proposition form')
                active.add(current)
                stack.append((current, True))
                if dependency in forms:
                    stack.append((dependency, False))
    return resolved


def _is_form_triple(subject, predicate, obj, forms, graph):
    return isinstance(subject, BNode) and (graph, subject) in forms and (
        predicate == RDF.type and obj == RDF.PropositionForm
        or predicate in (RDF.propositionFormSubject, RDF.propositionFormPredicate, RDF.propositionFormObject)
    )


def _decode_term(term, forms, graph):
    if isinstance(term, BNode) and (graph, term) in forms:
        return forms[(graph, term)]
    return term


def interop_downgrade(value, target_version):
    if target_version == "1.2-basic":
        return basic_encode(value)
    if target_version == "1.1":
        literals = set()
        def collect(term):
            if isinstance(term, Literal):
                literals.add(term)
            elif isinstance(term, TripleTerm):
                for component in term:
                    collect(component)
        for row in _statements(value):
            for term in row[:3]:
                collect(term)
        for literal in literals:
            if literal.direction and encode_direction_i18n(literal) in literals:
                raise ValueError('directional downgrade collides with an existing i18n literal')
        result = basic_encode(value)
        from .dataset import Dataset
        from .graph import Graph
        output = Dataset() if hasattr(result, "quads") else Graph()
        _copy_graph_names(result, output)
        quads = _statements(result)
        for subject, predicate, obj, graph in quads:
            obj = _encode_directional_term(obj)
            _add_quad(output, (subject, predicate, obj, graph))
        return output
    raise ValueError(f"unsupported downgrade target {target_version!r}")


def _encode_directional_term(term):
    if isinstance(term, Literal) and term.direction:
        return encode_direction_i18n(term)
    if isinstance(term, TripleTerm):
        return TripleTerm(
            _encode_directional_term(term.subject),
            _encode_directional_term(term.predicate),
            _encode_directional_term(term.object),
        )
    return term
