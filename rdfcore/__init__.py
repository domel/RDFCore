"""RDFLib-compatible RDF library."""

__version__ = "0.1.0.dev0"

from .exceptions import (
    BadSyntax,
    CompValueException,
    Error,
    ModificationException,
    ObjectTypeError,
    ParserError,
    PluginException,
    StoreException,
    UniquenessError,
)
from .term import BNode, Identifier, IdentifiedNode, Literal, Node, TripleTerm, URIRef, Variable
from .rdf_version import required_rdf_version, validate_rdf_version, version_allows
from .namespace import ClosedNamespace, DC, DCTERMS, DefinedNamespace, FOAF, Namespace, NamespaceManager, OWL, RDF, RDFS, SKOS, XSD
from .store import Memory, SQLiteStore, Store
from .collection import Collection
from .resource import Resource
from .graph import Graph
from .dataset import ConjunctiveGraph, DATASET_DEFAULT_GRAPH_ID, Dataset
from .parser import InputSource, Parser, create_input_source
from .serializer import Serializer
from .streaming import BoundedReadStream, DatasetSink, FilterSink, GraphSink, MapSink, NQStreamingWriter, NTStreamingWriter, QuadSink, TripleSink, TriGStreamingWriter, TurtleStreamingWriter, parse_stream
from .pipeline import convert, count, validate
from .io import BoundedWriteStream, open_input, open_output
from .tokenizer import ChunkReader, Token, TokenReader
from .benchmark import benchmark_parse
from .external_sort import external_sort, statement_key
from . import plugin

from .plugins.parsers.ntriples11 import NTParser, ParseError, W3CNTriplesParser
from .plugins.parsers.ntriples12 import NT12Parser
from .plugins.parsers.nquads11 import NQuadsParser, W3CNQuadsParser
from .plugins.parsers.nquads12 import NQuads12Parser
from .plugins.parsers.turtle11 import Notation3Parser, TurtleParser
from .plugins.parsers.turtle12 import Turtle12Parser
from .plugins.parsers.trig11 import TriGParser
from .plugins.parsers.trig12 import TriG12Parser
from .plugins.serializers.nt11 import NT11Serializer, NTSerializer
from .plugins.serializers.nt12 import NT12Serializer
from .plugins.serializers.nq11 import NQuadsSerializer
from .plugins.serializers.nq12 import NQuads12Serializer
from .plugins.serializers.turtle11 import TurtleSerializer
from .plugins.serializers.turtle12 import Turtle12Serializer
from .plugins.serializers.trig11 import TriGSerializer
from .plugins.serializers.trig12 import TriG12Serializer

for _alias in ("nt", "ntriples", "nt11", "application/n-triples"):
    plugin.register(_alias, Parser, NTParser)
for _alias in ("nt12",):
    plugin.register(_alias, Parser, NT12Parser)
for _alias in ("nquads", "application/n-quads"):
    plugin.register(_alias, Parser, NQuadsParser)
plugin.register("nq12", Parser, NQuads12Parser)
for _alias in ("turtle", "ttl", "text/turtle"):
    plugin.register(_alias, Parser, TurtleParser)
plugin.register("turtle11", Parser, TurtleParser)
plugin.register("turtle12", Parser, Turtle12Parser)
for _alias in ("trig", "application/trig"):
    plugin.register(_alias, Parser, TriGParser)
plugin.register("trig11", Parser, TriGParser)
plugin.register("trig12", Parser, TriG12Parser)
for _alias in ("nt", "ntriples", "nt11", "application/n-triples"):
    plugin.register(_alias, Serializer, NT11Serializer if _alias == "nt11" else NTSerializer)
plugin.register("nt12", Serializer, NT12Serializer)
for _alias in ("nquads", "application/n-quads"):
    plugin.register(_alias, Serializer, NQuadsSerializer)
plugin.register("nq12", Serializer, NQuads12Serializer)
for _alias in ("turtle", "ttl", "text/turtle"):
    plugin.register(_alias, Serializer, TurtleSerializer)
plugin.register("turtle11", Serializer, TurtleSerializer)
plugin.register("turtle12", Serializer, Turtle12Serializer)
for _alias in ("trig", "application/trig"):
    plugin.register(_alias, Serializer, TriGSerializer)
plugin.register("trig11", Serializer, TriGSerializer)
plugin.register("trig12", Serializer, TriG12Serializer)

__all__ = [
    "BadSyntax",
    "CompValueException",
    "Error",
    "ModificationException",
    "ObjectTypeError",
    "ParserError",
    "PluginException",
    "StoreException",
    "UniquenessError",
    "Node",
    "Identifier",
    "IdentifiedNode",
    "URIRef",
    "BNode",
    "Literal",
    "Variable",
    "TripleTerm",
    "required_rdf_version",
    "validate_rdf_version",
    "version_allows",
    "Namespace",
    "DefinedNamespace",
    "ClosedNamespace",
    "NamespaceManager",
    "RDF",
    "RDFS",
    "XSD",
    "OWL",
    "SKOS",
    "FOAF",
    "DC",
    "DCTERMS",
    "Store",
    "Memory",
    "SQLiteStore",
    "Collection",
    "Resource",
    "Graph",
    "Dataset",
    "ConjunctiveGraph",
    "DATASET_DEFAULT_GRAPH_ID",
    "InputSource",
    "Parser",
    "Serializer",
    "TripleSink",
    "QuadSink",
    "GraphSink",
    "FilterSink",
    "MapSink",
    "DatasetSink",
    "BoundedReadStream",
    "NTStreamingWriter",
    "NQStreamingWriter",
    "TurtleStreamingWriter",
    "TriGStreamingWriter",
    "parse_stream",
    "convert",
    "count",
    "validate",
    "BoundedWriteStream",
    "open_input",
    "open_output",
    "ChunkReader",
    "Token",
    "TokenReader",
    "external_sort",
    "statement_key",
    "benchmark_parse",
    "create_input_source",
    "plugin",
    "NTParser",
    "NT12Parser",
    "W3CNTriplesParser",
    "ParseError",
    "NQuadsParser",
    "NQuads12Parser",
    "W3CNQuadsParser",
    "TurtleParser",
    "Turtle12Parser",
    "Notation3Parser",
    "TriGParser",
    "TriG12Parser",
    "NTSerializer",
    "NT11Serializer",
    "NT12Serializer",
    "NQuadsSerializer",
    "NQuads12Serializer",
    "TurtleSerializer",
    "Turtle12Serializer",
    "TriGSerializer",
    "TriG12Serializer",
]
