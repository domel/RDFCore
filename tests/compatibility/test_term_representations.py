import warnings
import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('kind', ['URIRef', 'BNode', 'Variable', 'Literal'])
@pytest.mark.parametrize('lexical', ['text', '', 'a\nb', 'a\tb', '\\"', 'a\n"""b', 'a\n"', '\r'])
def test_repr_and_n3(kind, lexical):
    results = []
    for module in (rdflib, rdfcore):
        if kind == 'Variable' and not lexical:
            continue
        value = getattr(module, kind)(lexical)
        with warnings.catch_warnings(record=True) as caught:
            try:
                n3 = value.n3()
            except Exception as error:
                n3 = type(error).__name__
        # Only the library's import prefix is different; retain all arguments.
        results.append((repr(value).replace(module.__name__ + '.', 'library.'), n3,
                        [type(w.message).__name__ for w in caught]))
    assert len(set(map(repr, results))) <= 1


@pytest.mark.parametrize('value', [float('inf'), float('-inf'), float('nan')])
def test_special_numeric_n3(value):
    assert rdfcore.Literal(value).n3() == rdflib.Literal(value).n3()


@pytest.mark.parametrize('case', ['language', 'typed', 'subclass'])
def test_literal_repr_keeps_metadata_and_subclass_name(case):
    results = []
    for module in (rdflib, rdfcore):
        cls = type('LiteralSubclass', (module.Literal,), {}) if case == 'subclass' else module.Literal
        options = {'lang': 'en'} if case == 'language' else {'datatype': module.URIRef('http://www.w3.org/2001/XMLSchema#integer')}
        value = cls('2', **options)
        results.append(repr(value).replace(module.__name__ + '.', 'library.'))
    assert results[0] == results[1]
