"""Manifest runner for the RDF 1.1 N-Triples/N-Quads suites.

The runner deliberately dispatches by RDF test vocabulary type instead of by
directory naming. It accepts a local checkout of the snapshot listed in
``manifest.lock`` and does not download tests implicitly.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse
from xml.sax import SAXParseException

from rdfcore import Dataset, Graph, RDF, URIRef
from rdfcore.compare import isomorphic
from rdfcore.exceptions import BadSyntax, ParserError

MF = "http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#"
RDFT = "http://www.w3.org/ns/rdftest#"


def run_manifest(manifest: str | Path, format: str, mode: str = "auto", *, key_by_id: bool = False,
                 diagnostics=None) -> dict[str, bool]:
    manifest = Path(manifest).resolve()
    graph = Graph().parse(manifest, publicID=manifest.as_uri(), format="turtle")
    entries = _manifest_entries(graph, manifest.parent)
    results = {}
    for source_graph, entry, source_base in entries:
        test_types = tuple(source_graph.objects(entry, RDF.type))
        action = source_graph.value(entry, URIRef(MF + "action"))
        if action is None:
            continue
        action_path = _uri_path(action, source_base)
        name = str(entry) if key_by_id else str(source_graph.value(entry, URIRef(MF + "name"), default=entry))
        type_names = tuple(str(test_type) for test_type in test_types)
        detail = {}
        if any("NegativeSyntax" in name for name in type_names):
            results[name] = _expect_failure(action_path, format, detail)
        elif any("PositiveSyntax" in name for name in type_names):
            results[name] = _expect_success(action_path, format, detail)
        elif any("Eval" in name for name in type_names):
            result = source_graph.value(entry, URIRef(MF + "result"))
            result_path = _uri_path(result, source_base)
            results[name] = _expect_eval(action_path, result_path, format, result_path.suffix.lower(), detail)
        elif any("C14N" in name for name in type_names) or mode == "c14n":
            result = source_graph.value(entry, URIRef(MF + "result"))
            results[name] = _expect_c14n(action_path, _uri_path(result, source_base), format, detail)
        if diagnostics is not None:
            diagnostics[name] = detail.get('reason', 'test expectations satisfied')
    return results


def _manifest_entries(graph, base):
    manifest = next(graph.subjects(RDF.type, URIRef(MF + "Manifest")), None)
    if manifest is None:
        raise ValueError("manifest does not contain mf:Manifest")
    def list_entries(current):
        while current and current != RDF.nil:
            entry = graph.value(current, RDF.first)
            if entry is not None:
                yield graph, entry, base
            current = graph.value(current, RDF.rest)
    yield from list_entries(graph.value(manifest, URIRef(MF + "entries")))
    for include in graph.objects(manifest, URIRef(MF + "include")):
        children = graph.items(include) if (include, RDF.first, None) in graph else (include,)
        for child in children:
            included = _uri_path(child, base)
            included_graph = Graph().parse(included, publicID=included.as_uri(), format="turtle")
            yield from _manifest_entries(included_graph, included.parent)


def _uri_path(value, base):
    parsed = urlparse(str(value))
    if parsed.scheme == "file":
        return Path(parsed.path)
    if parsed.scheme:
        raise ValueError(f"remote W3C test action is not allowed: {value}")
    return (base / str(value)).resolve()


def _expect_success(path, format, detail=None):
    try:
        _parse(path, format)
    except OSError:
        raise
    except Exception as error:
        if detail is not None:
            detail['reason'] = f'{type(error).__name__}: {error}'
        return False
    return True


def _expect_failure(path, format, detail=None):
    try:
        _parse(path, format)
    except (BadSyntax, ParserError, ValueError, AssertionError, IndexError, SAXParseException):
        return True
    except TypeError as error:
        if str(error) in ('subject must be a URIRef or BNode', 'predicate must be a URIRef',
                          'object must be a URIRef, BNode, or Literal'):
            return True
        raise
    if detail is not None:
        detail['reason'] = 'negative syntax was accepted'
    return False


def _expect_eval(path, expected, format, result_suffix, detail=None):
    try:
        actual = _parse(path, format)
        result_format = {
            ".nt": "nt", ".nq": "nquads", ".ttl": "turtle", ".trig": "trig", '.rdf': 'xml',
        }.get(result_suffix, format)
        if format.endswith('12'):
            result_format = {'nt': 'nt12', 'nquads': 'nq12', 'turtle': 'turtle12', 'trig': 'trig12', 'xml': 'xml12'}.get(result_format, result_format)
        target = _parse(expected, result_format)
        equivalent = isomorphic(actual, target)
        if not equivalent and detail is not None:
            detail['reason'] = 'parsed graph/dataset is not isomorphic to the expected result'
        return equivalent
    except OSError:
        raise
    except Exception as error:
        if detail is not None:
            detail['reason'] = f'{type(error).__name__}: {error}'
        return False


def _expect_c14n(path, expected, format, detail=None):
    try:
        actual = _parse(path, format)
        # The expected fixture is already canonical. Parsing and serializing it
        # would hide precisely the lexical errors this test is meant to detect.
        # Canonical NT/NQ specifies each statement's bytes, not graph iteration
        # order. Compare whole lines without changing escapes or whitespace.
        equivalent = sorted(_canonical(actual, format).encode('utf-8').splitlines(keepends=True)) == sorted(
            Path(expected).read_bytes().splitlines(keepends=True))
        if not equivalent and detail is not None:
            detail['reason'] = 'canonical statement bytes differ from the original expected fixture'
        return equivalent
    except OSError:
        raise
    except Exception as error:
        if detail is not None:
            detail['reason'] = f'{type(error).__name__}: {error}'
        return False


def _canonical(value, format):
    serialization_format = {
        "nt": "nt", "nt12": "nt12", "nquads": "nquads", "nq12": "nq12",
        "turtle": "turtle", "turtle12": "turtle12", "trig": "trig", "trig12": "trig12",
    }[format]
    text = value.serialize(format=serialization_format, canonical=True, encoding="utf-8")
    if isinstance(text, bytes):
        text = text.decode("utf-8")
    return text


def _parse(path, format):
    public_id = _canonical_public_id(path)
    if format in ("nquads", "nq12"):
        return Dataset().parse(path, publicID=public_id, format=format, strict=True, preserve_bnode_ids=True)
    if format in ("nt", "nt12", 'xml', 'xml12'):
        return Graph().parse(path, publicID=public_id, format=format, strict=True, preserve_bnode_ids=True)
    if format in ("turtle", "turtle12"):
        return Graph().parse(path, publicID=public_id, format=format, strict=True)
    if format in ("trig", "trig12"):
        return Dataset().parse(path, publicID=public_id, format=format, strict=True)
    raise ValueError(f"S17 runner does not support format {format!r}")


def _canonical_public_id(path):
    path = Path(path).resolve()
    marker = "rdf-tests/"
    location = path.as_posix()
    if marker in location:
        return "https://w3c.github.io/rdf-tests/" + location.split(marker, 1)[1]
    for index, part in enumerate(path.parts[:-1]):
        if part == 'rdf' and path.parts[index + 1] in ('rdf11', 'rdf12'):
            return 'https://w3c.github.io/rdf-tests/' + '/'.join(path.parts[index:])
    return path.as_uri()


def _isomorphic(left, right):
    if len(left) != len(right):
        return False
    left = list(left)
    right = list(right)
    mapping = {}
    used = set()

    def match(index):
        if index == len(left):
            return True
        source = left[index]
        for target_index, target in enumerate(right):
            if target_index in used or len(source) != len(target):
                continue
            local = dict(mapping)
            if all(_term_match(a, b, local) for a, b in zip(source, target)):
                previous = dict(mapping)
                mapping.clear()
                mapping.update(local)
                used.add(target_index)
                if match(index + 1):
                    return True
                used.remove(target_index)
                mapping.clear()
                mapping.update(previous)
        return False

    return match(0)


def _term_match(left, right, mapping):
    from rdfcore import BNode
    if isinstance(left, BNode) != isinstance(right, BNode):
        return False
    if isinstance(left, BNode):
        if left in mapping:
            return mapping[left] == right
        if right in mapping.values():
            return False
        mapping[left] = right
        return True
    return left == right
