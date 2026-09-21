"""Namespace and QName helpers for RDF 1.1."""

from __future__ import annotations

from .term import URIRef


class Namespace(str):
    def __new__(cls, name: str = "", *args, **kwargs):
        return str.__new__(cls, name)

    def __init__(self, name: str):
        self._NS = str(name)

    def __str__(self):
        return self._NS

    def __repr__(self):
        return f"Namespace({self._NS!r})"

    def __getitem__(self, local):
        return URIRef(self._NS + str(local))

    def __getattr__(self, local):
        if local.startswith("_"):
            raise AttributeError(local)
        return self[local]

    def term(self, local):
        return self[local]


class DefinedNamespace(Namespace):
    _NS = ""
    _TERMS = frozenset()

    def __init__(self, name: str | None = None):
        super().__init__(name if name is not None else self._NS)

    def __getattr__(self, local):
        if local in self._TERMS:
            return self[local]
        raise AttributeError(local)


class ClosedNamespace(Namespace):
    def __init__(self, uri: str, terms=()):
        super().__init__(uri)
        self._terms = frozenset(terms)

    def __getitem__(self, local):
        if str(local) not in self._terms:
            raise KeyError(local)
        return super().__getitem__(local)

    def __getattr__(self, local):
        if local.startswith("_"):
            raise AttributeError(local)
        try:
            return self[local]
        except KeyError as error:
            raise AttributeError(local) from error


class NamespaceManager:
    def __init__(self, graph=None):
        self.graph = graph
        self._prefixes: dict[str, Namespace] = {}
        self._namespaces: dict[str, str] = {}

    def bind(self, prefix: str, namespace, override: bool = True, replace: bool = False):
        namespace = str(namespace)
        if not override and prefix in self._prefixes:
            return
        previous = self._prefixes.get(prefix)
        if previous is not None and str(previous) != namespace:
            self._namespaces.pop(str(previous), None)
        if replace:
            self._namespaces = {uri: p for uri, p in self._namespaces.items() if p != prefix}
        self._prefixes[prefix] = Namespace(namespace)
        self._namespaces[namespace] = prefix

    def namespaces(self):
        return iter((prefix, namespace) for prefix, namespace in self._prefixes.items())

    def store(self, namespace: str, prefix: str):
        self.bind(prefix, namespace)

    def qname(self, uri):
        value = str(uri)
        for namespace, prefix in sorted(self._namespaces.items(), key=lambda item: len(item[0]), reverse=True):
            if value.startswith(namespace):
                local = value[len(namespace):]
                if local and _valid_local(local):
                    return f"{prefix}:{local}"
        raise ValueError(f"No namespace binding for {value}")

    def normalizeUri(self, uri):
        try:
            return self.qname(uri)
        except ValueError:
            return f"<{uri}>"

    def compute_qname(self, uri, generate=True):
        value = str(uri)
        try:
            qname = self.qname(value)
            prefix, local = qname.split(":", 1)
            return prefix, str(self._prefixes[prefix]), local
        except ValueError:
            if not generate:
                raise
            base, local = value.rsplit("#", 1) if "#" in value else value.rsplit("/", 1)
            if not _valid_local(local):
                raise ValueError(f"Cannot create a QName for {value}")
            base += "#" if "#" in value else "/"
            prefix = f"ns{len(self._prefixes)}"
            self.bind(prefix, base)
            return prefix, base, local

    def absolutize(self, uri):
        return URIRef(uri)


def _valid_local(local):
    return bool(local) and not any(char.isspace() for char in local) and (local[0].isalpha() or local[0] == "_")


RDF = DefinedNamespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
RDF._TERMS = frozenset({"type", "Property", "subject", "predicate", "object", "Statement", "value", "langString", "dirLangString", "reifies", "PropositionForm", "propositionFormSubject", "propositionFormPredicate", "propositionFormObject", "HTML", "XMLLiteral", "JSON", "first", "rest", "nil"})
RDFS = DefinedNamespace("http://www.w3.org/2000/01/rdf-schema#")
RDFS._TERMS = frozenset({"Resource", "Class", "subClassOf", "subPropertyOf", "domain", "range", "label", "comment", "member", "seeAlso", "isDefinedBy", "Literal", "Datatype", "Container", "ContainerMembershipProperty", "Proposition"})
XSD = Namespace("http://www.w3.org/2001/XMLSchema#")
OWL = Namespace("http://www.w3.org/2002/07/owl#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
DC = Namespace("http://purl.org/dc/elements/1.1/")
DCTERMS = Namespace("http://purl.org/dc/terms/")
