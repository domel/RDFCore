"""Offline minimal regressions and implementation routes for the T23 backlog.

These are reduced scenarios, not replacements for the pinned W3C fixtures.
An unsupported contract expectation is never a successful conformance result.
"""

from dataclasses import dataclass

from rdfcore import BNode, Literal, RDF, RDFS, TripleTerm, URIRef, XSD
from tests.w3c.known_issues import BASE, SEM11, SEM12, SEMANTIC_11, SEMANTIC_12

S, P, O, Q, C, D = map(URIRef, ('urn:s', 'urn:p', 'urn:o', 'urn:q', 'urn:C', 'urn:D'))


@dataclass(frozen=True)
class Case:
    premise: tuple
    conclusion: tuple | bool
    regime: str
    datatypes: frozenset
    expected: bool
    supported: bool
    implementation: str


CASES = {}


def add(name, premise, conclusion, *, regime='rdf', datatypes=(), expected=True,
        supported=True, implementation='Value-aware matching and explicit recognition in semantics._decide.'):
    CASES[name] = Case(tuple(premise), False if conclusion is False else tuple(conclusion),
                       regime, frozenset(datatypes), expected, supported, implementation)


def literal(value, datatype):
    return Literal(value, datatype=datatype, normalize=False)


def value_case(name, left, right, datatype, *, expected=True, other=None):
    add(name, [(S, P, literal(left, datatype))], [(S, P, literal(right, other or datatype))],
        datatypes={datatype, other or datatype}, expected=expected)


add('datatypes-intensional-xsd-integer-decimal-compatible',
    [(XSD.integer, RDFS.subClassOf, XSD.decimal)], False, regime='rdfs',
    datatypes={XSD.integer, XSD.decimal}, expected=False,
    implementation='T38: _datatype_spaces.subset and a checked datatype-schema candidate establish consistency.')
for number, recognized in ((1, ()), (2, (XSD.integer,))):
    add(f'datatypes-non-well-formed-literal-{number}', [(S, P, literal('flargh', XSD.integer))], False,
        regime='rdfs', datatypes=recognized, expected=number == 2,
        implementation='Recognition-dependent lexical validation and inconsistency in semantics._decide.')
value_case('datatypes-semantic-equivalence-within-type-1', '010', '10', XSD.integer)
value_case('datatypes-semantic-equivalence-within-type-2', '10', '010', XSD.integer)
value_case('datatypes-semantic-equivalence-between-datatypes', '10', '10.0', XSD.integer, other=XSD.decimal)
for name, value, datatype in (
    ('datatypes-range-clash', literal('25', XSD.integer), XSD.string),
    ('datatypes-test010', Literal('25'), XSD.integer),
    ('rdfs-entailment-test002', Literal('flargh'), RDF.langString),
):
    add(name, [(S, P, value), (P, RDFS.range, datatype)], False, regime='rdfs',
        datatypes={XSD.integer, XSD.string, RDF.langString},
        implementation='T38: _datatype_reasoning checks inferred value membership against recognized ranges and detects disjoint spaces.')
add('datatypes-plain-literal-and-xsd-string', [(S, P, Literal('a string'))],
    [(S, P, literal('a string', XSD.string))], regime='rdfs', datatypes={XSD.string})
add('horst-01-subClassOf-intensional', [(C, RDF.type, RDFS.Class), (RDF.type, RDFS.domain, D)],
    [(C, RDFS.subClassOf, D)], regime='rdfs', expected=False,
    implementation='T39: intensional RDFS countermodel; extension inclusion must not assert a schema edge.')
add('horst-01-subPropertyOf-intensional',
    [(P, RDF.type, RDF.Property), (P, RDFS.range, XSD.integer),
     (P, RDFS.range, XSD.string), (Q, RDF.type, RDF.Property)],
    [(P, RDF.type, RDF.Property), (P, RDFS.subPropertyOf, Q)], regime='rdfs',
    datatypes={XSD.integer, XSD.string}, expected=False,
    implementation='T38: checked candidate with an empty property extension; no subPropertyOf edge is invented.')
for name, left, right in (
    ('rdf-charmod-uris-test003', 'André', 'Andr%C3%A9'),
    ('rdf-charmod-uris-test004', 'Andr%C3%A9', 'André'),
):
    add(name, [(URIRef('http://example.org/#'+left), P, Literal('2000'))],
        [(URIRef('http://example.org/#'+right), P, Literal('2000'))], expected=False,
        implementation='T37: ordinary-ground countermodel certificate; preserve exact IRI identity.')
add('rdfs-container-membership-superProperty-test001', [(S, RDFS.member, O)],
    [(S, RDF['_1'], O)], regime='rdfs', expected=False,
    implementation='T39: finite query-targeted container axioms and one-way subproperty countermodel.')
for suffix, predicate in (('range', RDFS.range), ('domain', RDFS.domain)):
    add('rdfs-domain-and-range-intensionality-'+suffix,
        [(C, RDF.type, RDFS.Class), (C, RDFS.subClassOf, D), (D, RDF.type, RDFS.Class),
         (P, RDF.type, URIRef(str(RDFS)+'Property')), (P, predicate, C)],
        [(D, RDF.type, RDFS.Class), (P, RDF.type, URIRef(str(RDFS)+'Property')), (P, predicate, D)],
        regime='rdfs', expected=False,
        implementation='T39: intensional domain/range countermodel; do not propagate schema range/domain through subclass edges.')
add('rdfs-entailment-test001', [(P, RDFS.range, RDF.XMLLiteral), (S, P, literal('<', RDF.XMLLiteral))],
    False, regime='rdfs', datatypes={RDF.XMLLiteral},
    implementation='T28/T37: secure XML lexical validation; malformed recognized literal proves inconsistency.')
add('rdfs-subClassOf-a-Property-test001', [(C, RDF.type, RDF.Property), (D, RDFS.subClassOf, C)],
    False, regime='rdfs', expected=False,
    implementation='T39: construct consistent RDFS model allowing class/property overlap.')
for number in range(1, 5):
    if number in (1, 3):
        a, b = URIRef('urn:statement1'), URIRef('urn:statement2')
        premise = [(node, p, o) for node in (a, b) for p, o in (
            (RDF.type, RDF.Statement), (RDF.subject, S), (RDF.predicate, P), (RDF.object, O))]
        premise.append((a, Q, C))
        conclusion = [(b, Q, C)]
        route = 'T39: reification descriptions do not identify statement resources; preserve a countermodel with distinct reifiers.'
    else:
        b = BNode('statement')
        premise = [(S, P, O)]
        conclusion = [(b, p, o) for p, o in (
            (RDF.type, RDF.Statement), (RDF.subject, S), (RDF.predicate, P), (RDF.object, O))]
        route = 'T39: existential reification requires all four correlated edges; asserted SPO does not generate rdf:Statement.'
    add(f'statement-entailment-test{number:03}', premise, conclusion,
        regime='rdfs' if number == 3 else 'rdf', expected=False, implementation=route)
add('xmlsch-02-whitespace-facet-1', [(S, P, literal('3', XSD.int))],
    [(S, P, literal(' 3 ', XSD.int))], regime='rdfs', datatypes={XSD.int}, expected=False,
    implementation='T38: preserve raw lexical input and review the historical whitespace expectation against the selected lexical space.')
for number in (2, 4):
    add(f'xmlsch-02-whitespace-facet-{number}', [(S, P, literal(' 3 ', XSD.int))], False,
        regime='rdfs', datatypes={XSD.int},
        implementation='T38: explicit recognized lexical validity; keep both historical manifest executions independent.')
x = BNode('value')
add('literal-type', [(S, P, literal('42', XSD.integer))],
    [(S, P, x), (x, RDF.type, XSD.integer)], datatypes={XSD.integer},
    implementation='T37/T38: recognized value witness, membership closure and shared-binding homomorphism.')
for kind, different, same in (
    ('float', ('16777206.5', '16777207.5'), ('16777206.5', '16777205.5')),
    ('double', ('9007199254740990.5', '9007199254740991.5'),
     ('9007199254740992.5', '9007199254740991.5')),
):
    for suffix, pair, expected in (
        ('zero', ('0', '-0'), False), ('round-different', different, False),
        ('round-same', same, True), ('infinity', ('1E400', '1E401'), True),
    ):
        value_case(kind+'-'+suffix, *pair, XSD[kind], expected=expected)
add('malformed-literal', [(S, P, TripleTerm(S, Q, literal('c', XSD.integer)))], False,
    datatypes={XSD.integer}, implementation='T37: validate nested literals without asserting embedded triples; inconsistency entails false.')
add('opaque-literal', [(S, P, TripleTerm(S, Q, literal('042', XSD.integer)))],
    [(S, P, TripleTerm(S, Q, literal('42', XSD.integer)))], regime='simple', datatypes={XSD.integer},
    implementation='T37: value-aware keys descend into triple terms with one shared existential mapping.')
for suffix, left, right, expected in (
    ('array-ordered', '[-0,0]', '[0,-0]', False),
    ('object-unordered', '{"a":0,"b":1}', '{"b":1,"a":0}', True),
    ('zero', '0', '-0', False), ('zero-array', '[0]', '[-0]', False),
    ('round-different', '9007199254740990.5', '9007199254740991.5', False),
    ('round-same', '9007199254740992.5', '9007199254740991.5', True),
    ('infinity', '1E400', '1E401', True),
):
    value_case('json-'+suffix, left, right, RDF.JSON, expected=expected)


def semantic_plan(identifier, document=None):
    """Link a reviewed case to a requirement, executable regression and route."""
    for prefix, catalogue, reference in (
        (BASE+'rdf11/rdf-mt/manifest.ttl#', SEMANTIC_11, SEM11),
        (BASE+'rdf12/rdf-semantics#', SEMANTIC_12, SEM12),
    ):
        if identifier.startswith(prefix):
            name = identifier[len(prefix):]
            if name in catalogue and name in CASES:
                task, anchor, requirement = catalogue[name]
                return dict(task=task, reference=(document or reference)+'#'+anchor,
                            requirement=requirement,
                            regression='tests/w3c/test_semantics_contract.py::test_case['+name+']',
                            implementation=CASES[name].implementation)
    return None
