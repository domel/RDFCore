"""Requirement evidence, distinct from success on the pinned manifest.

This is a coverage inventory, not a completeness theorem. A section marked
partial cannot pass release acceptance merely because its fixtures pass.
"""
from rdfcore import RDF, RDFS, URIRef, XSD
from rdfcore.semantics import EntailmentResourceLimit, UnsupportedEntailment, entails

SCHEMA = 'https://www.w3.org/TR/2026/WD-rdf12-schema-20261022/'
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


def _schema_reference(section, name):
    # Published heading IDs checked against the 2026-10-22 document.
    special = {'3.6': 'xml-schema-datatypes', '8.1': 'rdf-classes',
               '8.2': 'rdf-properties', 'A.1': 'rdf-namespace', 'A.2': 'rdfs-namespace'}
    rdfs = {'Resource', 'Class', 'Literal', 'Datatype', 'range', 'domain',
            'subClassOf', 'subPropertyOf', 'label', 'comment', 'seeAlso',
            'isDefinedBy', 'Proposition', 'Container', 'ContainerMembershipProperty', 'member'}
    slug = special.get(section, ('rdfs-' if name in rdfs else 'rdf-') + name.lower())
    number = section.lower().replace('.', '-')
    return SCHEMA + '#' + ('x' if section[0].isdigit() else '') + number + '-' + slug


def _probe(name, premise, datatypes):
    try:
        actual = entails(premise, False, regime='rdfs', mode='decide',
                         datatypes=datatypes, max_steps=100000)
    except EntailmentResourceLimit as exc:
        return dict(id=name, status='resource-limit', expected=False, reason=str(exc))
    except UnsupportedEntailment as exc:
        return dict(id=name, status='unsupported', expected=False, reason=str(exc))
    return dict(id=name, status='passed' if actual is False else 'failed',
                expected=False, actual=actual)


def coverage_report(suites):
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
    ]
    return {
        'reviewed': '2026-10-23', 'schema_reference': SCHEMA,
        'semantics_reference': SEMANTICS,
        'probe_options': {'regime': 'rdfs', 'mode': 'decide', 'max_steps': 100000},
        'schema_sections': [dict(section=n, requirement=name, status='partial',
                                reference=_schema_reference(n, name),
                                implementation='rdfcore/semantics.py; rdfcore/_schema_reasoning.py',
                                evidence='tests/integration/test_semantics.py; tests/integration/test_schema_reasoning.py; tests/integration/test_datatype_entailment.py; tests/compatibility/test_schema_registry.py; tests/w3c/test_semantics_contract.py',
                                limitation='Vocabulary/rule evidence does not establish all arbitrary schema interactions.')
                            for n, name in SCHEMA_SECTIONS.items()],
        'official_semantics_passed': suite_passed,
        'additional_probes': probes,
        'full_profile_verified': False,
        'blockers': [
            'General fixed-vocabulary datatype aliasing is not decided.',
            'Overlapping datatype spaces with arbitrary proposition constraints remain guarded.',
            'No completeness argument for all constructor/schema interactions.',
        ],
        'scope': 'Manifest results and requirement inventory are separate; full Semantics/Schema acceptance remains open.',
    }
