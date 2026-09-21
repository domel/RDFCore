from pathlib import Path

import pytest

from rdfcore import Literal, TripleTerm, URIRef, external_sort, statement_key


def triple(number):
    return (URIRef(f"urn:s{number}"), URIRef("urn:p"), Literal(str(number)))


def test_external_sort_uses_runs_and_deduplicates(tmp_path):
    values = [triple(3), triple(1), triple(2), triple(1)]
    assert list(external_sort(values, memory_budget=1, temp_dir=tmp_path, unique=True)) == [
        triple(1), triple(2), triple(3)
    ]
    assert list(tmp_path.iterdir()) == []


def test_external_sort_supports_quads_and_cleans_up_on_close(tmp_path):
    graph = URIRef("urn:g")
    values = [(subject, predicate, obj, graph) for subject, predicate, obj in (triple(2), triple(1))]
    result = external_sort(values, memory_budget=1, temp_dir=tmp_path)
    assert next(result) == values[1]
    result.close()
    assert list(tmp_path.iterdir()) == []


def test_external_sort_rejects_invalid_budget():
    with pytest.raises(ValueError, match="memory_budget"):
        list(external_sort([], memory_budget=0))


def test_external_sort_accepts_rdf12_triple_terms():
    embedded = TripleTerm(URIRef("urn:a"), URIRef("urn:b"), URIRef("urn:c"))
    statement = (URIRef("urn:s"), URIRef("urn:p"), embedded)
    assert list(external_sort([statement], memory_budget=1)) == [statement]


def test_external_sort_accepts_default_graph_quad():
    statement = (*triple(1), None)
    assert list(external_sort([statement], memory_budget=1)) == [statement]


def test_external_sort_limits_open_runs_during_multi_pass_merge(tmp_path):
    values = [triple(number) for number in range(30, -1, -1)]
    result = list(external_sort(values, memory_budget=1, temp_dir=tmp_path, max_open_runs=2))
    assert result == sorted(values, key=statement_key)
    assert list(tmp_path.iterdir()) == []
