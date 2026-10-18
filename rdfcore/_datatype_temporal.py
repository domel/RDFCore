"""XSD 1.1 temporal value keys, independent of Python datetime limits.

REC-xmlschema11-2-20120405 §§ 3.3.6-14 and Appendix E.3.5.
Timezone offsets are retained: identity is not instant equality.
"""
from decimal import Decimal
from fractions import Fraction
import re

TEMPORAL_TYPES = frozenset({'dateTime', 'dateTimeStamp', 'time', 'date',
                            'gYear', 'gYearMonth', 'gMonth', 'gDay', 'gMonthDay'})
DURATION_TYPES = frozenset({'duration', 'yearMonthDuration', 'dayTimeDuration'})
_YEAR = r'(?P<year>-?(?:[1-9][0-9]{3,}|0[0-9]{3}))'
_MONTH = r'(?P<month>[0-9]{2})'
_DAY = r'(?P<day>[0-9]{2})'
_CLOCK = r'(?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}):(?P<second>[0-9]{2}(?:\.[0-9]+)?)'
_ZONE = r'(?P<zone>Z|[+-][0-9]{2}:[0-9]{2})?'
_DATE = _YEAR+'-'+_MONTH+'-'+_DAY
_PATTERNS = {
    'dateTime': _DATE+'T'+_CLOCK, 'dateTimeStamp': _DATE+'T'+_CLOCK,
    'date': _DATE, 'time': _CLOCK, 'gYear': _YEAR,
    'gYearMonth': _YEAR+'-'+_MONTH, 'gMonth': '--'+_MONTH,
    'gDay': '---'+_DAY, 'gMonthDay': '--'+_MONTH+'-'+_DAY,
}
_PATTERNS = {name: re.compile(pattern+_ZONE) for name, pattern in _PATTERNS.items()}
_DURATION = re.compile(
    r'(?P<sign>-)?P(?:(?P<year>[0-9]+)Y)?(?:(?P<month>[0-9]+)M)?'
    r'(?:(?P<day>[0-9]+)D)?(?:T(?:(?P<hour>[0-9]+)H)?'
    r'(?:(?P<minute>[0-9]+)M)?(?:(?P<second>[0-9]+(?:\.[0-9]+)?)S)?)?')


def _number(value):
    # Decimal construction/int conversion does not use Python's str-int digit
    # limit or round to the ambient Decimal arithmetic context.
    return None if value is None else int(Decimal(value))


def _days(year, month):
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    return (31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)[month-1]


def temporal_key(lexical, datatype):
    match = _PATTERNS[datatype].fullmatch(lexical)
    if match is None: raise ValueError('invalid temporal lexical form')
    fields = match.groupdict()
    year, month, day, hour, minute = (_number(fields.get(name))
                                    for name in ('year', 'month', 'day', 'hour', 'minute'))
    second = Fraction(Decimal(fields['second'])) if fields.get('second') is not None else None
    zone = fields['zone']
    if datatype == 'dateTimeStamp' and zone is None: raise ValueError('timezone required')
    offset = None
    if zone == 'Z': offset = 0
    elif zone is not None:
        h, m = int(zone[1:3]), int(zone[4:])
        if h > 14 or m > 59 or (h == 14 and m): raise ValueError('invalid timezone')
        offset = (h*60 + m) * (-1 if zone[0] == '-' else 1)
    if month is not None and not 1 <= month <= 12: raise ValueError('invalid month')
    if day is not None and not 1 <= day <= (_days(year if year is not None else 2000, month) if month else 31):
        raise ValueError('invalid day')
    if hour is not None:
        if not 0 <= hour <= 24 or not 0 <= minute < 60 or not 0 <= second < 60:
            raise ValueError('invalid time')
        if hour == 24:
            if minute or second: raise ValueError('invalid end-of-day time')
            hour = 0
            if day is not None:
                day += 1
                if day > _days(year, month):
                    day, month = 1, month+1
                    if month == 13: year, month = year+1, 1
    return year, month, day, hour, minute, second, offset


def duration_key(lexical, datatype):
    match = _DURATION.fullmatch(lexical)
    if match is None or lexical.endswith('T'): raise ValueError('invalid duration')
    fields = match.groupdict()
    names = ('year', 'month', 'day', 'hour', 'minute', 'second')
    if not any(fields[name] is not None for name in names): raise ValueError('empty duration')
    if datatype == 'yearMonthDuration' and any(fields[name] is not None for name in names[2:]):
        raise ValueError('day/time component in yearMonthDuration')
    if datatype == 'dayTimeDuration' and any(fields[name] is not None for name in names[:2]):
        raise ValueError('year/month component in dayTimeDuration')
    values = {name: Fraction(Decimal(fields[name] or '0')) for name in names}
    sign = -1 if fields['sign'] else 1
    months = int(12*values['year'] + values['month'])
    seconds = 86400*values['day'] + 3600*values['hour'] + 60*values['minute'] + values['second']
    return sign*months, sign*seconds
