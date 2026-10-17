"""Benchmark checks are independent of timings and must detect data loss."""
import pytest

import rdfcore
from benchmarks.compare_rdflib_rdfcore import benchmarks, data, verify_equivalence


@pytest.mark.parametrize('format', ['nq', 'ttl', 'trig'])
def test_benchmark_measures_verified_workloads(format):
    rows = benchmarks(data(format, 5), 5, format)
    assert rows
    assert all(row['correctness_verified'] is True for row in rows)
    assert all(row['seconds'] >= 0 for row in rows)


def test_benchmark_rejects_different_literal_datatypes():
    left = rdfcore.Graph().add((rdfcore.URIRef('urn:s'), rdfcore.URIRef('urn:p'), rdfcore.Literal('1')))
    right = rdfcore.Graph().add((rdfcore.URIRef('urn:s'), rdfcore.URIRef('urn:p'), rdfcore.Literal(1)))
    with pytest.raises(AssertionError):
        verify_equivalence(left, right)


@pytest.mark.parametrize('mode', ['single', 'transaction', 'bulk'])
@pytest.mark.parametrize('size', [0, 5])
def test_disk_bulk_benchmark_verifies_persisted_records(mode, size):
    from benchmarks.sqlite_bulk import measure
    assert measure(size, mode) >= 0
