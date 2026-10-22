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

| Format | Short names | MIME alias |
|---|---|---|
| N-Triples | `nt`, `ntriples`, `nt11` | `application/n-triples` |
| N-Quads | `nquads`, `nq`, `nq11` | `application/n-quads` |
| Turtle | `turtle`, `ttl`, `turtle11` | `text/turtle` |
| TriG | `trig`, `trig11` | `application/trig` |
| RDF/XML | `xml`, `rdfxml` | `application/rdf+xml` |

Each name above works with both `parse(format=...)` and
`serialize(format=...)`. Bare MIME aliases select RDF 1.1 implementations;
use the explicit names below or a MIME `version` parameter for RDF 1.2.

RDF 1.2 formats have explicit names:

| Format | Parser and serializer names | Versioned MIME alias |
|---|---|---|
| N-Triples 1.2 | `nt12` | `application/n-triples; version=1.2` |
| N-Quads 1.2 | `nq12` | `application/n-quads; version=1.2` |
| Turtle 1.2 | `turtle12` | `text/turtle; version=1.2` |
| TriG 1.2 | `trig12` | `application/trig; version=1.2` |
| RDF/XML 1.2 | `xml12`, `xmlrdf12` | `application/rdf+xml; version=1.2` (RDFCore extension) |

MIME parameters work in `parse()`, `serialize()`, plugin lookup and
`parse_stream()`. Line-format `convert()` accepts them for both input and output:

```python
from rdfcore import Graph

graph = Graph().parse(
    data='<urn:s> <urn:p> <<( <urn:a> <urn:b> <urn:c> )>> .',
    format="text/turtle; version=1.2",
)
text = graph.serialize(format="text/turtle; version=1.2")
restored = Graph().parse(data=text, format="text/turtle; version=1.2")
```

The MIME aliases in the first table accept `version=1.1`, `version=1.2-basic`
and `version=1.2`. Quoted values, such as `version="1.2"`, are accepted;
media types and parameter names are case-insensitive. `1.2-basic` permits
directional literals but rejects triple terms. Unknown versions, duplicate
version parameters and conflicts with an explicit `rdf_version` raise
`ValueError`. `auto` is an API option, not a media version label. Other
syntactically valid parameters do not select the RDF version or change decoding.

For HTTP input, `Graph.parse()` uses a versioned `Content-Type` when no
`format` is supplied. An explicit format takes precedence. RDF/XML MIME
version dispatch is an RDFCore extension: it does not replace the required
in-document `rdf:version` announcement for RDF 1.2 constructs.

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

`rdf:JSON` value comparison preserves the distinction between positive and
negative zero, including inside arrays and objects. Object member order does
not affect value identity. The mutable Python containers returned by
`toPython()` do not change the literal's lexical form or its `eq()` result;
copying a JSON literal rebuilds its Python value from the lexical form.

### Explicit datatype values

`rdfcore.datatypes` validates lexical forms independently of RDFLib-compatible
`Literal.toPython()`. Use `normalize=False` when validating original input,
because constructor normalization can otherwise change it first. For raw
input, `lexical_value(text, datatype)` bypasses constructor normalization
entirely, including the whitespace handling of `normalizedString` and `token`.

```python
from rdfcore import Literal, XSD
from rdfcore.datatypes import datatype_value, same_value

a = Literal("01", datatype=XSD.integer, normalize=False)
b = Literal("1", datatype=XSD.integer, normalize=False)
assert a != b                 # Different RDF terms.
assert same_value(a, b)       # The same datatype value.
assert hash(datatype_value(a)) == hash(datatype_value(b))
```

The supported subset includes integer types, decimal, binary32/binary64,
boolean, binary encodings, dates/times (including partial dates and
`dateTimeStamp`), durations, selected string types, language and directional
strings, JSON and DOM fragment values. Value keys are immutable. Floating
point value identity distinguishes signed zeros and treats NaN as identical
to itself; it is not arithmetic equality. Distinct XSD primitive spaces
remain disjoint, even when their Python values compare equal. Binary32 mapping
rounds directly
from the decimal rational, without an intermediate binary64 rounding.
Temporal keys retain timezone offsets, arbitrary-size years and exact
fractional seconds. Two equal instants with different offsets are not
identical XSD 1.1 values. Duration keys retain months and seconds separately.

For HTML5 fragment values, install `pip install 'rdfcore[html]'`. Without
that optional parser, HTML value mapping raises `UnsupportedDatatype`.
The XML fragment mapper forbids DTDs and limits nesting to 256 elements.
It applies XML 1.1 line-end handling and restricted character references
without interpreting references in comments, processing instructions or
CDATA. Those rules are separate from the legacy RDF/XML parser.

`InvalidLexicalForm` reports invalid input for a supported datatype;
`UnsupportedDatatype` reports missing types or comparisons, and
`DatatypeResourceLimit` reports a processing limit without declaring the
literal invalid. Datatype entailment remains unsupported by this module.
See `SUPPORTED_DATATYPES` for the exact recognized set. Ordinary graph
operations do not use this module to infer triples or reject stored literals.

### RDF/XML

Use `xml12` or its alias `xmlrdf12` explicitly for RDF 1.2. Both names select
the same parser and serializer. The serializer writes
`rdf:version="1.2"` on `rdf:RDF` by default, including for an empty graph. An
explicit `rdf_version="1.2-basic"` writes that profile; `rdf_version="1.1"`
omits the announcement and rejects terms that require RDF 1.2. The parser
requires an in-scope version announcement for RDF 1.2-only constructs.
The legacy `xml` serializer does not add this announcement.
Like RDFLib 7.6.0, the `xml` serializer writes UTF-8 even when another
`encoding` argument is supplied; the argument still selects a bytes return
value. The explicit `xml12` serializer honors the requested encoding.
For `xml`, caller-supplied output streams must accept bytes, as in RDFLib.
Text streams raise `TypeError`; sink exceptions propagate without a text retry. File
paths are opened in binary mode. The low-level XML11 writer also follows
RDFLib's replacement policy if its `encoding` attribute is changed to ASCII.
The `xml12` writer selects text output for standard `io.TextIOBase` streams
(including `StringIO`) before writing. Other sinks receive bytes by default;
use `text_output=True` for a custom text sink or `text_output=False` to
require bytes. The option accepts a boolean or `None` for automatic selection.
Sink errors, including `TypeError` after a partial write, propagate without a
retry or closing the caller's stream. Text wrappers must use an encoding
consistent with the XML encoding requested from the serializer.
Direct serializer calls use the graph's base when `base=None`, as in RDFLib;
an explicit empty base suppresses it. Writer round-trip tests cover shared
blank nodes, XMLLiteral lexical forms, Unicode, directional literals, nested
triple terms and multiple reifiers. UTF-8 and UTF-16 output can be parsed
directly. UTF-32 output must be decoded to text before parsing because the
current XML parser does not accept UTF-32 byte input. Namespace prefixes and
statement order are not promised to match RDFLib byte for byte.
For predicates in the reserved XMLNS namespace, `xml12` selects a legal
QName split or raises `ValueError` before writing. Legacy `xml` retains
RDFLib 7.6.0's namespace behavior, including its invalid XMLNS binding;
use `safe_iris=True` to select the corrected writer explicitly.
An XML12 writer with `rdf_version="1.1"` accepts the RDF 1.1 vocabulary,
including ordinary `rdf:version`, `rdf:annotation` and `rdf:annotationNodeID`
predicates. This does not enable RDF 1.2 terms in that profile.

The `xml` parser follows RDFLib's XMLLiteral handling, including CDATA,
omission of comments and processing instructions, CR text normalization,
and omission of default namespace undeclarations. These legacy lexical
rules do not apply to `xml12`, which retains comments, processing
instructions and default namespace undeclarations inside XML literals.
Outside XML literals, `xml12` accepts only XML whitespace between RDF
elements; `xml` preserves RDFLib's broader Unicode whitespace handling.
The XML12 event mapping ignores reserved `xml*` element and attribute names,
except inside XML literals. XML11 retains the reference's legacy handling.

Both parsers reject DTD declarations before processing RDF or accessing
external entities, including declarations split across input chunks or
encoded as UTF-16. XML nesting is limited to 256 elements, including the
RDF wrapper and XML literal content. The XML12 writer rejects more than
126 nested triple terms so that its output stays within the parser's limit.
Input streams supplied by the caller remain open after success or failure.
The parsers build a tree and do not provide a hard memory bound for large
text or documents.

```python
from rdfcore import Graph, TripleTerm, URIRef

graph = Graph().add((
    URIRef("urn:statement"), URIRef("urn:describes"),
    TripleTerm(URIRef("urn:s"), URIRef("urn:p"), URIRef("urn:o")),
))
xml = graph.serialize(format="xmlrdf12")
assert 'rdf:version="1.2"' in xml
assert graph.isomorphic(Graph().parse(data=xml, format="xmlrdf12"))
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

`count()` and `validate()` close files they open and any decompression wrappers
they create, including after a parse error. A stream supplied by the caller
remains open; closing an internally created wrapper does not transfer ownership
of that stream.

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
An experimental zero-thread RDF 1.1 NT/NQ iterator is measured by
`benchmarks/line_iterator.py`. It reuses the line parsers but changes
read-ahead and producer-thread behavior. It is not enabled in `parse_stream()`
and is not a public library API.

Turtle and TriG parsers consume bounded readers, and their RDF 1.2 streaming
serializers are available with `mode="stream"`:

```python
graph.serialize("output.ttl", format="turtle12", mode="stream")
```

Streaming serializers write statements as they are processed. They do not
provide the prefix grouping, complete-graph sorting, or formatting used by
the default pretty serializers.

Convert N-Triples and N-Quads through a streaming pipeline:

`convert()` also accepts `nt12` and `nq12`, in either direction, as well as
the registered RDF 1.1 line-format aliases. RDF 1.2 output announces version
1.2 unless `canonical=True`. Writing RDF 1.2 terms to a 1.1 target raises
an error, including with a custom sink; graph-selection policies do not
disable that check. Conversion does not construct an intermediate graph.
Input is opened before output. Conversion rejects input/output aliases of the
same file, including symlinks and hard links. Missing input, an invalid buffer
size, or an invalid graph-selection policy does not truncate an existing
destination. A parsing or writing error can still leave partial output;
discard that output after failure. Bounded output writes retry partial writes
and raise an error if the destination makes no progress, also with compression.

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

Canonical storage keys compare language tags case-insensitively. A separate
`lexical_forms` table retains the first spelling in each context and in the
union, including within triple terms. This optional metadata does not change
the version-one term codec. Existing version-one databases remain readable,
but spelling already lowercased by an older release cannot be recovered.

When serializing a dataset to a graph format, RDFLib's format-specific
projection applies: N-Triples includes its quads as triple statements, while
Turtle and RDF/XML use the default graph unless `default_union=True`.
Serialization uses `Graph.base` when `base` is omitted. Turtle and TriG pretty
and streaming output emit the base declaration and relativize eligible IRIs;
RDF/XML emits `xml:base`. An explicit `base` overrides the graph's base.

Turtle/TriG 1.2 writers only shorten an IRI when resolving the shortened
form against the base reproduces the original IRI exactly. This applies to
pretty and streaming output, graph names and nested triple terms. Legacy
`turtle`/`trig` keep RDFLib-compatible prefix stripping by default, including
its known round-trip defect when the base is a partial path prefix. Select
the corrected behavior with `graph.serialize(format="turtle", safe_iris=True)`
(also available for `trig`). Direct `TurtleStreamingWriter` and
`TriGStreamingWriter` calls use safe handling by default. `safe_iris=False`
explicitly selects the older behavior; the option requires a boolean.

`Graph.isomorphic()` follows RDFLib's approximate RDF 1.1 check and can return
false positives when blank nodes occur. Use `rdfcore.compare.isomorphic()`
for exact graph/dataset comparison. It includes nested triple terms and empty
named graphs, with one blank-node mapping across data and graph names.
Comparison reads dataset contexts without changing graph bases, namespace
bindings or the graph-view cache, including when comparison fails.
Graphs without blank nodes use set comparison; blank-node matching uses an
iterative search, though symmetric graphs can still be expensive.
For RDF 1.2 data, the graph method uses this exact comparison as an extension.
The explicit interoperability transformations also retain empty named graphs.

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

The historical `benchmark_parse()` field `peak_rss_bytes` is an increase in
the process high-water mark, not an isolated peak for that operation. It may
be zero after an earlier memory-heavy operation. Streaming regression tests
measure absolute RSS in fresh processes instead; neither measure proves a
hard memory bound for arbitrary RDF input.

Run the RDFLib comparison benchmark from the project root:

```bash
python benchmarks/compare_rdflib_rdfcore.py --statements 1000 10000 --repeats 3 --warmup 1
python benchmarks/sqlite_bulk.py --statements 10000 --repeats 5 --modes transaction bulk
python benchmarks/memory_queries.py --statements 10000 --repeats 5
```

The benchmark covers N-Quads, Turtle, and TriG in standard, streaming, and
SQLite-backed paths where applicable. Serialization timings exclude parsing.
Correctness checks run outside timed sections. Reports record Python,
RDFLib, the RDFCore revision and whether the worktree was dirty. Memory
figures from this script are traced Python allocations, not process RSS.
Repeated runs retain individual samples and report median time. Each parse
run uses a fresh graph prepared outside the timer. `sqlite_bulk.py` checks
persistence on disk; `memory_queries.py` verifies eight SPO patterns in the
default graph and two named graphs against RDFLib before timing them.

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
Reports separate syntax from entailment, record the published reference
document alongside the pinned test snapshot, and include individual failure
reasons and SHA-256 hashes of the original action and expected-result files.
A published reference link does not mean the snapshot covers every
requirement of that revision. Checkout directory names do not change the
base IRIs assigned to official fixtures.

The current snapshot is `d5d930b03ee6b63b388d0bb28fdb29ee78a59ec0`
(2026-10-12). The previous revision, `369a90d1a60c021b746df2e411da0ff36258a758`
(2026-09-21), is retained in `tests/w3c/manifest.previous.lock` for comparison.
The refresh adds five N-Triples version-announcement tests, all passing, and
changes manifest metadata. None of the 2447 previous executions changes
status or fixture bytes; no test is removed.

| Snapshot | Passed | Failed | Unsupported | Error |
|---|---:|---:|---:|---:|
| Previous, default profile | 2345 | 23 | 79 | 0 |
| Current, default profile | 2350 | 23 | 79 | 0 |

These totals count executions across suites, including repeated RDF 1.1
cases. The current snapshot contains 2452 executions and 1411 unique test IDs.

The reviewed snapshot still has RDF/XML failures (including XMLLiteral
lexical-form expectations) and unsupported datatype/inconsistency reasoning
cases. These remain visible failures or unsupported results, not successful
conformance checks. The RDFLib-compatible XMLLiteral behavior has separate
differential tests; expected W3C fixtures are not rewritten to hide the gap.

Audit a report or compare two snapshots using the same execution profile:

```bash
python -m tests.w3c.official /path/to/previous-rdf-tests --lock tests/w3c/manifest.previous.lock --output .w3c/previous.json
python -m tests.w3c.audit --current conformance-results.json --output .w3c/audit.json
python -m tests.w3c.audit --before .w3c/previous.json --current conformance-results.json --output .w3c/comparison.json
```

The audit explains reviewed issues and identifies unreviewed ones. It does
not alter test statuses and returns a nonzero exit status while issues remain.
Comparison retains repeated executions, format and RDF-version distinctions,
and reports added, removed and changed cases, including changed fixture bytes,
action/result IRIs, entailment regimes, test types and recognized datatypes.
Reordering a set of types or recognized datatypes alone is not a semantic change.
Default and archived-recovery profiles cannot be compared as equivalent runs.

The reviewed issues comprise 79 unsupported semantic executions, 17 XML
announcement conflicts, four XMLLiteral lexical conflicts with the pinned
RDFLib behavior, and two disputed XML fixtures. The four lexical executions
reuse two test IDs across XML11 and XML12. Fixture-conflict explanations for
the two disputed cases require matching reviewed input and result hashes;
an unknown snapshot or changed disputed fixture remains unreviewed.

The XML conflict regressions run offline, independently of the official checkout.
They cover each of the 17 annotation constructions with separate default,
announced `1.2`, and archived-recovery expectations. The selected
[XML Working Draft of 9 October 2026](https://www.w3.org/TR/2026/WD-rdf12-xml-20261009/)
has inconsistencies between the Triple grammar summary, detailed production,
and Example 22. RDFCore retains the example's single outer assertion with a
triple-term object, without asserting the inner triple. This is an explicit
interpretation of the disputed text, not evidence that the draft is unambiguous.
The [Editor's Draft](https://w3c.github.io/rdf-xml/spec/), checked on 18 October
2026, retains those inconsistencies. Neither an empty expected graph nor a
directionless expected literal overrides the retained triple or direction.

For archived XML fixtures only, opt into `legacy_w3c=True`:

```python
archived_xml = '''<rdf:RDF
  xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
  xmlns:e="urn:e:">
  <rdf:Description rdf:about="urn:s">
    <e:p rdf:annotation="urn:reifier">value</e:p>
  </rdf:Description>
</rdf:RDF>'''
graph = Graph().parse(data=archived_xml, format="xml12", legacy_w3c=True)
```

This recovery mode assumes RDF 1.2 when no version is announced in `xml12`
and expands empty elements inside XML literals (`<br/>` becomes `<br></br>`).
Explicit version declarations still take precedence. In `xml`, only the
XML-literal expansion applies. Default parsing and serializers are unchanged;
this option is not a general XML canonicalization implementation. DTD rejection
and other validation remain active.

To report this mode separately, run:

```bash
python -m tests.w3c.official /path/to/rdf-tests --legacy-w3c-xml --output legacy-results.json
```

The JSON records `execution_profile="legacy-w3c-xml"` and the parser option.
On both reviewed snapshots, this resolves 21 of the 23 default-profile failures.
Two XML 1.2 failures remain: `rdf12-xml-tt-01` has an empty expected file,
and `rdf12-xml-dir-02` expects a literal without the input's direction.
Recovery does not discard either triple terms or direction to match those
expectations. Results in this mode are archived-fixture compatibility evidence,
not current RDF 1.2 conformance. The 79 unsupported reasoning cases remain.

The separate **W3C conformance** workflow runs weekly, on relevant pull
requests and `v*` release tags, and can be started manually. It fetches or
restores the current and archived fixtures from cache, verifies their clean
revisions, and uploads both reports, their comparison and issue classifications
even when tests fail. It remains red while conformance gaps are open;
failures are not suppressed to obtain a green badge.
