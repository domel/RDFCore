"""Offline tests for normative-source accounting, not conformance checks."""

import pytest

from tests.w3c.requirements import inventory_document, validate_matrix


DOCUMENT = '''<html><body>
<section id="intro" class="informative"><p>Examples MUST NOT count as requirements.</p></section>
<section id="model"><h2>Model</h2><p>A graph is a set of triples.</p>
<ul><li>The subject is an IRI or blank node.</li><li>The object may be a triple term.</li></ul>
<section id="grammar"><table><tr><th>Rule</th></tr>
<tr id="prod"><td>[1]</td><td>triple</td><td>::= subject predicate object '.'</td></tr></table></section>
<section id="semantics"><table><tr><td>If x is in IC, then x is in IR.</td></tr></table></section>
<p>Implementations MUST reject invalid positions.</p></section>
<section id="references"><p>References are not implementation requirements.</p></section>
<script>fake MUST text</script></body></html>'''


def test_model_grammar_and_semantic_conditions_are_inventoried():
    report = inventory_document('test', DOCUMENT.encode(), 'https://example.org/spec/', '2026-10-17')
    assert len(report['clauses']) == 6
    assert {clause['kind'] for clause in report['clauses']} == {'prose', 'list-item', 'grammar', 'condition'}
    assert all('Examples' not in clause['text'] and 'References' not in clause['text'] for clause in report['clauses'])
    assert next(clause for clause in report['clauses'] if clause['kind'] == 'grammar')['anchor'] == 'prod'


def test_clause_inventory_is_deterministic_and_detects_changes():
    left = inventory_document('test', DOCUMENT.encode(), 'https://example.org/spec/', '2026-10-17')
    assert left == inventory_document('test', DOCUMENT.encode(), 'https://example.org/spec/', '2026-10-17')
    right = inventory_document('test', DOCUMENT.replace('valid positions', 'valid components').encode(),
                               'https://example.org/spec/', '2026-10-17')
    assert left['source_sha256'] != right['source_sha256']
    assert {c['id'] for c in left['clauses']} != {c['id'] for c in right['clauses']}


def test_informative_document_is_explicitly_excluded():
    report = inventory_document('primer', DOCUMENT.encode(), 'https://example.org/primer/', '2026-10-17', informative=True)
    assert not report['clauses']
    assert report['exclusion_reason']


def test_matrix_cannot_omit_or_invent_requirements():
    report = inventory_document('test', DOCUMENT.encode(), 'https://example.org/spec/', '2026-10-17')
    records = [{'id': c['id'], 'status': 'partial', 'implementation': 'rdfcore/term.py',
                'expected': 'Validate the referenced model constraint', 'tests': ['tests/formats/test_rdf12_terms.py'],
                'reason': 'selected cases only'} for c in report['clauses']]
    assert validate_matrix([report], records)['unaccounted'] == []
    with pytest.raises(ValueError, match='unaccounted'):
        validate_matrix([report], records[:-1])
    with pytest.raises(ValueError, match='unknown'):
        validate_matrix([report], records + [{**records[0], 'id': 'invented'}])


@pytest.mark.parametrize('field,value', [('status','implemented'), ('reason',''), ('expected',''), ('implementation','')])
def test_unsubstantiated_matrix_entries_are_rejected(field, value):
    report = inventory_document('test', b'<section id="a"><p>A graph is a set.</p></section>',
                                'https://example.org/spec/', '2026-10-17')
    record = {'id': report['clauses'][0]['id'], 'status': 'partial', 'implementation': 'rdfcore/term.py',
              'expected': 'Use set semantics', 'tests': [], 'reason': 'no exhaustive evidence'}
    record[field] = value
    with pytest.raises(ValueError):
        validate_matrix([report], [record])


def test_not_applicable_requires_a_reason_and_duplicates_are_rejected():
    report = inventory_document('test', b'<section id="a"><p>An HTTP server MUST reply.</p></section>',
                                'https://example.org/spec/', '2026-10-17')
    record = {'id': report['clauses'][0]['id'], 'status': 'not-applicable-with-reason',
              'expected': 'Server response', 'implementation': 'not applicable', 'tests': [], 'reason': 'not an HTTP server'}
    assert validate_matrix([report], [record])['unaccounted'] == []
    with pytest.raises(ValueError, match='duplicate'):
        validate_matrix([report], [record, record])


def test_void_elements_do_not_leak_excluded_scope():
    source = b'<section class="informative"><p>Example<br>only</p></section><section id="real"><p>A <em>graph</em> is a set.<br>It has triples.</p></section>'
    report = inventory_document('test', source, 'https://example.org/', '2026-10-17')
    assert len(report['clauses']) == 1
    assert report['clauses'][0]['anchor'] == 'real'
    assert report['exclusions']


def test_examples_are_excluded_even_inside_normative_sections():
    source = b'<section id="real"><div class="example"><p>Example MUST not count.</p></div><p>A graph is a set.</p></section>'
    report = inventory_document('test', source, 'https://example.org/', '2026-10-17')
    assert len(report['clauses']) == 1
    assert 'Example' not in report['clauses'][0]['text']


def test_optional_html_closing_tags_and_eof_do_not_erase_requirements():
    source = b'<!doctype html><title>Spec</title><p>First MUST rule.<p>Second MUST rule.<ul><li>One<li>Two</ul><p>Last rule.'
    report = inventory_document('test', source, 'https://example.org/', '2026-10-17')
    assert [c['text'] for c in report['clauses']] == ['First MUST rule.', 'Second MUST rule.', 'One', 'Two', 'Last rule.']
