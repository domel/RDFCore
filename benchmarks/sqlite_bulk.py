"""Compare SQLite ingestion paths on fresh disk databases.

Run: python benchmarks/sqlite_bulk.py --statements 10000 --repeats 5
"""

import argparse
import json
import platform
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import rdflib
from rdfcore import Literal, SQLiteStore, URIRef


def measure(size, mode):
    triples = [(URIRef(f'urn:s{i}'), URIRef('urn:p'), Literal(i)) for i in range(size)]
    context = URIRef('urn:g')
    with tempfile.TemporaryDirectory(prefix='rdfcore-bulk-') as directory:
        path = Path(directory) / 'store.sqlite'
        store = SQLiteStore(path)
        started = perf_counter()
        if mode == 'single':
            for triple in triples:
                store.add(triple, context)
        elif mode == 'transaction':
            with store.transaction():
                for triple in triples:
                    store.add(triple, context)
        else:
            assert store.add_many(iter(triples), context) == size
        elapsed = perf_counter() - started
        store.close()
        reopened = SQLiteStore(path)
        try:
            assert len(reopened) == size
            assert {triple for triple, _ in reopened.triples((None, None, None), context)} == set(triples)
            assert (context in set(reopened.contexts())) == (size > 0)
        finally:
            reopened.close()
    return elapsed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--statements', type=int, default=10000)
    parser.add_argument('--repeats', type=int, default=5)
    parser.add_argument('--modes', nargs='+', choices=['single', 'transaction', 'bulk'],
                        default=['single', 'transaction', 'bulk'])
    args = parser.parse_args()
    if args.statements < 0 or args.repeats < 1:
        parser.error('statements must be nonnegative and repeats must be positive')
    modes = list(dict.fromkeys(args.modes))
    for mode in modes:
        measure(min(args.statements, 100), mode)
    runs = {mode: [] for mode in modes}
    for index in range(args.repeats):
        for mode in modes[index % len(modes):] + modes[:index % len(modes)]:
            runs[mode].append(measure(args.statements, mode))
    print(json.dumps({
        'python': platform.python_version(), 'rdflib': rdflib.__version__,
        'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], text=True).strip()),
        'statements': args.statements, 'repeats': args.repeats, 'storage': 'disk',
        'seconds': runs, 'median_seconds': {mode: statistics.median(values) for mode, values in runs.items()},
    }, indent=2))


if __name__ == '__main__':
    main()
