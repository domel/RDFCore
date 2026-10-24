# RDFCore

RDFCore is a Python library for RDF 1.1 and selected RDF 1.2 features, with a
small RDFLib-compatible API, streaming I/O, SQLite storage and external sorting.
It requires Python 3.10+ and has no runtime dependencies.

## Installation

Install from a local checkout:

```bash
python -m pip install .
```

For development, including test tools:

```bash
python -m pip install -e '.[test]'
```

## Quick start

Create and serialize a graph:

```python
from rdfcore import Graph, Literal, URIRef

graph = Graph()
graph.add((URIRef("urn:alice"), URIRef("urn:name"), Literal("Alice")))

text = graph.serialize(format="nt")
print(text)
```

Parse and query Turtle:

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

RDFCore implements common RDFLib graph and term APIs, including `Graph`,
`Dataset`, collections, resources, skolemization and graph comparison.
[Compare_with_rdflib.md](Compare_with_rdflib.md) lists supported operations
and gaps, including SPARQL and JSON-LD.

Differential tests use RDFLib 7.6.0. Compatibility is verified for tested
inputs; RDFCore is not a replacement for every RDFLib API or plugin.
See [RDF/XML](#rdfxml) for its separate compatibility rules.

## RDF 1.1 and RDF 1.2 formats

RDF 1.1 formats use the usual names:

| Format | Short names | MIME alias |
|---|---|---|
| N-Triples | `nt`, `ntriples`, `nt11` | `application/n-triples` |
| N-Quads | `nquads`, `nq`, `nq11` | `application/n-quads` |
| Turtle | `turtle`, `ttl`, `turtle11` | `text/turtle` |
| TriG | `trig`, `trig11` | `application/trig` |
| RDF/XML | `xml`, `rdfxml` | `application/rdf+xml` |

All names work with `parse()` and `serialize()`. Bare MIME aliases select
RDF 1.1; use explicit names or a MIME `version` parameter for RDF 1.2.

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

For HTTP input without an explicit `format`, `Graph.parse()` and
`Dataset.parse()` prefer a registered `Content-Type` and its version over
the URL suffix. An explicit format overrides even an invalid version header.
Exact registered MIME names take priority; custom base types also accept
parameters such as `charset`.

Redirects use the final URL as the base unless `publicID` overrides it;
an empty `publicID` uses the original URL, as in RDFLib. Responses always
close. Legacy aliases send RDFLib 7.6.0's `Accept` header; RDF 1.2 names
request the versioned type. Override it with `http_accept`.
RDF/XML MIME version dispatch is an RDFCore extension and still requires
an in-document announcement for RDF 1.2 constructs.

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

`rdfcore.datatypes` validates lexical forms separately from RDFLib-compatible
`Literal.toPython()`. Use `normalize=False` to preserve constructor input,
or `lexical_value(text, datatype)` to bypass normalization entirely,
including whitespace handling for `normalizedString` and `token`.

```python
from rdfcore import Literal, XSD
from rdfcore.datatypes import datatype_value, same_value

a = Literal("01", datatype=XSD.integer, normalize=False)
b = Literal("1", datatype=XSD.integer, normalize=False)
assert a != b                 # Different RDF terms.
assert same_value(a, b)       # The same datatype value.
assert hash(datatype_value(a)) == hash(datatype_value(b))
```

Supported types include integers, decimal, binary32/64, boolean, binary
encodings, dates/times, durations, selected string types, directional strings,
JSON and DOM fragments. See `SUPPORTED_DATATYPES` for the exact set.

Value keys are immutable. Floating-point identity distinguishes signed zeros
and identifies NaN with itself; distinct XSD primitive spaces remain disjoint.
Binary32 rounds directly from the decimal rational. Temporal keys preserve
offsets, arbitrary-size years and exact fractions: equal instants with different
offsets are not identical XSD 1.1 values. Durations retain months and seconds.

HTML5 values require `pip install 'rdfcore[html]'`. The XML fragment mapper
forbids DTDs, limits nesting to 256 and applies XML 1.1 line-end/reference rules
without interpreting references inside comments, instructions or CDATA.

`InvalidLexicalForm` reports invalid supported input; `UnsupportedDatatype`
reports unavailable mappings or comparisons; `DatatypeResourceLimit` reports
a processing limit, not invalidity. This module neither performs entailment
nor changes ordinary graph storage.

## RDF/XML

### Choosing a version

| Use | Parser and serializer | Version announcement |
|---|---|---|
| RDF 1.1 with RDFLib-compatible behavior | `xml`, `rdfxml`, `application/rdf+xml` | None added by the writer |
| RDF 1.2 | `xml12`, `xmlrdf12` | Writer adds `rdf:version="1.2"` |
| RDF 1.2 basic profile | `xml12` with `rdf_version="1.2-basic"` | Writer announces `1.2-basic`; no triple terms |

Files ending in `.rdf` or `.xml` select RDF 1.1 unless a format is supplied.
`application/rdf+xml; version=1.2` selects XML12 as an RDFCore extension.
The parser still requires an in-scope `rdf:version` announcement for
RDF 1.2-only constructs, even when `format="xml12"` is explicit.

### Basic use

Read RDF/XML 1.1 and write it back:

```python
from rdfcore import Graph, URIRef

source = '''<rdf:RDF
  xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
  xmlns:e="urn:e:">
  <rdf:Description rdf:about="urn:alice">
    <e:name>Alice</e:name>
  </rdf:Description>
</rdf:RDF>'''
graph = Graph().parse(data=source, format="xml")
assert str(graph.value(URIRef("urn:alice"), URIRef("urn:e:name"))) == "Alice"
xml11 = graph.serialize(format="xml")
assert 'rdf:version=' not in xml11
```

Use the explicit RDF 1.2 writer for triple terms and directional literals:

```python
from rdfcore import Graph, Literal, TripleTerm, URIRef

graph = Graph().add((
    URIRef("urn:statement"), URIRef("urn:describes"),
    TripleTerm(URIRef("urn:s"), URIRef("urn:p"), URIRef("urn:o")),
))
graph.add((URIRef("urn:s"), URIRef("urn:label"),
           Literal("Hello", lang="en", direction="ltr")))
xml = graph.serialize(format="xmlrdf12")
assert 'rdf:version="1.2"' in xml
restored = Graph().parse(data=xml, format="xmlrdf12")
assert graph.isomorphic(restored)
assert (URIRef("urn:s"), URIRef("urn:p"), URIRef("urn:o")) not in restored
```

Triple terms do not assert their embedded triples. XML12 also supports
annotations, multiple reifiers and nested triple terms. The writer announces
1.2 even for an empty graph. With `rdf_version="1.1"`, it omits the
announcement, accepts ordinary RDF 1.1 vocabulary (including predicates named
`rdf:version` or `rdf:annotation`) and rejects RDF 1.2 terms.
An inherited direction in a local 1.1 scope raises an error if it would
produce a directional literal.

### Encodings and output streams

| Operation | `xml` | `xml12` |
|---|---|---|
| Byte input | RDFLib-compatible; decode UTF-32 to text first | UTF-8, UTF-16 and UTF-32, including short reads and byte-order variants |
| `serialize(encoding=...)` | Writes UTF-8 like RDFLib 7.6.0; the argument selects a bytes return | Honors the requested encoding |
| Caller-owned binary sink | Supported | Supported |
| Standard text sink, such as `StringIO` | Raises `TypeError` | Selected before writing |
| Custom sink | Must accept bytes | Bytes by default; use `text_output=True` for text |

For XML12, `text_output=False` requires bytes; `None` enables automatic
selection. Text-wrapper and XML-declaration encodings must agree.
File destinations use binary mode. Sink errors propagate without retrying
partially written output, and caller-owned streams remain open.

```python
from io import StringIO

target = StringIO()
graph.serialize(destination=target, format="xml12")
assert 'rdf:version="1.2"' in target.getvalue()
assert not target.closed

encoded = graph.serialize(format="xml12", encoding="utf-16")
assert graph.isomorphic(Graph().parse(data=encoded, format="xml12"))
```

Encoding declaration/byte-order mismatches raise `SAXParseException`.
XML12 accepts XML 1.1 character references on input, but the writer still
rejects characters forbidden in XML 1.0 with `ValueError`.

### XML literals and RDFLib compatibility

The XML11 parser preserves RDFLib 7.6.0's XMLLiteral handling, including
CDATA conversion, CR normalization and omission of comments, processing
instructions and default namespace undeclarations. XML12 retains comments,
instructions and namespace undeclarations.

Default `xml` parsing keeps RDFLib's permissive grammar behavior;
`strict=True` enables stricter RDF grammar checks. XML12 applies its own
grammar and IRI validation. Neither mode establishes complete conformance.

XML12 rejects predicates that cannot be represented by a legal XML QName.
Use `safe_iris=True` with XML11 to select corrected namespace handling
where the RDFLib-compatible default can produce an invalid XMLNS binding.
Writers use the graph base when `base=None`; an empty base suppresses it.
Prefixes and statement order need not match RDFLib's output.

### Security and resource limits

Both parsers reject DTD declarations and external entities. Caller-owned
input streams remain open after success or failure. Parsing builds a document
tree, so RDF/XML is not a bounded-memory streaming format.
XML nesting is limited to 256 elements, including XMLLiteral content;
the writer also limits deeply nested triple terms.

### Archived W3C fixtures

For archived input only, opt into `legacy_w3c=True`:

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

Recovery assumes 1.2 in unannounced XML12 input and expands empty XMLLiteral
elements (`<br/>` becomes `<br></br>`), including elements emptied by XML11
comment/instruction filtering. In XML11, only expansion applies.
Explicit versions and security checks remain effective.

Use this only for archived input. It does not implement general XML
canonicalization or establish current RDF 1.2 conformance.
See [W3C results](#official-w3c-tests) for current limitations.

## Optional entailment

`rdfcore.semantics.entails()` checks simple graph entailment, including
blank nodes inside triple terms. Optional `rdf` and `rdfs` regimes support
a subset of RDF/RDFS reasoning. Graph operations never infer triples
automatically; dataset inputs must be reduced to a selected graph.

| Option | Behavior |
|---|---|
| `mode="proof"` (default) | Prove supported conclusions; raise `UnsupportedEntailment` when RDF/RDFS rules cannot establish them |
| `mode="decide"` | Add datatype matching and supported countermodel checks; undecided cases still raise `UnsupportedEntailment` |
| `datatypes={XSD.integer, RDF.JSON}` | Recognize additional supported datatypes; other types remain opaque |
| `conclusion=False` in decision mode | Check premise inconsistency, distinct from an empty conclusion |
| `max_steps=N` | Bound internal work; exhaustion raises `EntailmentResourceLimit`, never an assumed `False` |

RDF/RDFS always recognize `xsd:string`, `rdf:langString` and
`rdf:dirLangString`. Unknown requested datatypes raise
`UnsupportedEntailment`; HTML requires the optional HTML extra.
Malformed literal components raise `TypeError` in decision mode.
Value matching follows RDF datatype identity rather than Python coercion.
An ill-typed recognized premise is inconsistent and entails any conclusion.

```python
from rdfcore import Graph, Literal, RDF, URIRef, XSD
from rdfcore.semantics import entails

premise = Graph().add((URIRef("urn:s"), URIRef("urn:p"), URIRef("urn:o")))
conclusion = [(URIRef("urn:p"), RDF.type, RDF.Property)]
assert entails(premise, conclusion, regime="rdf")

source = [(URIRef("urn:s"), URIRef("urn:p"),
           Literal("01", datatype=XSD.integer, normalize=False))]
target = [(URIRef("urn:s"), URIRef("urn:p"),
           Literal("1", datatype=XSD.integer, normalize=False))]
assert entails(source, target, datatypes={XSD.integer}, mode="decide")
assert entails(source, False, datatypes={XSD.integer}, mode="decide") is False
```

General RDF/RDFS reasoning remains incomplete. Work limits bound internal
steps, not elapsed time, memory, blocked input or individual term size.

`semantics.merge_datasets([first, second])` returns a new in-memory dataset
using the [Semantics section 10 merge](https://www.w3.org/TR/2026/CRD-rdf12-semantics-20260924/#x10-rdf-datasets).
It renames blank nodes apart between inputs, preserves sharing within each
input and combines equal IRI graph names. Default graphs stay separate from
named graphs; empty named graphs are omitted. Inputs remain unchanged.
The operation snapshots its inputs and accepts `max_steps`; it is not streaming.

## Graphs and datasets

Use `Graph` for one graph and `Dataset` for named graphs. For a union view,
set `Dataset(default_union=True)`. The RDFLib-compatible `ConjunctiveGraph`
also reads the union, but is deprecated; prefer `Dataset`.

```python
from rdfcore import Dataset, Literal, URIRef

dataset = Dataset()
dataset.add((URIRef("urn:s"), URIRef("urn:p"), Literal("default")))

named = dataset.graph("urn:graph")
named.add((URIRef("urn:s"), URIRef("urn:p"), Literal("named")))

for subject, predicate, obj, graph_name in dataset.quads():
    print(subject, predicate, obj, graph_name)

assert len(named) == 1                       # One named graph.
assert len(list(dataset.triples((None, None, None)))) == 1  # Default graph.
dataset.default_union = True
assert len(list(dataset.triples((None, None, None)))) == 2  # Union.
dataset.remove_context(named)               # Clear triples; retain the graph.
assert len(named) == 0
```

`dataset.remove((s, p, o))` removes matches from all graphs, as in RDFLib.
Use a graph's `remove()` or a four-item pattern to restrict the context.

`graph.value(s, p, default=...)` returns one matching object or the default.
Use `any=False` to require uniqueness and raise `UniquenessError` on ambiguity.

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

`parse()` accepts paths and file-like sources, or text/bytes through `data=`:

```python
from rdfcore import Graph

graph = Graph().parse("input.ttl", format="turtle")
graph.serialize("output.nt", format="nt")
```

Streaming helpers detect gzip, bzip2 and xz from file extensions.

Use an RDF 1.2 serializer for RDF 1.2 terms, or explicitly request conversion:

```python
graph.serialize(format="nt12", rdf_version="1.2")
graph.serialize(format="nt", rdf_version="1.1", downgrade="interop")
```

`downgrade="interop"` re-expresses supported constructs in RDF 1.1.
Unsupported downgrades raise an error; information is not silently discarded.

## Streaming processing

Streaming operations process statements without building a `Graph` or
`Dataset`:

```python
from rdfcore import count, validate

number_of_triples = count("large.nt", "nt")
is_valid = validate("large.nt", "nt")
```

`count()` and `validate()` close files and decompression wrappers they create,
including after errors; caller-owned streams remain open.

`parse_stream()` and `convert()` support N-Triples and N-Quads without an
intermediate graph. Bounded reads do not guarantee bounded total memory:
records, tokens, blank-node label maps and nested terms can grow.

The iterator form of `parse_stream()` uses a worker and one-item queue.
Call `close()` when stopping early. A caller source blocked in `read()`
cannot be forcibly interrupted; close waits at most one second.
The sink form runs without a worker.

Turtle and TriG parsers consume bounded readers, and their RDF 1.2 streaming
serializers are available with `mode="stream"`:

```python
graph.serialize("output.ttl", format="turtle12", mode="stream")
```

Streaming serializers omit pretty grouping and complete-graph sorting.
For existing graphs/datasets, RDF 1.2 serializers scan the required profile
before writing. Direct push writers cannot look ahead: select
`rdf_version="1.2"` before feeding mixed data.

`canonical=True` in Turtle12/TriG12 stream mode suppresses version directives
and lowercases language tags; it neither sorts statements nor canonicalizes
blank nodes. Non-UTF-8 output must be decoded before UTF-8 RDF syntax parsing.

RDF 1.2 serializers select standard text/binary sinks before writing.
For custom sinks, use `text_output=True` or `False`; sink errors propagate
without retry or closure. Direct Turtle/TriG push writers retain their older
text-first fallback when this option is unset.

`convert()` accepts `nt12`, `nq12` and registered RDF 1.1 line-format aliases.
RDF 1.2 output announces 1.2 unless `canonical=True`; writing 1.2 terms to
a 1.1 target raises an error regardless of graph-selection policy.

Conversion rejects input/output aliases of the same file. Missing input or
invalid buffer/policy options do not truncate an existing destination.
Parse/write failures can leave partial output; discard it after failure.

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

`transaction()` commits on success and rolls back on error; nested blocks
use savepoints. Writes outside transactions commit immediately.
`store.add_many(triples, context=None)` consumes input lazily in one transaction
and returns the number of input triples, including duplicates. Generator errors
roll back triples and context registrations. These are RDFCore extensions.

SQLite uses a versioned JSON term codec. Older databases migrate transactionally
through a restricted legacy reader; failed decoding preserves existing data.
Unknown versions are rejected. Back up existing databases before migration.
Language tags compare case-insensitively while metadata retains their first
spelling per context and union. Spelling lost by older releases is unrecoverable.

When serializing a dataset to a graph format, RDFLib's format-specific
projection applies: N-Triples includes its quads as triple statements, while
Turtle and RDF/XML use the default graph unless `default_union=True`.
Serialization uses `Graph.base` when `base` is omitted. Turtle and TriG pretty
and streaming output emit the base declaration and relativize eligible IRIs;
RDF/XML emits `xml:base`. An explicit `base` overrides the graph's base.

Turtle/TriG 1.2 writers shorten IRIs only when they resolve back to the original.
Legacy `turtle`/`trig` retain RDFLib's prefix-stripping behavior, including
a known round-trip defect for partial-path bases. Select corrected handling
with `safe_iris=True`; direct streaming writers use it by default.

`Graph.isomorphic()` follows RDFLib's approximate RDF 1.1 check, which may
return false positives for blank nodes. Use `rdfcore.compare.isomorphic()`
for exact graph/dataset comparison, including nested triple terms and empty
named graphs. The graph method uses exact comparison for RDF 1.2 as an extension.
Symmetric blank-node graphs may still be expensive.

For sorting large streams, use `external_sort()` with a memory budget:

```python
from rdfcore import external_sort, parse_stream
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

`external_sort()` writes temporary runs and merges them in passes;
`max_open_runs` limits open runs per pass. Its budget approximates run size,
not total RSS; one oversized statement can exceed it.
Graphs, datasets, pretty output, isomorphism and canonicalization may retain
or sort the complete graph in memory.

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

`peak_rss_bytes` is an increase in the process high-water mark, not an
isolated operation peak; it can be zero after earlier heavy work.
It does not prove a hard memory bound.

Run the RDFLib comparison benchmark from the project root:

```bash
python benchmarks/compare_rdflib_rdfcore.py --statements 1000 10000 --repeats 3 --warmup 1
python benchmarks/sqlite_bulk.py --statements 10000 --repeats 5 --modes transaction bulk
python benchmarks/memory_queries.py --statements 10000 --repeats 5
```

The comparison covers N-Quads, Turtle and TriG with standard, streaming and
SQLite paths where applicable. Correctness checks run outside timed sections;
serialization excludes parsing. Reports include repeated samples, median
times, versions and revision. Memory figures are traced Python allocations,
not process RSS.

## Tests

Run the complete test suite:

```bash
python -m pytest -q
```

Tests cover formats, streaming, persistence and RDFLib 7.6.0 compatibility.
CI verifies Python 3.10 and 3.14; intermediate versions remain declared supported.
README Python examples also run as tests.

### Official W3C tests

RDF 1.2 support remains partial. Run official suites against a clean checkout
at the revision in [manifest.lock](tests/w3c/manifest.lock):

```bash
python -m tests.w3c.official /path/to/rdf-tests --output conformance-results.json
```

The pinned snapshot is `d5d930b03ee6b63b388d0bb28fdb29ee78a59ec0`
(12 October 2026). Current default-profile results, verified on Python 3.10
and 3.14:

| Scope | Passed | Failed |
|---|---:|---:|
| N-Triples, N-Quads, Turtle and TriG, both RDF versions | 1964 | 0 |
| RDF/XML 1.1 | 164 | 2 |
| RDF/XML 1.2 | 176 | 21 |
| RDF Semantics 1.1 and 1.2 | 125 | 0 |
| Total | 2429 | 23 |

Totals count 2452 suite executions, including repeated tests (1411 unique IDs).
The XML failures comprise four XMLLiteral spelling conflicts, 17 missing-version
annotation fixtures and two disputed expected results. Explicit
`legacy_w3c=True` resolves 21 of them for archived-fixture compatibility;
it does not establish current-spec conformance. General RDF/RDFS reasoning
also remains incomplete beyond the pinned fixtures.

JSON reports separate syntax, entailment and additional checks, retaining
failures and unsupported cases with reasons. The command exits unsuccessfully
if applicable checks fail or remain unsupported. Audit results with:

```bash
python -m tests.w3c.audit --current conformance-results.json --output .w3c/audit.json
```

The separate W3C workflow runs weekly, on relevant pull requests and release
tags, or manually. It uploads reports and snapshot comparisons even on failure.
A green local pytest run is not a conformance certificate.
