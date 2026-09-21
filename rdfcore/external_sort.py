"""Fixed-memory external sorting for N-Triples/N-Quads statements."""

from __future__ import annotations

import heapq
import pickle
import tempfile
from pathlib import Path

from .plugins.serializers.nt12 import _term


def statement_key(statement):
    """Return the byte-sort key used by :func:`external_sort`."""
    if len(statement) == 3:
        parts = statement
    elif len(statement) == 4:
        parts = statement[:3] if statement[3] is None else statement
    else:
        raise ValueError("external sort accepts triples or quads")
    return tuple(_term(term, canonical=True) for term in parts)


def external_sort(
    statements, *, memory_budget=64 * 1024 * 1024, temp_dir=None,
    unique=False, max_open_runs=64
):
    """Yield statements in sorted order using bounded in-memory runs.

    ``memory_budget`` is an approximate upper bound for a run, measured using
    the pickle representation of each statement.  Only N-Triples/N-Quads
    terms are supported.  Temporary runs are removed when iteration finishes,
    is closed, or raises an exception.
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
            key = statement_key(statement)
            record_size = len(pickle.dumps((key, statement), protocol=4))
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
        for path in all_paths:
            try:
                Path(path).unlink()
            except FileNotFoundError:
                pass


def _write_run(records, temp_dir):
    records.sort(key=lambda record: record[0])
    handle = tempfile.NamedTemporaryFile(mode="wb", prefix="rdfcore-run-", dir=temp_dir, delete=False)
    path = handle.name
    try:
        with handle:
            for record in records:
                pickle.dump(record, handle, protocol=4)
    except BaseException:
        Path(path).unlink(missing_ok=True)
        raise
    return path


def _read_record(handle):
    try:
        return pickle.load(handle)
    except EOFError:
        return None


def _merged_records(paths):
    handles = []
    heap = []
    try:
        handles = [open(path, "rb") for path in paths]
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
    finally:
        for handle in handles:
            handle.close()


def _write_merged_run(paths, temp_dir):
    handle = tempfile.NamedTemporaryFile(mode="wb", prefix="rdfcore-run-", dir=temp_dir, delete=False)
    path = handle.name
    try:
        with handle:
            for record in _merged_records(paths):
                pickle.dump(record, handle, protocol=4)
    except BaseException:
        Path(path).unlink(missing_ok=True)
        raise
    return path


def _merge_runs(paths, unique):
    previous = None
    for key, statement in _merged_records(paths):
        if not unique or key != previous:
            yield statement
            previous = key


__all__ = ["external_sort", "statement_key"]
