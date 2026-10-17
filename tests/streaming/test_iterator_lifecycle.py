"""Lifecycle regressions for the RDFCore push/iterator extension."""

from io import BytesIO
from queue import Queue
from threading import Event

import pytest

from rdfcore import streaming
from rdfcore.exceptions import ParserError, PluginException
from rdfcore.parser import InputSource


def capture_workers(monkeypatch):
    import threading
    original = threading.Thread
    workers = []
    def thread(*args, **kwargs):
        worker = original(*args, **kwargs)
        workers.append(worker)
        return worker
    monkeypatch.setattr(threading, 'Thread', thread)
    return workers


def test_close_before_start_does_not_open_source(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError('source opened before iteration')
    monkeypatch.setattr('rdfcore.parser.create_input_source', unexpected)
    iterator = streaming.parse_stream('unused.nt', 'nt')
    iterator.close()


def test_lookup_failure_closes_owned_source(monkeypatch):
    handle = BytesIO(b'')
    monkeypatch.setattr('rdfcore.parser.create_input_source',
                        lambda *args, **kwargs: InputSource(file=handle, auto_close=True))
    with pytest.raises(PluginException):
        streaming.parse_stream(handle, 'missing-plugin', object())
    assert handle.closed


def test_close_during_pending_error_stops_worker(monkeypatch):
    import queue
    attempted = Event()
    queues = []
    class RecordingQueue(Queue):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            queues.append(self)

        def put(self, item, *args, **kwargs):
            if isinstance(item, BaseException):
                attempted.set()
            return super().put(item, *args, **kwargs)
    monkeypatch.setattr(queue, 'Queue', RecordingQueue)
    workers = capture_workers(monkeypatch)
    handle = BytesIO(b'<urn:s> <urn:p> "first" .\n<urn:s> <urn:p> "second" .\ninvalid\n')
    iterator = streaming.parse_stream(handle, 'nt')
    try:
        next(iterator)
        assert attempted.wait(2), 'producer did not reach the pending error'
        iterator.close()
        workers[0].join(2)
        assert not workers[0].is_alive(), 'producer blocked on an abandoned full queue'
        assert not handle.closed, 'caller-owned source must remain open'
    finally:
        iterator.close()
        # Unblock the old implementation when this regression deliberately fails.
        for pending in queues:
            while not pending.empty():
                pending.get_nowait()
        for worker in workers:
            worker.join(2)


@pytest.mark.parametrize('bad', [False, True])
def test_completion_or_error_stops_worker_and_closes_owned_source(monkeypatch, bad):
    workers = capture_workers(monkeypatch)
    handle = BytesIO(b'invalid\n' if bad else b'<urn:s> <urn:p> "x" .\n')
    monkeypatch.setattr('rdfcore.parser.create_input_source',
                        lambda *args, **kwargs: InputSource(file=handle, auto_close=True))
    iterator = streaming.parse_stream(handle, 'nt')
    if bad:
        with pytest.raises(ParserError):
            list(iterator)
    else:
        assert len(list(iterator)) == 1
    workers[0].join(2)
    assert not workers[0].is_alive()
    assert handle.closed


def test_sink_error_closes_owned_source_without_closing_caller_source(monkeypatch):
    for owned in (False, True):
        handle = BytesIO(b'<urn:s> <urn:p> "x" .\n')
        monkeypatch.setattr('rdfcore.parser.create_input_source',
                            lambda *args, **kwargs: InputSource(file=handle, auto_close=owned))
        class Sink:
            def add(self, statement):
                raise RuntimeError('sink failed')
        with pytest.raises(RuntimeError, match='sink failed'):
            streaming.parse_stream(handle, 'nt', Sink())
        assert handle.closed is owned
