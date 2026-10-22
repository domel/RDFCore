"""Evidence reviewed for S07 T23 on 2026-10-18; no result overrides.

Published XML WD 2026-10-09 and Semantics CRD 2026-09-24 are the
baseline. Linked XML/Semantics Editor's Drafts were also inspected; no
ED-only behavior is selected. This catalogue describes two reviewed test
snapshots, not arbitrary future fixtures or complete conformance.
"""

REVIEWED_SNAPSHOTS = frozenset({
    '369a90d1a60c021b746df2e411da0ff36258a758',
    'd5d930b03ee6b63b388d0bb28fdb29ee78a59ec0',
})
BASE = 'https://w3c.github.io/rdf-tests/rdf/'
XML11 = 'https://www.w3.org/TR/2014/REC-rdf-syntax-grammar-20140225/'
XML12 = 'https://www.w3.org/TR/2026/WD-rdf12-xml-20261009/'
SEM11 = 'https://www.w3.org/TR/2014/REC-rdf11-mt-20140225/'
SEM12 = 'https://www.w3.org/TR/2026/CRD-rdf12-semantics-20260924/'

# Expected answers below are MANIFEST expectations, not independently proved
# semantic verdicts. In particular, several historical whitespace tests need
# reconciliation with the selected datatype lexical space in T38.
# Values: target task, normative anchor, reviewed action/conclusion distinction.
SEMANTIC_11 = {
    'datatypes-intensional-xsd-integer-decimal-compatible': (
        'S11 T38', 'D_interpretations',
        'The integer subClassOf decimal premise is consistent with recognized '
        'integer/decimal; the negative false conclusion needs a consistency decision.'),
    'datatypes-non-well-formed-literal-1': (
        'S11 T38', 'D_interpretations',
        'The literal "flargh"^^xsd:integer has an unrecognized datatype here '
        '(recognized list empty); the manifest expects consistency, not blanket rejection.'),
    'datatypes-non-well-formed-literal-2': (
        'S11 T38', 'D_interpretations',
        'The same "flargh" literal with xsd:integer recognized is expected '
        'to entail false; recognition changes the satisfiability question.'),
    'datatypes-semantic-equivalence-within-type-1': (
        'S11 T38', 'D_entailment',
        'Recognized xsd:integer maps lexical "010" to the value of "10"; '
        'the positive conclusion is value entailment, not term equality.'),
    'datatypes-semantic-equivalence-within-type-2': (
        'S11 T38', 'D_entailment',
        'The reverse recognized integer entailment is "10" to "010"; '
        'normalizing parser output is not a D-interpretation decision.'),
    'datatypes-semantic-equivalence-between-datatypes': (
        'S11 T38', 'D_entailment',
        'Recognized integer "10" entails decimal "10.0" by shared numeric '
        'value across two datatypes, not identical RDF literals.'),
    'datatypes-range-clash': (
        'S11 T38', 'rdfs_interpretations',
        'The integer value 25 is forced into xsd:string by rdfs:range; '
        'both types are recognized and the manifest expects inconsistency.'),
    'datatypes-test010': (
        'S11 T38', 'rdfs_interpretations',
        'Plain string "25" is forced into recognized xsd:integer by range; '
        'the manifest expects false, not conversion of the string to an integer.'),
    'datatypes-plain-literal-and-xsd-string': (
        'S11 T38', 'D_entailment',
        'Plain "a string" and explicit xsd:string share the string value; '
        'the historical runner rejected the explicit recognized datatype request.'),
    'horst-01-subClassOf-intensional': (
        'S11 T39', 'rdfs_interpretations',
        'A class x and rdf:type domain y constrain class extensions but do '
        'not entail the asserted x subClassOf y relation under intensional RDFS.'),
    'horst-01-subPropertyOf-intensional': (
        'S11 T38', 'rdfs_interpretations',
        'Property p has disjoint recognized integer/string ranges and hence '
        'an empty extension; that does not assert p subPropertyOf q.'),
    'rdf-charmod-uris-test003': (
        'S11 T37', 'rdf_d_interpretations',
        'The IRI ending André does not entail the percent-encoded Andr%C3%A9 '
        'IRI; failure of the current partial RDF proof is not a negative verdict.'),
    'rdf-charmod-uris-test004': (
        'S11 T37', 'rdf_d_interpretations',
        'The reverse percent-encoded IRI to André entailment is also negative; '
        'no percent-decoding equivalence may be imposed on RDF IRI identity.'),
    'rdfs-container-membership-superProperty-test001': (
        'S11 T39', 'rdfs_interpretations',
        'An rdfs:member edge does not entail rdf:_1; the membership '
        'subproperty implication is one-way and needs a negative decision.'),
    'rdfs-domain-and-range-intensionality-range': (
        'S11 T39', 'rdfs_interpretations',
        'A subClassOf B and prop range A do not assert prop range B; '
        'propagating instance types must not invent schema range triples.'),
    'rdfs-domain-and-range-intensionality-domain': (
        'S11 T39', 'rdfs_interpretations',
        'A subClassOf B and prop domain A do not assert prop domain B; '
        'the negative schema conclusion needs intensional RDFS reasoning.'),
    'rdfs-entailment-test001': (
        'S11 T38', 'D_interpretations',
        'Recognized rdf:XMLLiteral lexical "<" is malformed and its range '
        'is XMLLiteral; the manifest expects inconsistency.'),
    'rdfs-entailment-test002': (
        'S11 T38', 'rdfs_interpretations',
        'An xsd:string value is forced by range into rdf:langString; '
        'both recognized value spaces must be checked for the false conclusion.'),
    'rdfs-subClassOf-a-Property-test001': (
        'S11 T39', 'rdfs_interpretations',
        'A resource may be both a Property and a Class (as object of '
        'subClassOf); the premise is consistent, not an OWL-style disjointness error.'),
    'statement-entailment-test001': (
        'S11 T39', 'Reif',
        'Two reification resources describe the same SPO; an extra property '
        'of stmt1 does not transfer to stmt2. Reification is not identity.'),
    'statement-entailment-test002': (
        'S11 T39', 'Reif',
        'An asserted triple does not entail existence of its four-triple '
        'reification; the existential conclusion must be decided negatively.'),
    'statement-entailment-test003': (
        'S11 T39', 'Reif',
        'Under RDFS too, equal reification SPO descriptions of stmt1/stmt2 '
        'do not transfer the additional stmt1 property to stmt2.'),
    'statement-entailment-test004': (
        'S11 T39', 'Reif',
        'Under RDF semantics, asserting SPO does not create an existential '
        'rdf:Statement reification. Partial closure cannot certify non-entailment.'),
    'xmlsch-02-whitespace-facet-1': (
        'S11 T38', 'D_interpretations',
        'The historical manifest expects "3"^^xsd:int not to entail '
        '" 3 "^^xsd:int; review its whitespace lexical-space assumption '
        'against the selected datatype standard before implementing a verdict.'),
    'xmlsch-02-whitespace-facet-2': (
        'S11 T38', 'D_interpretations',
        'The historical manifest labels whitespace " 3 "^^xsd:int '
        'inconsistent (positive false); T38 must reconcile this lexical-space '
        'assumption, not infer inconsistency from Python normalization.'),
    'xmlsch-02-whitespace-facet-4': (
        'S11 T38', 'D_interpretations',
        'This separate manifest entry reuses whitespace " 3 "^^xsd:int '
        'and expects false; preserve the duplicate execution and review '
        'the same historical lexical-space assumption independently.'),
    'literal-type': (
        'S11 T38', 'rdf_d_interpretations',
        'Recognized integer "42" must witness an existential object '
        'whose rdf:type is xsd:integer; requires datatype value-space typing.'),
}

# Separate signed-zero, precision and overflow cases, not generic "numbers".
for _kind, _precision, _different, _same in (
    ('float', 'binary32', '16777206.5 versus 16777207.5', '16777206.5 versus 16777205.5'),
    ('double', 'binary64', '9007199254740990.5 versus 9007199254740991.5',
     '9007199254740992.5 versus 9007199254740991.5'),
):
    for _case, _detail in {
        'zero': 'The manifest distinguishes signed zero "0" and "-0" and expects non-entailment.',
        'round-different': f'{_different} round to different representable values; the manifest expects non-entailment.',
        'round-same': f'{_same} round to the same representable value; the manifest expects positive entailment.',
        'infinity': 'Lexical 1E400 and 1E401 overflow to the same positive infinity; the manifest expects positive entailment.',
    }.items():
        SEMANTIC_11[_kind + '-' + _case] = (
            'S11 T38', 'D_entailment',
            f'Recognized xsd:{_kind} uses {_precision}. {_detail}')

SEMANTIC_12 = {
    'malformed-literal': (
        'S11 T38', 'D_interpretations',
        'The unasserted triple term contains "c"^^recognized xsd:integer; '
        'the manifest expects false from datatype inconsistency even inside '
        'the triple term, without asserting its embedded triple.'),
    'opaque-literal': (
        'S11 T38', 'D_interpretations',
        'Despite its name, the manifest comment says literals in triple terms '
        'are transparent: recognized integer "042" entails "42" within '
        'the term under the declared simple regime with datatype recognition.'),
    'json-array-ordered': (
        'S11 T38', 'D_interpretations',
        'Recognized rdf:JSON arrays [-0,0] and [0,-0] differ by element '
        'order with signed zero; the manifest expects non-entailment.'),
    'json-object-unordered': (
        'S11 T38', 'D_interpretations',
        'Recognized rdf:JSON objects {"a":0,"b":1} and {"b":1,"a":0} '
        'differ only by member order; the manifest expects positive entailment.'),
    'json-zero': (
        'S11 T38', 'D_interpretations',
        'Recognized rdf:JSON scalar 0 versus -0 tests signed zero identity; '
        'the manifest expects non-entailment, unlike Python numeric equality.'),
    'json-zero-array': (
        'S11 T38', 'D_interpretations',
        'Recognized rdf:JSON [0] versus [-0] tests signed zero recursively '
        'inside arrays; the manifest expects non-entailment.'),
    'json-round-different': (
        'S11 T38', 'D_interpretations',
        'JSON 9007199254740990.5 versus 9007199254740991.5 round to '
        'different binary64 values; the manifest expects non-entailment.'),
    'json-round-same': (
        'S11 T38', 'D_interpretations',
        'JSON 9007199254740992.5 versus 9007199254740991.5 round to '
        'the same binary64 value; the manifest expects positive entailment.'),
    'json-infinity': (
        'S11 T38', 'D_interpretations',
        'JSON 1E400 and 1E401 exercise overflow to the same positive '
        'infinity; the manifest expects positive entailment.'),
}

ANNOTATIONS = {
    '01': 'IRI reifier of literal blah',
    '02': 'blank-node reifier via annotationNodeID of literal blah',
    '03': 'IRI reifier with an additional explicit description',
    '04': 'empty property with an anonymous object',
    '05': 'empty parseType Resource object',
    '06': 'property attributes on the anonymous object',
    '07': 'annotated rdf:type with resource object',
    '08': 'annotated ordinary resource object',
    '09': 'annotated nodeID object',
    '10': 'nested annotated property elements with two reifiers',
    '11': 'blank subject and IRI reifier',
    '12': 'blank subject and annotationNodeID reifier',
    '13': 'parseType Literal and IRI reifier',
    '14': 'parseType Literal and annotationNodeID reifier',
    '15': 'parseType Collection and IRI reifier',
    '16': 'parseType Collection and annotationNodeID reifier',
    'reif-01': 'rdf:ID statement reification coexisting with rdf:annotation',
}

DISPUTED = {
    'rdf12-xml-tt-01': (
        '74a2255b38ca9e44fb4045d3f1d04489572391ac1f78ce2caa62abed3c5d9d15',
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        'section-Syntax-triple-terms',
        'The reviewed result file is empty although parseType Triple describes '
        'an outer ex:prop triple with a triple-term object. The action also '
        'lacks rdf:version="1.2"; default rejection and legacy recovery mismatch '
        'are separate facts. Do not replace the expected file or assert the inner triple.'),
    'rdf12-xml-dir-02': (
        '192169cfbfa03cb13548ae92f355a657361439573c3b0bd3128e265d898cbc1a',
        'c19cbd377772916df5baf1191f48543cd267826abc6dc7107ddcdb4979f116b9',
        'section-Syntax-base-direction',
        'The reviewed action has inherited its:dir="ltr" and xml:lang="en" '
        'on the ex:name="bar" property attribute, but the result has only '
        '"bar"@en and loses direction. It also lacks rdf:version; default '
        'invalid-attribute rejection and legacy recovery mismatch are not the same bug.'),
}


def _record(classification, task, reference, reason, evidence):
    return dict(classification=classification, task=task, reference=reference,
                reason=reason, evidence=evidence)


def classify_issue(report, suite, test):
    """Annotate an observed issue without changing inputs, counts or status.

    Unknown snapshots, IDs, suites, statuses and unverified disputed bytes
    remain unreviewed. Only this fixed catalogue is trusted: observed error
    message substrings alone never establish a fixture defect.
    """
    identifier = test.get('id', '')
    evidence = (
        f"id={identifier}; snapshot={report.get('snapshot')}; "
        f"profile={report.get('execution_profile')}; format={suite.get('format')}; "
        f"observed_status={test.get('status')}; observed_reason={test.get('reason')}; "
        f"regime={test.get('regime')}; types={test.get('types', [])}; "
        f"recognized_datatypes={test.get('recognized_datatypes', [])}; "
        f"action={test.get('action')}; result={test.get('result')}; "
        f"action_sha256={test.get('action_sha256')}; result_sha256={test.get('result_sha256')}"
    )
    unknown = _record('unreviewed', None, None,
                      'No reviewed classification for this execution or fixture bytes.', evidence)
    if (report.get('snapshot') not in REVIEWED_SNAPSHOTS
            or report.get('execution_profile') not in ('default', 'legacy-w3c-xml')
            or test.get('status') not in ('failed', 'unsupported')):
        return unknown

    if suite.get('format') in ('xml', 'xml12') and test.get('status') == 'failed':
        if identifier in {BASE + 'rdf11/rdf-xml/manifest.ttl#xml-canon-test' + n
                          for n in ('001', '002')}:
            reified = identifier.endswith('002')
            return _record(
                'compatibility-conformance-conflict', 'S09 T29',
                (XML12 if suite['format'] == 'xml12' else XML11) + '#parseTypeLiteralPropertyElt',
                'The fixture expects XMLLiteral lexical <br></br>, but both RDFCore '
                'and pinned RDFLib return <br/>. Resolve the W3C lexical expectation '
                'without silently breaking the RDFLib-compatible XML mode.',
                evidence + '; executable RDFLib 7.6.0 oracle and RDFCore: '
                + ('5 triples; property/object reification literals both <br/>.' if reified
                   else '1 triple; XMLLiteral <br/>.'))
        if suite['format'] != 'xml12':
            return unknown
        prefix = BASE + 'rdf12/rdf-xml/eval#'
        name = identifier.removeprefix(prefix)
        if identifier.startswith(prefix) and name in DISPUTED:
            action, result, anchor, reason = DISPUTED[name]
            if (test.get('action_sha256'), test.get('result_sha256')) != (action, result):
                return unknown
            return _record('snapshot-fixture-conflict', 'S09 T29', XML12 + '#' + anchor,
                           reason, evidence + '; both fixture byte hashes match the reviewed pair.')
        annotation_prefix = prefix + 'rdf12-xml-an-'
        suffix = identifier.removeprefix(annotation_prefix)
        if identifier.startswith(annotation_prefix) and suffix in ANNOTATIONS:
            return _record(
                'snapshot-profile-conflict', 'S09 T29', XML12 + '#section-MIME-Type',
                'This positive annotation fixture has no in-scope rdf:version="1.2". '
                'The selected published XML profile requires that announcement; '
                'legacy_w3c recovery is explicit, not a reason to accept it by default.',
                evidence + f'; reviewed annotation {suffix}: {ANNOTATIONS[suffix]}; '
                'reviewed legacy report passes this execution whereas default rejects it.')
        return unknown

    if suite.get('format') != 'semantics' or test.get('status') != 'unsupported':
        return unknown
    for prefix, catalogue, document in (
        (BASE + 'rdf11/rdf-mt/manifest.ttl#', SEMANTIC_11, SEM11),
        (BASE + 'rdf12/rdf-semantics#', SEMANTIC_12, SEM12),
    ):
        name = identifier.removeprefix(prefix)
        if identifier.startswith(prefix) and name in catalogue:
            task, anchor, reason = catalogue[name]
            blocker = ('official.semantic_result uses explicit mode=decide and manifest '
                       'datatype recognition. Unsupported means the requested facility '
                       'is unavailable or neither a proof nor a countermodel/consistency '
                       'certificate was established; see the per-test semantic_plan.')
            return _record('missing-functionality', task, document + '#' + anchor,
                           reason, evidence + '; ' + blocker
                           + ' No semantic verdict is inferred from an unsupported execution.')
    return unknown
