"""Resource convenience wrapper compatible with RDFLib's Resource API."""

from .namespace import RDF
from .term import BNode, URIRef


class Resource:
    def __init__(self, graph, identifier):
        self._graph = graph
        self._identifier = identifier

    @property
    def graph(self):
        return self._graph

    @property
    def identifier(self):
        return self._identifier

    def __eq__(self, other):
        return isinstance(other, Resource) and self.graph is other.graph and self.identifier == other.identifier

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((id(self.graph), self.identifier))

    def __str__(self):
        return f"Resource({self.identifier})"

    def __repr__(self):
        return f"Resource({self.graph!r},{self.identifier!r})"

    def add(self, predicate, obj):
        self.graph.add((self.identifier, predicate, getattr(obj, "identifier", obj)))

    def remove(self, predicate, obj=None):
        self.graph.remove((self.identifier, predicate, getattr(obj, "identifier", obj)))

    def set(self, predicate, obj):
        self.graph.set((self.identifier, predicate, getattr(obj, "identifier", obj)))

    def subjects(self, predicate=None):
        return (self._cast(item) for item in self.graph.subjects(predicate, self.identifier))

    def predicates(self, obj=None):
        return (self._cast(item) for item in self.graph.predicates(self.identifier, getattr(obj, "identifier", obj)))

    def objects(self, predicate=None):
        return (self._cast(item) for item in self.graph.objects(self.identifier, predicate))

    def subject_predicates(self):
        return ((self._cast(s), self._cast(p)) for s, p in self.graph.subject_predicates(self.identifier))

    def subject_objects(self):
        return ((self._cast(s), self._cast(o)) for s, o in self.graph.subject_objects(self.identifier))

    def predicate_objects(self):
        return ((self._cast(p), self._cast(o)) for p, o in self.graph.predicate_objects(self.identifier))

    def value(self, predicate=RDF.value, obj=None, default=None, any=True):
        return self._cast(self.graph.value(self.identifier, predicate, getattr(obj, "identifier", obj), default, any))

    def items(self):
        return (self._cast(item) for item in self.graph.items(self.identifier))

    def transitive_objects(self, predicate, remember=None):
        return (self._cast(item) for item in self.graph.transitive_objects(self.identifier, predicate, remember))

    def transitive_subjects(self, predicate, remember=None):
        return (self._cast(item) for item in self.graph.transitive_subjects(predicate, self.identifier, remember))

    def qname(self):
        return self.graph.qname(self.identifier)

    def __iter__(self):
        return ((self._cast(subject), self._cast(predicate), self._cast(obj))
                for subject, predicate, obj in self.graph.triples((self.identifier, None, None)))

    def __getitem__(self, item):
        if isinstance(item, slice):
            if item.step is not None:
                raise TypeError("Resources fix the subject for slicing, and can only be sliced by predicate/object.")
            predicate, obj = item.start, item.stop
            predicate = getattr(predicate, "identifier", predicate)
            obj = getattr(obj, "identifier", obj)
            if predicate is None and obj is None:
                return self.predicate_objects()
            if predicate is None:
                return self.predicates(obj)
            if obj is None:
                return self.objects(predicate)
            return (self.identifier, predicate, obj) in self.graph
        if isinstance(item, (URIRef, BNode)):
            return self.objects(item)
        raise TypeError("You can only index a resource by an RDF term or a slice of RDF terms")

    def __setitem__(self, predicate, obj):
        self.set(predicate, obj)

    def _cast(self, value):
        return self.__class__(self.graph, value) if isinstance(value, (URIRef, BNode)) else value


__all__ = ["Resource"]
