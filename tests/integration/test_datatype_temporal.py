"""XSD 1.1 Part 2 §§ 3.3.6-14, 3.4.26-28: value identity."""
import pytest

from rdfcore import Literal, XSD
from rdfcore.datatypes import datatype_value, same_value, InvalidLexicalForm


@pytest.mark.parametrize('datatype,left,right', [
    ('duration', 'P1Y', 'P12M'), ('duration', 'P1DT24H', 'P2D'),
    ('yearMonthDuration', '-P1Y2M', '-P14M'),
    ('dayTimeDuration', 'PT1.500S', 'PT1.5S'),
    ('dateTime', '2020-02-29T24:00:00Z', '2020-03-01T00:00:00+00:00'),
    ('dateTime', '0000-02-29T24:00:00', '0000-03-01T00:00:00'),
    ('dateTime', '12345-12-31T24:00:00', '12346-01-01T00:00:00'),
    ('dateTimeStamp', '2020-01-01T00:00:00.00Z', '2020-01-01T00:00:00-00:00'),
    ('time', '24:00:00', '00:00:00'), ('date', '2020-02-29Z', '2020-02-29+00:00'),
    ('gYear', '-0000Z', '0000+00:00'), ('gYearMonth', '0000-02Z', '-0000-02Z'),
    ('gMonth', '--01Z', '--01-00:00'), ('gDay', '---01Z', '---01+00:00'),
    ('gMonthDay', '--02-29Z', '--02-29+00:00'),
])
def test_temporal_value_identity(datatype, left, right):
    assert same_value(Literal(left, datatype=XSD[datatype], normalize=False),
                      Literal(right, datatype=XSD[datatype], normalize=False))


@pytest.mark.parametrize('datatype,lexical', [
    ('duration', 'P'), ('duration', 'P1YT'), ('duration', '+P1D'), ('duration', 'PT.5S'),
    ('yearMonthDuration', 'P1D'), ('dayTimeDuration', 'P1M'),
    ('dateTime', '2020-01-01'), ('dateTime', '2020-02-30T00:00:00'),
    ('dateTime', '1900-02-29T00:00:00'), ('dateTime', '2020-01-01T24:00:01'),
    ('dateTime', '2020-01-01T00:00:00+14:01'), ('dateTime', '02020-01-01T00:00:00'),
    ('dateTimeStamp', '2020-01-01T00:00:00'),
    ('time', '12:00:60'), ('date', '2020-01-01T00:00:00'),
    ('gMonth', '--00'), ('gMonth', '--01--'), ('gDay', '---32'),
    ('gYear', '001'), ('gYearMonth', '2020-13'), ('gMonthDay', '--02-30'),
])
def test_temporal_invalid_lexical_forms(datatype, lexical):
    with pytest.raises(InvalidLexicalForm):
        datatype_value(Literal(lexical, datatype=XSD[datatype], normalize=False))


def test_temporal_identity_retains_timezone_offset_not_only_instant():
    assert not same_value(Literal('2020-01-01T12:00:00Z', datatype=XSD.dateTime, normalize=False),
                          Literal('2020-01-01T13:00:00+01:00', datatype=XSD.dateTime, normalize=False))
    assert same_value(Literal('2020-01-01T12:00:00Z', datatype=XSD.dateTime, normalize=False),
                      Literal('2020-01-01T12:00:00Z', datatype=XSD.dateTimeStamp, normalize=False))


def test_gregorian_calendar_across_centuries_and_year_zero():
    import calendar
    for year in range(-400, 401, 100):
        lexical_year = ('-' if year < 0 else '') + f'{abs(year):04d}'
        for month in range(1, 13):
            last_day = calendar.monthrange(year, month)[1]
            valid = f'{lexical_year}-{month:02d}-{last_day:02d}'
            assert datatype_value(Literal(valid, datatype=XSD.date, normalize=False)).key[:3] == (year, month, last_day)
            invalid = f'{lexical_year}-{month:02d}-{last_day+1:02d}'
            with pytest.raises(InvalidLexicalForm):
                datatype_value(Literal(invalid, datatype=XSD.date, normalize=False))
