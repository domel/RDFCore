"""Namespace and QName helpers for RDF 1.1."""

from __future__ import annotations

from pathlib import Path
from unicodedata import category
from urllib.parse import urldefrag, urljoin

from .term import URIRef, Variable


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
        self._prefixes: dict[str, URIRef] = {}
        self._namespaces: dict[str, str] = {}
        self._qname_cache: dict[str, tuple[str, URIRef, str]] = {}
        self._bound_namespaces: set[str] = set()

    def bind(self, prefix: str, namespace, override: bool = True, replace: bool = False):
        namespace = str(namespace)
        if prefix is None:
            prefix = ""
        elif " " in prefix:
            raise KeyError("Prefixes may not contain spaces.")
        previous = self._prefixes.get(prefix)
        if previous and str(previous) != namespace:
            if replace:
                self._bind(prefix, namespace, override)
                self._bound_namespaces.add(namespace)
                return
            stem = prefix or "default"
            num = 1
            while True:
                candidate = f"{stem}{num}"
                existing = self._prefixes.get(candidate)
                if existing and str(existing) == namespace:
                    return
                if not existing:
                    break
                num += 1
            self._bind(candidate, namespace, override)
        else:
            bound_prefix = self._namespaces.get(namespace)
            if bound_prefix is None:
                self._bind(prefix, namespace, override)
            elif bound_prefix != prefix and (override or bound_prefix.startswith("_")):
                self._bind(prefix, namespace, override)
        self._bound_namespaces.add(namespace)

    def _bind(self, prefix, namespace, override):
        """Apply the same bidirectional binding rules as RDFLib Memory."""
        bound_namespace = self._prefixes.get(prefix)
        bound_prefix = self._namespaces.get(namespace)
        if bound_prefix is None and bound_namespace is not None:
            bound_prefix = self._namespaces.get(str(bound_namespace))
        if override:
            if bound_prefix is not None:
                del self._prefixes[bound_prefix]
            if bound_namespace is not None:
                del self._namespaces[str(bound_namespace)]
            self._namespaces[namespace] = prefix
            self._prefixes[prefix] = URIRef(namespace)
        else:
            selected_namespace = namespace if bound_namespace is None else str(bound_namespace)
            selected_prefix = prefix if bound_prefix is None else bound_prefix
            self._namespaces[selected_namespace] = selected_prefix
            self._prefixes[selected_prefix] = URIRef(selected_namespace)

    def namespaces(self):
        return iter((prefix, namespace) for prefix, namespace in self._prefixes.items())

    def store(self, namespace: str, prefix: str):
        self.bind(prefix, namespace)

    def qname(self, uri):
        prefix, _, local = self.compute_qname(uri)
        return f"{prefix}:{local}" if prefix else local

    def normalizeUri(self, rdfTerm):
        try:
            namespace, _ = _split_uri(rdfTerm)
        except Exception:
            return f"?{rdfTerm}" if isinstance(rdfTerm, Variable) else f"<{rdfTerm}>"
        if self._namespaces.get(namespace) is None:
            return f"?{rdfTerm}" if isinstance(rdfTerm, Variable) else f"<{rdfTerm}>"
        prefix, _, local = self.compute_qname(rdfTerm)
        return f"{prefix}:{local}"

    def compute_qname(self, uri, generate=True):
        value = uri
        if value in self._qname_cache:
            return self._qname_cache[value]
        if any(char in value for char in '<>" {}|\\^`'):
            raise ValueError(f'"{value}" does not look like a valid URI, cannot serialize this. Did you want to urlencode it?')
        try:
            namespace, local = _split_uri(value)
        except ValueError:
            namespace, local = str(value), ""
            if not self._namespaces.get(namespace):
                raise
        # RDFLib's namespace trie can select a longer previously bound base.
        candidates = [ns for ns in self._bound_namespaces
                      if ns.startswith(namespace) and value.startswith(ns)]
        if candidates:
            namespace = max(candidates, key=len)
            local = value[len(namespace):]
        prefix = self._namespaces.get(namespace)
        if prefix is None:
            if not generate:
                raise KeyError(f"No known prefix for {namespace} and generate=False")
            num = 1
            while self._prefixes.get(f"ns{num}"):
                num += 1
            prefix = f"ns{num}"
            self.bind(prefix, namespace)
        result = prefix, URIRef(namespace), local
        self._qname_cache[value] = result
        return result

    def absolutize(self, uri, defrag=1):
        result = urljoin(Path.cwd().as_uri() + '/', uri, allow_fragments=not defrag)
        if defrag:
            result = urldefrag(result)[0]
        elif uri and uri.endswith('#') and not result.endswith('#'):
            result += '#'
        return URIRef(result)


_NAME_CATEGORIES = frozenset(("Ll", "Lu", "Lo", "Lt", "Nl", "Mc", "Me", "Mn", "Lm", "Nd"))
_SPLIT_START_CATEGORIES = frozenset(("Ll", "Lu", "Lo", "Lt", "Nl", "Nd"))
_ALLOWED_NAME_CHARS = frozenset("··-._%()")


def _split_uri(uri):
    """Split using RDFLib's Unicode QName rules (not strict XML NCNames)."""
    xml = "http://www.w3.org/XML/1998/namespace"
    if uri.startswith(xml):
        return xml, uri.split(xml)[1]
    for index in range(len(uri) - 1, -1, -1):
        char = uri[index]
        if category(char) in _NAME_CATEGORIES or char in _ALLOWED_NAME_CHARS:
            continue
        for start in range(index, len(uri)):
            if category(uri[start]) in _SPLIT_START_CATEGORIES or uri[start] == "_":
                if start == 0:
                    break
                return uri[:start], uri[start:]
        break
    raise ValueError(f"Can't split '{uri}'")


RDF = DefinedNamespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
RDF._TERMS = frozenset({"type", "Property", "subject", "predicate", "object", "Statement", "value", "langString", "dirLangString", "reifies", "PropositionForm", "propositionFormSubject", "propositionFormPredicate", "propositionFormObject", "HTML", "XMLLiteral", "JSON", "first", "rest", "nil"})
RDF._TERMS |= frozenset({'List', 'Alt', 'Bag', 'Seq'})
RDFS = DefinedNamespace("http://www.w3.org/2000/01/rdf-schema#")
RDFS._TERMS = frozenset({"Resource", "Class", "subClassOf", "subPropertyOf", "domain", "range", "label", "comment", "member", "seeAlso", "isDefinedBy", "Literal", "Datatype", "Container", "ContainerMembershipProperty", "Proposition"})
XSD = Namespace("http://www.w3.org/2001/XMLSchema#")
OWL = Namespace("http://www.w3.org/2002/07/owl#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
DC = Namespace("http://purl.org/dc/elements/1.1/")
DCTERMS = Namespace("http://purl.org/dc/terms/")
