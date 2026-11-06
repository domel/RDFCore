"""Report shared API signature differences without treating them as parity proof."""

import hashlib
import inspect
import json
import platform
from pathlib import Path
import subprocess
import warnings

import rdflib
import rdfcore
from benchmarks.api_evidence import evidence_for
from rdflib.collection import Collection
from rdflib.resource import Resource
from rdflib.namespace import NamespaceManager


def signature(value):
    result = []
    for parameter in inspect.signature(value).parameters.values():
        default = parameter.default
        result.append((parameter.name, parameter.kind.name,
                       '<required>' if default is inspect.Parameter.empty else str(default)))
    return result


def inventory():
    reference = {'Node': rdflib.term.Node, 'Identifier': rdflib.term.Identifier,
                 'IdentifiedNode': rdflib.term.IdentifiedNode, 'Genid': rdflib.term.Genid,
                 'RDFLibGenid': rdflib.term.RDFLibGenid, 'Namespace': rdflib.Namespace,
                 'Parser': rdflib.parser.Parser, 'Serializer': rdflib.serializer.Serializer,
                 'InputSource': rdflib.parser.InputSource, 'Collection': Collection, 'Resource': Resource, 'NamespaceManager': NamespaceManager,
                 'Store': rdflib.store.Store, 'Memory': type(rdflib.Graph().store)}
    report, classes = [], []
    def sample(module, name, cls):
        graph = lambda: module.Graph(identifier=module.URIRef('urn:audit'), bind_namespaces='none')
        if name in ('URIRef', 'BNode', 'Variable', 'Literal', 'Genid', 'RDFLibGenid'):
            return cls('urn:audit')
        if name == 'Namespace':
            return cls('urn:audit:')
        if name == 'Collection':
            return cls(graph(), module.URIRef('urn:list'))
        if name == 'Resource':
            return cls(graph(), module.URIRef('urn:resource'))
        if name in ('NamespaceManager', 'Serializer'):
            return cls(graph())
        if name == 'ConjunctiveGraph':
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', DeprecationWarning)
                return cls()
        if name in ('Node', 'Identifier', 'IdentifiedNode'):
            return None
        return cls()
    special = {'__new__', '__repr__', '__init__', '__add__', '__sub__', '__mul__', '__truediv__', '__neg__',
               '__pos__', '__abs__', '__eq__', '__hash__', '__contains__', '__iter__',
               '__len__', '__getitem__', '__iadd__', '__isub__', '__and__', '__or__', '__xor__'}
    for name in ('URIRef', 'BNode', 'Variable', 'Literal', 'Graph', 'Dataset',
                 'ConjunctiveGraph', 'Collection', 'Resource', 'NamespaceManager', 'Store', 'Memory',
                 'Node', 'Identifier', 'IdentifiedNode', 'Genid', 'RDFLibGenid', 'Namespace', 'Parser', 'Serializer', 'InputSource'):
        expected = reference.get(name) or getattr(rdflib, name)
        actual = getattr(rdfcore, name, None) or getattr(rdfcore.term, name)
        left_sample, right_sample = sample(rdflib, name, expected), sample(rdfcore, name, actual)
        classes.append({'name': name, 'rdflib': {'module': expected.__module__, 'bases': [base.__name__ for base in expected.__bases__]},
                        'rdfcore': {'module': actual.__module__, 'bases': [base.__name__ for base in actual.__bases__]}})
        left_names = set(dir(expected)) | (set(dir(left_sample)) if left_sample is not None else set())
        right_names = set(dir(actual)) | (set(dir(right_sample)) if right_sample is not None else set())
        for method in sorted(left_names | right_names):
            if method.startswith('_') and method not in special:
                continue
            left = inspect.getattr_static(left_sample if left_sample is not None else expected, method, None)
            right = inspect.getattr_static(right_sample if right_sample is not None else actual, method, None)
            row = {'class': name, 'method': method,
                   'status': 'missing' if method in left_names and method not in right_names else
                             'extension' if method not in left_names else 'present-unverified',
                   'rdflib_kind': type(left).__name__, 'rdfcore_kind': type(right).__name__}
            for label, value in [('rdflib', left), ('rdfcore', right)]:
                try:
                    row[label] = signature(value)
                except (TypeError, ValueError):
                    row[label] = None
            row['evidence'] = evidence_for(name, method)
            if row['status'] == 'present-unverified' and row['evidence']:
                row['status'] = 'verified-scoped'
            if row['status'] == 'missing':
                if method in ('query', 'update', '__neg__', '__truediv__'):
                    row['plan'] = 'SPARQL/property-path milestone: implement evaluation and differential error/result matrices'
                elif name == 'NamespaceManager':
                    row['plan'] = 'Namespace adapters: add strict QName/CURIE/reset differential scenarios before exposing these methods'
                elif name in ('Store', 'Memory'):
                    row['plan'] = 'Raw Store/plugin adapters: implement contexts/namespaces/graph lifecycle protocols; retain the safe RDF codec'
                elif name == 'InputSource':
                    row['plan'] = 'SAX InputSource adapters: encoding/system/public IDs, setters and stream ownership tests'
                else:
                    row['plan'] = 'Optional API expansion: add a dedicated differential matrix before exposing the missing convenience method'
            report.append(row)
    plugins = []
    for module in (rdflib, rdfcore):
        plugins.extend({'library': module.__name__, 'name': plugin.name,
                        'kind': plugin.kind.__name__} for plugin in module.plugin.plugins())
    exceptions = []
    from rdflib import exceptions as expected_exceptions
    from rdfcore import exceptions as actual_exceptions
    for name in sorted(set(dir(expected_exceptions)) | set(dir(actual_exceptions))):
        left, right = getattr(expected_exceptions, name, None), getattr(actual_exceptions, name, None)
        if any(isinstance(value, type) and issubclass(value, BaseException) for value in (left, right)):
            exceptions.append({'name': name, 'rdflib': isinstance(left, type), 'rdfcore': isinstance(right, type),
                               'rdflib_bases': [base.__name__ for base in left.__bases__] if isinstance(left, type) else [],
                               'rdfcore_bases': [base.__name__ for base in right.__bases__] if isinstance(right, type) else []})
    untracked = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], text=True).splitlines()
    hashes = {path: hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in untracked
              if path.endswith('.py') and path.startswith(('rdfcore/', 'benchmarks/', 'tests/'))}
    return {'python': platform.python_version(), 'rdflib': rdflib.__version__,
            'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
            'worktree_status': subprocess.check_output(['git', 'status', '--porcelain'], text=True).strip(),
            'untracked_source_sha256': hashes,
            'tracked_diff_sha256': hashlib.sha256(subprocess.check_output(['git', 'diff', 'HEAD', '--binary'])).hexdigest(),
            'members': report, 'classes': classes, 'plugins': plugins, 'exceptions': exceptions,
            'policy': 'verified-scoped means only the cited scenarios, never all-input parity',
            'public_exports': {module.__name__: sorted(getattr(module, '__all__', ())) for module in (rdflib, rdfcore)},
            'signature_differences': [row for row in report if row['status'] in ('present-unverified', 'verified-scoped')
                                      and row['rdflib'] != row['rdfcore']]}


def main():
    print(json.dumps(inventory(), indent=2))


if __name__ == '__main__':
    main()
