"""RDF 1.1 TriG parser built on the Turtle statement parser."""

from __future__ import annotations

from ...exceptions import BadSyntax
from ...term import BNode, URIRef
from .notation3 import TurtleParser, _StreamingTokens


class TriGParser(TurtleParser):
    def parse(self, source, sink, **kwargs):
        stream = source.getCharacterStream() or source.getByteStream()
        if stream is None:
            raise BadSyntax("TriG source has no readable stream")
        self.sink = sink
        self.base = source.publicID or kwargs.get("base")
        self.prefixes = {}
        self.bnodes = {}
        self.tokens = _StreamingTokens(stream)
        self.index = 0
        self.current_graph = None
        while not self._at_end():
            if self._peek() == "@prefix" or self._peek_lower() == "prefix":
                self._directive_prefix()
            elif self._peek() == "@base" or self._peek_lower() == "base":
                self._directive_base()
            else:
                self._graph_statement()
        return sink

    def _graph_statement(self):
        if self._accept("{"):
            self._block(None)
            return
        if self._accept("["):
            node = BNode()
            if self._peek() == "]" and self._peek(1) == "{":
                self._next()
                self._next()
                self._block(node)
                return
            self._last_subject_is_property_list = True
            if not self._accept("]"):
                self._predicate_objects(node)
                self._expect("]")
            if self._accept("{"):
                raise self._error("blank-node graph labels cannot have properties")
            if self._accept("."):
                return
            self._predicate_objects(node)
            self._expect(".")
            return
        if self._accept("GRAPH"):
            graph = self._subject() if self._peek() == "[" else self._term("graph")
            self._expect("{")
            self._block(graph)
            return
        candidate = self._subject()
        if self._accept("{"):
            if self._last_subject_is_collection:
                raise self._error("graph label cannot be a collection")
            if not isinstance(candidate, (URIRef, BNode)):
                raise self._error("graph label must be an IRI or blank node")
            self._block(candidate)
            return
        self._predicate_objects(candidate)
        self._expect(".")

    def _block(self, graph):
        previous = self.current_graph
        self.current_graph = graph
        while not self._at_end() and self._peek() != "}":
            subject = self._subject()
            if self._accept("."):
                if not self._last_subject_is_property_list and not getattr(self, "_last_subject_was_reifier", False):
                    raise self._error("expected predicate")
                continue
            if self._last_subject_is_property_list and self._peek() == "}":
                continue
            self._predicate_objects(subject)
            if not self._accept(".") and self._peek() != "}":
                raise self._error("expected '.'")
        self._expect("}")
        self.current_graph = previous

    def _add(self, triple):
        self.sink.add(triple if self.current_graph is None else (*triple, self.current_graph))
