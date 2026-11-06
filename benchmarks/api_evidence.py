"""Selected executable evidence; entries never imply all-input API parity."""

C = 'tests/compatibility/'
SCOPES = {
    'graph-core': {
        'classes': ['Graph', 'Dataset'],
        'members': ['add', 'addN', 'remove', 'set', 'subjects', 'objects', 'predicates',
                    'predicate_objects', 'subject_predicates', 'subject_objects', 'triples', 'triples_choices',
                    '__getitem__', 'connected', 'all_nodes', 'items', 'transitiveClosure',
                    'transitive_objects', 'transitive_subjects', 'bind', 'namespaces', 'qname', 'resource', 'n3'],
        'scope': 'controlled ordinary/empty/invalid inputs, mutation state, iterator consumption; Memory/SQLite',
        'tests': [C + 'test_s13_graph_acceptance.py']},
    'graph-value': {'classes': ['Graph', 'Dataset'], 'members': ['value'],
        'scope': 'context isolation, lazy access, uniqueness diagnostics and return identity',
        'tests': [C + 'test_graph_value.py', C + 'test_s13_selectors.py']},
    'lifecycle': {'classes': ['Graph', 'Dataset', 'ConjunctiveGraph'],
        'members': ['open', 'close', 'commit', 'rollback', 'destroy'],
        'scope': 'Store forwarding; SQLite savepoints, reopen, failed configuration changes; destroy explicitly unsupported',
        'tests': [C + 'test_graph_lifecycle.py']},
    'formats': {'classes': ['Graph', 'Dataset'], 'members': ['parse', 'serialize'],
        'scope': 'selected shared-format input/output types, ownership, invalid inputs, return identities; not full syntax parity',
        'tests': [C + 'test_format_contracts.py']},
    'dataset': {'classes': ['Dataset'], 'members': ['graph', 'graphs', 'contexts', 'quads', 'remove_graph',
                 'remove_context', 'get_graph', 'get_context', 'add_graph', 'context_id'],
        'scope': 'default/named/union, lookup and removal; controlled identifiers and graph retention',
        'tests': [C + 'test_remove_context.py', C + 'test_dataset_signatures.py', C + 'test_context_lookup.py']},
    'namespace': {'classes': ['NamespaceManager'], 'members': ['bind', 'namespaces', 'qname', 'normalizeUri', 'compute_qname', 'absolutize', 'store'],
        'scope': 'prefix collisions, QName caching and resolution, default binding sets and shared Store property',
        'tests': [C + 'test_namespace_matrix.py', C + 'test_s13_graph_acceptance.py']},
    'collection': {'classes': ['Collection'], 'members': ['__init__', '__getitem__', '__setitem__', '__delitem__',
                  '__iter__', '__len__', '__iadd__', 'append', 'clear', 'index', 'n3'],
        'scope': 'controlled list cells, empty/malformed/false values, errors and mutation state; native stores',
        'tests': [C + 'test_collection_matrix.py', C + 'test_s13_graph_acceptance.py']},
    'resource': {'classes': ['Resource'], 'members': ['add', 'set', 'remove', '__getitem__', 'objects',
                 'predicates', 'value', 'identifier', 'graph'],
        'scope': 'wrapped/unwrapped arguments, keyword calls, Node indexing and false-y slice steps',
        'tests': [C + 'test_resource_keywords.py', C + 'test_s13_graph_acceptance.py']},
    'literal': {'classes': ['Literal'], 'members': ['__new__', 'datatype', 'language', 'ill_typed', 'value', 'normalize', 'toPython', '__add__', '__sub__', '__neg__', '__pos__', '__abs__'],
        'scope': 'numeric/string/temporal matrix, calendar/fixed durations, normalization, native types and errors',
        'tests': [C + 'test_literal_arithmetic.py', C + 'test_literal_unary.py', C + 'test_literal_matrix.py']},
    'representations': {'classes': ['Literal', 'URIRef', 'BNode', 'Variable'], 'members': ['n3', '__repr__'],
        'scope': 'lexical escaping, metadata, multiline strings and numeric special values; import prefixes distinguished',
        'tests': [C + 'test_term_representations.py']},
    'skolem': {'classes': ['Graph', 'BNode', 'URIRef', 'Genid', 'RDFLibGenid'], 'members': ['skolemize', 'de_skolemize'],
        'scope': 'controlled blank IDs, selective and destination graph modes, Genid dispatch and store identity',
        'tests': [C + 'test_s13_graph_acceptance.py']},
}


def evidence_for(class_name, member):
    return [dict(id=key, scope=value['scope'], tests=value['tests']) for key, value in SCOPES.items()
            if class_name in value['classes'] and member in value['members']]
