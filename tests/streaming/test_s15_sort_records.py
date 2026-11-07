"""Temporary sort files are data, never executable pickle."""

import importlib
import io
import pickle

import pytest
from rdfcore import Literal, TripleTerm, URIRef, external_sort, statement_key

sort = importlib.import_module("rdfcore.external_sort")


@pytest.mark.parametrize(
    "payload",
    [
        b"not a run",
        b"RCR2",
        b"RCR2" + (2**63).to_bytes(8, "big"),
        pickle.dumps(("foreign",)),
    ],
)
def test_corrupt_sort_record_rejected(payload):
    with pytest.raises(ValueError):
        sort._read_record(io.BytesIO(payload))


def test_spills_do_not_contain_pickle_and_preserve_spelling(tmp_path):
    s, p = URIRef("urn:s"), URIRef("urn:p")
    values = [
        (s, p, TripleTerm(s, p, Literal("v", lang="EN", direction="rtl")), None)
    ] * 4
    result = external_sort(values, memory_budget=1, temp_dir=tmp_path, max_open_runs=2)
    first = next(result)
    assert first[2].object.language == "EN"
    assert statement_key(first) == statement_key(values[0])
    assert all(path.read_bytes().startswith(b"RCR2") for path in tmp_path.iterdir())
    result.close()
    assert not list(tmp_path.iterdir())


def test_truncated_payload_is_not_silent_eof(tmp_path):
    row = (URIRef("urn:s"), URIRef("urn:p"), Literal("v"))
    path = sort._write_run([(statement_key(row), row)], tmp_path)
    raw = open(path, "rb").read()
    for offset in range(1, len(raw)):
        with pytest.raises(ValueError):
            sort._read_record(io.BytesIO(raw[:offset]))


def test_partial_open_failure_closes_previous_handles(tmp_path, monkeypatch):
    import builtins

    row = (URIRef("urn:s"), URIRef("urn:p"), Literal("v"))
    path = sort._write_run([(statement_key(row), row)], tmp_path)
    handles = []
    real_open = builtins.open

    def tracking(path, *args, **kwargs):
        result = real_open(path, *args, **kwargs)
        handles.append(result)
        return result

    monkeypatch.setattr(sort, "open", tracking, raising=False)
    with pytest.raises(FileNotFoundError):
        list(sort._merged_records([path, tmp_path / "missing"]))
    assert handles and all(handle.closed for handle in handles)


def test_hostile_pickle_sort_file_does_not_execute(tmp_path):
    marker = tmp_path / "executed"

    class Hostile:
        def __reduce__(self):
            return eval, (
                f"__import__('pathlib').Path({str(marker)!r}).write_text('bad')",
            )

    with pytest.raises(ValueError):
        sort._read_record(io.BytesIO(pickle.dumps(Hostile())))
    assert not marker.exists()


def test_cleanup_attempts_all_paths_after_unlink_error(tmp_path, monkeypatch):
    from pathlib import Path

    paths = [tmp_path / "blocked", tmp_path / "removed"]
    for path in paths:
        path.touch()
    original = Path.unlink

    def unlink(path, *args, **kwargs):
        if path == paths[0]:
            raise PermissionError("blocked")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", unlink)
    with pytest.raises(PermissionError):
        sort._remove_runs(paths)
    assert paths[0].exists() and not paths[1].exists()


def test_early_close_explicitly_closes_merge_inputs(tmp_path, monkeypatch):
    import builtins

    handles = []
    original = builtins.open

    def tracking(*args, **kwargs):
        result = original(*args, **kwargs)
        handles.append(result)
        return result

    monkeypatch.setattr(sort, "open", tracking, raising=False)
    row = (URIRef("urn:s"), URIRef("urn:p"), Literal("v"))
    iterator = external_sort([row, row], memory_budget=1, temp_dir=tmp_path)
    next(iterator)
    iterator.close()
    assert handles and all(handle.closed for handle in handles)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "value",
    [
        Literal(
            "01", datatype="http://www.w3.org/2001/XMLSchema#integer", normalize=False
        ),
        Literal("INF", datatype="http://www.w3.org/2001/XMLSchema#double"),
        Literal("NaN", datatype="http://www.w3.org/2001/XMLSchema#double"),
        Literal(
            "broken",
            datatype="http://www.w3.org/2001/XMLSchema#integer",
            normalize=False,
        ),
        Literal("v", lang="EN"),
        Literal("v", lang="EN", direction="rtl"),
    ],
)
def test_record_retains_exact_spelling_and_key(value, tmp_path):
    row = (URIRef("urn:s"), URIRef("urn:p"), value)
    path = sort._write_run([(statement_key(row), row)], tmp_path)
    with open(path, "rb") as handle:
        key, restored = sort._read_record(handle)
    assert key == statement_key(row)
    assert str(restored[2]) == str(value)
    assert restored[2].language == value.language
    assert restored[2].datatype == value.datatype
    assert restored[2].direction == value.direction


def test_merge_closes_all_handles_when_one_close_fails(tmp_path, monkeypatch):
    import builtins

    row = (URIRef("urn:s"), URIRef("urn:p"), Literal("v"))
    paths = [sort._write_run([(statement_key(row), row)], tmp_path) for _ in range(2)]
    original = builtins.open
    handles = []

    class Reader:
        def __init__(self, stream, fail):
            self.stream, self.fail = stream, fail

        def __getattr__(self, name):
            return getattr(self.stream, name)

        def close(self):
            self.stream.close()
            if self.fail:
                raise OSError("close failed")

    def tracking(*args, **kwargs):
        result = Reader(original(*args, **kwargs), not handles)
        handles.append(result)
        return result

    monkeypatch.setattr(sort, "open", tracking, raising=False)
    with pytest.raises(OSError, match="close failed"):
        list(sort._merged_records(paths))
    assert all(handle.closed for handle in handles)


def test_sort_preserves_literal_native_values_and_flags():
    from rdfcore import XSD

    values = [
        Literal(1),
        Literal(True),
        Literal("P1D", datatype=XSD.duration) - Literal("P1M", datatype=XSD.duration),
    ]
    for value in values:
        restored = list(
            external_sort([(URIRef("urn:s"), URIRef("urn:p"), value)], memory_budget=1)
        )[0][2]
        assert restored.ill_typed is value.ill_typed
        assert type(restored.value) is type(value.value)
        assert restored.value == value.value
