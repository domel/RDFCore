"""Offline clause probes, separate from official W3C manifest executions.

References: Semantics CRD 2026-09-24; Schema WD 2026-10-23. These finite
examples test the stated consequences, not completeness on arbitrary inputs.
"""
from dataclasses import dataclass

from rdfcore import BNode, Literal, RDF, RDFS, TripleTerm, URIRef, XSD


@dataclass(frozen=True)
class RequirementProbe:
    id: str
    section: str
    requirement: str
    premise: tuple
    conclusion: tuple | bool
    expected: bool = True
    regime: str = 'rdfs'
    datatypes: tuple = ()


S, P, O, C, D, Q = map(URIRef, ('urn:audit:s', 'urn:audit:p', 'urn:audit:o',
                               'urn:audit:C', 'urn:audit:D', 'urn:audit:q'))
X = BNode('audit-x')
TERM = TripleTerm(S, P, O)


def _case(name, section, requirement, premise, conclusion, **options):
    return RequirementProbe(name, section, requirement, tuple(premise),
                            conclusion if conclusion is False else tuple(conclusion), **options)


PROBES = (
    _case('simple-empty', 'x5-2-simple-entailment', 'Every graph entails the empty graph',
          [(S, P, O)], [], regime='simple'),
    _case('simple-no-new-name', 'x5-3-properties-of-simple-entailment-and-satisfiability',
          'Simple entailment does not introduce a fresh IRI', [(S, P, O)],
          [(S, P, C)], expected=False, regime='simple'),
    _case('blank-correlation', 'x5-1-blank-nodes', 'A blank node has one mapping throughout a graph',
          [(S, P, O), (O, Q, S)], [(X, P, O), (X, Q, S)], expected=False, regime='simple'),
    _case('inner-not-asserted', 'x5-simple-interpretations',
          'A triple-term occurrence does not assert its components',
          [(C, RDF.reifies, TERM)], [(S, P, O)], expected=False),
    _case('datatype-value-equality', 'x7-1-d-interpretations',
          'Recognized literals denote their mapped values',
          [(S, P, Literal('01', datatype=XSD.integer, normalize=False))],
          [(S, P, Literal('1', datatype=XSD.integer))], datatypes=(XSD.integer,)),
    _case('datatype-ill-typed', 'x7-2-datatype-entailment',
          'An ill-typed recognized literal makes the graph unsatisfiable',
          [(S, P, Literal('bad', datatype=XSD.integer))], False, datatypes=(XSD.integer,)),
    _case('datatype-unrecognized', 'x7-literals-and-datatypes',
          'An unrecognized datatype does not impose its value mapping',
          [(S, P, Literal('bad', datatype=URIRef('urn:audit:opaque')))], False, expected=False),
    _case('rdf-property', 'x8-rdf-interpretations', 'Predicates denote properties',
          [(S, P, O)], [(P, RDF.type, RDF.Property)], regime='rdf'),
    _case('domain', 'x9-rdfs-interpretations', 'Domain constrains each subject',
          [(P, RDFS.domain, C), (S, P, O)], [(S, RDF.type, C)]),
    _case('range', 'x9-rdfs-interpretations', 'Range constrains each object',
          [(P, RDFS.range, C), (S, P, O)], [(O, RDF.type, C)]),
    _case('domain-not-inherited', 'x9-rdfs-interpretations',
          'Extension inclusion does not assert an additional domain edge',
          [(P, RDFS.domain, C), (C, RDFS.subClassOf, D)],
          [(P, RDFS.domain, D)], expected=False),
    _case('subclass-transitive', 'x9-rdfs-interpretations', 'Subclass relations are transitive',
          [(S, RDFS.subClassOf, C), (C, RDFS.subClassOf, D)], [(S, RDFS.subClassOf, D)]),
    _case('subclass-reflexive', 'x9-rdfs-interpretations', 'Classes are subclasses of themselves',
          [(C, RDF.type, RDFS.Class)], [(C, RDFS.subClassOf, C)]),
    _case('subclass-members', 'x9-rdfs-interpretations', 'Subclass relations include instances',
          [(C, RDFS.subClassOf, D), (S, RDF.type, C)], [(S, RDF.type, D)]),
    _case('subproperty-transitive', 'x9-rdfs-interpretations', 'Subproperty relations are transitive',
          [(P, RDFS.subPropertyOf, Q), (Q, RDFS.subPropertyOf, C)], [(P, RDFS.subPropertyOf, C)]),
    _case('subproperty-reflexive', 'x9-rdfs-interpretations', 'Properties are subproperties of themselves',
          [(P, RDF.type, RDF.Property)], [(P, RDFS.subPropertyOf, P)]),
    _case('subproperty-extension', 'x9-rdfs-interpretations', 'Subproperty pairs belong to the superproperty',
          [(P, RDFS.subPropertyOf, Q), (S, P, O)], [(S, Q, O)]),
    _case('resource-universal', 'x9-rdfs-interpretations', 'IRIs denote resources',
          [], [(S, RDF.type, RDFS.Resource)]),
    _case('class-resource', 'x9-rdfs-interpretations', 'Every class is a subclass of Resource',
          [(C, RDF.type, RDFS.Class)], [(C, RDFS.subClassOf, RDFS.Resource)]),
    _case('datatype-class', 'x9-rdfs-interpretations', 'Recognized datatypes are datatypes and literal subclasses',
          [], [(XSD.integer, RDF.type, RDFS.Datatype), (XSD.integer, RDFS.subClassOf, RDFS.Literal)],
          datatypes=(XSD.integer,)),
    _case('proposition', 'x9-rdfs-interpretations', 'Triple terms denote propositions',
          [(C, RDF.reifies, TERM)], [(X, RDF.type, RDFS.Proposition), (C, RDF.reifies, X)]),
    _case('reifies-not-functional', 'x9-rdfs-interpretations', 'Reification is not functional',
          [(C, RDF.reifies, TERM), (C, RDF.reifies, TripleTerm(O, P, S))], False, expected=False),
    _case('constructor-cycle', 'x5-simple-interpretations',
          'A free IT interpretation refutes an unforced recursive subclass witness',
          [(RDFS.Resource, RDFS.subClassOf, RDFS.Class)],
          [(X, RDFS.subClassOf, TripleTerm(X, RDF.type, X))], expected=False),
    _case('value-no-assertion', 'x9-rdfs-interpretations', 'rdf:value has no assertion operation',
          [(S, RDF.value, O), (S, RDF.value, C)], [(S, P, O)], expected=False),
    _case('list-not-functional', 'x9-rdfs-interpretations', 'List vocabulary imposes no functional or acyclic constraint',
          [(S, RDF.first, O), (S, RDF.first, C), (S, RDF.rest, S)], False, expected=False),
    _case('list-typing', 'x9-rdfs-interpretations', 'List properties carry domain and range constraints',
          [(S, RDF.rest, O)], [(S, RDF.type, RDF.List), (O, RDF.type, RDF.List)]),
    _case('container-membership', 'x9-rdfs-interpretations', 'Positive decimal container properties imply member',
          [(S, RDF['_100000'], O)], [(S, RDFS.member, O)]),
    _case('container-not-gap-free', 'x9-rdfs-interpretations', 'Containers need not be gap-free',
          [(S, RDF.type, RDF.Seq), (S, RDF['_3'], O)], [(S, RDF['_2'], X)], expected=False),
    _case('container-overlap', 'x9-rdfs-interpretations', 'Container classes are not disjoint',
          [(S, RDF.type, RDF.Seq), (S, RDF.type, RDF.Bag), (S, RDF.type, RDF.Alt)], False, expected=False),
    _case('legacy-no-assertion', 'x9-rdfs-interpretations', 'Old-style reification does not assert its described triple',
          [(C, RDF.subject, S), (C, RDF.predicate, P), (C, RDF.object, O)],
          [(S, P, O)], expected=False),
    _case('documentation-subproperty', 'x9-rdfs-interpretations', 'isDefinedBy is a subproperty of seeAlso',
          [(S, RDFS.isDefinedBy, O)], [(S, RDFS.seeAlso, O)]),
)


# Transcribed from the normative axiom tables, not generated by _axioms().
# Container families are infinite; distant indices check query-local dispatch.
_DOMAINS = (
    (RDF.type, RDFS.Resource), (RDF.reifies, RDFS.Resource),
    (RDFS.domain, RDF.Property), (RDFS.range, RDF.Property),
    (RDFS.subPropertyOf, RDF.Property), (RDFS.subClassOf, RDFS.Class),
    (RDF.subject, RDF.Statement), (RDF.predicate, RDF.Statement),
    (RDF.object, RDF.Statement), (RDFS.member, RDFS.Resource),
    (RDF.first, RDF.List), (RDF.rest, RDF.List),
    (RDFS.seeAlso, RDFS.Resource), (RDFS.isDefinedBy, RDFS.Resource),
    (RDFS.comment, RDFS.Resource), (RDFS.label, RDFS.Resource),
    (RDF.value, RDFS.Resource),
)
_RANGES = (
    (RDF.type, RDFS.Class), (RDF.reifies, RDFS.Proposition),
    (RDFS.domain, RDFS.Class), (RDFS.range, RDFS.Class),
    (RDFS.subPropertyOf, RDF.Property), (RDFS.subClassOf, RDFS.Class),
    (RDF.subject, RDFS.Resource), (RDF.predicate, RDFS.Resource),
    (RDF.object, RDFS.Resource), (RDFS.member, RDFS.Resource),
    (RDF.first, RDFS.Resource), (RDF.rest, RDF.List),
    (RDFS.seeAlso, RDFS.Resource), (RDFS.isDefinedBy, RDFS.Resource),
    (RDFS.comment, RDFS.Literal), (RDFS.label, RDFS.Literal),
    (RDF.value, RDFS.Resource),
)
AXIOM_PROBES = tuple(
    _case('rdf-axiom-' + name, 'x8-rdf-interpretations',
          'Normative RDF property axiom: ' + name, [], [(RDF[name], RDF.type, RDF.Property)], regime='rdf')
    for name in ('type', 'subject', 'predicate', 'object', 'reifies', 'first', 'rest', 'value')
) + tuple(
    _case('rdfs-' + relation + '-' + str(i), 'x9-rdfs-interpretations',
          'Normative RDFS ' + relation + ' axiom', [], [(s, RDFS[relation], o)])
    for relation, pairs in (('domain', _DOMAINS), ('range', _RANGES))
    for i, (s, o) in enumerate(pairs)
) + tuple(
    _case('container-family-' + str(i), 'x9-rdfs-interpretations',
          'Infinite container membership axiom family', [],
          [(RDF['_' + str(i)], RDF.type, RDFS.ContainerMembershipProperty),
           (RDF['_' + str(i)], RDFS.domain, RDFS.Resource),
           (RDF['_' + str(i)], RDFS.range, RDFS.Resource)])
    for i in (1, 17, 100000)
) + (
    _case('rdf-nil', 'x8-rdf-interpretations', 'The empty-list resource is a List',
          [], [(RDF.nil, RDF.type, RDF.List)], regime='rdf'),
    _case('rdfs-fixed-hierarchy', 'x9-rdfs-interpretations', 'Normative fixed class/property hierarchy', [],
          [(RDF.Alt, RDFS.subClassOf, RDFS.Container),
           (RDF.Bag, RDFS.subClassOf, RDFS.Container),
           (RDF.Seq, RDFS.subClassOf, RDFS.Container),
           (RDFS.ContainerMembershipProperty, RDFS.subClassOf, RDF.Property),
           (RDFS.Proposition, RDFS.subClassOf, RDFS.Resource),
           (RDFS.Datatype, RDFS.subClassOf, RDFS.Class),
           (RDFS.isDefinedBy, RDFS.subPropertyOf, RDFS.seeAlso)]),
)
DATATYPE_PROBES = tuple(
    _case('datatype-membership-' + name, 'x9-rdfs-interpretations',
          'Recognized value belongs to its datatype class: ' + name,
          [(S, P, literal)], [(S, P, X), (X, RDF.type, datatype)], datatypes=(datatype,))
    for name, datatype, literal in (
        ('langString', RDF.langString, Literal('v', lang='en')),
        ('dirLangString', RDF.dirLangString, Literal('v', lang='en', direction='rtl')),
        ('HTML', RDF.HTML, Literal('<p>v</p>', datatype=RDF.HTML)),
        ('XMLLiteral', RDF.XMLLiteral, Literal('<p>v</p>', datatype=RDF.XMLLiteral)),
        ('JSON', RDF.JSON, Literal('{"v":1}', datatype=RDF.JSON)),
    )
)
SCHEMA_PROBES = (
    _case('multiple-domains', 'x9-rdfs-interpretations',
          'Multiple domains constrain every subject conjunctively',
          [(P, RDFS.domain, C), (P, RDFS.domain, D), (S, P, O)],
          [(S, RDF.type, C), (S, RDF.type, D), (P, RDF.type, RDF.Property),
           (C, RDF.type, RDFS.Class), (D, RDF.type, RDFS.Class)]),
    _case('multiple-ranges', 'x9-rdfs-interpretations',
          'Multiple ranges constrain every object conjunctively',
          [(P, RDFS.range, C), (P, RDFS.range, D), (S, P, O)],
          [(O, RDF.type, C), (O, RDF.type, D), (P, RDF.type, RDF.Property),
           (C, RDF.type, RDFS.Class), (D, RDF.type, RDFS.Class)]),
    _case('class-self-member', 'x9-rdfs-interpretations',
          'Classes may contain themselves and have empty or overlapping extensions',
          [(C, RDF.type, C), (C, RDF.type, RDFS.Class), (D, RDF.type, RDFS.Class)],
          False, expected=False),
    _case('no-extensional-class-identity', 'x9-rdfs-interpretations',
          'Coinciding known instances do not identify two classes',
          [(S, RDF.type, C), (S, RDF.type, D), (C, P, O)],
          [(D, P, O)], expected=False),
    _case('value-not-functional', 'x9-rdfs-interpretations',
          'Structured-value vocabulary does not impose a unique value',
          [(S, RDF.value, O), (S, RDF.value, C)], False, expected=False),
    _case('container-no-property-transfer', 'x9-rdfs-interpretations',
          'Container attributes do not automatically apply to members',
          [(S, RDF['_1'], O), (S, P, C)], [(O, P, C)], expected=False),
    _case('container-not-permuted', 'x9-rdfs-interpretations',
          'Bag convention does not permute indexed membership statements',
          [(S, RDF.type, RDF.Bag), (S, RDF['_1'], C), (S, RDF['_2'], D)],
          [(S, RDF['_1'], D)], expected=False),
    _case('legacy-predicate-not-property', 'x9-rdfs-interpretations',
          'Describing a statement predicate does not assert its use as a property',
          [(C, RDF.predicate, P)], [(P, RDF.type, RDF.Property)], expected=False),
    _case('legacy-not-from-assertion', 'x9-rdfs-interpretations',
          'Asserting a triple does not assert an old-style reification',
          [(S, P, O)], [(X, RDF.subject, S), (X, RDF.predicate, P), (X, RDF.object, O)],
          expected=False),
    _case('constructor-unconstrained', 'x5-simple-interpretations',
          'A query-only predicate need not denote a property',
          [(RDFS.Resource, RDFS.subClassOf, RDFS.Class)],
          [(X, RDFS.subClassOf, TripleTerm(S, P, O))], expected=False),
)
ALL_PROBES = PROBES + AXIOM_PROBES + DATATYPE_PROBES + SCHEMA_PROBES


def run_probe(probe):
    from rdfcore.semantics import EntailmentResourceLimit, UnsupportedEntailment, entails
    result = dict(id=probe.id, requirement=probe.requirement, section=probe.section,
                  expected=probe.expected, regime=probe.regime,
                  datatypes=[str(d) for d in probe.datatypes])
    try:
        actual = entails(probe.premise, probe.conclusion, regime=probe.regime,
                         datatypes=probe.datatypes, mode='decide', max_steps=100000)
    except EntailmentResourceLimit as exc:
        return dict(result, status='resource-limit', reason=str(exc))
    except UnsupportedEntailment as exc:
        return dict(result, status='unsupported', reason=str(exc))
    return dict(result, actual=actual, status='passed' if actual is probe.expected else 'failed')
