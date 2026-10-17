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


def test_repeated_measurement_has_warmup_and_individual_samples():
    from benchmarks.compare_rdflib_rdfcore import measure
    calls = []
    def work():
        calls.append(True)
        return 7
    row = measure('controlled', work, repeats=3, warmup=2)
    assert len(calls) == 5
    assert len(row['runs']) == 3
    assert all(run['result'] == 7 for run in row['runs'])
    import statistics
    assert row['seconds'] == statistics.median(run['seconds'] for run in row['runs'])


def test_measurement_stops_tracing_after_failure():
    import tracemalloc
    from benchmarks.compare_rdflib_rdfcore import measure
    def broken():
        raise RuntimeError('workload failed')
    with pytest.raises(RuntimeError, match='workload failed'):
        measure('broken', broken)
    assert not tracemalloc.is_tracing()


@pytest.mark.parametrize('format', ['nq', 'ttl', 'trig'])
def test_repeated_benchmarks_verify_all_runs(format):
    rows = benchmarks(data(format, 3), 3, format, repeats=2, warmup=1)
    assert all(len(row['runs']) == 2 and row['correctness_verified'] for row in rows)


def test_memory_query_benchmarks_cover_patterns_and_contexts():
    from benchmarks.memory_queries import query_benchmarks
    rows = query_benchmarks(12, repeats=1, warmup=0)
    assert len(rows) == 48
    assert len({tuple(row['bound']) for row in rows}) == 8
    assert {row['context'] for row in rows} == {0, 1, 2}
    assert all(row['correctness_verified'] for row in rows)
