# RDFLib vs RDFCore

Legend: ✅ implemented within the listed scope, ⚠️ partial or available in a different form, ❌ not implemented. These marks do not certify complete RDFLib parity. The executable reference is RDFLib 7.6.0.

The machine-readable inventory (`python -m benchmarks.audit_api`) separates
missing APIs, RDFCore extensions and present-but-unverified members. It records
signature differences, plugins, exceptions, Python version and revision;
matching signatures are not evidence of behavioral parity.

S13 review regressions cover bulk Store dispatch, calendar subtraction and legacy
duration mapping, graph-node persistence, rollback of context views, schema
rejection and instance-field inventory: [tests](tests/compatibility/test_s13_review_fixes.py).

## Classes

| Format dispatch | RDFLib 7.6.0 | RDFCore | Scope / executable evidence |
| --- | --- | --- | --- |
| MIME `version` parameter | Not registered by default | `1.1`, `1.2-basic`, `1.2`; parsing, serialization, streaming and line-format conversion | — |
| HTTP RDF input | URL parser with format-specific Accept and redirect base | ✅ Differential tests for shared short-name Accept, final URL/publicID and custom base Content-Type with charset; exact parameterized registry entries take priority; versioned MIME and `http_accept` are extensions; not a server negotiation implementation | shared HTTP Accept/redirect/base observations; versioned MIME is an extension; [test_http_input_contracts.py](tests/compatibility/test_http_input_contracts.py) |
| RDF/XML MIME version | Not registered by default | Explicit dispatch extension; document version announcement remains required | — |
| Explicit datatype value identity | No corresponding module | ⚠️ `rdfcore.datatypes`: immutable XSD/JSON/DOM keys, XML 1.1 character handling, optional HTML5 parser; primitive value identity is separate from arithmetic equality; no D-entailment | — |

| Area | RDFLib | RDFCore | Scope / executable evidence |
| --- | ---: | ---: | --- |
| `Graph` | ✅ | ✅ | controlled ordinary/empty/invalid inputs, mutation state, iterator consumption; Memory/SQLite; [test_s13_graph_acceptance.py](tests/compatibility/test_s13_graph_acceptance.py) |
| `Dataset` | ✅ | ✅ | default/named/union, lookup and removal; controlled identifiers and graph retention; [test_remove_context.py](tests/compatibility/test_remove_context.py), [test_dataset_signatures.py](tests/compatibility/test_dataset_signatures.py), [test_context_lookup.py](tests/compatibility/test_context_lookup.py) |
| `ConjunctiveGraph` | ✅ | ⚠️ Core constructor, union/context queries, mutations, store lifecycle and RDF 1.1 parsing/output covered by differential tests; inherited Graph API limitations remain | — |
| ConjunctiveGraph dispatch and lifecycle | Store/parser overrides | ✅ Registered store names, overridden bulk writes and context parsers; local file URIs and unnamed streams; removed context caches cleared, including SQLite rollback recovery | six reviewed dispatch/cache regressions and SQLite rollback; [test_s14_review.py](tests/compatibility/test_s14_review.py) |
| `Store` | ✅ | ⚠️ | Present but behavior unverified; [inventory](benchmarks/audit_api.py) |
| `Memory` | ✅ | ✅ | Graph-adapted store operations and reopen, not raw Store protocol; [test_store_parity.py](tests/integration/test_store_parity.py) |
| Disk-backed store | Store-dependent | ✅ `SQLiteStore` | Graph-adapted store operations and reopen, not raw Store protocol; [test_store_parity.py](tests/integration/test_store_parity.py) |
| `URIRef` | ✅ | ✅ | selected constructors, class hierarchy and identity; not all inherited str behavior; [test_term_model_matrix.py](tests/compatibility/test_term_model_matrix.py) |
| `BNode` | ✅ | ✅ | selected constructors, class hierarchy and identity; not all inherited str behavior; [test_term_model_matrix.py](tests/compatibility/test_term_model_matrix.py) |
| `Literal` | ✅ | ✅ | selected constructors, class hierarchy and identity; not all inherited str behavior; [test_term_model_matrix.py](tests/compatibility/test_term_model_matrix.py) |
| `Variable` | ✅ | ✅ | selected constructors, class hierarchy and identity; not all inherited str behavior; [test_term_model_matrix.py](tests/compatibility/test_term_model_matrix.py) |
| `TripleTerm` | ❌ | ✅ RDF 1.2 | RDF12 model extension; not exposed by the oracle; [test_rdf12_model_matrix.py](tests/integration/test_rdf12_model_matrix.py) |
| `Namespace` | ✅ | ⚠️ | Present but behavior unverified; [inventory](benchmarks/audit_api.py) |
| RDF vocabulary registry | ✅ RDFLib 7.6.0 names | ✅ Shared `CompoundLiteral`, `direction`, `language`, `PlainLiteral`; additive RDF 1.2 `langRange` | shared RDF vocabulary oracle; additive RDF12 names separately; [test_schema_registry.py](tests/compatibility/test_schema_registry.py) |
| `NamespaceManager` | ✅ | ✅ | prefix collisions, QName caching and resolution, default binding sets and shared Store property; [test_namespace_matrix.py](tests/compatibility/test_namespace_matrix.py), [test_s13_graph_acceptance.py](tests/compatibility/test_s13_graph_acceptance.py) |
| `Parser` | ✅ | ⚠️ | Present but behavior unverified; [inventory](benchmarks/audit_api.py) |
| `Serializer` | ✅ | ⚠️ | Present but behavior unverified; [inventory](benchmarks/audit_api.py) |
| `InputSource` | ✅ | ⚠️ | Present but behavior unverified; [inventory](benchmarks/audit_api.py) |
| SPARQL | ✅ | ❌ | — |
| RDF/XML | ✅ | ⚠️ `xml` / `xml12`; DTDs rejected; complete syntax and byte parity not established | — |
| JSON-LD | ✅ via plugin | ❌ | — |
| RDFa/Microdata | ⚠️ | ❌ | — |

## `Graph`

| Method | RDFLib | RDFCore | Scope / executable evidence |
| --- | ---: | ---: | --- |
| `add`, `addN`, `remove` | ✅ | ✅ `addN` tests include context identity, raw identifiers, duplicates and validation order | controlled ordinary/empty/invalid inputs, mutation state, iterator consumption; Memory/SQLite; [test_s13_graph_acceptance.py](tests/compatibility/test_s13_graph_acceptance.py) |
| `triples` | ✅ | ✅ | controlled ordinary/empty/invalid inputs, mutation state, iterator consumption; Memory/SQLite; [test_s13_graph_acceptance.py](tests/compatibility/test_s13_graph_acceptance.py) |
| `graph[term]`, `graph[s:p:o]` | ✅ | ✅ differential tests for term and slice indexing; SPARQL paths unsupported | controlled ordinary/empty/invalid inputs, mutation state, iterator consumption; Memory/SQLite; [test_s13_graph_acceptance.py](tests/compatibility/test_s13_graph_acceptance.py); slice projections; [test_graph_slicing.py](tests/compatibility/test_graph_slicing.py) |
| `subjects`, `predicates`, `objects` | ✅ | ✅ | controlled ordinary/empty/invalid inputs, mutation state, iterator consumption; Memory/SQLite; [test_s13_graph_acceptance.py](tests/compatibility/test_s13_graph_acceptance.py); slice projections; [test_graph_slicing.py](tests/compatibility/test_graph_slicing.py) |
| `predicate_objects` | ✅ | ✅ | controlled ordinary/empty/invalid inputs, mutation state, iterator consumption; Memory/SQLite; [test_s13_graph_acceptance.py](tests/compatibility/test_s13_graph_acceptance.py); slice projections; [test_graph_slicing.py](tests/compatibility/test_graph_slicing.py) |
| `subject_predicates` | ✅ | ✅ | controlled ordinary/empty/invalid inputs, mutation state, iterator consumption; Memory/SQLite; [test_s13_graph_acceptance.py](tests/compatibility/test_s13_graph_acceptance.py); slice projections; [test_graph_slicing.py](tests/compatibility/test_graph_slicing.py) |
| `subject_objects` | ✅ | ✅ | controlled ordinary/empty/invalid inputs, mutation state, iterator consumption; Memory/SQLite; [test_s13_graph_acceptance.py](tests/compatibility/test_s13_graph_acceptance.py); slice projections; [test_graph_slicing.py](tests/compatibility/test_graph_slicing.py) |
| `value` | ✅ | ⚠️ `tests/compatibility/test_graph_value.py` runs both libraries: Graph/Dataset context isolation with conflicting values in other graphs, Memory/SQLite, default identity, duplicates, repeat calls, lazy access and uniqueness diagnostics; custom-store contexts and diagnostic `StopIteration` handling follow the reference; list and false-y scalar selectors additionally tested with Memory/SQLite; unrelated unverified input types remain outside the scoped claim | — |
| `set` | ✅ | ✅ | controlled ordinary/empty/invalid inputs, mutation state, iterator consumption; Memory/SQLite; [test_s13_graph_acceptance.py](tests/compatibility/test_s13_graph_acceptance.py) |
| `parse` | ✅ | ✅ | selected shared-format input/output types, ownership, invalid inputs, return identities; not full syntax parity; [test_format_contracts.py](tests/compatibility/test_format_contracts.py) |
| `serialize` | ✅ | ✅ legacy default projection and base fallback/override tested against RDFLib; explicit Dataset `dataset_policy` extension; RDF12 graph output/interop defaults to strict graph-name preservation; format-specific output parity remains scoped | selected shared-format input/output types, ownership, invalid inputs, return identities; not full syntax parity; [test_format_contracts.py](tests/compatibility/test_format_contracts.py) |
| `bind`, `namespaces`, `qname` | ✅ | ✅ | prefix collisions, QName caching and resolution, default binding sets and shared Store property; [test_namespace_matrix.py](tests/compatibility/test_namespace_matrix.py), [test_s13_graph_acceptance.py](tests/compatibility/test_s13_graph_acceptance.py) |
| `compute_qname`, `absolutize` | ✅ | ✅ | prefix collisions, QName caching and resolution, default binding sets and shared Store property; [test_namespace_matrix.py](tests/compatibility/test_namespace_matrix.py), [test_s13_graph_acceptance.py](tests/compatibility/test_s13_graph_acceptance.py) |
| `close` | ✅ | ✅ | Store forwarding; SQLite savepoints, reopen, failed configuration changes; destroy explicitly unsupported; [test_graph_lifecycle.py](tests/compatibility/test_graph_lifecycle.py) |
| `n3` | ✅ | ✅ | controlled ordinary/empty/invalid inputs, mutation state, iterator consumption; Memory/SQLite; [test_s13_graph_acceptance.py](tests/compatibility/test_s13_graph_acceptance.py) |
| `resource` | ✅ | ✅ | controlled ordinary/empty/invalid inputs, mutation state, iterator consumption; Memory/SQLite; [test_s13_graph_acceptance.py](tests/compatibility/test_s13_graph_acceptance.py) |
| `collection`, `items` | ✅ | ✅ | controlled ordinary/empty/invalid inputs, mutation state, iterator consumption; Memory/SQLite; [test_s13_graph_acceptance.py](tests/compatibility/test_s13_graph_acceptance.py) |
| `transitiveClosure` | ✅ | ✅ | controlled ordinary/empty/invalid inputs, mutation state, iterator consumption; Memory/SQLite; [test_s13_graph_acceptance.py](tests/compatibility/test_s13_graph_acceptance.py) |
| `transitive_subjects`, `transitive_objects` | ✅ | ✅ | controlled ordinary/empty/invalid inputs, mutation state, iterator consumption; Memory/SQLite; [test_s13_graph_acceptance.py](tests/compatibility/test_s13_graph_acceptance.py) |
| `connected`, `all_nodes` | ✅ | ✅ | controlled ordinary/empty/invalid inputs, mutation state, iterator consumption; Memory/SQLite; [test_s13_graph_acceptance.py](tests/compatibility/test_s13_graph_acceptance.py) |
| `isomorphic` method | ✅ approximate | ✅ same RDF 1.1 approximation; exact comparison for RDF 1.2 data | legacy approximation versus exact RDF12 comparison; [test_nine_review_fixes.py](tests/compatibility/test_nine_review_fixes.py) |
| `triples_choices` | ✅ | ✅ list-only choices, empty-list wildcard, repeated results and errors tested against RDFLib | controlled ordinary/empty/invalid inputs, mutation state, iterator consumption; Memory/SQLite; [test_s13_graph_acceptance.py](tests/compatibility/test_s13_graph_acceptance.py) |
| `query`, `update` | ✅ | ❌ | — |
| `skolemize`, `de_skolemize` | ✅ | ✅ | controlled blank IDs, selective and destination graph modes, Genid dispatch and store identity; [test_s13_graph_acceptance.py](tests/compatibility/test_s13_graph_acceptance.py) |
| `commit`, `rollback` | ✅ | ✅ Store delegation with differential tests; SQLite rollback affects the active savepoint, commit inside transaction contexts raises | Store forwarding; SQLite savepoints, reopen, failed configuration changes; destroy explicitly unsupported; [test_graph_lifecycle.py](tests/compatibility/test_graph_lifecycle.py) |
| `open`, `destroy` | ✅ | ⚠️ Differential Store delegation; SQLite destroy raises NotImplementedError, SQLite open/reopen returns store status codes; missing/corrupt files and nested transactions tested | — |

## `Dataset`

| Method | RDFLib | RDFCore | Scope / executable evidence |
| --- | ---: | ---: | --- |
| `add`, `addN`, `remove` | ✅ | ✅ | default/named/union, lookup and removal; controlled identifiers and graph retention; [test_remove_context.py](tests/compatibility/test_remove_context.py), [test_dataset_signatures.py](tests/compatibility/test_dataset_signatures.py), [test_context_lookup.py](tests/compatibility/test_context_lookup.py); controlled ordinary/empty/invalid inputs, mutation state, iterator consumption; Memory/SQLite; [test_s13_graph_acceptance.py](tests/compatibility/test_s13_graph_acceptance.py) |
| `triples`, `quads` | ✅ | ✅ | default/named/union, lookup and removal; controlled identifiers and graph retention; [test_remove_context.py](tests/compatibility/test_remove_context.py), [test_dataset_signatures.py](tests/compatibility/test_dataset_signatures.py), [test_context_lookup.py](tests/compatibility/test_context_lookup.py); controlled ordinary/empty/invalid inputs, mutation state, iterator consumption; Memory/SQLite; [test_s13_graph_acceptance.py](tests/compatibility/test_s13_graph_acceptance.py) |
| `graphs`, `contexts` | ✅ | ✅ | default/named/union, lookup and removal; controlled identifiers and graph retention; [test_remove_context.py](tests/compatibility/test_remove_context.py), [test_dataset_signatures.py](tests/compatibility/test_dataset_signatures.py), [test_context_lookup.py](tests/compatibility/test_context_lookup.py) |
| `graph` | ✅ | ✅ | default/named/union, lookup and removal; controlled identifiers and graph retention; [test_remove_context.py](tests/compatibility/test_remove_context.py), [test_dataset_signatures.py](tests/compatibility/test_dataset_signatures.py), [test_context_lookup.py](tests/compatibility/test_context_lookup.py) |
| `default_graph`, `default_context` | ✅ | ✅ | default/named/union, lookup and removal; controlled identifiers and graph retention; [test_remove_context.py](tests/compatibility/test_remove_context.py), [test_dataset_signatures.py](tests/compatibility/test_dataset_signatures.py), [test_context_lookup.py](tests/compatibility/test_context_lookup.py) |
| `remove_graph` | ✅ | ✅ | default/named/union, lookup and removal; controlled identifiers and graph retention; [test_remove_context.py](tests/compatibility/test_remove_context.py), [test_dataset_signatures.py](tests/compatibility/test_dataset_signatures.py), [test_context_lookup.py](tests/compatibility/test_context_lookup.py) |
| `remove_context(context)` | ✅ | ✅ `Dataset` and `ConjunctiveGraph`; RDFLib 7.6.0 differential tests, return `None`, retain empty graphs | default/named/union, lookup and removal; controlled identifiers and graph retention; [test_remove_context.py](tests/compatibility/test_remove_context.py), [test_dataset_signatures.py](tests/compatibility/test_dataset_signatures.py), [test_context_lookup.py](tests/compatibility/test_context_lookup.py) |
| `get_graph`, `get_context` | ✅ | ✅ | default/named/union, lookup and removal; controlled identifiers and graph retention; [test_remove_context.py](tests/compatibility/test_remove_context.py), [test_dataset_signatures.py](tests/compatibility/test_dataset_signatures.py), [test_context_lookup.py](tests/compatibility/test_context_lookup.py) |
| `add_graph` | ✅ | ✅ | default/named/union, lookup and removal; controlled identifiers and graph retention; [test_remove_context.py](tests/compatibility/test_remove_context.py), [test_dataset_signatures.py](tests/compatibility/test_dataset_signatures.py), [test_context_lookup.py](tests/compatibility/test_context_lookup.py) |
| `context_id` | ✅ | ✅ differential tests for resolution, empty identifiers, and invalid URI arguments | default/named/union, lookup and removal; controlled identifiers and graph retention; [test_remove_context.py](tests/compatibility/test_remove_context.py), [test_dataset_signatures.py](tests/compatibility/test_dataset_signatures.py), [test_context_lookup.py](tests/compatibility/test_context_lookup.py) |
| `parse`, `serialize` | ✅ | ✅ | selected shared-format input/output types, ownership, invalid inputs, return identities; not full syntax parity; [test_format_contracts.py](tests/compatibility/test_format_contracts.py) |
| `bind`, `namespaces`, `qname` | ✅ | ✅ | prefix collisions, QName caching and resolution, default binding sets and shared Store property; [test_namespace_matrix.py](tests/compatibility/test_namespace_matrix.py), [test_s13_graph_acceptance.py](tests/compatibility/test_s13_graph_acceptance.py) |
| `query`, `update` | ✅ | ❌ | — |
| `commit`, `rollback` | ✅ | ✅ Differential Store delegation; explicit SQLite savepoint semantics | Store forwarding; SQLite savepoints, reopen, failed configuration changes; destroy explicitly unsupported; [test_graph_lifecycle.py](tests/compatibility/test_graph_lifecycle.py) |

## RDF Terms

| Feature | RDFLib | RDFCore | Scope / executable evidence |
| --- | ---: | ---: | --- |
| `URIRef.n3()` | ✅ | ✅ | controlled lexical forms, native types and N3; [test_term_conversions.py](tests/compatibility/test_term_conversions.py) |
| `URIRef.toPython()` | ✅ | ✅ differential tests | controlled lexical forms, native types and N3; [test_term_conversions.py](tests/compatibility/test_term_conversions.py) |
| `URIRef.defrag()` | ✅ | ✅ differential tests, including return identity | fragment removal and return identity; [test_uriref_helpers.py](tests/compatibility/test_uriref_helpers.py) |
| `BNode.n3()` | ✅ | ✅ | controlled lexical forms, native types and N3; [test_term_conversions.py](tests/compatibility/test_term_conversions.py) |
| `BNode.skolemize()` | ✅ | ✅ | controlled blank IDs, selective and destination graph modes, Genid dispatch and store identity; [test_s13_graph_acceptance.py](tests/compatibility/test_s13_graph_acceptance.py) |
| `URIRef.de_skolemize()` | ✅ | ✅ | controlled blank IDs, selective and destination graph modes, Genid dispatch and store identity; [test_s13_graph_acceptance.py](tests/compatibility/test_s13_graph_acceptance.py) |
| `Literal.n3()` | ✅ | ✅ | lexical escaping, metadata, multiline strings and numeric special values; import prefixes distinguished; [test_term_representations.py](tests/compatibility/test_term_representations.py) |
| `Literal.toPython()` | ✅ | ✅ | numeric/string/temporal matrix, calendar/fixed durations, normalization, native types and errors; [test_literal_arithmetic.py](tests/compatibility/test_literal_arithmetic.py), [test_literal_unary.py](tests/compatibility/test_literal_unary.py), [test_literal_matrix.py](tests/compatibility/test_literal_matrix.py) |
| `Literal.normalize()` | ✅ | ✅ | numeric/string/temporal matrix, calendar/fixed durations, normalization, native types and errors; [test_literal_arithmetic.py](tests/compatibility/test_literal_arithmetic.py), [test_literal_unary.py](tests/compatibility/test_literal_unary.py), [test_literal_matrix.py](tests/compatibility/test_literal_matrix.py) |
| `Literal.datatype` | ✅ | ✅ | numeric/string/temporal matrix, calendar/fixed durations, normalization, native types and errors; [test_literal_arithmetic.py](tests/compatibility/test_literal_arithmetic.py), [test_literal_unary.py](tests/compatibility/test_literal_unary.py), [test_literal_matrix.py](tests/compatibility/test_literal_matrix.py) |
| `Literal.language` | ✅ | ✅ | numeric/string/temporal matrix, calendar/fixed durations, normalization, native types and errors; [test_literal_arithmetic.py](tests/compatibility/test_literal_arithmetic.py), [test_literal_unary.py](tests/compatibility/test_literal_unary.py), [test_literal_matrix.py](tests/compatibility/test_literal_matrix.py) |
| `Literal.ill_typed` | ✅ | ✅ | numeric/string/temporal matrix, calendar/fixed durations, normalization, native types and errors; [test_literal_arithmetic.py](tests/compatibility/test_literal_arithmetic.py), [test_literal_unary.py](tests/compatibility/test_literal_unary.py), [test_literal_matrix.py](tests/compatibility/test_literal_matrix.py) |
| `rdf:JSON` datatype | ❌ in RDFLib 7.6.0 | ✅ RDF 1.2 | RDF12 datatype extension; no RDFLib oracle; [test_rdf_json.py](tests/formats/test_rdf_json.py) |
| `Literal.direction` | ❌ in RDFLib 7.6.0 | ✅ RDF 1.2 | RDF12 model extension, separate from legacy acceptance; [test_rdf12_model_matrix.py](tests/integration/test_rdf12_model_matrix.py) |
| `TripleTerm` | ❌ in RDFLib 7.6.0 | ✅ | RDF12 model extension, separate from legacy acceptance; [test_rdf12_model_matrix.py](tests/integration/test_rdf12_model_matrix.py) |
| Term identity, hashing and ordering | ✅ | ✅ tested constructor and comparison matrices, including term-subclass ordering, in `tests/compatibility/` | constructor-kind equality, order and hash matrix; [test_term_model_matrix.py](tests/compatibility/test_term_model_matrix.py) |
| Literal binary arithmetic | ✅ | ✅ Selected numeric/string/date/time/duration matrix; conversion and normalization included, no full datatype coverage claim | numeric/string/temporal matrix, calendar/fixed durations, normalization, native types and errors; [test_literal_arithmetic.py](tests/compatibility/test_literal_arithmetic.py), [test_literal_unary.py](tests/compatibility/test_literal_unary.py), [test_literal_matrix.py](tests/compatibility/test_literal_matrix.py) |
| Unary Literal `-`, `+`, `abs()` | ✅ | ✅ `tests/compatibility/test_literal_unary.py`, executable oracle including bool, Decimal errors and datatype changes | numeric/string/temporal matrix, calendar/fixed durations, normalization, native types and errors; [test_literal_arithmetic.py](tests/compatibility/test_literal_arithmetic.py), [test_literal_unary.py](tests/compatibility/test_literal_unary.py), [test_literal_matrix.py](tests/compatibility/test_literal_matrix.py) |
| Namespace prefix collisions and QName resolution | ✅ | ✅ executable differential matrices | prefix collisions, QName caching and resolution, default binding sets and shared Store property; [test_namespace_matrix.py](tests/compatibility/test_namespace_matrix.py), [test_s13_graph_acceptance.py](tests/compatibility/test_s13_graph_acceptance.py) |
| Collection indexing, deletion and malformed lists | ✅ | ✅ executable differential matrices; cyclic lists may not terminate, as in the reference | controlled list cells, empty/malformed/false values, errors and mutation state; native stores; [test_collection_matrix.py](tests/compatibility/test_collection_matrix.py), [test_s13_graph_acceptance.py](tests/compatibility/test_s13_graph_acceptance.py) |

## Parsers

| Format | RDFLib | RDFCore | Scope / executable evidence |
| --- | ---: | ---: | --- |
| N-Triples 1.1 | ✅ `nt` | ✅ `nt`, `nt11` | selected shared-format input/output types, ownership, invalid inputs, return identities; not full syntax parity; [test_format_contracts.py](tests/compatibility/test_format_contracts.py) |
| N-Triples 1.2 | ❌ | ✅ `nt12` | RDF12 local syntax cases; full suite status is separate; [test_nt12.py](tests/formats/test_nt12.py) |
| N-Quads 1.1 | ✅ `nquads` | ✅ `nquads`, `nq`, `nq11`, `application/n-quads` | selected shared-format input/output types, ownership, invalid inputs, return identities; not full syntax parity; [test_format_contracts.py](tests/compatibility/test_format_contracts.py) |
| N-Quads 1.2 | ❌ | ✅ `nq12` | RDF12 local syntax cases; full suite status is separate; [test_nq12.py](tests/formats/test_nq12.py) |
| Turtle 1.1 | ✅ `turtle`, `ttl` | ✅ `turtle`, `turtle11` | selected shared-format input/output types, ownership, invalid inputs, return identities; not full syntax parity; [test_format_contracts.py](tests/compatibility/test_format_contracts.py) |
| Turtle 1.2 | ❌ | ✅ `turtle12` | RDF12 local syntax cases; full suite status is separate; [test_turtle12.py](tests/formats/test_turtle12.py) |
| TriG 1.1 | ✅ `trig` | ✅ `trig`, `trig11` | selected shared-format input/output types, ownership, invalid inputs, return identities; not full syntax parity; [test_format_contracts.py](tests/compatibility/test_format_contracts.py) |
| TriG 1.2 | ❌ | ✅ `trig12` | RDF12 local syntax cases; full suite status is separate; [test_trig12.py](tests/formats/test_trig12.py) |
| RDF/XML 1.1 | ✅ `xml`, `rdfxml` | ⚠️ `xml`, `rdfxml`; secure tree parser, no DTDs | — |
| RDF/XML legacy parser dispatch | Executable reference: 7.6.0 | ⚠️ Differential cases cover unqualified attributes/elements, ignored root attributes/resource text, relative datatype/type IRIs and repeated property IDs; `strict=True` retains stricter RDF grammar checks | — |
| XML12 document transport | Legacy UTF-32 bytes unsupported | ⚠️ UTF-8/16/32, short reads, XML 1.1 line ends/restricted references, encoding mismatch and DTD rejection tested; buffered tree parser; writer still rejects XML 1.0-forbidden literal characters | — |
| XML12 IRI validation and local profiles | XML11 keeps reference-compatible permissive IRI handling | ✅ XML12 validates expanded IRI references before resolution and rejects directional literal emission in a local 1.1 scope | XML12 IRI/profile extension; [test_rdfxml_scope_regressions.py](tests/formats/test_rdfxml_scope_regressions.py) |
| RDF/XML XMLLiteral lexical handling | Executable reference: 7.6.0 | ⚠️ Differential tests cover CR text, CDATA, comments, processing instructions and default namespace undeclarations; XML12 keeps separate lexical rules | — |
| RDF/XML 1.2 | ❌ | ⚠️ `xml12`, `xmlrdf12`; same parser, explicit version, triple terms, annotations and direction; full conformance not established | — |
| Archived W3C XML recovery | ❌ | ⚠️ Explicit `legacy_w3c=True`; missing-version recovery in `xml12`, empty XMLLiteral element expansion in `xml`/`xml12`, including elements emptied by XML11 event filtering; reification preserves the expanded term; not current-spec conformance | — |
| RDF/XML specification/snapshot conflicts | XML11 lexical oracle: 7.6.0 | ⚠️ Offline regressions distinguish all 17 reviewed annotation cases, XMLLiteral lexical conflicts and two disputed results; official expectations and failure statuses remain unchanged | — |
| JSON-LD | ✅ plugin | ❌ | — |
| RDFa | ⚠️ | ❌ | — |

## Serializers

| Format or feature | RDFLib | RDFCore | Scope / executable evidence |
| --- | ---: | ---: | --- |
| N-Triples 1.1 | ✅ | ✅ | selected shared-format input/output types, ownership, invalid inputs, return identities; not full syntax parity; [test_format_contracts.py](tests/compatibility/test_format_contracts.py) |
| N-Triples 1.2 | ❌ | ✅ `nt12` | RDF12 lexical layout cases, not RDFC or full syntax conformance; [test_canonical_contracts.py](tests/formats/test_canonical_contracts.py) |
| N-Quads 1.1 | ✅ | ✅ `nquads`, `nq`, `nq11`, `application/n-quads` | selected shared-format input/output types, ownership, invalid inputs, return identities; not full syntax parity; [test_format_contracts.py](tests/compatibility/test_format_contracts.py) |
| N-Quads 1.2 | ❌ | ✅ `nq12` | RDF12 lexical layout cases, not RDFC or full syntax conformance; [test_canonical_contracts.py](tests/formats/test_canonical_contracts.py) |
| Turtle 1.1 | ✅ | ✅ | selected shared-format input/output types, ownership, invalid inputs, return identities; not full syntax parity; [test_format_contracts.py](tests/compatibility/test_format_contracts.py) |
| Turtle 1.2 | ❌ | ✅ `turtle12` | RDF12 lexical layout cases, not RDFC or full syntax conformance; [test_canonical_contracts.py](tests/formats/test_canonical_contracts.py) |
| TriG 1.1 | ✅ | ✅ | selected shared-format input/output types, ownership, invalid inputs, return identities; not full syntax parity; [test_format_contracts.py](tests/compatibility/test_format_contracts.py) |
| TriG 1.2 | ❌ | ✅ `trig12` | RDF12 lexical layout cases, not RDFC or full syntax conformance; [test_canonical_contracts.py](tests/formats/test_canonical_contracts.py) |
| RDF/XML 1.1 | ✅ | ⚠️ `xml`, `rdfxml`; semantic round trips tested, not byte-identical output | — |
| RDF/XML 1.1 encoding argument | UTF-8 output regardless of argument | ✅ Differential tests cover empty/nonempty graphs, bytes/str returns and caller-owned binary streams | legacy return/encoding observations against RDFLib; [test_rdfxml_encoding.py](tests/compatibility/test_rdfxml_encoding.py) |
| XML12 sink error handling | XML11 requires bytes; sink errors propagate | ✅ TextIOBase selected before writing; custom text sinks use `text_output=True`; no retry on TypeError and no caller-stream closure | selected round trips and writer profiles; byte parity not claimed; [test_rdfxml_writer_matrix.py](tests/formats/test_rdfxml_writer_matrix.py) |
| Direct RDF/XML serializer base | Graph base when `base=None`; empty string suppresses it | ✅ Executable differential tests against 7.6.0 | direct XML11 base fallback/override oracle; [test_rdfxml_writer_contracts.py](tests/compatibility/test_rdfxml_writer_contracts.py) |
| Reserved XMLNS predicate output | May emit an invalid namespace binding | ⚠️ Legacy `xml` preserves the reference behavior; `safe_iris=True` selects legal QName splitting or an explicit error; enabled by default in `xml12` | — |
| XML12 writer with RDF 1.1 profile | RDF 1.1 vocabulary in `xml` | ✅ Ordinary version/annotation/annotationNodeID predicates tested against the XML11 oracle; no RDF 1.2 terms enabled | XML11 oracle for ordinary RDF vocabulary predicates; XML12 extension separately; [test_rdfxml_writer_matrix.py](tests/formats/test_rdfxml_writer_matrix.py) |
| RDF/XML 1.2 | ❌ | ⚠️ `xml12`, `xmlrdf12`; same serializer, announces `1.2` by default, respects explicit `1.1` / `1.2-basic` profiles | — |
| RDF/XML writer round trips | RDF 1.1 reference | ✅ Tested XML11 reference parsing and XML12 profiles, Unicode, XMLLiteral, shared BNodes, nested terms and reifiers; XML12 accepts UTF-32 bytes, legacy XML requires decoding; no byte-parity claim | selected round trips and writer profiles; byte parity not claimed; [test_rdfxml_writer_matrix.py](tests/formats/test_rdfxml_writer_matrix.py) |
| JSON-LD | ✅ | ❌ | — |
| Canonical NT/NQ lexical syntax | ⚠️ | ⚠️ `nt12`/`nq12` implement canonical statement layout; legacy NT/NQ flags provide case/string normalization, not strict RDF 1.1 canonical syntax; ordering is separate; no blank-node canonicalization (RDFC-1.0) | — |
| RDF12 output sink selection | Shared legacy behavior remains separate | ✅ NT12/NQ12/Turtle12/TriG12 text/binary selection and `text_output`; no retry after sink TypeError; caller streams remain open | RDFCore streaming/output extension; no corresponding RDFLib stream mode; [test_output_encoding.py](tests/streaming/test_output_encoding.py) |
| Turtle12/TriG12 stream profile | ❌ RDF 1.2 | ✅ Existing graphs select their profile before output; canonical lexical options omit VERSION and lowercase language tags, without statement sorting or RDFC-1.0 | RDFCore streaming/output extension; no corresponding RDFLib stream mode; [test_output_encoding.py](tests/streaming/test_output_encoding.py) |
| Turtle/TriG binary stream encoding | No shared RDFLib stream mode | ✅ One incremental encoder per document; no repeated UTF-16/32 BOM; stateful finalization and caller-sink ownership tested; decode non-UTF-8 output before RDF parsing | RDFCore streaming/output extension; no corresponding RDFLib stream mode; [test_output_encoding.py](tests/streaming/test_output_encoding.py) |
| `mode="stream"` | ❌ | ✅ Turtle/TriG | RDFCore streaming/output extension; no corresponding RDFLib stream mode; [test_output_encoding.py](tests/streaming/test_output_encoding.py) |
| Safe relative IRI output | Prefix stripping can change an IRI on round trip | ⚠️ Legacy Turtle/TriG defaults retained; explicit `safe_iris=True` extension, default in Turtle/TriG 1.2 and direct streaming writers | — |
| File-like output | ✅ | ✅ | selected shared-format input/output types, ownership, invalid inputs, return identities; not full syntax parity; [test_format_contracts.py](tests/compatibility/test_format_contracts.py) |
| Binary output with `encoding` | ✅ | ✅ | selected shared-format input/output types, ownership, invalid inputs, return identities; not full syntax parity; [test_format_contracts.py](tests/compatibility/test_format_contracts.py) |

## Stores

| Feature | RDFLib `Memory` | RDFCore `Memory` | RDFCore `SQLiteStore` | Scope / executable evidence |
| --- | ---: | ---: | ---: | --- |
| `add` | ✅ | ✅ | ✅ | Graph-adapted query/removal observations against RDFLib; raw Store protocol remains partial; [test_store_parity.py](tests/integration/test_store_parity.py) |
| `remove` | ✅ | ✅ | ✅ | Graph-adapted query/removal observations against RDFLib; raw Store protocol remains partial; [test_store_parity.py](tests/integration/test_store_parity.py) |
| `triples` | ✅ | ✅ | ✅ | Graph-adapted query/removal observations against RDFLib; raw Store protocol remains partial; [test_store_parity.py](tests/integration/test_store_parity.py) |
| `contexts` | ✅ | ✅ | ✅ | Graph-adapted query/removal observations against RDFLib; raw Store protocol remains partial; [test_store_parity.py](tests/integration/test_store_parity.py) |
| `remove_context` store extension | ❌ (graph API uses `store.remove`) | ✅ removes graph registration | ✅ removes graph registration | Graph-adapted query/removal observations against RDFLib; raw Store protocol remains partial; [test_store_parity.py](tests/integration/test_store_parity.py) |
| SPO index | ✅ | ✅ | ✅ | Graph-adapted query/removal observations against RDFLib; raw Store protocol remains partial; [test_store_parity.py](tests/integration/test_store_parity.py) |
| POS/OSP indexes | Store-dependent | In-memory | ✅ | Graph-adapted query/removal observations against RDFLib; raw Store protocol remains partial; [test_store_parity.py](tests/integration/test_store_parity.py) |
| Persistence across restarts | Store-dependent | ❌ | ✅ | SQLite extension: atomic state and persistence; [test_sqlite_transactions.py](tests/integration/test_sqlite_transactions.py) |
| Equal integer, boolean and case-insensitive language literals: lookup and removal | ✅ reference | ✅ differential tests | ✅ differential tests including reopen | Graph-adapted query/removal observations against RDFLib; raw Store protocol remains partial; [test_store_parity.py](tests/integration/test_store_parity.py) |
| Original language-tag spelling per context and union | ✅ reference | ✅ | ✅ spelling metadata, including nested terms and reopen | Graph-adapted query/removal observations against RDFLib; raw Store protocol remains partial; [test_store_parity.py](tests/integration/test_store_parity.py) |
| Empty registered contexts after triple removal | ✅ | ✅ | ✅ including reopen | Graph-adapted query/removal observations against RDFLib; raw Store protocol remains partial; [test_store_parity.py](tests/integration/test_store_parity.py) |
| No full Python materialization | Store-dependent | ❌ | ✅ | Graph-adapted query/removal observations against RDFLib; raw Store protocol remains partial; [test_store_parity.py](tests/integration/test_store_parity.py) |
| Atomic lazy bulk ingestion | No RDFCore `add_many` extension | ❌ | ✅ `add_many`, including rollback of contexts | SQLite extension: atomic state and persistence; [test_sqlite_transactions.py](tests/integration/test_sqlite_transactions.py) |

## RDFCore Extensions

| Component | Purpose |
|---|---|
| `parse_stream()` | Push/iterator parser |
| Iterator resource cleanup | Cancellable queue delivery; bounded worker join on early close; caller-owned streams remain open |
| Zero-thread line iterator | Benchmark prototype only; not enabled in the public API |
| W3C reporting | Current and archived pinned fixtures, original fixture hashes, per-test diagnostics and reviewed issue explanations; comparison preserves repeated executions and detects changed regimes, types, recognized datatypes and action/result IRIs; latest refresh adds five passing NT version tests without hiding existing gaps; full RDF 1.2 conformance not established |
| `convert()` | Streaming NT/NQ 1.1/1.2 conversion; explicit graph policies; rejects unsupported downgrade and same-file output; input/preflight failures do not truncate output |
| `compare.isomorphic()` | Exact structural comparison, including nested triple terms and empty named graphs; independent blank-node components paired by structural invariants, with iterative connected matching; symmetric/cyclic/random structures checked against RDFLib's exact function; dataset bases, graph-view caches and namespace bindings are not changed |
| Interoperability graph identity | `basic_encode`, `basic_decode` and explicit downgrade retain empty named graphs without resetting input graph bases; fresh nodes avoid nested and graph-name collisions; incomplete, ambiguous, cyclic or hybrid forms raise explicit errors; informative Interop DNOTE 2026-07-23 mapping, not entailment preservation |
| `count()` | Streaming count; owned input and decompression layers closed on success/error; caller input remains open |
| `validate()` | Streaming validation; same input ownership contract as `count()` |
| `external_sort()` | External-memory sorting |
| `statement_key()` | Stable sorting key |
| `benchmark_parse()` | Benchmark with peak RSS |
| `semantics.entails()` | Legacy proof mode retained; decision mode adds datatype constraints and membership regions, guarded countermodels, vocabulary value aliases, IT congruence/injectivity, infinite-image cardinality checks and free-class countermodels for restricted constructor cycles and unconstrained predicates; syntax constructors unchanged; unknown decisions and resource limits stay distinct; general RDF/RDFS reasoning remains incomplete |
| `semantics.entailment_closure()` | Optional finite RDF/RDFS axioms and rules; no automatic Graph inference; optional work budget (not a time/memory bound) |
| `semantics.merge_datasets()` | Explicit Semantics §10 statement-labelled merge; standardizes blank nodes apart across inputs, preserves graph boundaries and nested-term sharing; input triples, graph views and bases stay unchanged; returns a new in-memory Dataset; empty named graphs omitted; no change to Dataset operators |
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

## Remaining API work

Legend: missing entries are not exposed or claimed as supported. Inherited members may repeat across classes. The inventory records per-member plans.

| Class | Missing members | Next work |
|---|---|---|
| URIRef | `__neg__`, `__or__`, `__truediv__` | SPARQL property-path operators |
| Graph | `__or__`, `__xor__`, `cbd`, `context_aware`, `default_union`, `formula_aware`, `print`, `query`, `toPython`, `update` | SPARQL query/update separately; graph convenience/algebra APIs incrementally |
| Dataset | `__or__`, `__xor__`, `cbd`, `formula_aware`, `print`, `query`, `toPython`, `update` | SPARQL query/update separately; graph convenience/algebra APIs incrementally |
| ConjunctiveGraph | `__or__`, `__xor__`, `cbd`, `identifier`, `namespace_manager`, `print`, `query`, `store`, `toPython`, `update` | SPARQL query/update separately; graph convenience/algebra APIs incrementally |
| NamespaceManager | `__contains__`, `compute_qname_strict`, `curie`, `expand_curie`, `qname_strict`, `reset` | Strict QName/CURIE and reset adapters |
| Store | `bind`, `contexts`, `create`, `dispatcher`, `gc`, `namespace`, `namespaces`, `node_pickler`, `prefix`, `query`, `remove_graph`, `update` | Raw Store/plugin adapters; safe persistence retained |
| Memory | `bind`, `create`, `dispatcher`, `gc`, `identifier`, `namespace`, `namespaces`, `node_pickler`, `prefix`, `query`, `remove_graph`, `update` | Raw Store/plugin adapters; safe persistence retained |
| Genid | `__neg__`, `__or__`, `__truediv__` | SPARQL property-path operators |
| RDFLibGenid | `__neg__`, `__or__`, `__truediv__` | SPARQL property-path operators |
| Serializer | `base`, `encoding`, `relativize` | Dedicated differential scenarios before implementation |
| InputSource | `getEncoding`, `getPublicId`, `getSystemId`, `setByteStream`, `setCharacterStream`, `setEncoding`, `setPublicId`, `setSystemId` | SAX metadata/setter and stream-ownership adapters |
