"""Experimental zero-thread line iterator; deliberately not a public API.

It reuses the RDF 1.1 parsers' line grammar. A faster loop alone does not
justify changing parse_stream's asynchronous read-ahead contract.
"""

import argparse
from importlib.metadata import PackageNotFoundError, version
from io import BytesIO
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rdfcore.exceptions import ParserError
from rdfcore.parser import Parser, create_input_source
from rdfcore.plugin import get
from rdfcore.plugins.parsers.ntriples import NTParser, _PreservedBNodes
from rdfcore.plugins.parsers.nquads import NQuadsParser
from rdfcore.streaming import parse_stream


def _native_lines(source=None, format=None, **kwargs):
    parser_class = get(format, Parser).getClass()
    if parser_class not in (NTParser, NQuadsParser):
        raise ValueError('prototype supports only the built-in RDF 1.1 NT/NQ parsers')
    input_source = create_input_source(source, format=format, **kwargs)
    try:
        stream = input_source.getCharacterStream()
        if stream is None:
            stream = input_source.getByteStream()
        if stream is None:
            name = 'N-Triples' if parser_class is NTParser else 'N-Quads'
            raise ParserError(f'{name} source has no readable stream')
        parser = parser_class()
        bnode_map = _PreservedBNodes() if kwargs.get('preserve_bnode_ids', False) else {}
        class Sink:
            value = None
            def add(self, statement):
                self.value = (*statement, None) if len(statement) == 3 else statement
        sink = Sink()
        for number, line in enumerate(stream, 1):
            sink.value = None
            try:
                if isinstance(line, bytes):
                    line = line.decode('utf-8')
                parser._parse_line(line, sink, number, bnode_map)
            except ParserError:
                raise
            except (UnicodeDecodeError, ValueError) as error:
                raise ParserError(f'line {number}: {error}') from error
            if sink.value is not None:
                yield sink.value
    finally:
        input_source.close()


def main():
    args_parser = argparse.ArgumentParser(description=__doc__)
    args_parser.add_argument('--statements', type=int, default=10000)
    args_parser.add_argument('--repeats', type=int, default=5)
    args_parser.add_argument('--format', choices=['nt', 'nquads'], default='nt')
    args = args_parser.parse_args()
    if args.statements < 0 or args.repeats < 1:
        args_parser.error('statements must be nonnegative and repeats positive')
    graph = ' <urn:g>' if args.format == 'nquads' else ''
    payload = ''.join(f'_:s{i % 32} <urn:p> "{i}"{graph} .\n' for i in range(args.statements)).encode()
    implementations = {'threaded': parse_stream, 'native_prototype': _native_lines}
    # Exact controlled term identity and order, outside all timing intervals.
    reference = list(parse_stream(BytesIO(payload), args.format, preserve_bnode_ids=True))
    assert list(_native_lines(BytesIO(payload), args.format, preserve_bnode_ids=True)) == reference
    samples = {name: [] for name in implementations}
    def measure(function):
        source = BytesIO(payload)
        start = perf_counter()
        count = sum(1 for _ in function(source, args.format, preserve_bnode_ids=True))
        elapsed = perf_counter() - start
        assert count == args.statements
        return elapsed
    for function in implementations.values():
        measure(function)
    names = list(implementations)
    for repeat in range(args.repeats):
        for name in (names if repeat % 2 == 0 else names[::-1]):
            samples[name].append(measure(implementations[name]))
    try:
        reference_version = version('rdflib')
    except PackageNotFoundError:
        reference_version = None
    print(json.dumps({'python': platform.python_version(), 'platform': platform.platform(),
        'rdflib': reference_version, 'revision': subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], text=True).strip(), 'dirty': bool(subprocess.check_output(
        ['git', 'status', '--porcelain'], text=True).strip()), 'statements': args.statements,
        'format': args.format, 'correctness_verified': True, 'seconds': samples,
        'median_seconds': {name: statistics.median(values) for name, values in samples.items()},
        'limitations': ['in-memory input; no RSS measurement',
                        'prototype changes read-ahead and producer-thread behavior; not enabled in parse_stream']}, indent=2))


if __name__ == '__main__':
    main()
