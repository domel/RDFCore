"""Executable RDFLib 7.6.0 regressions for the 2026-10-18 review."""
from collections import Counter
import operator

import pytest
import rdflib
from rdflib.compare import isomorphic as reference_isomorphic

import rdfcore
from rdfcore.compare import isomorphic


def term_record(term):
    return (type(term).__name__, str(term), getattr(term, 'language', None),
            str(getattr(term, 'datatype', None)), getattr(term, 'direction', None))


@pytest.mark.parametrize('case', ['self', 'shared_id', 'equal_id', 'raw', 'none', 'other', 'invalid_selected', 'invalid_other'])
def test_addn_context_filter_and_validation(case):
    outcomes = []
    for module in (rdflib, rdfcore):
        graph = module.Graph(identifier=module.URIRef('urn:g'))
        contexts = {
            'self': graph, 'shared_id': module.Graph(identifier=graph.identifier),
            'equal_id': module.Graph(identifier=module.URIRef('urn:g')),
            'raw': graph.identifier, 'none': None,
            'other': module.Graph(identifier=module.URIRef('urn:other')),
        }
        context = graph if case == 'invalid_selected' else contexts.get(case, contexts['other'])
        triple = (module.URIRef('urn:s'), module.URIRef('urn:p'), module.Literal('x'))
        if case.startswith('invalid'):
            triple = (1, 2, 3)
        try:
            result = graph.addN([(*triple, context)] * 2)
            outcome = (None, result is graph, len(graph))
        except Exception as error:
            outcome = (type(error).__name__, None, len(graph))
        outcomes.append(outcome)
    assert outcomes[0] == outcomes[1]


@pytest.mark.parametrize('kind', ['Graph', 'Dataset'])
@pytest.mark.parametrize('case', ['scalar', 'empty_s', 'empty_p', 'empty_o', 'duplicates', 'multi_sp', 'multi_so', 'multi_po', 'tuple', 'none'])
def test_choices_results_duplicates_and_errors(kind, case):
    outcomes = []
    for module in (rdflib, rdfcore):
        graph = getattr(module, kind)()
        s, p, o = module.URIRef('urn:s'), module.URIRef('urn:p'), module.Literal('x')
        graph.add((s, p, o))
        patterns = {'scalar': (s, p, o), 'empty_s': ([], p, o), 'empty_p': (s, [], o),
                    'empty_o': (s, p, []), 'duplicates': ([s, s], p, o),
                    'multi_sp': ([s], [p], o), 'multi_so': ([s], p, [o]),
                    'multi_po': (s, [p], [o]), 'tuple': ((s,), p, o), 'none': (None, None, None)}
        try:
            rows = list(graph.triples_choices(patterns[case]))
            outcome = (None, Counter(tuple(term_record(term) for term in row) for row in rows))
        except Exception as error:
            outcome = (type(error).__name__, str(error))
        outcomes.append(outcome)
    assert outcomes[0] == outcomes[1]


@pytest.mark.parametrize('union', [False, True])
@pytest.mark.parametrize('context', [None, 'default', 'named', 'missing', 'named_string', 'bad_int', 'false', 'empty_list', 'empty_string', 'zero'])
def test_dataset_choices_context_selection(union, context):
    outcomes = []
    for module in (rdflib, rdfcore):
        graph = module.Dataset(default_union=union)
        s, p = module.URIRef('urn:s'), module.URIRef('urn:p')
        graph.default_graph.add((s, p, module.Literal('default')))
        named = graph.graph(module.URIRef('urn:g'))
        named.add((s, p, module.Literal('named')))
        selected = {None: None, 'default': graph.default_graph, 'named': named,
                    'missing': module.URIRef('urn:missing'), 'named_string': 'urn:g',
                    'bad_int': 42, 'false': False, 'empty_list': [], 'empty_string': '', 'zero': 0}[context]
        try:
            outcomes.append((None, sorted(str(row[2]) for row in graph.triples_choices(([s], p, None), context=selected))))
        except Exception as error:
            outcomes.append((type(error).__name__, str(error)))
    assert outcomes[0] == outcomes[1]


@pytest.mark.parametrize('case', ['empty', 'equal', 'different', 'blank_position', 'shared_blank', 'length'])
def test_graph_isomorphic_method_matches_reference_approximation(case):
    outcomes = []
    for module in (rdflib, rdfcore):
        a, b = module.Graph(), module.Graph()
        p, x, n = module.URIRef('urn:p'), module.URIRef('urn:x'), module.BNode('n')
        if case != 'empty':
            a.add((n if case in ('blank_position', 'shared_blank') else x, p, x))
            if case != 'length':
                b.add((x, p, n if case == 'blank_position' else module.URIRef('urn:y') if case == 'different' else x))
        outcomes.append(a.isomorphic(b))
    assert outcomes[0] == outcomes[1]


@pytest.mark.parametrize('blank', [False, True])
def test_exact_comparison_beyond_python_recursion_limit(blank):
    outcomes = []
    for module, compare in ((rdflib, reference_isomorphic), (rdfcore, isomorphic)):
        a, b = module.Graph(), module.Graph()
        for i in range(1100):
            a.add((module.BNode(f'a{i}') if blank else module.URIRef(f'urn:s{i}'), module.URIRef('urn:p'), module.Literal(i)))
            b.add((module.BNode(f'b{i}') if blank else module.URIRef(f'urn:s{i}'), module.URIRef('urn:p'), module.Literal(i)))
        outcomes.append(compare(a, b))
    assert outcomes == [True, True]


@pytest.mark.parametrize('format', ['turtle', 'trig', 'xml'])
@pytest.mark.parametrize('base,explicit', [('https://example.org/', None), (None, 'https://example.org/'), ('https://old/', 'https://example.org/'), ('https://old/', ''), (None, None)])
def test_serialization_base_metadata_and_meaning(format, base, explicit):
    outputs = []
    for module in (rdflib, rdfcore):
        graph = module.Graph(base=base, bind_namespaces='none')
        graph.add((module.URIRef('https://example.org/s'), module.URIRef('https://example.org/p'), module.Literal('x')))
        value = graph.serialize(format=format, base=explicit)
        marker = 'xml:base=' if format == 'xml' else '@base'
        outputs.append(marker in value)
        # This assertion checks IRI expansion; a Graph's TriG serializer can
        # use its generated identifier for a named block in the reference.
        restored = (rdflib.Dataset(default_union=True) if format == 'trig' else rdflib.Graph()).parse(
            data=value, format=format, publicID='https://unrelated/')
        assert (rdflib.URIRef('https://example.org/s'), rdflib.URIRef('https://example.org/p'), rdflib.Literal('x')) in restored
    assert outputs[0] == outputs[1]


@pytest.mark.parametrize('cls', ['URIRef', 'BNode', 'Variable', 'Literal'])
@pytest.mark.parametrize('other_cls', ['URIRef', 'BNode', 'Variable', 'Literal'])
@pytest.mark.parametrize('op', [operator.lt, operator.gt, operator.le, operator.ge])
def test_term_subclass_ordering(cls, other_cls, op):
    outcomes = []
    for module in (rdflib, rdfcore):
        custom = type('Custom', (getattr(module, cls),), {})
        outcomes.append((op(custom('a'), getattr(module, other_cls)('b')),
                         op(getattr(module, other_cls)('b'), custom('a'))))
    assert outcomes[0] == outcomes[1]


@pytest.mark.parametrize('case', ['cycle', 'split_cycles', 'loop', 'star'])
def test_exact_comparison_backtracks_like_reference(case):
    outcomes = []
    cycle = [(i, (i + 1) % 6) for i in range(6)]
    variants = {'cycle': cycle, 'split_cycles': [(i, (i // 3) * 3 + (i + 1) % 3) for i in range(6)],
                'loop': [(i, i) for i in range(6)], 'star': [(0, i) for i in range(6)]}
    for module, compare in ((rdflib, reference_isomorphic), (rdfcore, isomorphic)):
        a, b = module.Graph(), module.Graph()
        for source, edges, prefix in ((a, cycle, 'a'), (b, variants[case], 'b')):
            for s, o in edges:
                source.add((module.BNode(prefix + str(s)), module.URIRef('urn:p'), module.BNode(prefix + str(o))))
        outcomes.append(compare(a, b))
    assert outcomes[0] == outcomes[1]


@pytest.mark.parametrize('backend', ['memory', 'sqlite'])
def test_addn_and_choices_store_parity(backend, tmp_path):
    outcomes = []
    for module in (rdflib, rdfcore):
        store = rdfcore.SQLiteStore(tmp_path / 'data.sqlite') if module is rdfcore and backend == 'sqlite' else 'default'
        graph = module.Graph(store=store, identifier=module.URIRef('urn:g'))
        try:
            triple = (module.URIRef('urn:s'), module.URIRef('urn:p'), module.Literal('text', lang='EN'))
            assert graph.addN([(*triple, graph), (*triple, graph), (*triple, graph.identifier)]) is graph
            outcomes.append((len(graph), [tuple(term_record(t) for t in row)
                                         for row in graph.triples_choices(([triple[0], triple[0]], None, None))]))
        finally:
            graph.close()
    assert outcomes[0] == outcomes[1]
    if backend == 'sqlite':
        reopened = rdfcore.SQLiteStore(tmp_path / 'data.sqlite')
        try:
            graph = rdfcore.Graph(store=reopened, identifier=rdfcore.URIRef('urn:g'))
            assert len(list(graph.triples_choices(([], None, None)))) == 1
        finally:
            reopened.close()
