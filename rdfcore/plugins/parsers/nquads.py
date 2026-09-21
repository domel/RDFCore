"""RDF 1.1 N-Quads parser."""

from __future__ import annotations

from ...exceptions import ParserError
from ...parser import Parser
from ...term import BNode, URIRef
from .ntriples import _spaces, _term, _required_spaces


class NQuadsParser(Parser):
    rdf_version = "1.1"
    allow_rdf12 = False

    def parse(self, source, sink, **kwargs):
        stream = source.getCharacterStream() or source.getByteStream()
        if stream is None:
            raise ParserError("N-Quads source has no readable stream")
        bnode_map = {}
        for line_number, raw_line in enumerate(stream, 1):
            try:
                if isinstance(raw_line, bytes):
                    raw_line = raw_line.decode("utf-8")
                self._parse_line(raw_line, sink, line_number, bnode_map)
            except ParserError:
                raise
            except (UnicodeDecodeError, ValueError) as error:
                raise ParserError(f"line {line_number}: {error}") from error
        return sink

    def _parse_line(self, line, sink, line_number, bnode_map):
        text = line.strip()
        if not text or text.startswith("#"):
            return
        position = 0
        subject, position = _term(text, position, line_number, "subject", bnode_map, allow_rdf12=self.allow_rdf12)
        position = _spaces(text, position)
        predicate, position = _term(text, position, line_number, "predicate", bnode_map, allow_rdf12=self.allow_rdf12)
        position = _spaces(text, position)
        obj, position = _term(text, position, line_number, "object", bnode_map, allow_rdf12=self.allow_rdf12)
        position = _spaces(text, position)
        if position < len(text) and text[position] == ".":
            graph = None
            position += 1
        else:
            graph, position = _term(text, position, line_number, "graph", bnode_map, allow_rdf12=self.allow_rdf12)
            if not isinstance(graph, (URIRef, BNode)):
                raise ParserError(f"line {line_number}: graph label must be an IRI or blank node")
            position = _spaces(text, position)
            if position >= len(text) or text[position] != ".":
                raise ParserError(f"line {line_number}: expected final '.'")
            position += 1
        position = _spaces(text, position)
        if position < len(text) and text[position] == "#":
            position = len(text)
        if position != len(text):
            raise ParserError(f"line {line_number}: unexpected trailing input")
        if not isinstance(subject, (URIRef, BNode)) or not isinstance(predicate, URIRef):
            raise ParserError(f"line {line_number}: invalid subject or predicate")
        validator = getattr(self, "_validate_rdf_version", None)
        if validator is not None:
            validator(obj, line_number)
        if graph is None:
            sink.add((subject, predicate, obj))
        elif hasattr(sink, "add"):
            sink.add((subject, predicate, obj, graph))
        else:
            raise ParserError(f"line {line_number}: named graph requires a Dataset")


W3CNQuadsParser = NQuadsParser
