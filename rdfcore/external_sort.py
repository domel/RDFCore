"""External sorting with approximate run budgets for RDF statements."""

from __future__ import annotations

from contextlib import ExitStack, closing
import heapq
import struct
from .codec import encode, decode_value, load_json
import tempfile
from pathlib import Path

from .plugins.serializers.nt12 import _term


def statement_key(statement):
    """Return a tuple of canonical RDF12 term strings, including graph names.

    Raw default quads (graph=None) share a key with triples. Labels are not
    renamed. Equal keys need not imply equal Python objects or term spellings.
    """
    if len(statement) == 3:
        parts = statement
    elif len(statement) == 4:
        graph = getattr(statement[3], 'identifier', statement[3])
        parts = statement[:3] if graph is None else (*statement[:3], graph)
    else:
        raise ValueError("external sort accepts triples or quads")
    return tuple(_term(term, canonical=True) for term in parts)


def external_sort(
    statements, *, memory_budget=64 * 1024 * 1024, temp_dir=None,
    unique=False, max_open_runs=64
):
    """Yield statements in sorted order using bounded in-memory runs.

    ``memory_budget`` is an approximate upper bound for a run, measured using
    the framed JSON representation of each statement.  Only N-Triples/N-Quads
    terms are supported.  Temporary runs are removed when iteration finishes,
    is closed, or raises an exception. Cleanup attempts every run; filesystem
    errors are propagated if removal is not possible.

    Equal-key records retain input order. ``unique=True`` keeps their first
    spelling, using canonical keys rather than Python object equality.
    Quad contexts supplied as Graph views are returned as RDF identifiers.
    """
    if memory_budget <= 0:
        raise ValueError("memory_budget must be positive")
    if max_open_runs < 2:
        raise ValueError("max_open_runs must be at least 2")
    return _external_sort(iter(statements), memory_budget, temp_dir, unique, max_open_runs)


def _external_sort(statements, memory_budget, temp_dir, unique, max_open_runs):
    all_paths = []
    try:
        run_paths = []
        run = []
        run_size = 0
        for statement in statements:
            statement = tuple(statement)
            # Graph views carry their whole store (and possibly a live SQLite
            # connection). Spill RDF identifiers, never those live objects.
            if len(statement) == 4:
                statement = (*statement[:3], getattr(statement[3], 'identifier', statement[3]))
            key = statement_key(statement)
            record_size = len(_encode_record(statement))
            if run and run_size + record_size > memory_budget:
                path = _write_run(run, temp_dir)
                run_paths.append(path)
                all_paths.append(path)
                run = []
                run_size = 0
            run.append((key, statement))
            run_size += record_size
        if run:
            path = _write_run(run, temp_dir)
            run_paths.append(path)
            all_paths.append(path)
        if not run_paths:
            return
        while len(run_paths) > max_open_runs:
            merged_paths = []
            for offset in range(0, len(run_paths), max_open_runs):
                group = run_paths[offset:offset + max_open_runs]
                if len(group) == 1:
                    merged_paths.append(group[0])
                    continue
                path = _write_merged_run(group, temp_dir)
                merged_paths.append(path)
                all_paths.append(path)
                for old_path in group:
                    Path(old_path).unlink(missing_ok=True)
            run_paths = merged_paths
        yield from _merge_runs(run_paths, unique)
    finally:
        _remove_runs(all_paths)


def _remove_runs(paths):
    error = None
    for path in paths:
        try:
            Path(path).unlink()
        except FileNotFoundError:
            pass
        except OSError as failure:
            if error is None:
                error = failure
    if error is not None:
        raise error


def _write_run(records, temp_dir):
    records.sort(key=lambda record: record[0])
    handle = tempfile.NamedTemporaryFile(mode="wb", prefix="rdfcore-run-", dir=temp_dir, delete=False)
    path = handle.name
    try:
        with handle:
            for record in records:
                handle.write(_encode_record(record[1]))
    except BaseException:
        Path(path).unlink(missing_ok=True)
        raise
    return path


def _encode_record(statement):
    payload = b'[' + b','.join(encode(term, canonical=False, preserve_state=True) for term in statement) + b']'
    return b'RCR2' + struct.pack('>Q', len(payload)) + payload


def _read_record(handle):
    header = handle.read(12)
    if not header:
        return None
    if len(header) != 12 or header[:4] != b'RCR2':
        raise ValueError('invalid external sort record version or header')
    size = struct.unpack('>Q', header[4:])[0]
    position = handle.tell()
    remaining = handle.seek(0, 2) - position
    handle.seek(position)
    if size > remaining:
        raise ValueError('truncated external sort record')
    payload = handle.read(size)
    if len(payload) != size:
        raise ValueError('truncated external sort record')
    values = load_json(payload)
    if not isinstance(values, list) or len(values) not in (3, 4):
        raise ValueError('invalid external sort statement')
    statement = tuple(decode_value(value) for value in values)
    return statement_key(statement), statement


def _merged_records(paths):
    handles = []
    heap = []
    with ExitStack() as cleanup:
        for path in paths:
            handle = open(path, "rb")
            cleanup.callback(handle.close)
            handles.append(handle)
        for index, handle in enumerate(handles):
            record = _read_record(handle)
            if record is not None:
                heapq.heappush(heap, (record[0], index, record[1]))
        while heap:
            key, index, statement = heapq.heappop(heap)
            yield key, statement
            record = _read_record(handles[index])
            if record is not None:
                heapq.heappush(heap, (record[0], index, record[1]))


def _write_merged_run(paths, temp_dir):
    handle = tempfile.NamedTemporaryFile(mode="wb", prefix="rdfcore-run-", dir=temp_dir, delete=False)
    path = handle.name
    try:
        with handle, closing(_merged_records(paths)) as records:
            for record in records:
                handle.write(_encode_record(record[1]))
    except BaseException:
        Path(path).unlink(missing_ok=True)
        raise
    return path


def _merge_runs(paths, unique):
    previous = None
    with closing(_merged_records(paths)) as records:
        for key, statement in records:
            if not unique or key != previous:
                yield statement
                previous = key


__all__ = ["external_sort", "statement_key"]
