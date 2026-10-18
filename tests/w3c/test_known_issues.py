"""Reviewed explanations are evidence, never replacements for test results."""

from copy import deepcopy

import pytest
import rdflib
import rdfcore

from tests.w3c.known_issues import classify_issue


PIN = '369a90d1a60c021b746df2e411da0ff36258a758'
BASE = 'https://w3c.github.io/rdf-tests/rdf/'


def issue(identifier, *, status='unsupported', **kwargs):
    return {'id': BASE + identifier, 'status': status, 'reason': 'observed failure', **kwargs}


def classify(test, *, format='semantics', profile='default', pin=PIN):
    report = {'snapshot': pin, 'execution_profile': profile}
    suite = {'format': format}
    original = deepcopy((report, suite, test))
    result = classify_issue(report, suite, test)
    assert (report, suite, test) == original
    assert set(result) == {'classification', 'task', 'reference', 'reason', 'evidence'}
    assert result['reason'] and result['evidence']
    assert 'status' not in result
    return result


@pytest.mark.parametrize('pin', [PIN, 'f' * 40])
def test_unknown_id_is_unreviewed(pin):
    result = classify(issue('rdf12/new#unknown'), pin=pin)
    assert result['classification'] == 'unreviewed'


def test_known_id_at_unknown_snapshot_is_unreviewed():
    test = issue('rdf11/rdf-mt/manifest.ttl#float-zero')
    assert classify(test, pin='f' * 40)['classification'] == 'unreviewed'


def test_unreviewed_profile_does_not_inherit_a_reviewed_explanation():
    test = issue('rdf11/rdf-mt/manifest.ttl#float-zero')
    assert classify(test, profile='future-recovery')['classification'] == 'unreviewed'


@pytest.mark.parametrize('number', ['001', '002'])
@pytest.mark.parametrize('format', ['xml', 'xml12'])
def test_xml_canonical_gap_is_shared_with_pinned_oracle(number, format):
    assert rdflib.__version__ == '7.6.0'
    reification = ' rdf:ID="reif"' if number == '002' else ''
    data = f'''<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
        xmlns:eg="http://example.org/" xml:base="http://example.com/">
      <rdf:Description rdf:about="http://www.example.org/a">
        <eg:prop{reification} rdf:parseType="Literal"><br /></eg:prop>
      </rdf:Description></rdf:RDF>'''
    observations = []
    for module in (rdflib, rdfcore):
        graph = module.Graph().parse(data=data, format='xml' if module is rdflib else format)
        literals = sorted(str(o) for o in graph.objects() if isinstance(o, module.Literal))
        observations.append((len(graph), literals))
    assert observations[0] == observations[1]
    assert observations[0] == ((1, ['<br/>']) if number == '001'
                               else (5, ['<br/>', '<br/>']))
    assert '<br></br>' not in observations[0][1]  # Official expected lexical form.
    test = issue('rdf11/rdf-xml/manifest.ttl#xml-canon-test' + number, status='failed')
    result = classify(test, format=format)
    assert result['classification'] == 'compatibility-conformance-conflict'
    assert result['task'] == 'S09 T29'
    assert '7.6.0' in result['evidence']


@pytest.mark.parametrize('name,action,result', [
    ('tt-01', '74a2255b38ca9e44fb4045d3f1d04489572391ac1f78ce2caa62abed3c5d9d15',
     'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'),
    ('dir-02', '192169cfbfa03cb13548ae92f355a657361439573c3b0bd3128e265d898cbc1a',
     'c19cbd377772916df5baf1191f48543cd267826abc6dc7107ddcdb4979f116b9'),
])
def test_disputed_fixture_requires_both_reviewed_hashes(name, action, result):
    test = issue('rdf12/rdf-xml/eval#rdf12-xml-' + name, status='failed')
    assert classify(test, format='xml12')['classification'] == 'unreviewed'
    test.update(action_sha256=action, result_sha256=result)
    assert classify(test, format='xml12')['classification'] == 'snapshot-fixture-conflict'
    for key in ('action_sha256', 'result_sha256'):
        changed = dict(test, **{key: '0' * 64})
        assert classify(changed, format='xml12')['classification'] == 'unreviewed'


@pytest.mark.parametrize('number', list(range(1, 17)) + ['reif-01'])
def test_annotation_profile_conflicts_are_individually_reviewed(number):
    suffix = f'{number:02}' if isinstance(number, int) else number
    test = issue('rdf12/rdf-xml/eval#rdf12-xml-an-' + suffix, status='failed')
    result = classify(test, format='xml12')
    assert result['classification'] == 'snapshot-profile-conflict'
    assert result['task'] == 'S09 T29'
    assert 'rdf:version' in result['reason']
    assert suffix in result['evidence']


@pytest.mark.parametrize('name,task,fragment', [
    ('float-zero', 'S11 T38', 'signed zero'),
    ('datatypes-non-well-formed-literal-1', 'S11 T38', 'unrecognized'),
    ('datatypes-non-well-formed-literal-2', 'S11 T38', 'flargh'),
    ('rdfs-subClassOf-a-Property-test001', 'S11 T39', 'consistent'),
    ('rdf-charmod-uris-test003', 'S11 T37', 'percent'),
    ('statement-entailment-test002', 'S11 T39', 'reification'),
    ('xmlsch-02-whitespace-facet-2', 'S11 T38', 'whitespace'),
])
def test_semantic_explanations_are_specific(name, task, fragment):
    test = issue('rdf11/rdf-mt/manifest.ttl#' + name)
    result = classify(test)
    assert result['classification'] == 'missing-functionality'
    assert result['task'] == task
    assert fragment.lower() in result['reason'].lower()
    assert '#' in result['reference']


def test_semantic_metadata_is_included_without_claiming_a_proof():
    test = issue('rdf12/rdf-semantics#opaque-literal', regime='simple',
                 types=['http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#PositiveEntailmentTest'],
                 recognized_datatypes=['http://www.w3.org/2001/XMLSchema#integer'], result='urn:conclusion')
    result = classify(test)
    assert '042' in result['reason'] and '42' in result['reason']
    assert 'simple' in result['evidence'] and 'integer' in result['evidence']


def test_passed_and_wrong_suite_are_not_classified_as_open_issues():
    test = issue('rdf11/rdf-mt/manifest.ttl#float-zero', status='passed')
    assert classify(test)['classification'] == 'unreviewed'
    test['status'] = 'unsupported'
    assert classify(test, format='nt12')['classification'] == 'unreviewed'


# Independent inventory of the 35 historical and 9 new unsupported IDs.
# Do not derive this list from the implementation's catalogue.
SEMANTIC_IDS = '''
datatypes-intensional-xsd-integer-decimal-compatible
datatypes-non-well-formed-literal-1
datatypes-non-well-formed-literal-2
datatypes-semantic-equivalence-within-type-1
datatypes-semantic-equivalence-within-type-2
datatypes-semantic-equivalence-between-datatypes
datatypes-range-clash
datatypes-test010
datatypes-plain-literal-and-xsd-string
horst-01-subClassOf-intensional
horst-01-subPropertyOf-intensional
rdf-charmod-uris-test003
rdf-charmod-uris-test004
rdfs-container-membership-superProperty-test001
rdfs-domain-and-range-intensionality-range
rdfs-domain-and-range-intensionality-domain
rdfs-entailment-test001
rdfs-entailment-test002
rdfs-subClassOf-a-Property-test001
statement-entailment-test001
statement-entailment-test002
statement-entailment-test003
statement-entailment-test004
xmlsch-02-whitespace-facet-1
xmlsch-02-whitespace-facet-2
xmlsch-02-whitespace-facet-4
literal-type
float-zero
float-round-different
float-round-same
float-infinity
double-zero
double-round-different
double-round-same
double-infinity
'''.split()
NEW_SEMANTIC_IDS = '''malformed-literal opaque-literal json-array-ordered
json-object-unordered json-zero json-zero-array json-round-different
json-round-same json-infinity'''.split()


@pytest.mark.parametrize('name,version', [(name, 'rdf11') for name in SEMANTIC_IDS]
                         + [(name, 'rdf12') for name in NEW_SEMANTIC_IDS])
@pytest.mark.parametrize('pin', [PIN, 'd5d930b03ee6b63b388d0bb28fdb29ee78a59ec0'])
def test_every_reviewed_semantic_id_has_a_specific_target(name, version, pin):
    path = ('rdf11/rdf-mt/manifest.ttl#' if version == 'rdf11'
            else 'rdf12/rdf-semantics#')
    result = classify(issue(path + name), pin=pin)
    assert result['classification'] == 'missing-functionality'
    assert result['task'] in {'S11 T37', 'S11 T38', 'S11 T39'}
    assert result['reference'].startswith('https://www.w3.org/TR/')
    assert name in result['evidence']


def test_complete_execution_accounting_including_inherited_cases():
    from collections import Counter

    # Two XML11 failures recur in XML12; 35 semantic unsupported IDs recur
    # in the RDF12 suite. Count executions, not merely unique identifiers.
    executions = []
    for format in ('xml', 'xml12'):
        for number in ('001', '002'):
            executions.append(classify(issue('rdf11/rdf-xml/manifest.ttl#xml-canon-test'
                                            + number, status='failed'), format=format))
    for number in list(range(1, 17)) + ['reif-01']:
        suffix = f'{number:02}' if isinstance(number, int) else number
        executions.append(classify(issue('rdf12/rdf-xml/eval#rdf12-xml-an-' + suffix,
                                        status='failed'), format='xml12'))
    from tests.w3c.known_issues import DISPUTED
    for name, (action, result, _, _) in DISPUTED.items():
        executions.append(classify(issue('rdf12/rdf-xml/eval#' + name, status='failed',
                                        action_sha256=action, result_sha256=result), format='xml12'))
    for name in SEMANTIC_IDS * 2:
        executions.append(classify(issue('rdf11/rdf-mt/manifest.ttl#' + name)))
    for name in NEW_SEMANTIC_IDS:
        executions.append(classify(issue('rdf12/rdf-semantics#' + name)))
    assert len(executions) == 102
    assert Counter(item['classification'] for item in executions) == {
        'compatibility-conformance-conflict': 4, 'snapshot-profile-conflict': 17,
        'snapshot-fixture-conflict': 2, 'missing-functionality': 79,
    }
