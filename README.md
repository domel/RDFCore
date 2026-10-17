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
that are not implemented, such as SPARQL and JSON-LD. RDF/XML is available,
with the limitations listed below. Differential tests use RDFLib 7.6.0;
support for a method does not establish parity for every possible input.

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
| RDF/XML | `xml`, `rdfxml`, `application/rdf+xml` |

RDF 1.2 formats have explicit names:

| Format | Parser and serializer names |
|---|---|
| N-Triples 1.2 | `nt12` |
| N-Quads 1.2 | `nq12` |
| Turtle 1.2 | `turtle12` |
| TriG 1.2 | `trig12` |
| RDF/XML 1.2 | `xml12` |

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

### RDF/XML

Use `xml12` explicitly for RDF 1.2. Its serializer writes
`rdf:version="1.2"` on `rdf:RDF`, including for an empty graph. The parser
requires an in-scope version announcement for RDF 1.2-only constructs.
The legacy `xml` serializer does not add this announcement.

```python
from rdfcore import Graph, TripleTerm, URIRef

graph = Graph().add((
    URIRef("urn:statement"), URIRef("urn:describes"),
    TripleTerm(URIRef("urn:s"), URIRef("urn:p"), URIRef("urn:o")),
))
xml = graph.serialize(format="xml12")
assert 'rdf:version="1.2"' in xml
assert graph.isomorphic(Graph().parse(data=xml, format="xml12"))
```

Both XML parsers reject DTD declarations and external entities. This is a
deliberate security restriction compared with RDFLib. XML parsing builds a
document tree and is not a bounded-memory streaming operation. Files ending
in `.rdf` or `.xml` select the RDF 1.1 parser unless a format is supplied.

### Optional entailment

`rdfcore.semantics.entails()` decides simple graph entailment, including
blank nodes inside triple terms. The `rdf` and `rdfs` regimes can prove a
subset of entailments using finite vocabulary axioms and forward rules.
When they cannot prove a conclusion, they raise `UnsupportedEntailment`;
this does not mean the conclusion is false. Datatype reasoning and
inconsistency detection are not implemented. Graph operations never infer
additional triples automatically.

```python
from rdfcore import Graph, RDF, URIRef
from rdfcore.semantics import entails

premise = Graph().add((URIRef("urn:s"), URIRef("urn:p"), URIRef("urn:o")))
conclusion = [(URIRef("urn:p"), RDF.type, RDF.Property)]
assert entails(premise, conclusion, regime="rdf")
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

`dataset.remove((subject, predicate, obj))` removes matching triples from all
graphs, as in RDFLib. To restrict removal to one graph, call that graph's
`remove()` method or pass a four-item pattern with its graph identifier.

Use `Graph.resource()` and `Graph.collection()` for convenience wrappers:

```python
from rdfcore import Graph, Literal, URIRef

graph = Graph()
resource = graph.resource(URIRef("urn:alice"))
resource.add(URIRef("urn:name"), Literal("Alice"))

collection = graph.collection(URIRef("urn:list"))
collection += [Literal("one"), Literal("two")]
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
Bounded reads do not impose a fixed bound on total memory. A parser may
buffer a whole record or token; its blank-node label map grows with the
number of distinct labels in the document. Nested terms also consume parser
state. External sorting budgets approximate run size, not total process
RSS, and a single oversized statement may exceed a run budget. RDF/XML
parsing builds a document tree.

The iterator form of `parse_stream()` uses a worker and a one-item queue.
Call `close()` when abandoning the iterator. Queue waits are cancellable,
but an arbitrary caller-provided source blocked inside `read()` cannot be
forcibly interrupted; close waits at most one second for that worker.
The push form with a sink does not create a worker.

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
with store.transaction():
    graph.parse("large.nt", format="nt")
print(len(graph))
store.close()
```

`SQLiteStore.transaction()` commits the whole block on success and rolls it
back on error. Nested blocks use savepoints. Individual writes outside a
transaction still commit immediately. `store.add_many(triples, context=None)`
consumes an iterable in one transaction and returns the number of input
triples, including duplicates. These are RDFCore storage extensions.
The built-in bulk path feeds records lazily to SQLite's `executemany()`;
it does not collect the input into a list. A generator failure rolls back
both inserted triples and context registrations. Stores overriding `add()`
retain that override during bulk ingestion.

SQLite databases use a versioned JSON representation of RDF terms. Opening
an older database migrates its term records in one transaction through a
restricted legacy reader. If decoding fails, the original rows and storage
version are retained. Unknown storage versions are rejected. Keep a backup
before migrating an existing database; the legacy reader does not impose
hard limits on record size or nesting depth.

For sorting large streams, use `external_sort()` with a memory budget:

```python
from rdfcore import external_sort, parse_stream, statement_key
from rdfcore.io import open_input

stream, owned = open_input("input.nq")
try:
    statements = parse_stream(stream, "nquads")
    ordered = external_sort(
        statements,
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
| Canonical NT/NQ lexical layout | `canonical=True`; does not rename blank nodes or implement RDFC-1.0 |
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
SQLite-backed paths where applicable. Serialization timings exclude parsing.
Correctness checks run outside timed sections. Reports record Python,
RDFLib, the RDFCore revision and whether the worktree was dirty. Memory
figures from this script are traced Python allocations, not process RSS.

## Tests

Run the complete test suite:

```bash
python -m pytest -q
```

The suite includes format tests, RDF 1.2 tests, streaming tests, compatibility
tests, and differential checks against RDFLib 7.6.0.

CI tests Python 3.10 through 3.14 and builds an installable wheel and source
distribution. README Python examples are executed against small local files.

### Official W3C tests

RDF 1.2 support remains partial; a green local pytest run is not a conformance
certificate.

Run the official suites against a clean local checkout at the revision in
`tests/w3c/manifest.lock`:

```bash
python -m tests.w3c.official /path/to/rdf-tests --output conformance-results.json
```

The command returns a nonzero status for any failed or unsupported case.
The separate **W3C conformance** workflow runs weekly and can be started
manually. It fetches the pinned snapshot and uploads a JSON artifact listing
passed, failed, unsupported and operationally erroneous tests. It is expected
to remain red while conformance gaps are open;
failures are not suppressed to obtain a green badge.
