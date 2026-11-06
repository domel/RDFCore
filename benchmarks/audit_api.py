"""Report shared API signature differences without treating them as parity proof."""

import inspect
import json
import platform
import subprocess

import rdflib
import rdfcore
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
    reference = {'Collection': Collection, 'Resource': Resource, 'NamespaceManager': NamespaceManager,
                 'Store': rdflib.store.Store, 'Memory': type(rdflib.Graph().store)}
    report = []
    special = {'__init__', '__add__', '__sub__', '__mul__', '__truediv__', '__neg__',
               '__pos__', '__abs__', '__eq__', '__hash__', '__contains__', '__iter__',
               '__len__', '__getitem__', '__iadd__', '__isub__', '__and__', '__or__', '__xor__'}
    for name in ('URIRef', 'BNode', 'Variable', 'Literal', 'Graph', 'Dataset',
                 'ConjunctiveGraph', 'Collection', 'Resource', 'NamespaceManager', 'Store', 'Memory'):
        expected = reference.get(name) or getattr(rdflib, name)
        actual = getattr(rdfcore, name)
        for method in sorted(set(dir(expected)) | set(dir(actual))):
            if method.startswith('_') and method not in special:
                continue
            left = inspect.getattr_static(expected, method, None)
            right = inspect.getattr_static(actual, method, None)
            row = {'class': name, 'method': method,
                   'status': 'missing' if left is not None and right is None else
                             'extension' if left is None else 'present-unverified',
                   'rdflib_kind': type(left).__name__, 'rdfcore_kind': type(right).__name__}
            for label, value in [('rdflib', left), ('rdfcore', right)]:
                try:
                    row[label] = signature(value)
                except (TypeError, ValueError):
                    row[label] = None
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
            exceptions.append({'name': name, 'rdflib': isinstance(left, type), 'rdfcore': isinstance(right, type)})
    return {'python': platform.python_version(), 'rdflib': rdflib.__version__,
            'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
            'members': report, 'plugins': plugins, 'exceptions': exceptions,
            'signature_differences': [row for row in report if row['status'] == 'present-unverified'
                                      and row['rdflib'] != row['rdfcore']]}


def main():
    print(json.dumps(inventory(), indent=2))


if __name__ == '__main__':
    main()
