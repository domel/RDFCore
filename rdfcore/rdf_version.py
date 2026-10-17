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
    if hasattr(graph_or_dataset, "quads"):
        statements = graph_or_dataset.quads()
    else:
        statements = iter(graph_or_dataset)

    required = "1.1"
    for statement in statements:
        for term in statement:
            if isinstance(term, TripleTerm):
                return "1.2"
            if isinstance(term, Literal) and term.direction is not None:
                required = "1.2-basic"
    return required


def version_allows(requested: str, required: str) -> bool:
    validate_rdf_version(requested)
    if required not in RDF_VERSIONS:
        raise ValueError(f"unsupported required RDF version {required!r}")
    if requested == "auto":
        return True
    return RDF_VERSIONS.index(required) <= RDF_VERSIONS.index(requested)
