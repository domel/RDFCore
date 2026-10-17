"""RDF 1.2 syntax announcements constrain the following statements.

Selected N-Triples/Turtle/TriG WDs 2026-10-07, N-Quads WD 2026-10-10.
"""
import pytest

from rdfcore import Dataset, Graph
from rdfcore.exceptions import BadSyntax, ParserError


@pytest.mark.parametrize('format,cls', [('nt12', Graph), ('nq12', Dataset),
                                       ('turtle12', Graph), ('trig12', Dataset)])
@pytest.mark.parametrize('version,obj', [
    ('1.1', '"v"@en--ltr'),
    ('1.1', '<<( <urn:a> <urn:b> <urn:c> )>>'),
    ('1.2-basic', '<<( <urn:a> <urn:b> <urn:c> )>>'),
])
def test_declared_profile_rejects_newer_constructs(format, cls, version, obj):
    error = ParserError if format in ('nt12', 'nq12') else BadSyntax
    with pytest.raises(error):
        cls().parse(data=f'VERSION "{version}"\n<urn:s> <urn:p> {obj} .', format=format)


@pytest.mark.parametrize('format,cls', [('nt12', Graph), ('nq12', Dataset),
                                       ('turtle12', Graph), ('trig12', Dataset)])
def test_announcement_can_change_between_statements(format, cls):
    data = ('VERSION "1.1"\n<urn:s> <urn:p> "plain" .\n'
            'VERSION "1.2"\n<urn:s> <urn:p> <<( <urn:a> <urn:b> <urn:c> )>> .')
    assert len(cls().parse(data=data, format=format)) == 2


@pytest.mark.parametrize('format', ['turtle12', 'trig12'])
def test_annotation_is_a_full_rdf12_construct(format):
    with pytest.raises(BadSyntax):
        Graph().parse(data='VERSION "1.2-basic"\n<urn:s> <urn:p> <urn:o> {| <urn:q> <urn:v> |} .', format=format)
