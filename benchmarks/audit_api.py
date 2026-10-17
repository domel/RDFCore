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


def main():
    reference = {'Collection': Collection, 'Resource': Resource, 'NamespaceManager': NamespaceManager}
    report = []
    for name in ('URIRef', 'BNode', 'Variable', 'Literal', 'Graph', 'Dataset',
                 'Collection', 'Resource', 'NamespaceManager'):
        expected = reference.get(name) or getattr(rdflib, name)
        actual = getattr(rdfcore, name)
        for method in sorted(set(dir(expected)) & set(dir(actual))):
            if method.startswith('_'):
                continue
            try:
                left = signature(getattr(expected, method))
                right = signature(getattr(actual, method))
            except (TypeError, ValueError):
                continue
            if left != right:
                report.append({'class': name, 'method': method, 'rdflib': left, 'rdfcore': right})
    print(json.dumps({'python': platform.python_version(), 'rdflib': rdflib.__version__,
                      'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                      'signature_differences': report}, indent=2))


if __name__ == '__main__':
    main()
