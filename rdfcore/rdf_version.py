"""RDF 1.2 model version classification helpers."""

from __future__ import annotations

from .term import Literal, TripleTerm

RDF_VERSIONS = ("1.1", "1.2-basic", "1.2")


def validate_rdf_version(value: str) -> str:
    if value not in ("auto", *RDF_VERSIONS):
        raise ValueError(f"unsupported rdf_version {value!r}")
    return value


def required_rdf_version(graph_or_dataset) -> str:
    """Return the least RDF version capable of representing the data."""
    terms = []
    if hasattr(graph_or_dataset, "quads"):
        terms.extend(term for quad in graph_or_dataset.quads() for term in quad)
    else:
        terms.extend(term for triple in graph_or_dataset for term in triple)

    def visit(term):
        if isinstance(term, TripleTerm):
            yield "1.2"
            for component in term:
                yield from visit(component)
        elif isinstance(term, Literal) and term.direction is not None:
            yield "1.2-basic"

    required = "1.1"
    for term in terms:
        for version in visit(term):
            if version == "1.2":
                return version
            required = version
    return required


def version_allows(requested: str, required: str) -> bool:
    validate_rdf_version(requested)
    if required not in RDF_VERSIONS:
        raise ValueError(f"unsupported required RDF version {required!r}")
    if requested == "auto":
        return True
    return RDF_VERSIONS.index(required) <= RDF_VERSIONS.index(requested)
