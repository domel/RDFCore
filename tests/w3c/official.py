"""Accounted official-suite report; run with python -m tests.w3c.official.

Requires the test extra and an explicit local rdf-tests checkout. No implicit
downloads or fixture rewriting. Results are keyed by test IRI, not display name.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess
from urllib.parse import unquote, urlparse

import rdflib
from rdflib import Graph, RDF, URIRef

from tests.w3c.runner import run_manifest

ROOT = Path(__file__).resolve().parents[2]
LOCK = Path(__file__).with_name("manifest.lock")
MF = "http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#"
RT = "http://www.w3.org/ns/rdftest#"
FORMATS = {"rdf-n-triples": ("nt", "nt12"), "rdf-n-quads": ("nquads", "nq12"), 'rdf-xml': ('xml', 'xml12'),
           "rdf-turtle": ("turtle", "turtle12"), "rdf-trig": ("trig", "trig12")}
TYPES = {RT + "Test" + syntax + kind for syntax in ("NTriples", "NQuads", "Turtle", "Trig", 'XML')
         for kind in ("PositiveSyntax", "NegativeSyntax", "Eval", "C14N", "PositiveC14N")}

# Published references reviewed 2026-10-17, not claims that the older locked
# fixtures cover every requirement in these document revisions.
REFERENCES = {
    'nt12': 'https://www.w3.org/TR/2026/WD-rdf12-n-triples-20261007/',
    'nq12': 'https://www.w3.org/TR/2026/WD-rdf12-n-quads-20261010/',
    'turtle12': 'https://www.w3.org/TR/2026/WD-rdf12-turtle-20261007/',
    'trig12': 'https://www.w3.org/TR/2026/WD-rdf12-trig-20261007/',
    'xml12': 'https://www.w3.org/TR/2026/WD-rdf12-xml-20261009/',
    'semantics12': 'https://www.w3.org/TR/2026/CRD-rdf12-semantics-20260924/',
    'nt': 'https://www.w3.org/TR/2014/REC-n-triples-20140225/',
    'nquads': 'https://www.w3.org/TR/2014/REC-n-quads-20140225/',
    'turtle': 'https://www.w3.org/TR/2014/REC-turtle-20140225/',
    'trig': 'https://www.w3.org/TR/2014/REC-trig-20140225/',
    'xml': 'https://www.w3.org/TR/2014/REC-rdf-syntax-grammar-20140225/',
    'semantics11': 'https://www.w3.org/TR/2014/REC-rdf11-mt-20140225/',
}


def git(path, *args):
    return subprocess.check_output(["git", "-C", str(path), *args], text=True).strip()


def verify_checkout(checkout):
    """Check the existing lock without requiring tomllib on Python 3.10."""
    match = re.search(r'^commit\s*=\s*"([0-9a-f]{40})"', LOCK.read_text(), re.M)
    if match is None:
        raise ValueError('manifest lock must contain a 40-character hexadecimal commit')
    pin = match.group(1)
    try:
        actual = git(checkout, "rev-parse", "HEAD")
        dirty = git(checkout, "status", "--porcelain")
    except subprocess.CalledProcessError as exc:
        raise ValueError("checkout must be a git checkout at the locked revision") from exc
    if actual != pin or dirty:
        raise ValueError(f"checkout must be clean at {pin}; found {actual}, dirty={bool(dirty)}")
    return actual


def local_path(value):
    parsed = urlparse(str(value))
    if parsed.scheme != "file" or parsed.netloc:
        raise ValueError(f"only local manifest paths allowed: {value}")
    return Path(unquote(parsed.path))


def inventory(manifest, ancestors=()):
    """Enumerate entries including unknown types, absent actions and duplicates."""
    manifest = Path(manifest).resolve()
    if manifest in ancestors:
        raise ValueError(f"manifest include cycle: {manifest}")
    graph = Graph().parse(manifest, format="turtle", publicID=manifest.as_uri())
    records = []
    manifests = list(graph.subjects(RDF.type, URIRef(MF + "Manifest")))
    if not manifests:
        raise ValueError(f"no mf:Manifest in {manifest}")
    for subject in manifests:
        for head in graph.objects(subject, URIRef(MF + "entries")):
            for entry in graph.items(head):
                records.append({"id": str(entry), "name": str(graph.value(entry, URIRef(MF + "name"), default=entry)),
                                "types": sorted(map(str, graph.objects(entry, RDF.type))),
                                "action": str(graph.value(entry, URIRef(MF + "action")) or ""),
                                'result': str(graph.value(entry, URIRef(MF + 'result')) or ''),
                                'regime': str(graph.value(entry, URIRef(MF + 'entailmentRegime')) or 'simple').lower(),
                                'recognized_datatypes': [str(item) for item in graph.items(graph.value(entry, URIRef(MF + 'recognizedDatatypes')))],
                                "manifest": str(manifest)})
        for include in graph.objects(subject, URIRef(MF + "include")):
            children = graph.items(include) if (include, RDF.first, None) in graph else (include,)
            for child in children:
                records.extend(inventory(local_path(child), (*ancestors, manifest)))
    return records


def report_suite(manifest, format):
    report = {"manifest": str(manifest), "format": format, "total": 0,
              "counts": dict.fromkeys(("passed", "failed", "unsupported", "error"), 0), "tests": []}
    try:
        entries = inventory(manifest)
    except Exception as exc:
        report["suite_error"] = f"{type(exc).__name__}: {exc}"
        return report
    # Execute the existing runner against each physical manifest. This preserves
    # its assertions while accounting independently for every declared entry.
    results, errors, diagnostics = {}, {}, {}
    for leaf in sorted({entry["manifest"] for entry in entries}):
        if format is not None and format != 'semantics':
            try:
                diagnostics[leaf] = {}
                results[leaf] = run_manifest(leaf, format, key_by_id=True, diagnostics=diagnostics[leaf])
            except Exception as exc:
                errors[leaf] = f"{type(exc).__name__}: {exc}"
    for entry in entries:
        status, reason = "unsupported", "unknown or unsupported test type"
        leaf, name = entry["manifest"], entry["id"]
        if format == 'semantics':
            status, reason = semantic_result(entry)
        elif format is None:
            reason = "no RDFCore parser/entailment runner for this suite"
        elif not entry["action"]:
            reason = "missing mf:action"
        elif not set(entry["types"]) & TYPES:
            pass
        elif leaf in errors:
            status, reason = "error", errors[leaf]
        elif name not in results[leaf]:
            reason = "declared entry omitted by existing runner"
        else:
            status = "passed" if results[leaf][name] else "failed"
            reason = diagnostics[leaf].get(name, "existing runner returned " + str(results[leaf][name]))
        report["tests"].append({**entry, "status": status, "reason": reason})
        report["counts"][status] += 1
    report["total"] = len(entries)
    assert sum(report["counts"].values()) == report["total"]
    return report


def semantic_result(entry):
    from rdfcore.semantics import entails, UnsupportedEntailment
    from tests.w3c.runner import _parse
    if entry['recognized_datatypes'] or entry['result'] in ('', 'false'):
        return 'unsupported', 'datatype recognition or inconsistency reasoning is not implemented'
    kinds = {MF+'PositiveEntailmentTest': True, MF+'NegativeEntailmentTest': False}
    expected = next((result for kind, result in kinds.items() if kind in entry['types']), None)
    if expected is None:
        return 'unsupported', 'unknown entailment test type'
    def parse(uri):
        path = local_path(uri)
        format = {'.nt': 'nt12', '.ttl': 'turtle12', '.rdf': 'xml', '.xml': 'xml'}.get(path.suffix)
        if format is None:
            raise UnsupportedEntailment('unsupported premise/conclusion format')
        return _parse(path, format)
    try:
        actual = entails(parse(entry['action']), parse(entry['result']), regime=entry['regime'])
    except UnsupportedEntailment as error:
        return 'unsupported', str(error)
    except Exception as error:
        return 'error', f'{type(error).__name__}: {error}'
    return ('passed', 'entailment result matches manifest') if actual is expected else ('failed', 'entailment result differs from manifest')


def build_report(checkout):
    checkout = Path(checkout).resolve()
    pin = verify_checkout(checkout)
    suites = []
    for version, index in (("rdf11", 0), ("rdf12", 1)):
        for directory, formats in FORMATS.items():
            suite = report_suite(checkout / "rdf" / version / directory / "manifest.ttl", formats[index])
            suite.update(reference_document=REFERENCES[formats[index]], rdf_version=version,
                         category='syntax', reference_reviewed='2026-10-17')
            suites.append(suite)
        for directory in ("rdf-mt" if version == "rdf11" else "rdf-semantics",):
            suite = report_suite(checkout / "rdf" / version / directory / "manifest.ttl", 'semantics')
            suite.update(reference_document=REFERENCES['semantics11' if index == 0 else 'semantics12'],
                         rdf_version=version, category='entailment', reference_reviewed='2026-10-17')
            suites.append(suite)
    # Relativize the temporary checkout location while retaining entry identity.
    encoded = json.dumps(suites).replace(checkout.as_uri() + "/", "https://w3c.github.io/rdf-tests/")
    encoded = encoded.replace(str(checkout) + "/", "")
    changed = git(ROOT, "status", "--porcelain")
    tracked_diff = subprocess.check_output(["git", "-C", str(ROOT), "diff", "--binary", "HEAD"])
    totals = {status: sum(suite['counts'].get(status, 0) for suite in suites)
              for status in ('passed', 'failed', 'unsupported', 'error')}
    return {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
            "snapshot": pin, "python": platform.python_version(), "rdflib": rdflib.__version__,
            "rdfcore_revision": git(ROOT, "rev-parse", "HEAD"), "worktree_status": changed,
            "tracked_diff_sha256": hashlib.sha256(tracked_diff).hexdigest(),
            "totals": totals, "test_executions": sum(suite.get('total', 0) for suite in suites),
            "unique_test_ids": len({test['id'] for suite in suites for test in suite['tests']}),
            "limitations": ["Passed means the selected test passed, not a complete conformance certification.",
                "Canonical syntax tests compare original UTF-8 statement bytes, ignoring only statement order; this is not RDFC-1.0.",
                "Unsupported and suite errors never count as success; no skipped test counts as passed.",
                "Suite includes may repeat RDF 1.1 cases; totals across suites are executions, not unique tests.",
                "Published reference_document metadata does not mean the older snapshot covers that revision.",
                "Snapshot predates October 2026 publications; passing it cannot verify later changes."],
            "suites": json.loads(encoded)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        report = build_report(args.checkout)
    except ValueError as exc:
        parser.error(str(exc))
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return int(any(suite.get("suite_error") or suite["counts"]["failed"] or
                   suite["counts"]["unsupported"] or suite["counts"]["error"] for suite in report["suites"]))


if __name__ == "__main__":
    raise SystemExit(main())
