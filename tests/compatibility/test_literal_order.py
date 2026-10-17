"""Executable RDFLib 7.6.0 oracle for the independently wired order helpers."""

from datetime import date, datetime, time, timezone
from decimal import Decimal
import operator
import platform
import subprocess

import pytest
import rdflib
import rdfcore

from rdfcore import literal_order


XSD = "http://www.w3.org/2001/XMLSchema#"
NUMERIC = (
    "integer", "decimal", "double", "float", "byte", "int", "long",
    "negativeInteger", "nonNegativeInteger", "nonPositiveInteger",
    "positiveInteger", "short", "unsignedByte", "unsignedInt",
    "unsignedLong", "unsignedShort",
)
# Preserve lexical forms to exercise value ordering independently of normalization.
CASES = [
    ("", None, None), ("a", None, None), ("b", None, None),
    ("a", "string", None), ("b", "string", None),
    ("a", None, "en"), ("a", None, "EN"), ("b", None, "en"),
    ("a", None, "fr"), ("", None, "en"),
    ("false", "boolean", None), ("true", "boolean", None),
    ("bad", "boolean", None),
    ("bad", "integer", None), ("worse", "integer", None),
    ("bad", "decimal", None), ("bad", "double", None),
    ("NaN", "double", None), ("INF", "double", None),
    ("-INF", "float", None), ("NaN", "decimal", None),
    ("a", "urn:unknown", None), ("b", "urn:unknown", None),
    ("a", "urn:other", None),
    (None, None, None), (None, "integer", None), (None, "string", None),
    ("2000-01-01", "date", None), ("2001-01-01", "date", None),
    ("2000-01-01T00:00:00", "dateTime", None),
    ("2000-01-01T00:00:00Z", "dateTime", None),
    ("1999-12-31T23:00:00-01:00", "dateTime", None),
    ("00:00:00", "time", None), ("00:00:00Z", "time", None),
    ("AA", "hexBinary", None), ("AB", "hexBinary", None),
    ("YQ==", "base64Binary", None), ("Yg==", "base64Binary", None),
] + [
    (value, datatype, None)
    for datatype in NUMERIC
    for value in (
        ("-10", "-2", "-1") if datatype == "negativeInteger" else
        ("-10", "-2", "0") if datatype == "nonPositiveInteger" else
        ("1", "2", "10") if datatype == "positiveInteger" else
        ("0", "2", "10")
    )
]


def make(module, spec):
    value, datatype, language = spec
    if datatype is not None:
        datatype = module.URIRef(datatype if ":" in datatype else XSD + datatype)
    return module.Literal(value, datatype=datatype, lang=language, normalize=False)


def outcome(call):
    try:
        value = call()
        return ("return", type(value), value)
    except Exception as error:
        return ("raise", type(error))


def test_oracle_version(record_property):
    assert rdflib.__version__ == "7.6.0"
    record_property("rdflib", rdflib.__version__)
    record_property("python", platform.python_version())
    record_property("rdfcore_revision", subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True).strip())


@pytest.mark.parametrize("name", ["lt", "gt", "le", "ge"])
@pytest.mark.parametrize("left", CASES)
def test_literal_pair_matrix(name, left):
    core_left, reference_left = make(rdfcore, left), make(rdflib, left)
    helper = getattr(literal_order, "literal_" + name)
    method = getattr(rdflib.Literal, "__" + name + "__")
    for right in CASES:
        core_right, reference_right = make(rdfcore, right), make(rdflib, right)
        assert outcome(lambda: helper(core_left, core_right)) == outcome(
            lambda: method(reference_left, reference_right)), (name, left, right)


@pytest.mark.parametrize("name", ["lt", "gt", "le", "ge"])
@pytest.mark.parametrize("kind,value", [
    (None, None), (None, "a"), (None, 1), (None, 1.5),
    (None, False), (None, Decimal("1")), (None, object()),
    ("URIRef", "urn:a"), ("BNode", "a"), ("Variable", "a"),
])
def test_nonliteral_operands(name, kind, value):
    for spec in [("a", None, None), ("1", "integer", None)]:
        a, b = make(rdfcore, spec), make(rdflib, spec)
        x = getattr(rdfcore, kind)(value) if kind else value
        y = getattr(rdflib, kind)(value) if kind else value
        assert outcome(lambda: getattr(literal_order, "literal_" + name)(a, x)) == outcome(
            lambda: getattr(b, "__" + name + "__")(y))


@pytest.mark.parametrize("spec", CASES)
def test_literal_truth(spec):
    assert literal_order.literal_bool(make(rdfcore, spec)) is bool(make(rdflib, spec))


@pytest.mark.parametrize("value", [
    None, "", "text", 0, 1, -1, False, True, 0.0, float("nan"),
    Decimal("0"), Decimal("2"), date(2000, 1, 1),
    datetime(2000, 1, 1), datetime(2000, 1, 1, tzinfo=timezone.utc),
    time(0), time(0, tzinfo=timezone.utc),
])
def test_python_value_truth(value):
    assert literal_order.literal_bool(rdfcore.Literal(value)) is bool(rdflib.Literal(value))


@pytest.mark.parametrize("lexical,datatype", [
    ("0", "negativeInteger"), ("2", "negativeInteger"),
    ("2", "nonPositiveInteger"), ("0", "positiveInteger"),
])
def test_out_of_range_constructor_preserves_value(lexical, datatype):
    core = make(rdfcore, (lexical, datatype, None))
    reference = make(rdflib, (lexical, datatype, None))
    assert core.ill_typed is reference.ill_typed is True
    assert core.value == reference.value == int(lexical)
    assert literal_order.literal_bool(core) is bool(reference)


class WiredLiteral(rdfcore.Literal):
    __lt__ = literal_order.literal_lt
    __gt__ = literal_order.literal_gt
    __le__ = literal_order.literal_le
    __ge__ = literal_order.literal_ge
    __bool__ = literal_order.literal_bool


@pytest.mark.parametrize("operation", [operator.lt, operator.gt, operator.le, operator.ge])
@pytest.mark.parametrize("other", [None, 1, "a", False])
def test_operator_dispatch(operation, other):
    assert outcome(lambda: operation(WiredLiteral("a"), other)) == outcome(
        lambda: operation(rdflib.Literal("a"), other))
    assert outcome(lambda: operation(other, WiredLiteral("a"))) == outcome(
        lambda: operation(other, rdflib.Literal("a")))
