"""Binary arithmetic, normalization and native values against RDFLib 7.6.0."""
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import operator
import pytest
import rdflib
import rdfcore

CASES = [(1, None), (2.5, None), (Decimal('1.20'), None), ('one', None),
         ('2', 'integer'), ('bad', 'integer'), ('2', 'float'), ('3', 'int'),
         (True, None), ('text', 'string'), ('value', 'urn:custom'),
         (date(2024, 1, 31), None), (datetime(2024, 1, 31, 5), None),
         (time(5), None), (timedelta(days=2), None),
         ('P1M', 'duration'), ('P2D', 'dayTimeDuration'), ('P1Y', 'yearMonthDuration')]


def make(module, case):
    value, datatype = case
    if datatype:
        datatype = module.URIRef(datatype if ':' in datatype else 'http://www.w3.org/2001/XMLSchema#' + datatype)
    return module.Literal(value, datatype=datatype)


def outcome(module, operation, left, right):
    a = make(module, left)
    b = make(module, right) if right is not None else None
    try:
        result = operation(a, b)
        assert isinstance(result, module.Literal)
        return ('value', str(result), str(result.datatype), result.language, result is a)
    except Exception as error:
        return ('error', type(error).__name__)


@pytest.mark.parametrize('left', CASES)
@pytest.mark.parametrize('right', CASES + [None])
@pytest.mark.parametrize('operation', [operator.add, operator.sub])
def test_binary_arithmetic(left, right, operation):
    assert outcome(rdfcore, operation, left, right) == outcome(rdflib, operation, left, right)


@pytest.mark.parametrize('case', CASES)
@pytest.mark.parametrize('normalize', [True, False])
def test_normalization_and_value_types(case, normalize):
    observations = []
    for module in (rdflib, rdfcore):
        value, datatype = case
        datatype = module.URIRef(datatype if ':' in datatype else 'http://www.w3.org/2001/XMLSchema#' + datatype) if datatype else None
        literal = module.Literal(value, datatype=datatype, normalize=normalize)
        native = literal.toPython()
        observations.append((str(literal), str(literal.normalize()), literal.ill_typed,
                             type(native).__name__, literal.normalize() is literal))
    assert observations[0] == observations[1]


@pytest.mark.parametrize('lexical', ['P', 'PT', 'P0D', 'P1Y2M', 'P12M', 'P0.5Y', 'P1.5M',
                                   'P1W', 'P1DT0.5H', 'P1D2Y', 'p1d', '-P1M', '-P1Y2D',
                                   '-PT0.0000001S', 'P0001Y', 'P1,5D', '+P1D', 'P1DT', ''])
@pytest.mark.parametrize('datatype', ['duration', 'dayTimeDuration', 'yearMonthDuration'])
def test_duration_lexical_and_value_mapping(lexical, datatype):
    results = []
    for module in (rdflib, rdfcore):
        try:
            value = module.Literal(lexical, datatype=module.URIRef('http://www.w3.org/2001/XMLSchema#' + datatype))
        except Exception as error:
            results.append(('constructor-error', type(error).__name__))
            continue
        native = value.value
        results.append((str(value), value.ill_typed, type(native).__name__,
                        str(getattr(native, 'years', None)), str(getattr(native, 'months', None)),
                        str(getattr(native, 'tdelta', native)) if native is not None else None))
    assert results[0] == results[1]


@pytest.mark.parametrize('language', [None, 'en'])
@pytest.mark.parametrize('other', [None, 'text', 1, 2.5, Decimal('1.2')])
@pytest.mark.parametrize('operation', [operator.add, operator.sub])
def test_python_operands_and_language(language, other, operation):
    results = []
    for module in (rdflib, rdfcore):
        left = module.Literal('text', lang=language)
        try:
            value = operation(left, other)
            results.append((str(value), str(value.datatype), value.language, value is left))
        except Exception as error:
            results.append(type(error).__name__)
    assert results[0] == results[1]


def test_calendar_value_operations():
    for module in (rdflib, rdfcore):
        duration = module.Literal('P1M', datatype=module.URIRef('http://www.w3.org/2001/XMLSchema#duration')).toPython()
        assert date(2024, 1, 31) + duration == date(2024, 2, 29)
        assert duration.totimedelta(start=date(2024, 1, 31)) == timedelta(days=29)
        assert duration.totimedelta(end=date(2024, 3, 31)) == timedelta(days=31)
        assert date(2024, 1, 31) + 2 * duration == date(2024, 3, 31)
        with pytest.raises(ValueError):
            duration.totimedelta()


def test_directional_arithmetic_is_not_a_lossy_string_operation():
    value = rdfcore.Literal('text', lang='en', direction='rtl')
    assert value + None is value
    assert value - None is value
    with pytest.raises(TypeError):
        value + rdfcore.Literal('other')
    assert value.direction == 'rtl'


@pytest.mark.parametrize('left,right,operation', [(('text', None), (1, None), operator.sub),
                                                ((1, None), ('text', None), operator.sub),
                                                ((date(2024, 1, 1), None), (1, None), operator.add),
                                                ((1, None), ('other', 'urn:type'), operator.sub)])
def test_stable_arithmetic_error_messages(left, right, operation):
    errors = []
    for module in (rdflib, rdfcore):
        with pytest.raises(TypeError) as caught:
            operation(make(module, left), make(module, right))
        errors.append(str(caught.value))
    assert errors[0] == errors[1]


@pytest.mark.parametrize('normalize', [True, False, None])
def test_duration_literal_copy_retains_lexical_form(normalize):
    results = []
    for module in (rdflib, rdfcore):
        original = module.Literal('P12M', datatype=module.URIRef('http://www.w3.org/2001/XMLSchema#duration'), normalize=False)
        copied = module.Literal(original, normalize=normalize)
        results.append((str(copied), copied.value is original.value, copied.ill_typed))
    assert results[0] == results[1]
