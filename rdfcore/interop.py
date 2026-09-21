"""Explicit RDF 1.2 interoperability transformations."""

from __future__ import annotations

import re

from .namespace import RDF
from .term import BNode, Literal, TripleTerm, URIRef

I18N_BASE = "https://www.w3.org/ns/i18n#"
_I18N = re.compile(r"^https://www\.w3\.org/ns/i18n#([a-z0-9]+(?:-[a-z0-9]+)*)_(ltr|rtl)$")


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
    mapping = {}
    quads = list(value.quads()) if is_dataset else [(*triple, None) for triple in value]
    occupied = {
        term for quad in quads for term in quad[:3] if isinstance(term, BNode)
    }
    if any(
        isinstance(subject, BNode)
        and predicate == RDF.type
        and obj == RDF.PropositionForm
        for subject, predicate, obj, _graph in quads
    ) and any(isinstance(term, TripleTerm) for quad in quads for term in quad[:3]):
        raise ValueError("cannot basic-encode data containing existing PropositionForm nodes")
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
    quads = list(value.quads()) if is_dataset else [(*triple, None) for triple in value]
    forms = _proposition_forms(quads)
    for subject, predicate, obj, graph in quads:
        if _is_form_triple(subject, predicate, obj, forms, graph):
            continue
        converted = _decode_term(obj, forms, graph)
        _add_quad(result, (subject, predicate, converted, graph))
    return result


def _encode_term(term, mapping, result, graph, occupied):
    if not isinstance(term, TripleTerm):
        return term
    if term in mapping:
        return mapping[term]
    node = BNode()
    while node in occupied:
        node = BNode()
    occupied.add(node)
    mapping[term] = node
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
    forms = {}
    for subject, predicate, obj, graph in quads:
        key = (graph, subject)
        if predicate == RDF.type and obj == RDF.PropositionForm and isinstance(subject, BNode):
            forms.setdefault(key, {})["type"] = True
        elif isinstance(subject, BNode) and predicate in (
            RDF.propositionFormSubject,
            RDF.propositionFormPredicate,
            RDF.propositionFormObject,
        ):
            forms.setdefault(key, {})[predicate] = obj
    complete = {}
    for (graph, node), fields in forms.items():
        if all(key in fields for key in ("type", RDF.propositionFormSubject, RDF.propositionFormPredicate, RDF.propositionFormObject)):
            complete[(graph, node)] = TripleTerm(
                fields[RDF.propositionFormSubject],
                fields[RDF.propositionFormPredicate],
                fields[RDF.propositionFormObject],
            )
    return complete


def _is_form_triple(subject, predicate, obj, forms, graph):
    return isinstance(subject, BNode) and (graph, subject) in forms and (
        predicate == RDF.type and obj == RDF.PropositionForm
        or predicate in (RDF.propositionFormSubject, RDF.propositionFormPredicate, RDF.propositionFormObject)
    )


def _decode_term(term, forms, graph):
    if isinstance(term, BNode) and (graph, term) in forms:
        return _decode_term(forms[(graph, term)], forms, graph)
    if isinstance(term, TripleTerm):
        return TripleTerm(_decode_term(term.subject, forms, graph), _decode_term(term.predicate, forms, graph), _decode_term(term.object, forms, graph))
    return term


def interop_downgrade(value, target_version):
    if target_version == "1.2-basic":
        return basic_encode(value)
    if target_version == "1.1":
        result = basic_encode(value)
        from .dataset import Dataset
        from .graph import Graph
        output = Dataset() if hasattr(result, "quads") else Graph()
        quads = list(result.quads()) if hasattr(result, "quads") else [(*triple, None) for triple in result]
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
