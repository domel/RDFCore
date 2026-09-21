# rdfcore

`rdfcore` is a lightweight, RDFLib-compatible library for RDF 1.1 and the
implemented RDF 1.2 syntax features. Runtime dependencies are empty.

## Quick start

```python
from rdfcore import Graph, URIRef, Literal

graph = Graph()
graph.add((URIRef("urn:s"), URIRef("urn:p"), Literal("value")))
print(graph.serialize(format="nt"))
```

RDF 1.1 formats retain their usual names. RDF 1.2 parsers and serializers are
explicitly versioned: `nt12`, `nq12`, `turtle12`, and `trig12`.

```python
from rdfcore import Graph

graph = Graph().parse(data='VERSION "1.2"\n<urn:s> <urn:p> <<( <urn:a> <urn:b> <urn:c> )>> .', format="turtle12")
output = graph.serialize(format="turtle12", rdf_version="1.2")
```

## Scope

RDFCore provides RDF 1.1-compatible APIs together with the implemented RDF 1.2
syntax features. RDF/XML and JSON-LD are not supported. RDF 1.2 formats use
the explicit `nt12`, `nq12`, `turtle12`, and `trig12` identifiers.

```python
from rdfcore.compare import isomorphic

round_tripped = Graph().parse(output, format="turtle12")
assert isomorphic(graph, round_tripped)
```

## Development

Install the optional test dependencies and run the suite with:

```bash
python -m pip install -e '.[test]'
python -m pytest
```

The `benchmarks/compare_rdflib_rdfcore.py` script compares RDFCore with the
pinned RDFLib version for common parsing and serialization paths.
