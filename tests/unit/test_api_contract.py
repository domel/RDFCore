"""Reviewable public API baseline; presence is not behavioral parity."""

import argparse
import inspect
import json
from pathlib import Path

import rdfcore
from rdfcore.cli import build_parser


def public_contract():
    assert len(rdfcore.__all__) == len(set(rdfcore.__all__))
    result = {}
    for name in sorted(rdfcore.__all__):
        value = getattr(rdfcore, name)
        members = {"<call>": value}
        if inspect.isclass(value):
            members.update(
                (key, getattr(value, key))
                for key in dir(value)
                if not key.startswith("_") and callable(getattr(value, key))
            )
        signatures = {}
        for key, member in members.items():
            if not callable(member) or (
                key != "<call>"
                and not str(getattr(member, "__module__", "")).startswith("rdfcore")
            ):
                continue
            try:
                parameters = inspect.signature(member).parameters.values()
            except (ValueError, TypeError):
                continue
            signatures[key] = [
                [
                    p.name,
                    p.kind.name,
                    "<required>"
                    if p.default is inspect.Parameter.empty
                    else str(p.default),
                ]
                for p in parameters
            ]
        result[name] = signatures
    return result


def test_public_api_matches_reviewed_baseline():
    expected = Path(__file__).with_name("public_api.json")
    assert public_contract() == json.loads(expected.read_text())


def test_cli_commands_remain_available():
    parser = build_parser()
    for command in ("count", "validate"):
        assert parser.parse_args([command, "--format", "nt"]).command == command
    assert (
        parser.parse_args(["convert", "--from", "nt", "--to", "nq"]).dataset_policy
        == "strict"
    )


def dispatch_contract():
    """Freeze built-in aliases independently of runtime plugin registrations."""
    aliases = {
        rdfcore.Parser: (
            "nt",
            "nt11",
            "nt12",
            "ntriples",
            "nq",
            "nq11",
            "nq12",
            "nquads",
            "turtle",
            "ttl",
            "turtle11",
            "turtle12",
            "trig",
            "trig11",
            "trig12",
            "xml",
            "rdfxml",
            "xml12",
            "xmlrdf12",
        ),
        rdfcore.Serializer: (
            "nt",
            "nt11",
            "nt12",
            "ntriples",
            "nq",
            "nq11",
            "nq12",
            "nquads",
            "turtle",
            "ttl",
            "turtle11",
            "turtle12",
            "trig",
            "trig11",
            "trig12",
            "xml",
            "rdfxml",
            "xml12",
            "xmlrdf12",
        ),
        rdfcore.Store: ("default", "Memory"),
    }
    result = {}
    for kind, names in aliases.items():
        entries = {}
        for name in names:
            cls = rdfcore.plugin.get(name, kind).getClass()
            entries[name] = cls.__module__ + "." + cls.__qualname__
        if kind is not rdfcore.Store:
            for mime in (
                "application/n-triples",
                "application/n-quads",
                "text/turtle",
                "application/trig",
                "application/rdf+xml",
            ):
                for suffix in (
                    "",
                    "; version=1.1",
                    "; version=1.2-basic",
                    "; version=1.2",
                ):
                    name = mime + suffix
                    alias, version = rdfcore.plugin.resolve_format(name, kind)
                    entries[name] = [alias, version]
        result[kind.__name__] = entries
    result["classes"] = {
        name: [
            base.__module__ + "." + base.__qualname__
            for base in getattr(rdfcore, name).__bases__
        ]
        for name in (
            "Graph",
            "Dataset",
            "ConjunctiveGraph",
            "Store",
            "Memory",
            "SQLiteStore",
        )
    }
    result["exceptions"] = {
        name: [base.__module__ + "." + base.__qualname__ for base in value.__bases__]
        for name in rdfcore.__all__
        if inspect.isclass(value := getattr(rdfcore, name))
        and issubclass(value, BaseException)
    }
    return result


def test_dispatch_and_exception_contract_matches_reviewed_baseline():
    path = Path(__file__).with_name("public_dispatch.json")
    assert dispatch_contract() == json.loads(path.read_text())


def cli_contract():
    return {
        command: [
            {
                "dest": action.dest,
                "flags": action.option_strings,
                "default": action.default,
                "required": action.required,
                "nargs": action.nargs,
                "choices": list(action.choices) if action.choices is not None else None,
            }
            for action in parser._actions
            if action.dest != "help"
        ]
        for group in build_parser()._actions
        if isinstance(group, argparse._SubParsersAction)
        for command, parser in group.choices.items()
    }


def test_cli_option_contract_matches_reviewed_baseline():
    path = Path(__file__).with_name("public_cli.json")
    assert cli_contract() == json.loads(path.read_text())
