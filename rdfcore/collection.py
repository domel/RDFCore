"""RDF collection convenience wrapper compatible with RDFLib."""

from .namespace import RDF
from .term import BNode, Node, TripleTerm


class Collection:
    def __init__(self, graph, uri, seq=[]):
        self.graph = graph
        self.uri = uri or BNode()
        if seq:
            self += seq

    def __iter__(self):
        return self.graph.items(self.uri)

    def __len__(self):
        return len(list(self.graph.items(self.uri)))

    def __getitem__(self, key):
        container = self._get_container(key)
        if not container:
            raise IndexError(key)
        value = self.graph.value(container, RDF.first)
        if not value:
            raise KeyError(key)
        return value

    def __setitem__(self, key, value):
        container = self._get_container(key)
        if not container:
            raise IndexError(key)
        if not isinstance(value, (Node, TripleTerm)):
            # RDFLib removes the existing value before Graph.add rejects it.
            self.graph.remove((container, RDF.first, None))
            assert isinstance(value, (Node, TripleTerm)), "Object %s must be an rdflib term" % (value,)
        self.graph.set((container, RDF.first, value))

    def __delitem__(self, key):
        self[key]
        current = self._get_container(key)
        assert current
        if len(self) == 1 and key > 0:
            pass
        elif key == len(self) - 1:
            previous = self._get_container(key - 1)
            self.graph.set((previous, RDF.rest, RDF.nil))
            self.graph.remove((current, None, None))
        else:
            following = self._get_container(key + 1)
            previous = self._get_container(key - 1)
            assert following and previous
            self.graph.remove((current, None, None))
            self.graph.set((previous, RDF.rest, following))

    def _end(self):
        container = self.uri
        while True:
            rest = self.graph.value(container, RDF.rest)
            if rest is None or rest == RDF.nil:
                return container
            container = rest

    def append(self, item):
        end = self._end()
        if end == RDF.nil:
            raise ValueError("Cannot append to empty list")
        if (end, RDF.first, None) in self.graph:
            node = BNode()
            self.graph.set((end, RDF.rest, node))
            end = node
        assert isinstance(item, (Node, TripleTerm)), "Object %s must be an rdflib term" % (item,)
        self.graph.add((end, RDF.first, item))
        self.graph.add((end, RDF.rest, RDF.nil))
        return self

    def extend(self, values):
        for value in values:
            self.append(value)
        return self

    def __iadd__(self, other):
        end = self._end()
        if end == RDF.nil:
            raise ValueError("Cannot append to empty list")
        self.graph.remove((end, RDF.rest, None))
        for item in other:
            if (end, RDF.first, None) in self.graph:
                node = BNode()
                self.graph.add((end, RDF.rest, node))
                end = node
            assert isinstance(item, (Node, TripleTerm)), "Object %s must be an rdflib term" % (item,)
            self.graph.add((end, RDF.first, item))
        self.graph.add((end, RDF.rest, RDF.nil))
        return self

    def clear(self):
        node = self.uri
        while node:
            rest = self.graph.value(node, RDF.rest)
            self.graph.remove((node, RDF.first, None))
            self.graph.remove((node, RDF.rest, None))
            node = rest
        return self

    def index(self, item):
        node = self.uri
        index = 0
        while True:
            if (node, RDF.first, item) in self.graph:
                return index
            links = list(self.graph.objects(node, RDF.rest))
            index += 1
            if links == [RDF.nil]:
                raise ValueError(f"{item} is not in {self.uri}")
            if not links:
                raise Exception(f"Malformed RDF Collection: {self.uri}")
            assert len(links) == 1, f"Malformed RDF Collection: {self.uri}"
            node = links[0]

    def n3(self):
        return "( %s )" % " ".join(item.n3() for item in self)

    def _nodes(self):
        current = self.uri
        seen = set()
        while current and current != RDF.nil and current not in seen:
            seen.add(current)
            yield current
            current = self.graph.value(current, RDF.rest)

    def _get_container(self, index):
        assert isinstance(index, int)
        current = self.uri
        position = 0
        while position < index:
            position += 1
            current = self.graph.value(current, RDF.rest)
            if current is None:
                break
        return current


__all__ = ["Collection"]
