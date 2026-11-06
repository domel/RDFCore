"""RSS guards apply to named workloads, not arbitrary RDF documents."""

import gzip
import json
import subprocess
import sys
import pytest


def probe(path, format, *options):
    pytest.importorskip("resource")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tests.streaming.memory_probe",
            str(path),
            format,
            *options,
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return json.loads(result.stdout)


def fixture(path, count, format, *, compressed=False, labels=False, token=8, depth=0):
    writer = gzip.open if compressed else open
    with writer(path, "wb") as stream:
        if format == "xml12":
            stream.write(
                b'<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:ex="urn:" rdf:version="1.2">'
            )
            for i in range(count):
                stream.write(
                    f'<rdf:Description rdf:about="urn:s{i}"><ex:p>v</ex:p></rdf:Description>'.encode()
                )
            stream.write(b"</rdf:RDF>")
            return
        if format.endswith("12"):
            stream.write(b'VERSION "1.2"\n')
        if format == "trig12":
            stream.write(b"<urn:g> {\n")
        obj = '"' + ("x" * token) + '"' + ("@en--rtl" if format.endswith("12") else "")
        for _ in range(depth):
            obj = f"<<( <urn:s> <urn:p> {obj} )>>"
        for i in range(count):
            subject = f"_:b{i}" if labels else "<urn:s>"
            stream.write(f"{subject} <urn:p> {obj} .\n".encode())
        if format == "trig12":
            stream.write(b"}\n")


@pytest.mark.parametrize("format", ["turtle12", "trig12"])
@pytest.mark.parametrize("compressed", [False, True])
def test_rdf12_short_record_rss_is_bounded(tmp_path, format, compressed):
    reports = []
    for size in (5000, 50000):
        path = tmp_path / f"{size}.rdf"
        fixture(path, size, format, compressed=compressed)
        result = probe(path, format, *(["--compression", "gz"] if compressed else []))
        assert result["statements"] == size
        reports.append(result)
    assert reports[1]["peak_rss_bytes"] - reports[0]["peak_rss_bytes"] < 24 * 1024**2, (
        reports
    )


def test_rss_guard_detects_deliberate_materialization(tmp_path):
    path = tmp_path / "data.nt"
    fixture(path, 100000, "nt")
    streamed = probe(path, "nt")
    retained = probe(path, "nt", "--collect")
    assert streamed["statements"] == retained["statements"] == 100000
    assert retained["peak_rss_bytes"] - streamed["peak_rss_bytes"] > 16 * 1024**2, (
        streamed,
        retained,
    )


@pytest.mark.parametrize("case", ["labels", "long-token", "nested", "sort", "xml-tree"])
def test_explicit_resource_profiles(tmp_path, case):
    path = tmp_path / "profile.rdf"
    format = (
        "nt12" if case == "nested" else "turtle12" if case == "long-token" else "nt"
    )
    if case == "xml-tree":
        format = "xml12"
    count = 5000 if case == "xml-tree" else 20000 if case in ("labels", "sort") else 20
    fixture(
        path,
        count,
        format,
        labels=case == "labels",
        token=65536 if case == "long-token" else 8,
        depth=24 if case == "nested" else 0,
    )
    result = probe(
        path,
        format,
        *(["--operation", "sort", "--budget", "16384"] if case == "sort" else []),
    )
    assert result["statements"] == count
    # These profiles deliberately vary parser/sort state; this is a generous
    # per-workload guard, not a constant-space assertion for unique BNodes.
    assert result["peak_rss_bytes"] - result["initial_rss_bytes"] < 96 * 1024**2, result
