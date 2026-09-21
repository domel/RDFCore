"""RDF 1.1 N-Triples parser module."""

from .ntriples import NTParser, ParseError, W3CNTriplesParser

__all__ = ["NTParser", "ParseError", "W3CNTriplesParser"]
