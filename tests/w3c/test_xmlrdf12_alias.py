import pytest

from rdfcore import TripleTerm
from tests.w3c.runner import _parse


@pytest.mark.parametrize('legacy', [False, True])
def test_w3c_runner_accepts_xmlrdf12_with_existing_recovery_option(tmp_path, legacy):
    announcement = '' if legacy else ' rdf:version="1.2"'
    path = tmp_path / 'alias.rdf'
    path.write_text(
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" '
        'xmlns:e="urn:"' + announcement + '>'
        '<rdf:Description rdf:about="urn:s"><e:p rdf:parseType="Triple">'
        '<rdf:Description rdf:about="urn:a"><e:b rdf:resource="urn:c"/>'
        '</rdf:Description></e:p></rdf:Description></rdf:RDF>', encoding='utf-8')
    graph = _parse(path, 'xmlrdf12', legacy_w3c=legacy)
    assert len(graph) == 1
    assert isinstance(next(iter(graph))[2], TripleTerm)
