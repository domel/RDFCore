"""Reviewable public API baseline; presence is not behavioral parity."""
import inspect
import json
from pathlib import Path

import rdfcore
from rdfcore.cli import build_parser


def public_contract():
    result = {}
    for name in sorted(rdfcore.__all__):
        value = getattr(rdfcore, name)
        members = {'<call>': value}
        if inspect.isclass(value):
            members.update((key, getattr(value, key)) for key in dir(value)
                           if not key.startswith('_') and callable(getattr(value, key)))
        signatures = {}
        for key, member in members.items():
            if not callable(member) or (key != '<call>' and not
                str(getattr(member, '__module__', '')).startswith('rdfcore')):
                continue
            try:
                parameters = inspect.signature(member).parameters.values()
            except (ValueError, TypeError):
                continue
            signatures[key] = [[p.name, p.kind.name,
                                '<required>' if p.default is inspect.Parameter.empty else str(p.default)]
                               for p in parameters]
        result[name] = signatures
    return result


def test_public_api_matches_reviewed_baseline():
    expected = Path(__file__).with_name('public_api.json')
    assert public_contract() == json.loads(expected.read_text())


def test_cli_commands_remain_available():
    parser = build_parser()
    for command in ('count', 'validate'):
        assert parser.parse_args([command, '--format', 'nt']).command == command
    assert parser.parse_args(['convert', '--from', 'nt', '--to', 'nq']).dataset_policy == 'strict'
