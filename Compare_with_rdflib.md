# RDFLib vs RDFCore

Legend: ✅ implemented within the listed scope, ⚠️ partial or available in a different form, ❌ not implemented. These marks do not certify complete RDFLib parity. The executable reference is RDFLib 7.6.0.

## Classes

| Format dispatch | RDFLib 7.6.0 | RDFCore |
|---|---|---|
| MIME `version` parameter | Not registered by default | `1.1`, `1.2-basic`, `1.2`; parsing, serialization, streaming and line-format conversion |
| HTTP RDF input | URL parser with format-specific Accept and redirect base | ✅ Differential tests for shared short-name Accept, final URL/publicID and bare Content-Type; versioned MIME and `http_accept` are extensions; not a server negotiation implementation |
| RDF/XML MIME version | Not registered by default | Explicit dispatch extension; document version announcement remains required |
| Explicit datatype value identity | No corresponding module | ⚠️ `rdfcore.datatypes`: immutable XSD/JSON/DOM keys, XML 1.1 character handling, optional HTML5 parser; primitive value identity is separate from arithmetic equality; no D-entailment |

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
| RDF/XML | ✅ | ⚠️ `xml` / `xml12`; DTDs rejected; complete syntax and byte parity not established |
| JSON-LD | ✅ via plugin | ❌ |
| RDFa/Microdata | ⚠️ | ❌ |

## `Graph`

| Method | RDFLib | RDFCore |
|---|---:|---:|
| `add`, `addN`, `remove` | ✅ | ✅ `addN` tests include context identity, raw identifiers, duplicates and validation order |
| `triples` | ✅ | ✅ |
| `graph[term]`, `graph[s:p:o]` | ✅ | ✅ differential tests for term and slice indexing; SPARQL paths unsupported |
| `subjects`, `predicates`, `objects` | ✅ | ✅ |
| `predicate_objects` | ✅ | ✅ |
| `subject_predicates` | ✅ | ✅ |
| `subject_objects` | ✅ | ✅ |
| `value` | ✅ | ✅ |
| `set` | ✅ | ✅ |
| `parse` | ✅ | ✅ |
| `serialize` | ✅ | ✅ base fallback/override tested against RDFLib; format-specific output parity remains scoped |
| `bind`, `namespaces`, `qname` | ✅ | ✅ |
| `compute_qname`, `absolutize` | ✅ | ✅ |
| `close` | ✅ | ✅ |
| `n3` | ✅ | ✅ |
| `resource` | ✅ | ✅ |
| `collection`, `items` | ✅ | ✅ |
| `transitiveClosure` | ✅ | ✅ |
| `transitive_subjects`, `transitive_objects` | ✅ | ✅ |
| `connected`, `all_nodes` | ✅ | ✅ |
| `isomorphic` method | ✅ approximate | ✅ same RDF 1.1 approximation; exact comparison for RDF 1.2 data |
| `triples_choices` | ✅ | ✅ list-only choices, empty-list wildcard, repeated results and errors tested against RDFLib |
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
| `remove_context(context)` | ✅ | ✅ `Dataset` and `ConjunctiveGraph`; RDFLib 7.6.0 differential tests, return `None`, retain empty graphs |
| `get_graph`, `get_context` | ✅ | ✅ |
| `add_graph` | ✅ | ✅ |
| `context_id` | ✅ | ✅ differential tests for resolution, empty identifiers, and invalid URI arguments |
| `parse`, `serialize` | ✅ | ✅ |
| `bind`, `namespaces`, `qname` | ✅ | ✅ |
| `query`, `update` | ✅ | ❌ |
| `commit`, `rollback` | ✅ | ❌ |

## RDF Terms

| Feature | RDFLib | RDFCore |
|---|---:|---:|
| `URIRef.n3()` | ✅ | ✅ |
| `URIRef.toPython()` | ✅ | ✅ differential tests |
| `URIRef.defrag()` | ✅ | ✅ differential tests, including return identity |
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
| Term identity, hashing and ordering | ✅ | ✅ tested constructor and comparison matrices, including term-subclass ordering, in `tests/compatibility/` |
| Literal arithmetic and complete datatype API | ✅ | ⚠️ incomplete; constructor/value compatibility does not imply arithmetic parity |
| Namespace prefix collisions and QName resolution | ✅ | ✅ executable differential matrices |
| Collection indexing, deletion and malformed lists | ✅ | ✅ executable differential matrices; cyclic lists may not terminate, as in the reference |

## Parsers

| Format | RDFLib | RDFCore |
|---|---:|---:|
| N-Triples 1.1 | ✅ `nt` | ✅ `nt`, `nt11` |
| N-Triples 1.2 | ❌ | ✅ `nt12` |
| N-Quads 1.1 | ✅ `nquads` | ✅ `nquads`, `nq`, `nq11`, `application/n-quads` |
| N-Quads 1.2 | ❌ | ✅ `nq12` |
| Turtle 1.1 | ✅ `turtle`, `ttl` | ✅ `turtle`, `turtle11` |
| Turtle 1.2 | ❌ | ✅ `turtle12` |
| TriG 1.1 | ✅ `trig` | ✅ `trig`, `trig11` |
| TriG 1.2 | ❌ | ✅ `trig12` |
| RDF/XML 1.1 | ✅ `xml`, `rdfxml` | ⚠️ `xml`, `rdfxml`; secure tree parser, no DTDs |
| RDF/XML legacy parser dispatch | Executable reference: 7.6.0 | ⚠️ Differential cases cover unqualified attributes/elements, ignored root attributes/resource text, relative datatype/type IRIs and repeated property IDs; `strict=True` retains stricter RDF grammar checks |
| XML12 document transport | Legacy UTF-32 bytes unsupported | ⚠️ UTF-8/16/32, short reads, XML 1.1 line ends/restricted references, encoding mismatch and DTD rejection tested; buffered tree parser; writer still rejects XML 1.0-forbidden literal characters |
| RDF/XML XMLLiteral lexical handling | Executable reference: 7.6.0 | ⚠️ Differential tests cover CR text, CDATA, comments, processing instructions and default namespace undeclarations; XML12 keeps separate lexical rules |
| RDF/XML 1.2 | ❌ | ⚠️ `xml12`, `xmlrdf12`; same parser, explicit version, triple terms, annotations and direction; full conformance not established |
| Archived W3C XML recovery | ❌ | ⚠️ Explicit `legacy_w3c=True`; missing-version recovery in `xml12`, empty XMLLiteral element expansion in `xml`/`xml12`; not current-spec conformance |
| RDF/XML specification/snapshot conflicts | XML11 lexical oracle: 7.6.0 | ⚠️ Offline regressions distinguish all 17 reviewed annotation cases, XMLLiteral lexical conflicts and two disputed results; official expectations and failure statuses remain unchanged |
| JSON-LD | ✅ plugin | ❌ |
| RDFa | ⚠️ | ❌ |

## Serializers

| Format or feature | RDFLib | RDFCore |
|---|---:|---:|
| N-Triples 1.1 | ✅ | ✅ |
| N-Triples 1.2 | ❌ | ✅ `nt12` |
| N-Quads 1.1 | ✅ | ✅ `nquads`, `nq`, `nq11`, `application/n-quads` |
| N-Quads 1.2 | ❌ | ✅ `nq12` |
| Turtle 1.1 | ✅ | ✅ |
| Turtle 1.2 | ❌ | ✅ `turtle12` |
| TriG 1.1 | ✅ | ✅ |
| TriG 1.2 | ❌ | ✅ `trig12` |
| RDF/XML 1.1 | ✅ | ⚠️ `xml`, `rdfxml`; semantic round trips tested, not byte-identical output |
| RDF/XML 1.1 encoding argument | UTF-8 output regardless of argument | ✅ Differential tests cover empty/nonempty graphs, bytes/str returns and caller-owned binary streams |
| XML12 sink error handling | XML11 requires bytes; sink errors propagate | ✅ TextIOBase selected before writing; custom text sinks use `text_output=True`; no retry on TypeError and no caller-stream closure |
| Direct RDF/XML serializer base | Graph base when `base=None`; empty string suppresses it | ✅ Executable differential tests against 7.6.0 |
| Reserved XMLNS predicate output | May emit an invalid namespace binding | ⚠️ Legacy `xml` preserves the reference behavior; `safe_iris=True` selects legal QName splitting or an explicit error; enabled by default in `xml12` |
| XML12 writer with RDF 1.1 profile | RDF 1.1 vocabulary in `xml` | ✅ Ordinary version/annotation/annotationNodeID predicates tested against the XML11 oracle; no RDF 1.2 terms enabled |
| RDF/XML 1.2 | ❌ | ⚠️ `xml12`, `xmlrdf12`; same serializer, announces `1.2` by default, respects explicit `1.1` / `1.2-basic` profiles |
| RDF/XML writer round trips | RDF 1.1 reference | ✅ Tested XML11 reference parsing and XML12 profiles, Unicode, XMLLiteral, shared BNodes, nested terms and reifiers; XML12 accepts UTF-32 bytes, legacy XML requires decoding; no byte-parity claim |
| JSON-LD | ✅ | ❌ |
| Canonical NT/NQ lexical syntax | ⚠️ | ✅ explicit `canonical=True`; not blank-node canonicalization (RDFC-1.0) |
| RDF12 output sink selection | Shared legacy behavior remains separate | ✅ NT12/NQ12/Turtle12/TriG12 text/binary selection and `text_output`; no retry after sink TypeError; caller streams remain open |
| Turtle12/TriG12 stream profile | ❌ RDF 1.2 | ✅ Existing graphs select their profile before output; canonical lexical options omit VERSION and lowercase language tags, without statement sorting or RDFC-1.0 |
| `mode="stream"` | ❌ | ✅ Turtle/TriG |
| Safe relative IRI output | Prefix stripping can change an IRI on round trip | ⚠️ Legacy Turtle/TriG defaults retained; explicit `safe_iris=True` extension, default in Turtle/TriG 1.2 and direct streaming writers |
| File-like output | ✅ | ✅ |
| Binary output with `encoding` | ✅ | ✅ |

## Stores

| Feature | RDFLib `Memory` | RDFCore `Memory` | RDFCore `SQLiteStore` |
|---|---:|---:|---:|
| `add` | ✅ | ✅ | ✅ |
| `remove` | ✅ | ✅ | ✅ |
| `triples` | ✅ | ✅ | ✅ |
| `contexts` | ✅ | ✅ | ✅ |
| `remove_context` store extension | ❌ (graph API uses `store.remove`) | ✅ removes graph registration | ✅ removes graph registration |
| SPO index | ✅ | ✅ | ✅ |
| POS/OSP indexes | Store-dependent | In-memory | ✅ |
| Persistence across restarts | Store-dependent | ❌ | ✅ |
| Equal integer, boolean and case-insensitive language literals: lookup and removal | ✅ reference | ✅ differential tests | ✅ differential tests including reopen |
| Original language-tag spelling per context and union | ✅ reference | ✅ | ✅ spelling metadata, including nested terms and reopen |
| Empty registered contexts after triple removal | ✅ | ✅ | ✅ including reopen |
| No full Python materialization | Store-dependent | ❌ | ✅ |
| Atomic lazy bulk ingestion | No RDFCore `add_many` extension | ❌ | ✅ `add_many`, including rollback of contexts |

## RDFCore Extensions

| Component | Purpose |
|---|---|
| `parse_stream()` | Push/iterator parser |
| Iterator resource cleanup | Cancellable queue delivery; bounded worker join on early close; caller-owned streams remain open |
| Zero-thread line iterator | Benchmark prototype only; not enabled in the public API |
| W3C reporting | Current and archived pinned fixtures, original fixture hashes, per-test diagnostics and reviewed issue explanations; comparison preserves repeated executions and detects changed regimes, types, recognized datatypes and action/result IRIs; latest refresh adds five passing NT version tests without hiding existing gaps; full RDF 1.2 conformance not established |
| `convert()` | Streaming NT/NQ 1.1/1.2 conversion; explicit graph policies; rejects unsupported downgrade and same-file output; input/preflight failures do not truncate output |
| `compare.isomorphic()` | Exact structural comparison, including nested triple terms and empty named graphs; iterative blank-node matching, ground set comparison; dataset bases, graph-view caches and namespace bindings are not changed |
| Interoperability graph identity | `basic_encode`, `basic_decode` and explicit downgrade retain empty named graphs |
| `count()` | Streaming count; owned input and decompression layers closed on success/error; caller input remains open |
| `validate()` | Streaming validation; same input ownership contract as `count()` |
| `external_sort()` | External-memory sorting |
| `statement_key()` | Stable sorting key |
| `benchmark_parse()` | Benchmark with peak RSS |
| `semantics.entails()` | Simple entailment and partial positive RDF/RDFS proofs; unsupported decisions raise; optional `max_steps`, distinct `EntailmentResourceLimit` |
| `semantics.entailment_closure()` | Optional finite RDF/RDFS axioms and rules; no automatic Graph inference; optional work budget (not a time/memory bound) |
| `BoundedReadStream` | Bounded reads |
| `BoundedWriteStream` | Bounded writes with partial-write retries and progress validation, including compressed output |
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
