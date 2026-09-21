# RDFLib vs RDFCore

Legend: ✅ supported, ⚠️ partially supported or available in a different form, ❌ not supported.

## Classes

| Area | RDFLib | RDFCore |
|---|---:|---:|
| `Graph` | ✅ | ✅ |
| `Dataset` | ✅ | ✅ |
| `ConjunctiveGraph` | ✅ | ⚠️ |
| `Store` | ✅ | ✅ |
| `Memory` | ✅ | ✅ |
| Disk-backed store | Store-dependent | ✅ `SQLiteStore` |
| `URIRef` | ✅ | ✅ |
| `BNode` | ✅ | ✅ |
| `Literal` | ✅ | ✅ |
| `Variable` | ✅ | ✅ |
| `TripleTerm` | ❌ | ✅ RDF 1.2 |
| `Namespace` | ✅ | ✅ |
| `NamespaceManager` | ✅ | ✅ |
| `Parser` | ✅ | ✅ |
| `Serializer` | ✅ | ✅ |
| `InputSource` | ✅ | ✅ |
| SPARQL | ✅ | ❌ |
| RDF/XML | ✅ | ❌ |
| JSON-LD | ✅ via plugin | ❌ |
| RDFa/Microdata | ⚠️ | ❌ |

## `Graph`

| Method | RDFLib | RDFCore |
|---|---:|---:|
| `add`, `addN`, `remove` | ✅ | ✅ |
| `triples` | ✅ | ✅ |
| `subjects`, `predicates`, `objects` | ✅ | ✅ |
| `predicate_objects` | ✅ | ✅ |
| `subject_predicates` | ✅ | ✅ |
| `subject_objects` | ✅ | ✅ |
| `value` | ✅ | ✅ |
| `set` | ✅ | ✅ |
| `parse` | ✅ | ✅ |
| `serialize` | ✅ | ✅ |
| `bind`, `namespaces`, `qname` | ✅ | ✅ |
| `compute_qname`, `absolutize` | ✅ | ✅ |
| `close` | ✅ | ✅ |
| `n3` | ✅ | ✅ |
| `resource` | ✅ | ✅ |
| `collection`, `items` | ✅ | ✅ |
| `transitiveClosure` | ✅ | ✅ |
| `transitive_subjects`, `transitive_objects` | ✅ | ✅ |
| `connected`, `all_nodes` | ✅ | ✅ |
| `isomorphic` method | ✅ | ✅ |
| `triples_choices` | ✅ | ✅ |
| `query`, `update` | ✅ | ❌ |
| `skolemize`, `de_skolemize` | ✅ | ✅ |
| `commit`, `rollback` | ✅ | ❌ |
| `open`, `destroy` | ✅ | ❌ |

## `Dataset`

| Method | RDFLib | RDFCore |
|---|---:|---:|
| `add`, `addN`, `remove` | ✅ | ✅ |
| `triples`, `quads` | ✅ | ✅ |
| `graphs`, `contexts` | ✅ | ✅ |
| `graph` | ✅ | ✅ |
| `default_graph`, `default_context` | ✅ | ✅ |
| `remove_graph` | ✅ | ✅ |
| `remove_context` | ✅ | ❌ as a `Dataset` method |
| `get_graph`, `get_context` | ✅ | ✅ |
| `add_graph` | ✅ | ✅ |
| `context_id` | ✅ | ✅ |
| `parse`, `serialize` | ✅ | ✅ |
| `bind`, `namespaces`, `qname` | ✅ | ✅ |
| `query`, `update` | ✅ | ❌ |
| `commit`, `rollback` | ✅ | ❌ |

## RDF Terms

| Feature | RDFLib | RDFCore |
|---|---:|---:|
| `URIRef.n3()` | ✅ | ✅ |
| `URIRef.toPython()` | ✅ | ⚠️ |
| `URIRef.defrag()` | ✅ | ❌ |
| `BNode.n3()` | ✅ | ✅ |
| `BNode.skolemize()` | ✅ | ✅ |
| `URIRef.de_skolemize()` | ✅ | ✅ |
| `Literal.n3()` | ✅ | ✅ |
| `Literal.toPython()` | ✅ | ✅ |
| `Literal.normalize()` | ✅ | ✅ |
| `Literal.datatype` | ✅ | ✅ |
| `Literal.language` | ✅ | ✅ |
| `Literal.ill_typed` | ✅ | ✅ |
| `rdf:JSON` datatype | ❌ in RDFLib 7.6.0 | ✅ RDF 1.2 |
| `Literal.direction` | ❌ in RDFLib 7.6.0 | ✅ RDF 1.2 |
| `TripleTerm` | ❌ in RDFLib 7.6.0 | ✅ |

## Parsers

| Format | RDFLib | RDFCore |
|---|---:|---:|
| N-Triples 1.1 | ✅ `nt` | ✅ `nt`, `nt11` |
| N-Triples 1.2 | ❌ | ✅ `nt12` |
| N-Quads 1.1 | ✅ `nquads` | ✅ `nquads`, `nq11` |
| N-Quads 1.2 | ❌ | ✅ `nq12` |
| Turtle 1.1 | ✅ `turtle`, `ttl` | ✅ `turtle`, `turtle11` |
| Turtle 1.2 | ❌ | ✅ `turtle12` |
| TriG 1.1 | ✅ `trig` | ✅ `trig`, `trig11` |
| TriG 1.2 | ❌ | ✅ `trig12` |
| RDF/XML | ✅ `xml`, `rdfxml` | ❌ |
| JSON-LD | ✅ plugin | ❌ |
| RDFa | ⚠️ | ❌ |

## Serializers

| Format or feature | RDFLib | RDFCore |
|---|---:|---:|
| N-Triples 1.1 | ✅ | ✅ |
| N-Triples 1.2 | ❌ | ✅ `nt12` |
| N-Quads 1.1 | ✅ | ✅ |
| N-Quads 1.2 | ❌ | ✅ `nq12` |
| Turtle 1.1 | ✅ | ✅ |
| Turtle 1.2 | ❌ | ✅ `turtle12` |
| TriG 1.1 | ✅ | ✅ |
| TriG 1.2 | ❌ | ✅ `trig12` |
| RDF/XML | ✅ | ❌ |
| JSON-LD | ✅ | ❌ |
| Canonical NT/NQ | ✅ | ✅ |
| `mode="stream"` | ❌ | ✅ Turtle/TriG |
| File-like output | ✅ | ✅ |
| Binary output with `encoding` | ✅ | ✅ |

## Stores

| Feature | RDFLib `Memory` | RDFCore `Memory` | RDFCore `SQLiteStore` |
|---|---:|---:|---:|
| `add` | ✅ | ✅ | ✅ |
| `remove` | ✅ | ✅ | ✅ |
| `triples` | ✅ | ✅ | ✅ |
| `contexts` | ✅ | ✅ | ✅ |
| `remove_context` | ✅ | ✅ | ✅ |
| SPO index | ✅ | ✅ | ✅ |
| POS/OSP indexes | Store-dependent | In-memory | ✅ |
| Persistence across restarts | Store-dependent | ❌ | ✅ |
| No full Python materialization | Store-dependent | ❌ | ✅ |

## RDFCore Extensions

| Component | Purpose |
|---|---|
| `parse_stream()` | Push/iterator parser |
| `convert()` | Streaming NT/NQ conversion |
| `count()` | Streaming count |
| `validate()` | Streaming validation |
| `external_sort()` | External-memory sorting |
| `statement_key()` | Stable sorting key |
| `benchmark_parse()` | Benchmark with peak RSS |
| `BoundedReadStream` | Bounded reads |
| `BoundedWriteStream` | Bounded writes |
| `ChunkReader` | Chunked UTF-8 reader |
| `TokenReader` | Tokenization across chunk boundaries |
| `FilterSink` | Statement filtering |
| `MapSink` | Statement transformation |
| `GraphSink` | Parser-to-Graph adapter |
| `DatasetSink` | Parser-to-Dataset adapter |
| `NTStreamingWriter` | Streaming N-Triples writer |
| `NQStreamingWriter` | Streaming N-Quads writer |
| `TurtleStreamingWriter` | Streaming Turtle writer |
| `TriGStreamingWriter` | Streaming TriG writer |
| `SQLiteStore` | Disk-backed store |
