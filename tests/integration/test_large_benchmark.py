"""Benchmark results must preserve correctness, provenance and failures."""

from argparse import Namespace
import hashlib
import importlib
import json
import subprocess
import sys
import pytest

pytest.importorskip("resource")
from benchmarks.large_data import generate, verify, worker
import rdfcore


@pytest.mark.parametrize("format", ["nt", "nq", "ttl", "trig"])
def test_fixture_hash_and_worker_validation(tmp_path, format):
    path = tmp_path / "input"
    digest = generate(path, 11, format)
    assert digest == hashlib.sha256(path.read_bytes()).hexdigest()
    for library in ("rdfcore", "rdflib", "stream"):
        result = worker(
            Namespace(
                library=library,
                format=format,
                operation="parse",
                input=path,
                size=11,
                directory=tmp_path,
                budget=4096,
                compare_nodes=8,
            )
        )
        assert result["correctness_verified"] and result["seconds"] > 0


def test_correctness_check_rejects_lost_graph_name():
    graph = rdfcore.Dataset()
    graph.add(
        (rdfcore.URIRef("urn:s1"), rdfcore.URIRef("urn:p1"), rdfcore.Literal("1"))
    )
    with pytest.raises(AssertionError):
        verify(graph, 2, True)


def test_timeout_is_persisted_as_failure(tmp_path, monkeypatch):
    module = importlib.import_module("benchmarks.large_data")
    output = tmp_path / "result.json"
    real_run = subprocess.run

    def run(command, *args, **kwargs):
        if "--worker" in command:
            raise subprocess.TimeoutExpired(command, 1)
        return real_run(command, *args, **kwargs)

    monkeypatch.setattr(module.subprocess, "run", run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "large_data",
            "--sizes",
            "1",
            "--formats",
            "nt",
            "--operations",
            "parse",
            "--libraries",
            "rdfcore",
            "--repeats",
            "1",
            "--warmup",
            "0",
            "--output",
            str(output),
        ],
    )
    with pytest.raises(SystemExit) as error:
        module.main()
    assert error.value.code == 1
    result = json.loads(output.read_text())
    assert result["results"][0]["status"] == "failed"
    assert result["results"][0]["samples"] == []
    assert "dataset_sha256" in result["results"][0]


def test_regression_gate_uses_measured_baseline_and_rejects_mismatch():
    from copy import deepcopy
    from benchmarks.large_data import regression_checks

    row = {
        "size": 100,
        "format": "nt",
        "operation": "parse",
        "library": "rdfcore",
        "dataset_sha256": "fixed",
        "status": "passed",
        "median_seconds": 1.0,
        "samples": [{"seconds": t} for t in (0.99, 1.0, 1.01)],
    }
    baseline = {
        "python": "3.10",
        "platform": "same",
        "machine": "same",
        "cpu_count": 2,
        "results": [row],
    }
    current = deepcopy(baseline)
    assert regression_checks(current, baseline)[0]["passed"]
    current["results"][0]["median_seconds"] = 2.0
    assert not regression_checks(current, baseline)[0]["passed"]
    current["python"] = "3.14"
    with pytest.raises(ValueError, match="incompatible"):
        regression_checks(current, baseline)


def test_compare_report_uses_actual_bounded_workload(tmp_path, monkeypatch):
    module = importlib.import_module("benchmarks.large_data")
    output = tmp_path / "report.json"
    original = subprocess.run

    def run(command, *args, **kwargs):
        if "--worker" in command:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps(
                    {
                        "correctness_verified": True,
                        "seconds": 1.0,
                        "peak_rss_bytes": 100000,
                        "compare_nodes": 8,
                        "work_units": 8,
                        "work_unit": "nodes",
                    }
                ),
            )
        return original(command, *args, **kwargs)

    monkeypatch.setattr(module.subprocess, "run", run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "large_data",
            "--sizes",
            "100",
            "1000",
            "--formats",
            "nt",
            "--operations",
            "compare",
            "--libraries",
            "rdfcore",
            "--compare-nodes",
            "8",
            "--repeats",
            "1",
            "--warmup",
            "0",
            "--output",
            str(output),
        ],
    )
    module.main()
    rows = json.loads(output.read_text())["results"]
    assert len(rows) == 1
    assert rows[0]["size"] == 8 and rows[0]["input_bytes"] is None
    assert rows[0]["median_statements_per_second"] is None


@pytest.mark.parametrize("format", ["nt", "nq", "ttl", "trig"])
def test_streaming_write_validates_full_output(tmp_path, format):
    result = worker(
        Namespace(
            library="stream",
            format=format,
            operation="write",
            size=11,
            input=None,
            directory=tmp_path,
            budget=4096,
            compare_nodes=8,
        )
    )
    assert result["correctness_verified"]
    assert "term construction" in result["timing_includes"]


def test_incompatible_selection_is_not_empty_success(tmp_path, monkeypatch):
    module = importlib.import_module("benchmarks.large_data")
    output = tmp_path / "result.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "large_data",
            "--sizes",
            "1",
            "--formats",
            "ttl",
            "--operations",
            "sqlite",
            "--libraries",
            "rdflib",
            "--output",
            str(output),
        ],
    )
    with pytest.raises(SystemExit) as error:
        module.main()
    assert error.value.code == 2
    result = json.loads(output.read_text())
    assert result["results"] == [] and result["configuration_error"]


@pytest.mark.parametrize(
    "operation,library",
    [
        ("sqlite", "rdfcore"),
        ("query", "rdfcore"),
        ("query", "rdflib"),
        ("sort", "rdfcore"),
        ("compare", "rdfcore"),
        ("compare", "rdflib"),
    ],
)
def test_other_operations_verify_results(tmp_path, operation, library):
    path = tmp_path / "input.nt"
    generate(path, 11, "nt")
    result = worker(
        Namespace(
            library=library,
            format="nt",
            operation=operation,
            size=11,
            input=path,
            directory=tmp_path,
            budget=512,
            compare_nodes=8,
        )
    )
    assert result["correctness_verified"] and result["seconds"] > 0
    if operation == "compare":
        assert result["work_units"] == 8 and result["statements_per_second"] is None


def test_checkpoint_does_not_overwrite_preexisting_tmp_file(tmp_path):
    from benchmarks.large_data import write_report

    output = tmp_path / "report.json"
    baseline = tmp_path / "report.json.tmp"
    baseline.write_text("keep baseline")
    write_report(output, {"results": []})
    assert baseline.read_text() == "keep baseline"
    assert json.loads(output.read_text()) == {"results": []}
