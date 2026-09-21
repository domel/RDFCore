"""RDF 1.2 TriG parser module."""

from ...exceptions import BadSyntax
from ...parser import Parser
from .trig import TriGParser
from .turtle12 import Turtle12Parser
from .notation3 import _StreamingTokens


class TriG12Parser(Turtle12Parser):
    rdf_version = "1.2"
    allow_rdf12 = True

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
        self._requested_version = kwargs.get("rdf_version", "auto")
        while not self._at_end():
            if self._peek_lower() == "version" or self._peek() == "@version":
                self._directive_version()
            elif self._peek() == "@prefix" or self._peek_lower() == "prefix":
                self._directive_prefix()
            elif self._peek() == "@base" or self._peek_lower() == "base":
                self._directive_base()
            else:
                TriGParser._graph_statement(self)
        return sink

    _graph_statement = TriGParser._graph_statement
    _block = TriGParser._block
    _add = TriGParser._add


__all__ = ["TriG12Parser"]
