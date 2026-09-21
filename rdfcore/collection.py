"""RDF collection convenience wrapper compatible with RDFLib."""

from .namespace import RDF
from .term import BNode


class Collection:
    def __init__(self, graph, uri=None, seq=None):
        self.graph = graph
        self.uri = uri or BNode()
        if seq:
            self.extend(seq)

    def __iter__(self):
        return self.graph.items(self.uri)

    def __len__(self):
        return sum(1 for _ in self)

    def __getitem__(self, index):
        if not isinstance(index, int):
            raise TypeError("collection indices must be integers")
        container = self._get_container(index)
        if container is None:
            raise IndexError(index)
        value = self.graph.value(container, RDF.first)
        if value is None:
            raise KeyError(index)
        return value

    def __setitem__(self, index, value):
        container = self._get_container(index)
        if container is None:
            raise IndexError(index)
        self.graph.set((container, RDF.first, value))

    def __delitem__(self, index):
        self[index]
        container = self._get_container(index)
        if index == 0:
            next_node = self.graph.value(container, RDF.rest)
            if next_node == RDF.nil:
                self.graph.remove((container, None, None))
            else:
                self.graph.set((self.uri, RDF.first, self.graph.value(next_node, RDF.first)))
                self.graph.set((self.uri, RDF.rest, self.graph.value(next_node, RDF.rest)))
                self.graph.remove((next_node, None, None))
            return
        previous = self._get_container(index - 1)
        following = self.graph.value(container, RDF.rest)
        self.graph.set((previous, RDF.rest, following))
        self.graph.remove((container, None, None))

    def append(self, item):
        if self.uri == RDF.nil:
            raise ValueError("cannot modify rdf:nil")
        if self.graph.value(self.uri, RDF.first) is None:
            self.graph.add((self.uri, RDF.first, item))
            self.graph.add((self.uri, RDF.rest, RDF.nil))
            return self
        tail = self._get_container(len(self) - 1)
        node = BNode()
        self.graph.set((tail, RDF.rest, node))
        self.graph.add((node, RDF.first, item))
        self.graph.add((node, RDF.rest, RDF.nil))
        return self

    def extend(self, values):
        for value in values:
            self.append(value)
        return self

    def __iadd__(self, values):
        return self.extend(values)

    def clear(self):
        for node in list(self._nodes()):
            self.graph.remove((node, None, None))
        return self

    def index(self, item):
        for index, value in enumerate(self):
            if value == item:
                return index
        raise ValueError(f"{item} is not in {self.uri}")

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
        if index < 0:
            index += len(self)
        if index < 0:
            return None
        current = self.uri
        for _ in range(index):
            current = self.graph.value(current, RDF.rest)
            if current is None or current == RDF.nil:
                return None
        return current if current != RDF.nil else None


__all__ = ["Collection"]
