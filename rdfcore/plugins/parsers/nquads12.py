"""RDF 1.2 N-Quads parser module."""

import re

from ...exceptions import ParserError
from .nquads import NQuadsParser


class NQuads12Parser(NQuadsParser):
    rdf_version = "1.2"
    allow_rdf12 = True

    def parse(self, source, sink, **kwargs):
        from ...rdf_version import validate_rdf_version

        self._requested_version = validate_rdf_version(kwargs.get("rdf_version", "auto"))
        return super().parse(source, sink, **kwargs)

    def _parse_line(self, line, sink, line_number, bnode_map):
        text = line.strip()
        if text.startswith("VERSION"):
            if re.fullmatch(r'VERSION\s+"(1\.1|1\.2-basic|1\.2)"(?:\s+#.*)?', text) is None:
                raise ParserError(f"line {line_number}: invalid VERSION declaration")
            return
        super()._parse_line(line, sink, line_number, bnode_map)

    def _validate_rdf_version(self, term, line_number):
        # NQuadsParser shares the same term grammar as NT12Parser.
        from .ntriples12 import NT12Parser

        NT12Parser._validate_rdf_version(self, term, line_number)


__all__ = ["NQuads12Parser"]
