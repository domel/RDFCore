# RDF 1.2 coverage

Reviewed 2026-10-17. This is a requirements inventory and evidence map, not a
conformance certificate. Coverage is partial. The official snapshot is pinned
in `tests/w3c/manifest.lock`; it predates several selected published documents.
Every failed, unsupported, and operationally erroneous execution is retained
in [conformance-results.json](conformance-results.json).

Statuses: `implemented` means the named, limited behavior has local tests;
`partial` means applicable requirements or official evidence remain incomplete;
`missing` means no implementation; `not-applicable-with-reason` identifies
informative material without a separate implementation requirement.

## Selected documents

| Document | Published baseline | Scope/status |
|---|---|---|
| [What's New](https://w3c.github.io/rdf-new/spec/) | Informative draft, inspected 2026-10-17 | not-applicable-with-reason: overview, not a normative oracle |
| [Concepts](https://www.w3.org/TR/2026/CR-rdf12-concepts-20260407/) | CR 2026-04-07 | partial |
| [N-Quads](https://www.w3.org/TR/2026/WD-rdf12-n-quads-20261010/) | WD 2026-10-10 | partial |
| [N-Triples](https://www.w3.org/TR/2026/WD-rdf12-n-triples-20261007/) | WD 2026-10-07 | partial |
| [Primer](https://www.w3.org/TR/2026/DNOTE-rdf12-primer-20260917/) | Note draft 2026-09-17 | not-applicable-with-reason: informative examples |
| [Schema](https://www.w3.org/TR/2026/WD-rdf12-schema-20261010/) | WD 2026-10-10 | partial |
| [Semantics](https://www.w3.org/TR/2026/CRD-rdf12-semantics-20260924/) | CRD 2026-09-24 | partial |
| [TriG](https://www.w3.org/TR/2026/WD-rdf12-trig-20261007/) | WD 2026-10-07 | partial |
| [Turtle](https://www.w3.org/TR/2026/WD-rdf12-turtle-20261007/) | WD 2026-10-07 | partial |
| [XML](https://www.w3.org/TR/2026/WD-rdf12-xml-20261009/) | WD 2026-10-09 | partial |
| [Interoperability](https://www.w3.org/TR/2026/DNOTE-rdf12-interop-20260723/) | Note draft 2026-07-23 | partial: explicit transformations, not a normative conformance regime |

## Requirements and evidence

Section links use the selected document family above. Each row inherits its
document revision. Rows are grouped requirements; exhaustive clause-level
decomposition remains outstanding.

| Specification/section | Expected behavior | Implementation | Evidence | Status |
|---|---|---|---|---|
| [Concepts terms](https://www.w3.org/TR/rdf12-concepts/#section-triples) | Resource subjects, IRI predicates, legal objects | `term.py`, `graph.py` | `test_rdf12_terms.py` | partial: shared generalized RDFLib behavior requires explicit syntax validation |
| [Concepts triple terms](https://www.w3.org/TR/rdf12-concepts/#section-triple-terms) | Nested, immutable structural terms; no implied assertion | `TripleTerm` | term, comparison, XML and semantics tests | implemented |
| [Concepts literals](https://www.w3.org/TR/rdf12-concepts/#section-Graph-Literal) | Language/direction/datatype identity | `Literal` | directional and literal matrices | partial: complete BCP47 and datatype audit outstanding |
| [Concepts JSON](https://www.w3.org/TR/rdf12-concepts/#section-json) | I-JSON lexical space, duplicate rejection, double values | `term.py` | `test_rdf_json.py` | partial: noncharacters and datatype entailment require further evidence |
| [Concepts graph comparison](https://www.w3.org/TR/rdf12-concepts/#graph-isomorphism) | Consistent blank-node renaming, including nested terms | `compare.py` | `test_compare.py` | partial: large symmetric graphs not exhaustively evaluated |
| [N-Triples grammar](https://www.w3.org/TR/rdf12-n-triples/#sec-grammar) | Parse and emit legal terms, whitespace, escapes | `ntriples.py`, `nt12.py` | format tests, official report | partial |
| [N-Triples version](https://www.w3.org/TR/rdf12-n-triples/#sec-version) | Case-sensitive version announcement and profile checks | `NT12Parser` | `test_nt12.py` | partial: full announcement semantics review outstanding |
| [N-Triples canonical form](https://www.w3.org/TR/rdf12-n-triples/#canonical-ntriples) | Canonical lexical syntax | `NT12Serializer` | official C14N tests | partial: canonical blank-node identity remains unresolved |
| [N-Quads grammar](https://www.w3.org/TR/rdf12-n-quads/#sec-grammar) | Preserve graph names and default graph | `nquads12.py`, `nq12.py` | format, store parity, official report | partial |
| [N-Quads conformance](https://www.w3.org/TR/rdf12-n-quads/#conformance) | Reject illegal positions and malformed labels | line parser | format tests, official report | partial |
| [Turtle grammar](https://www.w3.org/TR/rdf12-turtle/#sec-grammar) | All legal terms, collections and property lists | `notation3.py`, `turtle12.py` | format and official tests | partial |
| [Turtle reification](https://www.w3.org/TR/rdf12-turtle/#reifying-triples) | Explicit/anonymous reifiers; multiple relationships | `Turtle12Parser` | `test_rdf12_annotation_matrix.py` | implemented for tested forms |
| [Turtle annotations](https://www.w3.org/TR/rdf12-turtle/#annotation-syntax) | Multiple blocks/reifiers, nesting, assertion expansion | `Turtle12Parser` | annotation and official tests | partial: exhaustive grammar proof absent |
| [TriG grammar](https://www.w3.org/TR/rdf12-trig/#sec-grammar) | Turtle additions with graph-local expansion | `TriG12Parser` | named-graph and official tests | partial |
| [XML grammar](https://www.w3.org/TR/rdf12-xml/#section-grammar-productions) | Node/property attributes, base, language, parseType | `rdfxml.py` plugins | `test_rdfxml.py`, official report | partial |
| [XML triple terms](https://www.w3.org/TR/rdf12-xml/#parseTypeTriplePropertyElt) | parseType Triple creates an unasserted triple term | `RDFXML12Parser`, `XML12Serializer` | nested roundtrip and non-assertion tests | implemented for tested forms |
| [XML conformance](https://www.w3.org/TR/rdf12-xml/#section-conformance) | Version announcement required for new features | XML context handling | XML positive/negative tests | partial: pinned tests predate this requirement |
| [XML security](https://www.w3.org/TR/rdf12-xml/#security) | No external entity/network expansion | Expat declaration guard | UTF-8/UTF-16 DTD tests | implemented: DTDs forbidden; tree memory proportional to input |
| [Semantics simple interpretations](https://www.w3.org/TR/rdf12-semantics/#simpleinterpretations) | Existential blank-node matching and transparent nested terms | `semantics.entails` | `test_semantics.py`, official subset | partial |
| [Semantics RDF](https://www.w3.org/TR/rdf12-semantics/#rdf-interpretations) | RDF axioms and entailment | `semantics.py` | optional-rule tests | partial: complete axioms and negative decisions missing |
| [Semantics RDFS](https://www.w3.org/TR/rdf12-semantics/#rdfs-interpretations) | RDFS hierarchy, domain/range and typing | `entailment_closure` | positive proofs and unsupported decisions | partial |
| [Semantics datatypes](https://www.w3.org/TR/rdf12-semantics/#datatype-interpretations) | Recognized value spaces, consistency, explosion | none beyond literal conversion | official cases reported unsupported | missing |
| [Schema vocabulary](https://www.w3.org/TR/rdf12-schema/) | RDF/RDFS classes, properties, domain/range | `namespace.py`, optional rules | namespace and semantics tests | partial: vocabulary inventory incomplete |
| [Interop](https://www.w3.org/TR/rdf12-interop/) | Explicit, tested downgrade without silent information loss | `interop.py`, serializer dispatch | `test_interop.py`, version tests | partial: all described transformations not audited |

## Version discrepancies

The locked W3C revision `369a90d1a60c021b746df2e411da0ff36258a758` is kept
unchanged. Its RDF/XML 1.2 positive fixtures include new features without an
in-scope `rdf:version`. The published XML WD dated 2026-10-09, section 3.1,
requires that announcement. The implementation follows the published text;
the older fixtures remain reported as failures, not silently rewritten or
counted as passes. Local XML tests cover announced positive and negative cases.

The XML WD grammar summary and detailed Triple production are inconsistent;
the implementation follows the detailed production and example 22. The XML,
Schema and Semantics Editor's Drafts were inspected during implementation.
Complete published-versus-ED comparisons for the other documents remain open.

## Completion gates still open

Full datatype semantics, inconsistency reasoning, complete RDF/RDFS axioms,
all applicable official tests, exhaustive syntax/profile coverage, and a
complete clause-by-clause matrix are required before claiming full RDF 1.2.
Local pytest success is reported separately from official-suite conformance.
