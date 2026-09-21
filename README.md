# RDFCore

RDFCore is a Python library for RDF 1.1 and selected RDF 1.2 features. It
provides a small RDFLib-compatible API, streaming parsers and writers, a
SQLite-backed store, external sorting, and bounded I/O helpers.

The package has no runtime dependencies and requires Python 3.10 or newer.

## Installation

Install the package in editable mode with the test tools:

```bash
python -m pip install -e '.[test]'
```

For normal use, install the package without the optional test dependencies:

```bash
python -m pip install .
```

## Quick start

Create a graph, add a triple, and serialize it:

```python
from rdfcore import Graph, Literal, URIRef

graph = Graph()
graph.add((URIRef("urn:alice"), URIRef("urn:name"), Literal("Alice")))

text = graph.serialize(format="nt")
print(text)
```

Parse Turtle and query the graph:

```python
from rdfcore import Graph, URIRef

graph = Graph().parse(
    data='@prefix ex: <urn:> . ex:alice ex:name "Alice" .',
    format="turtle",
)

for name in graph.objects(URIRef("urn:alice"), URIRef("urn:name")):
    print(name)
```

## RDFLib compatibility

RDFCore implements common RDFLib classes and graph operations, including
`Graph`, `Dataset`, `URIRef`, `BNode`, `Literal`, collections, resources,
transitive graph helpers, skolemization, and graph comparison.

The compatibility scope is documented in
[Compare_with_rdflib.md](Compare_with_rdflib.md). The table also lists areas
that are not implemented, such as SPARQL, RDF/XML, and JSON-LD.

RDFCore is not a drop-in replacement for every RDFLib plugin. Code that uses
the common graph and term APIs can usually be migrated with small changes.

## RDF 1.1 and RDF 1.2 formats

RDF 1.1 formats use the usual names:

| Format | Parser and serializer names |
|---|---|
| N-Triples | `nt`, `ntriples`, `nt11` |
| N-Quads | `nquads` |
| Turtle | `turtle`, `ttl` |
| TriG | `trig` |

RDF 1.2 formats have explicit names:

| Format | Parser and serializer names |
|---|---|
| N-Triples 1.2 | `nt12` |
| N-Quads 1.2 | `nq12` |
| Turtle 1.2 | `turtle12` |
| TriG 1.2 | `trig12` |

Example with an RDF 1.2 triple term:

```python
from rdfcore import Graph

graph = Graph().parse(
    data='VERSION "1.2"\n'
         '<urn:s> <urn:p> <<( <urn:a> <urn:b> <urn:c> )>> .',
    format="turtle12",
)

output = graph.serialize(format="turtle12", rdf_version="1.2")
```

RDF 1.2 also supports directional language tags and the `rdf:JSON` datatype:

```python
from rdfcore import Literal, RDF

json_value = Literal('{"items":[1,true,null]}', datatype=RDF.JSON)
assert json_value.ill_typed is False
assert json_value.value == {"items": [1.0, True, None]}
```

## Graphs and datasets

Use `Graph` for one graph and `Dataset` for a default graph plus named graphs:

```python
from rdfcore import Dataset, Literal, URIRef

dataset = Dataset()
dataset.add((URIRef("urn:s"), URIRef("urn:p"), Literal("default")))

named = dataset.graph("urn:graph")
named.add((URIRef("urn:s"), URIRef("urn:p"), Literal("named")))

for subject, predicate, obj, graph_name in dataset.quads():
    print(subject, predicate, obj, graph_name)
```

Use `Graph.resource()` and `Graph.collection()` for convenience wrappers:

```python
from rdfcore import Graph, Literal, URIRef

graph = Graph()
resource = graph.resource(URIRef("urn:alice"))
resource.add(URIRef("urn:name"), Literal("Alice"))

collection = graph.collection(URIRef("urn:list"), [Literal("one"), Literal("two")])
print(list(collection))
```

## Parsing and serialization

`parse()` accepts a string, bytes, file-like object, or file path. The format
can be given explicitly:

```python
from rdfcore import Graph

graph = Graph().parse("input.ttl", format="turtle")
graph.serialize("output.nt", format="nt")
```

RDFCore also detects gzip, bzip2, and xz compression from file extensions in
the streaming helpers.

RDF 1.2 data requires an RDF 1.2 serializer. RDF 1.1 output can be requested
only when the data can be represented by RDF 1.1:

```python
graph.serialize(format="nt12", rdf_version="1.2")
graph.serialize(format="nt", rdf_version="1.1", downgrade="interop")
```

The `downgrade="interop"` option converts supported RDF 1.2 constructs to an
RDF 1.1-compatible representation. Without this option, incompatible output
raises an error.

## Streaming processing

Streaming operations process statements without building a `Graph` or
`Dataset`:

```python
from rdfcore import count, validate

number_of_triples = count("large.nt", "nt")
is_valid = validate("large.nt", "nt")
```

`parse_stream()` and `convert()` are streamable for N-Triples and N-Quads.
Turtle and TriG parsers consume bounded readers, and their RDF 1.2 streaming
serializers are available with `mode="stream"`:

```python
graph.serialize("output.ttl", format="turtle12", mode="stream")
```

Streaming serializers write statements as they are processed. They do not
provide the prefix grouping, complete-graph sorting, or formatting used by
the default pretty serializers.

Convert N-Triples and N-Quads through a streaming pipeline:

```python
from rdfcore import convert

convert("input.nq", "output.nt", input_format="nquads", output_format="nt",
        dataset_policy="default")
```

The `dataset_policy` controls named graphs when converting N-Quads to
N-Triples:

| Policy | Behavior |
|---|---|
| `strict` | Raise an error if a named graph is encountered |
| `default` | Keep only statements from the default graph |
| `union` | Write statements from all graphs |

For custom processing, use `FilterSink`, `MapSink`, `GraphSink`, or
`DatasetSink`:

```python
from rdfcore import FilterSink, Graph, GraphSink, URIRef, parse_stream
from rdfcore.io import open_input

graph = Graph()
stream, owned = open_input("input.nt")
try:
    sink = FilterSink(
        GraphSink(graph),
        lambda triple: triple[1] == URIRef("urn:keep"),
    )
    parse_stream(stream, "nt", sink)
finally:
    if owned:
        stream.close()
```

## Storage and large inputs

The default `Memory` store is suitable for small and medium graphs. Use
`SQLiteStore` when data should remain on disk or when the full graph should
not be kept in Python memory:

```python
from rdfcore import Graph, SQLiteStore

store = SQLiteStore("data.sqlite3")
graph = Graph(store=store)
graph.parse("large.nt", format="nt")
print(len(graph))
store.close()
```

For sorting large streams, use `external_sort()` with a memory budget:

```python
from rdfcore import external_sort, parse_stream, statement_key
from rdfcore.io import open_input

stream, owned = open_input("input.nq")
try:
    statements = parse_stream(stream, "nquads")
    ordered = external_sort(
        statements,
        key=statement_key,
        memory_budget=64 * 1024 * 1024,
        unique=True,
        max_open_runs=64,
    )
    for statement in ordered:
        print(statement)
finally:
    if owned:
        stream.close()
```

`external_sort()` creates fixed-size temporary runs and merges them in passes.
`max_open_runs` limits the number of temporary runs opened by one merge pass.
The normal `Graph` and `Dataset` containers, pretty serializers, graph
isomorphism, and canonicalization operations may retain or sort the complete
graph in memory.

## Optimization options

Choose the processing path based on the data size and required operation:

| Situation | Recommended option |
|---|---|
| Small graph with random access | `Graph` with the default `Memory` store |
| Named graphs | `Dataset` |
| Large file, count or validation only | `count()` or `validate()` |
| Large N-Triples or N-Quads conversion | `convert()` |
| Large input with custom filtering | `parse_stream()` with `FilterSink` |
| Data larger than available memory | `SQLiteStore` or `external_sort()` |
| Reproducible output order | `canonical=True` where supported |
| Compressed input or output | `.gz`, `.bz2`, or `.xz` paths |
| Smaller I/O calls | Set `buffer_size` explicitly |

Use a bounded buffer for file processing:

```python
from rdfcore import count

count("large.nt.gz", "nt", buffer_size=1024 * 1024)
```

Benchmark a streaming parse and inspect throughput and peak memory:

```python
from rdfcore import benchmark_parse

result = benchmark_parse("large.nt", "nt", buffer_size=1024 * 1024)
print(result["statements_per_second"])
print(result["peak_rss_bytes"])
```

Run the RDFLib comparison benchmark from the project root:

```bash
python benchmarks/compare_rdflib_rdfcore.py --statements 1000 10000
```

The benchmark covers N-Quads, Turtle, and TriG in standard, streaming, and
SQLite-backed paths where applicable.

## Tests

Run the complete test suite:

```bash
python -m pytest -q
```

The suite includes format tests, RDF 1.2 tests, streaming tests, compatibility
tests, and differential checks against RDFLib 7.6.0.
