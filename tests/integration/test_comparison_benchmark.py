"""Benchmark checks are independent of timings and must detect data loss."""

import pytest

from benchmarks.compare_rdflib_rdfcore import benchmarks, data


@pytest.mark.parametrize("format", ["nq", "ttl", "trig"])
def test_benchmark_measures_verified_workloads(format):
    rows = benchmarks(data(format, 5), 5, format)
    assert rows
    assert all(row["correctness_verified"] is True for row in rows)
    assert all(row["seconds"] >= 0 for row in rows)
