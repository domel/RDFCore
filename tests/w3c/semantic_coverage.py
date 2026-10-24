"""Requirement evidence, distinct from success on the pinned manifest.

This is a coverage inventory, not a completeness theorem. A section marked
partial cannot pass release acceptance merely because its fixtures pass.
"""
from rdfcore import BNode, RDF, RDFS, TripleTerm, URIRef, XSD
from rdfcore.semantics import EntailmentResourceLimit, UnsupportedEntailment, entails

SCHEMA = 'https://www.w3.org/TR/2026/WD-rdf12-schema-20261023/'
SEMANTICS = 'https://www.w3.org/TR/2026/CRD-rdf12-semantics-20260924/'

# Every vocabulary leaf section, including registry entries defined elsewhere.
SCHEMA_SECTIONS = {
    '2.1.1': 'Resource', '2.1.2': 'Class', '2.1.3': 'Literal',
    '2.1.4': 'Datatype', '2.1.5': 'Property',
    '2.2.1': 'range', '2.2.2': 'domain', '2.2.3': 'type',
    '2.2.4': 'subClassOf', '2.2.5': 'subPropertyOf',
    '2.3.1': 'label', '2.3.2': 'comment', '2.3.3': 'seeAlso',
    '2.3.4': 'isDefinedBy',
    '3.1': 'langString', '3.2': 'dirLangString', '3.3': 'HTML',
    '3.4': 'XMLLiteral', '3.5': 'JSON', '3.6': 'XML Schema datatypes',
    '4.1': 'List', '4.2': 'first', '4.3': 'rest', '4.4': 'nil',
    '5.1': 'Proposition', '5.2': 'reifies', '6.1': 'value',
    '7.1.1': 'Container', '7.1.2': 'Bag', '7.1.3': 'Seq',
    '7.1.4': 'Alt', '7.1.5': 'ContainerMembershipProperty', '7.1.6': 'member',
    '7.2.1': 'Statement', '7.2.2': 'subject', '7.2.3': 'predicate',
    '7.2.4': 'object', '8.1': 'class summary', '8.2': 'property summary',
    'A.1': 'rdf registry', 'A.2': 'rdfs registry',
}

# Each section links to an executed consequence rather than to the same
# undifferentiated list of files. Registry policy itself governs W3C, not
# entailment; those entries have independent namespace/absence regressions.
SCHEMA_CHECKS = {
    '2.1.1': ('resource-universal',), '2.1.2': ('subclass-reflexive', 'class-resource'),
    '2.1.3': ('datatype-class',), '2.1.4': ('datatype-class',),
    '2.1.5': ('rdf-property', 'subproperty-reflexive'),
    '2.2.1': ('range',), '2.2.2': ('domain', 'domain-not-inherited'),
    '2.2.3': ('subclass-members',), '2.2.4': ('subclass-transitive', 'subclass-members'),
    '2.2.5': ('subproperty-transitive', 'subproperty-extension'),
    '2.3.1': ('rdfs-range-15',), '2.3.2': ('rdfs-range-14',),
    '2.3.3': ('rdfs-domain-12', 'rdfs-range-12'),
    '2.3.4': ('documentation-subproperty',),
    '3.1': ('datatype-membership-langString',),
    '3.2': ('datatype-membership-dirLangString',),
    '3.3': ('datatype-membership-HTML',),
    '3.4': ('datatype-membership-XMLLiteral',),
    '3.5': ('datatype-membership-JSON',),
    '3.6': ('datatype-value-equality', 'datatype-ill-typed', 'datatype-class'),
    '4.1': ('list-typing', 'list-not-functional'),
    '4.2': ('rdfs-domain-10', 'rdfs-range-10', 'list-not-functional'),
    '4.3': ('list-typing', 'list-not-functional'), '4.4': ('rdf-nil',),
    '5.1': ('proposition', 'inner-not-asserted'),
    '5.2': ('rdfs-range-1', 'reifies-not-functional'),
    '6.1': ('rdf-axiom-value', 'rdfs-domain-16', 'rdfs-range-16', 'value-no-assertion'),
    '7.1.1': ('rdfs-fixed-hierarchy',), '7.1.2': ('container-overlap',),
    '7.1.3': ('container-not-gap-free',), '7.1.4': ('container-overlap',),
    '7.1.5': ('container-family-100000',), '7.1.6': ('container-membership',),
    '7.2.1': ('legacy-no-assertion',), '7.2.2': ('rdfs-domain-6', 'legacy-no-assertion'),
    '7.2.3': ('rdfs-domain-7', 'legacy-no-assertion'),
    '7.2.4': ('rdfs-domain-8', 'legacy-no-assertion'),
    '8.1': ('rdfs-fixed-hierarchy',), '8.2': ('rdfs-fixed-hierarchy',),
    'A.1': (), 'A.2': (),
}


def _schema_reference(section, name):
    # Published heading IDs checked against the 2026-10-23 document.
    special = {'3.6': 'xml-schema-datatypes', '8.1': 'rdf-classes',
               '8.2': 'rdf-properties', 'A.1': 'rdf-namespace', 'A.2': 'rdfs-namespace'}
    rdfs = {'Resource', 'Class', 'Literal', 'Datatype', 'range', 'domain',
            'subClassOf', 'subPropertyOf', 'label', 'comment', 'seeAlso',
            'isDefinedBy', 'Proposition', 'Container', 'ContainerMembershipProperty', 'member'}
    slug = special.get(section, ('rdfs-' if name in rdfs else 'rdf-') + name.lower())
    number = section.lower().replace('.', '-')
    return SCHEMA + '#' + ('x' if section[0].isdigit() else '') + number + '-' + slug


def _probe(name, premise, datatypes, target=False):
    try:
        actual = entails(premise, target, regime='rdfs', mode='decide',
                         datatypes=datatypes, max_steps=100000)
    except EntailmentResourceLimit as exc:
        return dict(id=name, status='resource-limit', expected=False, reason=str(exc))
    except UnsupportedEntailment as exc:
        return dict(id=name, status='unsupported', expected=False, reason=str(exc))
    return dict(id=name, status='passed' if actual is False else 'failed',
                expected=False, actual=actual)


def coverage_report(suites):
    from .semantic_requirements import ALL_PROBES, run_probe
    semantic = [s for s in suites if s.get('category') == 'entailment']
    suite_passed = (len(semantic) == 2
                    and set(s.get('rdf_version') for s in semantic) == {'rdf11', 'rdf12'}
                    and all(s.get('tests') and not s.get('suite_error')
                            and s.get('total') == len(s['tests'])
                            and s.get('counts', {}).get('passed') == s['total']
                            and all(t.get('status') == 'passed' for t in s['tests'])
                            and not any(s.get('counts', {}).get(k, 0)
                                        for k in ('failed', 'unsupported', 'error'))
                            for s in semantic))
    s = URIRef('urn:coverage:proposition')
    probes = [
        _probe('reserved-property-datatype-alias',
               [(RDF.type, RDF.type, XSD.boolean)], {XSD.boolean}),
        _probe('proposition-overlapping-string-spaces',
               [(s, RDF.type, RDFS.Proposition), (s, RDF.type, XSD.token)], {XSD.token}),
        _probe('infinite-proposition-image',
               [(RDFS.Proposition, RDFS.subClassOf, XSD.string)], set()),
        _probe('constructor-schema-cycle-query',
               [(RDFS.Resource, RDFS.subClassOf, RDFS.Class)], set(),
               [(BNode('x'), RDFS.subClassOf,
                 TripleTerm(BNode('x'), RDF.type, BNode('x')))]),
        _probe('constructor-unconstrained-predicate',
               [(RDFS.Resource, RDFS.subClassOf, RDFS.Class)], set(),
               [(BNode('c'), RDFS.subClassOf,
                 TripleTerm(BNode('s'), URIRef('urn:coverage:unconstrained'), s))]),
    ]
    requirements = [dict(section=n, requirement=name, status='partial',
                         reference=_schema_reference(n, name),
                         implementation='rdfcore/semantics.py; rdfcore/_schema_reasoning.py',
                         checks=list(SCHEMA_CHECKS[n]),
                         evidence=('tests/w3c/test_semantic_requirements.py' if SCHEMA_CHECKS[n]
                                   else 'tests/compatibility/test_schema_registry.py'),
                         limitation='Vocabulary/rule evidence does not establish all arbitrary schema interactions.')
                    for n, name in SCHEMA_SECTIONS.items()]
    blockers = [
        'No completeness argument for arbitrary schema/constructor queries.',
        'Some vocabulary constraints still lack an interpretation certificate.',
        'Clause-level Semantics/Schema audit remains incomplete.',
    ]
    conditions = [dict(run_probe(p), reference=SEMANTICS + '#' + p.section,
                       evidence='tests/w3c/test_semantic_requirements.py',
                       coverage='example consequence; not a completeness proof') for p in ALL_PROBES]
    return {
        'reviewed': '2026-10-24', 'schema_reference': SCHEMA,
        'semantics_reference': SEMANTICS,
        'probe_options': {'regime': 'rdfs', 'mode': 'decide', 'max_steps': 100000},
        'schema_sections': requirements,
        'official_semantics_passed': suite_passed,
        'additional_probes': probes,
        'semantic_conditions': conditions,
        'specification_changes': [
            dict(reference=SCHEMA, previous='2026-10-22',
                 change='HTML, XMLLiteral and JSON sections are now normative; registry admission and custodianship clarified.',
                 impact='Datatype value support remains explicit; RDF-D recognition is optional under Semantics section 8. Registry policy adds no inference rule.'),
        ],
        'full_profile_verified': bool(suite_passed and not blockers
                                      and all(p['status'] == 'passed' for p in probes)
                                      and all(p['status'] == 'passed' for p in conditions)
                                      and all(r['status'] in {'implemented', 'not-applicable-with-reason'}
                                              for r in requirements)),
        'blockers': blockers,
        'scope': 'Manifest results and requirement inventory are separate; full Semantics/Schema acceptance remains open.',
    }
