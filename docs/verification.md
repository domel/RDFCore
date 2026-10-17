# Verification record

Checked on 2026-10-17 against RDFLib 7.6.0. The checked-in reports record
their source revision and worktree state. The four change groups are separate
commits; committing a group does not close an unmet acceptance gate.

## Local acceptance checks

| Check | Result |
|---|---|
| Python 3.10.12 | 1996 passed |
| Python 3.11.16 | 1996 passed |
| Python 3.12.14 | 1996 passed |
| Python 3.13.15 | 1996 passed |
| Python 3.14.7 | 1996 passed |
| Wheel and source distribution | Built successfully; `twine check` passed |
| Installed wheel outside the repository | Import and RDF/XML 1.2 announcement checked |
| Workflow YAML | Parsed successfully; remote workflow execution not performed |
| README Python examples | Executed against local fixtures |
| NQ, Turtle and TriG benchmarks | 1000 and 10000 statements; 44 measurements; independent correctness checks passed |

The test runs emit warnings, including reference-library deprecations and
deliberately malformed literal diagnostics. No failed test is hidden by an
xfail or a skip added for this work.

## Official suite results

The W3C snapshot is `369a90d1a60c021b746df2e411da0ff36258a758`.
[The report](conformance-results.json) accounts for 2447 executions:
2345 passed, 23 failed, 79 unsupported, zero operational errors. Included
RDF 1.1 cases appear again in RDF 1.2 suites, so these are not unique-test
counts. The command exits with status 1 because coverage is incomplete.

| Scope | Result |
|---|---|
| NT, NQ, Turtle and TriG, RDF 1.1 | All tests in the pinned suites passed |
| NT, NQ, Turtle and TriG, RDF 1.2 | All tests in the pinned suites passed, including canonical statement-byte checks |
| RDF/XML 1.1 | 164 passed, 2 failed |
| RDF/XML 1.2, including inherited cases | 176 passed, 21 failed |
| RDF 1.1 semantics | 13 passed, 35 unsupported |
| RDF 1.2 semantics, including inherited cases | 33 passed, 44 unsupported |

The XML failures include outdated fixtures without version announcements and
XMLLiteral lexical expectations that differ from RDFLib 7.6.0. These cases
remain failures in the official report. They are not rewritten or counted as
supported. Passing the September snapshot does not verify later draft changes.

## Area acceptance gates

| Area | Delivered changes | Remaining acceptance work |
|---|---|---|
| 1: RDFLib compatibility | Constructor, equality, ordering, hash safety, collection, namespace, dataset and format regression matrices; explicit None-context parity across Memory and SQLite | Complete shared-API audit, literal arithmetic/duration behavior and remaining API gaps; see `Compare_with_rdflib.md` |
| 2: W3C evidence | Twelve pinned suites, include lists, independent test identities, original canonical statement bytes, accounted failures and unsupported cases | Exhaustive clause-level requirements matrix and published-versus-Editor's-Draft review; all applicable conformance gates are not green |
| 3: RDF 1.2 | Secure XML parsers/writers, version announcements and profile enforcement, JSON validation/equality, graph-local interop definitions, finite RDF/RDFS axioms and optional proofs | Complete datatype and inconsistency reasoning, complete negative RDF/RDFS decisions, remaining XML discrepancies and full syntax/interop audit |
| 4: Documentation, CI and performance evidence | Python 3.10 to 3.14 CI, packaging job, separate strict W3C workflow, runnable documentation, corrected benchmark methodology | Remote CI execution is unverified; performance reports are single-machine measurements, not speed guarantees |

Areas 1 to 3 remain partial under the repository's full acceptance criteria.
The detailed specification evidence is in [the coverage matrix](rdf12-coverage.md).
JSON-LD and SPARQL remain separate, unimplemented compatibility milestones.

## Benchmark interpretation

[benchmark-results.json](benchmark-results.json) records single-run timings
and traced Python allocations. It does not measure process RSS, disk-backed
SQLite performance or a before/after optimization speedup. SQLite ingestion
uses an in-memory SQLite database. Streaming serialization captures output in
memory for verification; output-buffer allocations are included. Standard
RDFCore parsing was slower than RDFLib in these workloads, while streaming
parsing used fewer traced allocations than materializing an RDFCore graph.
