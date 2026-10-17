"""Verified SPO-pattern measurements against RDFLib, with isolated setup."""

import argparse
import itertools
import json
from pathlib import Path
import platform
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import rdflib
import rdfcore
from benchmarks.compare_rdflib_rdfcore import measure


def query_benchmarks(size, *, repeats=5, warmup=1):
    datasets = []
    for module in (rdflib, rdfcore):
        dataset = module.Dataset()
        graphs = [dataset.default_graph, dataset.graph(module.URIRef('urn:g1')),
                  dataset.graph(module.URIRef('urn:g2'))]
        for index in range(size):
            graphs[index % 3].add((module.URIRef(f'urn:s{index % 31}'), module.URIRef(f'urn:p{index % 7}'),
                                   module.Literal(index)))
        datasets.append(graphs)
    rows = []
    def records(graph, pattern):
        return {tuple((type(term).__name__, str(term), str(getattr(term, 'datatype', None)),
                       getattr(term, 'language', None)) for term in triple) for triple in graph.triples(pattern)}
    for context in range(3):
        for bound in itertools.product((False, True), repeat=3):
            patterns = []
            for module in (rdflib, rdfcore):
                target = module.URIRef('urn:s0'), module.URIRef('urn:p0'), module.Literal(0)
                patterns.append(tuple(term if flag else None for term, flag in zip(target, bound)))
            expected = records(datasets[0][context], patterns[0])
            assert records(datasets[1][context], patterns[1]) == expected
            for library, graphs, pattern in zip(('rdflib', 'rdfcore'), datasets, patterns):
                row = measure(f'{library}.memory.context{context}.{bound}',
                              lambda graph=graphs[context], pattern=pattern: sum(1 for _ in graph.triples(pattern)),
                              repeats=repeats, warmup=warmup)
                assert all(run['result'] == len(expected) for run in row['runs'])
                rows.append({**row, 'correctness_verified': True, 'context': context,
                             'bound': bound, 'statements': size})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--statements', type=int, default=10000)
    parser.add_argument('--repeats', type=int, default=5)
    parser.add_argument('--warmup', type=int, default=1)
    args = parser.parse_args()
    if args.statements < 1 or args.repeats < 1 or args.warmup < 0:
        parser.error('positive statements/repeats and nonnegative warmup required')
    rows = query_benchmarks(args.statements, repeats=args.repeats, warmup=args.warmup)
    print(json.dumps({'python': platform.python_version(), 'platform': platform.platform(),
                      'rdflib': rdflib.__version__, 'revision': subprocess.check_output(
                          ['git', 'rev-parse', 'HEAD'], text=True).strip(),
                      'dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], text=True).strip()),
                      'measurement': 'median seconds; tracemalloc Python allocations, not RSS',
                      'results': rows}, indent=2))


if __name__ == '__main__':
    main()
