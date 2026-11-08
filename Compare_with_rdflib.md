# RDFLib vs RDFCore

Legend: Yes = implemented for the tested scope; Partial = limited or unverified; No = unavailable.
RDFLib reference: 7.6.0. Neither full API parity nor full RDF 1.2 conformance is claimed.
Numbered links point to tests; support is limited to their scope. [API inventory](benchmarks/audit_api.py) lists signatures and remaining gaps.

## Format dispatch

| Format dispatch | RDFLib 7.6.0 | RDFCore | Notes / tests |
| --- | --- | --- | --- |
| MIME `version` parameter | No | 1.1 / 1.2-basic / 1.2 | Explicit RDF profile. |
| HTTP RDF input | Yes | Yes | Versioned MIME and Accept overrides are extensions. [1](tests/compatibility/test_http_input_contracts.py) |
| RDF/XML MIME version | No | Partial | Document announcement required. |
| Explicit datatype value identity | No | Partial | Separate value API; optional HTML parser; no D-entailment. |

## Classes

| Area | RDFLib | RDFCore | Notes / tests |
| --- | ---: | ---: | --- |
| `Graph` | Yes | Yes | [1](tests/compatibility/test_graph_api.py) |
| `Dataset` | Yes | Partial | [1](tests/compatibility/test_dataset_signatures.py) |
| `ConjunctiveGraph` | Yes | Partial | Inherited API gaps. |
| ConjunctiveGraph dispatch and lifecycle | Store/parser overrides | Yes | Store/parser overrides. [1](tests/compatibility/test_conjunctive_dispatch.py) [2](tests/compatibility/test_conjunctive_graph.py) |
| `Store` | Yes | Partial | Unverified protocol. [1](benchmarks/audit_api.py) |
| `Memory` | Yes | Yes | Graph API; raw Store partial. [1](tests/integration/test_store_parity.py) |
| Disk-backed store | Store-dependent | Yes: SQLiteStore | SQLite; raw Store partial. [1](tests/integration/test_store_parity.py) |
| `URIRef` | Yes | Partial | Selected term behavior. |
| `BNode` | Yes | Partial | Selected term behavior. |
| `Literal` | Yes | Partial | Selected term behavior. |
| `Variable` | Yes | Partial | Selected term behavior. |
| `TripleTerm` | No | Partial | RDF 1.2 only. |
| `Namespace` | Yes | Partial | Unverified behavior. [1](benchmarks/audit_api.py) |
| RDF vocabulary registry | Yes | Yes | Shared names + RDF 1.2 additions. [1](tests/compatibility/test_schema_registry.py) |
| `NamespaceManager` | Yes | Partial | [1](tests/compatibility/test_graph_api.py) |
| `Parser` | Yes | Partial | Unverified base API. [1](benchmarks/audit_api.py) |
| `Serializer` | Yes | Partial | Unverified base API. [1](benchmarks/audit_api.py) |
| `InputSource` | Yes | Partial | Unverified base API. [1](benchmarks/audit_api.py) |
| SPARQL | Yes | No | - |
| RDF/XML | Yes | Partial | Partial syntax; no DTDs or byte parity. |
| JSON-LD | Yes | No | - |
| RDFa/Microdata | Partial | No | - |

## `Graph`

| Method | RDFLib | RDFCore | Notes / tests |
| --- | ---: | ---: | --- |
| `add`, `addN`, `remove` | Yes | Yes | [1](tests/compatibility/test_graph_api.py) [2](tests/integration/test_store_parity.py) |
| `triples` | Yes | Yes | [1](tests/compatibility/test_graph_api.py) |
| `graph[term]`, `graph[s:p:o]` | Yes | Yes | No SPARQL paths. [1](tests/compatibility/test_graph_api.py) [2](tests/compatibility/test_graph_slicing.py) |
| `subjects`, `predicates`, `objects` | Yes | Yes | [1](tests/compatibility/test_graph_api.py) [2](tests/compatibility/test_graph_slicing.py) |
| `predicate_objects` | Yes | Yes | [1](tests/compatibility/test_graph_api.py) [2](tests/compatibility/test_graph_slicing.py) |
| `subject_predicates` | Yes | Yes | [1](tests/compatibility/test_graph_api.py) [2](tests/compatibility/test_graph_slicing.py) |
| `subject_objects` | Yes | Yes | [1](tests/compatibility/test_graph_api.py) [2](tests/compatibility/test_graph_slicing.py) |
| `value` | Yes | Partial | Selected selectors; uniqueness diagnostics. |
| `set` | Yes | Yes | [1](tests/compatibility/test_graph_api.py) |
| `+`, `-`, `&`, `*` | Yes | Yes | [1](tests/compatibility/test_graph_algebra.py) |
| `parse` | Yes | Yes | [1](tests/integration/test_rdflib_differential.py) [2](tests/compatibility/test_local_input_and_legacy_writers.py) |
| `serialize` | Yes | Yes | Format-specific projection; explicit dataset policies. [1](tests/integration/test_rdflib_differential.py) |
| `bind`, `namespaces`, `qname` | Yes | Partial | [1](tests/compatibility/test_graph_api.py) |
| `compute_qname`, `absolutize` | Yes | Partial | [1](tests/compatibility/test_graph_api.py) |
| `close` | Yes | Yes | [1](tests/compatibility/test_graph_lifecycle.py) |
| `n3` | Yes | Yes | [1](tests/compatibility/test_graph_api.py) |
| `resource` | Yes | Yes | [1](tests/compatibility/test_graph_api.py) |
| `collection`, `items` | Yes | Yes | [1](tests/compatibility/test_graph_api.py) |
| `transitiveClosure` | Yes | Yes | [1](tests/compatibility/test_graph_api.py) |
| `transitive_subjects`, `transitive_objects` | Yes | Yes | [1](tests/compatibility/test_graph_api.py) |
| `connected`, `all_nodes` | Yes | Yes | [1](tests/compatibility/test_graph_api.py) |
| `isomorphic` method | Approximate | Yes | Approximate RDF 1.1; exact RDF 1.2. [1](tests/compatibility/test_nine_review_fixes.py) |
| `triples_choices` | Yes | Yes | [1](tests/compatibility/test_graph_api.py) |
| `query`, `update` | Yes | No | - |
| `skolemize`, `de_skolemize` | Yes | Yes | [1](tests/compatibility/test_graph_api.py) |
| `commit`, `rollback` | Yes | Yes | SQLite: rollback current block; no inner commit. [1](tests/compatibility/test_graph_lifecycle.py) |
| `open`, `destroy` | Yes | Partial | SQLite destroy unsupported. |

## `Dataset`

| Method | RDFLib | RDFCore | Notes / tests |
| --- | ---: | ---: | --- |
| `add`, `addN`, `remove` | Yes | Partial | [1](tests/compatibility/test_dataset_signatures.py)  [2](tests/compatibility/test_graph_api.py) |
| `triples`, `quads` | Yes | Partial | [1](tests/compatibility/test_dataset_signatures.py)  [2](tests/compatibility/test_graph_api.py) |
| `graphs`, `contexts` | Yes | Partial | [1](tests/compatibility/test_dataset_signatures.py) |
| `graph` | Yes | Partial | [1](tests/compatibility/test_dataset_signatures.py) |
| `default_graph`, `default_context` | Yes | Partial | [1](tests/compatibility/test_dataset_signatures.py) |
| `remove_graph` | Yes | Partial | [1](tests/compatibility/test_dataset_signatures.py) |
| `remove_context(context)` | Yes | Partial | Returns None; retains empty graphs.  [1](tests/compatibility/test_dataset_signatures.py) |
| `get_graph`, `get_context` | Yes | Partial | [1](tests/compatibility/test_dataset_signatures.py) |
| `add_graph` | Yes | Partial | [1](tests/compatibility/test_dataset_signatures.py) |
| `context_id` | Yes | Partial | [1](tests/compatibility/test_dataset_signatures.py) |
| `parse`, `serialize` | Yes | Yes | [1](tests/integration/test_rdflib_differential.py) |
| `bind`, `namespaces`, `qname` | Yes | Partial | [1](tests/compatibility/test_graph_api.py) |
| `query`, `update` | Yes | No | - |
| `commit`, `rollback` | Yes | Yes | SQLite: rollback current block; no inner commit. [1](tests/compatibility/test_graph_lifecycle.py) |

## RDF Terms

| Feature | RDFLib | RDFCore | Notes / tests |
| --- | ---: | ---: | --- |
| `URIRef.n3()` | Yes | Partial | - |
| `URIRef.toPython()` | Yes | Partial | - |
| `URIRef.defrag()` | Yes | Partial | - |
| `BNode.n3()` | Yes | Partial | - |
| `BNode.skolemize()` | Yes | Yes | [1](tests/compatibility/test_graph_api.py) |
| `URIRef.de_skolemize()` | Yes | Yes | [1](tests/compatibility/test_graph_api.py) |
| `Literal.n3()` | Yes | Partial | - |
| `Literal.toPython()` | Yes | Partial | Native objects retained. [1](tests/compatibility/test_literal_native_values.py) |
| `Literal.normalize()` | Yes | Partial | - |
| `Literal.datatype` | Yes | Partial | - |
| `Literal.language` | Yes | Partial | - |
| `Literal.ill_typed` | Yes | Partial | SQLite diagnostics retained; predicate index state preserved. [1](tests/integration/test_sqlite_codec.py) |
| `rdf:JSON` datatype | No | Yes | RDF 1.2 only. [1](tests/formats/test_rdf_json.py) |
| `Literal.direction` | No | Partial | RDF 1.2 only. |
| `TripleTerm` | No | Partial | RDF 1.2 only. |
| Term identity, hashing and ordering | Yes | Partial | Tested term matrix. |
| Literal binary arithmetic | Yes | Partial | Selected datatypes only. |
| Unary Literal `-`, `+`, `abs()` | Yes | Partial | Decimal errors match reference. |
| Namespace prefix collisions and QName resolution | Yes | Partial | [1](tests/compatibility/test_graph_api.py) |
| Collection indexing, deletion and malformed lists | Yes | Partial | Cycles may not terminate.  [1](tests/compatibility/test_graph_api.py) |

## Parsers

| Format | RDFLib | RDFCore | Notes / tests |
| --- | ---: | ---: | --- |
| N-Triples 1.1 | Yes | Yes: nt, nt11 | [1](tests/integration/test_rdflib_differential.py) |
| N-Triples 1.2 | No | Yes: nt12 | [1](tests/formats/test_nt12.py) |
| N-Quads 1.1 | Yes | Yes: nq, nq11, nquads | [1](tests/integration/test_rdflib_differential.py) |
| N-Quads 1.2 | No | Yes: nq12 | [1](tests/formats/test_nq12.py) |
| Turtle 1.1 | Yes | Yes: ttl, turtle, turtle11 | [1](tests/integration/test_rdflib_differential.py) |
| Turtle 1.2 | No | Yes: turtle12 | [1](tests/formats/test_turtle12.py) |
| TriG 1.1 | Yes | Yes: trig, trig11 | [1](tests/integration/test_rdflib_differential.py) |
| TriG 1.2 | No | Yes: trig12 | [1](tests/formats/test_trig12.py) |
| RDF/XML 1.1 | Yes | Partial: `xml`, `rdfxml` | Tree parser; no DTDs. |
| RDF/XML legacy parser dispatch | Yes | Partial | Permissive legacy mode; optional strict checks. |
| XML12 document transport | No UTF-32 bytes | Partial | UTF-8/16/32; buffered tree; limited XML 1.1 output. |
| XML12 IRI validation and local profiles | Permissive IRIs | Partial | IRI validation; local profile checks. |
| RDF/XML XMLLiteral lexical handling | Yes | Partial | Separate XML11/XML12 lexical rules. |
| RDF/XML 1.2 | No | Partial: `xml12`, `xmlrdf12` | Explicit version; partial conformance. |
| Archived W3C XML recovery | No | Partial | Opt-in legacy_w3c; not current conformance. |
| RDF/XML specification/snapshot conflicts | XML 1.1 oracle | Partial | 23 W3C XML failures remain visible. |
| JSON-LD | Yes | No | - |
| RDFa | Partial | No | - |

## Serializers

| Format or feature | RDFLib | RDFCore | Notes / tests |
| --- | ---: | ---: | --- |
| N-Triples 1.1 | Yes | Yes | [1](tests/integration/test_rdflib_differential.py) |
| N-Triples 1.2 | No | Yes | [1](tests/formats/test_canonical_contracts.py) |
| N-Quads 1.1 | Yes | Yes | [1](tests/compatibility/test_conjunctive_formats.py) |
| N-Quads 1.2 | No | Yes | [1](tests/formats/test_canonical_contracts.py) |
| Turtle 1.1 | Yes | Yes | [1](tests/integration/test_rdflib_differential.py) |
| Turtle 1.2 | No | Yes | [1](tests/formats/test_canonical_contracts.py) |
| TriG 1.1 | Yes | Yes | [1](tests/compatibility/test_conjunctive_formats.py) |
| TriG 1.2 | No | Yes | [1](tests/formats/test_canonical_contracts.py) |
| RDF/XML 1.1 | Yes | Partial: `xml`, `rdfxml` | Selected round trips; no byte parity. |
| RDF/XML 1.1 encoding argument | UTF-8 only | Partial | Legacy UTF-8 behavior. |
| XML12 sink error handling | Byte sinks | Partial | Explicit custom text sinks; no TypeError retry. |
| Direct RDF/XML serializer base | Graph base fallback | Partial | Graph base fallback; empty string disables it. |
| Reserved XMLNS predicate output | May emit invalid XMLNS | Partial | Legacy behavior; safe_iris opt-in, default in XML12. |
| XML12 writer with RDF 1.1 profile | RDF 1.1 only | Partial | Rejects RDF 1.2 terms. |
| RDF/XML 1.2 | No | Partial: `xml12`, `xmlrdf12` | Default 1.2; explicit 1.1 / 1.2-basic profiles. |
| RDF/XML writer round trips | RDF 1.1 | Partial | Selected cases; no byte parity. |
| JSON-LD | Yes | No | - |
| Canonical NT/NQ lexical syntax | Partial | Partial | NT12/NQ12 lexical layout only; no RDFC-1.0. |
| RDF12 output sink selection | Legacy modes | Partial | Text/binary sinks; caller retains ownership. |
| Turtle12/TriG12 stream profile | No | Partial | Profile chosen before output; no sorting or RDFC. |
| Turtle/TriG binary stream encoding | No | Partial | Single encoder; decode non-UTF-8 before parsing. |
| `mode="stream"` | No | Partial | Turtle/TriG extension. |
| Safe relative IRI output | May alter relative IRIs | Partial | Opt-in for legacy; default in RDF 1.2. |
| File-like output | Yes | Partial | - |
| Binary output with `encoding` | Yes | Partial | - |

## Stores

| Feature | RDFLib `Memory` | RDFCore `Memory` | RDFCore `SQLiteStore` | Notes / tests |
| --- | ---: | ---: | ---: | --- |
| `add` | Yes | Yes | Yes | [1](tests/integration/test_store_parity.py) |
| `remove` | Yes | Yes | Yes | [1](tests/integration/test_store_parity.py) |
| `triples` | Yes | Yes | Yes | [1](tests/integration/test_store_parity.py) |
| `contexts` | Yes | Yes | Yes | [1](tests/integration/test_store_parity.py) |
| `remove_context` store extension | No | Yes | Yes | Removes registration. [1](tests/integration/test_store_parity.py) |
| SPO index | Yes | Yes | Yes | [1](tests/integration/test_store_parity.py) |
| POS/OSP indexes | Store-dependent | Yes | Yes | [1](tests/integration/test_store_parity.py) |
| Persistence across restarts | Store-dependent | No | Yes | [1](tests/integration/test_sqlite_transactions.py) |
| Equal-term lookup/removal | Yes | Yes | Yes | Includes reopen. [1](tests/integration/test_store_parity.py) |
| Language-tag spelling | Yes | Yes | Yes | First spelling retained. [1](tests/integration/test_store_parity.py) |
| Empty graphs after removal | Yes | Yes | Yes | SQLite retains them after reopen. [1](tests/integration/test_store_parity.py) |
| No full Python materialization | Store-dependent | No | Yes | Queries avoid loading all triples. [1](tests/integration/test_store_parity.py) |
| Atomic lazy bulk ingestion | No | No | Yes | SQLite add_many; contexts roll back too. [1](tests/integration/test_sqlite_transactions.py) |
| Persistence fault handling | Store-dependent | In-memory | Partial | Migration, WAL, locks and crash recovery. |

## RDFCore Extensions

| Component | Purpose |
| --- | --- |
| `parse_stream()` | Push parser and iterator. |
| Iterator resource cleanup | Early-close cancellation; caller streams stay open. |
| Zero-thread line iterator | Prototype only; different read-ahead/plugin behavior. |
| W3C reporting | Pinned suites; per-test failures and skips. |
| `convert()` | Streaming NT/NQ 1.1/1.2; explicit loss policies. |
| `compare.isomorphic()` | Exact graph/dataset comparison; nested terms and empty graphs. |
| Interoperability graph identity | Full/Basic transforms; empty graphs retained; no entailment guarantee. |
| `count()` | Streaming statement count. |
| `validate()` | Streaming syntax check. |
| `external_sort()` | Stable JSON runs; preserves literal state. [1](tests/streaming/test_sort_records.py) |
| `statement_key()` | Stable sort key; no BNode renaming. |
| `benchmark_parse()` | In-process RSS high-water delta. |
| Generated round-trip properties | Bounded Hypothesis cases; Memory/SQLite and interop. [1](tests/integration/test_roundtrip_properties.py) |
| TriG 1.2 from a single Graph | Retains the named graph in both output modes. [1](tests/integration/test_roundtrip_properties.py) |
| `semantics.entails()` | Partial RDF/RDFS reasoning; unknown stays distinct from False. |
| `semantics.entailment_closure()` | Optional finite rules; work budget, no hard memory/time bound. |
| `semantics.merge_datasets()` | Separates input BNodes; preserves graph sharing; omits empty named graphs. |
| `BoundedReadStream` | Bounded read requests. |
| `BoundedWriteStream` | Bounded writes; retries partial progress. |
| `ChunkReader` | Incremental UTF-8. |
| `TokenReader` | Tokens across input chunks. |
| `FilterSink` | Statement filter. |
| `MapSink` | Statement transform. |
| `GraphSink` | Graph adapter. |
| `DatasetSink` | Dataset adapter. |
| `NTStreamingWriter` | N-Triples 1.1; rejects directional literals. |
| `NQStreamingWriter` | N-Quads 1.1; rejects directional literals. |
| `TurtleStreamingWriter` | Turtle writer. |
| `TriGStreamingWriter` | TriG writer. |
| `SQLiteStore` | Disk store. |

## Remaining API work

Legend: missing API only; inherited names may repeat.

| Class | Missing members |
| --- | --- |
| URIRef | `__neg__`, `__or__`, `__truediv__` |
| Graph | `__or__`, `__xor__`, `cbd`, `context_aware`, `default_union`, `formula_aware`, `print`, `query`, `toPython`, `update` |
| Dataset | `__or__`, `__xor__`, `cbd`, `formula_aware`, `print`, `query`, `toPython`, `update` |
| ConjunctiveGraph | `__or__`, `__xor__`, `cbd`, `print`, `query`, `toPython`, `update` |
| NamespaceManager | `__contains__`, `compute_qname_strict`, `curie`, `expand_curie`, `qname_strict`, `reset` |
| Store | `bind`, `contexts`, `create`, `dispatcher`, `gc`, `namespace`, `namespaces`, `node_pickler`, `prefix`, `query`, `remove_graph`, `update` |
| Memory | `bind`, `create`, `dispatcher`, `gc`, `identifier`, `namespace`, `namespaces`, `node_pickler`, `prefix`, `query`, `remove_graph`, `update` |
| Genid | `__neg__`, `__or__`, `__truediv__` |
| RDFLibGenid | `__neg__`, `__or__`, `__truediv__` |
| Serializer | `base`, `encoding`, `relativize` |
| InputSource | `getEncoding`, `getPublicId`, `getSystemId`, `setByteStream`, `setCharacterStream`, `setEncoding`, `setPublicId`, `setSystemId` |
