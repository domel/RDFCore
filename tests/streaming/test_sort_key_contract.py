"""Sorting uses canonical term keys, not RDF dataset canonicalization."""
import pytest

from rdfcore import Literal, TripleTerm, URIRef, XSD, external_sort, statement_key

S, P = URIRef('urn:s'), URIRef('urn:p')


def test_key_is_a_tuple_of_canonical_rdf12_term_strings():
    term = TripleTerm(S, P, Literal('é\x7f', lang='EN', direction='rtl'))
    assert statement_key((S, P, term)) == (
        '<urn:s>', '<urn:p>', '<<( <urn:s> <urn:p> "é\\u007F"@en--rtl )>>')


def test_raw_default_quad_and_triple_share_a_key_but_named_sentinel_does_not():
    triple = (S, P, Literal('v'))
    assert statement_key(triple) == statement_key((*triple, None))
    assert statement_key(triple) != statement_key((*triple, URIRef('urn:x-rdflib:default')))


def test_unique_uses_canonical_spelling_not_python_literal_identity():
    plain, typed = Literal('v'), Literal('v', datatype=XSD.string)
    assert plain != typed
    assert statement_key((S, P, plain)) == statement_key((S, P, typed))
    rows = list(external_sort([(S, P, typed), (S, P, plain)], unique=True, memory_budget=1))
    assert len(rows) == 1 and rows[0][2].datatype == XSD.string


@pytest.mark.parametrize('unique', [False, True])
@pytest.mark.parametrize('budget', [1, 100000])
def test_equal_keys_retain_the_first_spelling_across_merge_passes(tmp_path, unique, budget):
    values = [
        (S, P, Literal('v', lang='EN'), None),
        (URIRef('urn:z'), P, Literal('later')),
        (S, P, Literal('v', lang='en')),
        (S, P, Literal('v', lang='eN'), None),
        (S, P, Literal('v', lang='EN'), URIRef('urn:x-rdflib:default')),
    ]
    expected = sorted(values, key=statement_key)
    if unique:
        first = {}
        for row in expected:
            first.setdefault(statement_key(row), row)
        expected = list(first.values())
    actual = list(external_sort(values, unique=unique, memory_budget=budget,
                                temp_dir=tmp_path, max_open_runs=2))

    def spelling(rows):
        return [(len(row), str(row[0]), row[2].language, str(row[3]) if len(row) == 4 else '')
                for row in rows]

    assert spelling(actual) == spelling(expected)
    assert list(tmp_path.iterdir()) == []
