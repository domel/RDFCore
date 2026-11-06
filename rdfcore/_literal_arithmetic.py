"""Native helpers for the pinned RDFLib literal arithmetic contract."""
from calendar import monthrange
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_FLOOR
import re

XSD = 'http://www.w3.org/2001/XMLSchema#'
DURATIONS = {XSD + name for name in ('duration', 'dayTimeDuration', 'yearMonthDuration')}
ARITH_DURATIONS = DURATIONS - {XSD + 'yearMonthDuration'}
DATES = {XSD + name for name in ('date', 'dateTime', 'time')}


class Duration:
    """Calendar duration: years/months plus a fixed timedelta component."""
    def __init__(self, years=0, months=0, tdelta=timedelta()):
        years, months = Decimal(years), Decimal(months)
        carry = (months / 12).to_integral_value(rounding=ROUND_FLOOR)
        self.years, self.months, self.tdelta = years + carry, months - carry * 12, tdelta

    def __getattr__(self, name):
        return getattr(self.tdelta, name)

    def __neg__(self):
        return Duration(-self.years, -self.months, -self.tdelta)

    def __add__(self, other):
        if isinstance(other, Duration):
            return Duration(self.years + other.years, self.months + other.months, self.tdelta + other.tdelta)
        if isinstance(other, timedelta):
            return Duration(self.years, self.months, self.tdelta + other)
        if isinstance(other, (date, datetime)):
            if self.years % 1 or self.months % 1:
                raise ValueError('fractional years or months not supported for date calculations')
            year, month = divmod(other.year * 12 + other.month - 1 + int(self.years * 12 + self.months), 12)
            return other.replace(year=year, month=month + 1,
                                 day=min(other.day, monthrange(year, month + 1)[1])) + self.tdelta
        return NotImplemented

    __radd__ = __add__

    def __sub__(self, other):
        if isinstance(other, (Duration, timedelta)):
            return self + (-other)
        return NotImplemented

    def __rsub__(self, other):
        return -self + other

    def __eq__(self, other):
        if isinstance(other, timedelta):
            return self.years * 12 + self.months == 0 and self.tdelta == other
        if isinstance(other, Duration):
            return self.years * 12 + self.months == other.years * 12 + other.months and self.tdelta == other.tdelta
        return False

    def __hash__(self):
        return hash((self.years * 12 + self.months, self.tdelta))

    def __mul__(self, factor):
        if not isinstance(factor, int):
            return NotImplemented
        return Duration(self.years * factor, self.months * factor, self.tdelta * factor)

    __rmul__ = __mul__

    def totimedelta(self, start=None, end=None):
        if (start is None) == (end is None):
            raise ValueError('exactly one of start or end is required')
        return start + self - start if start is not None else end - (end - self)

    def __str__(self):
        parts = []
        if self.years:
            parts.append(f'{int(self.years)} years')
        if self.months:
            parts.append(f'{int(self.months)} ' + ('month' if self.months <= 1 else 'months'))
        return ', '.join([*parts, str(self.tdelta)])


_PATTERN = re.compile(r'(?P<sign>[+-])?P(?:(?P<years>\d+(?:[.,]\d+)?)Y)?(?:(?P<months>\d+(?:[.,]\d+)?)M)?(?:(?P<weeks>\d+(?:[.,]\d+)?)W)?(?:(?P<days>\d+(?:[.,]\d+)?)D)?(?:T(?:(?P<hours>\d+(?:[.,]\d+)?)H)?(?:(?P<minutes>\d+(?:[.,]\d+)?)M)?(?:(?P<seconds>\d+(?:[.,]\d+)?)S)?)?')


def parse_duration(lexical):
    match = _PATTERN.fullmatch(lexical)
    if not match:
        raise ValueError('invalid duration')
    values = match.groupdict()
    sign = -1 if values.pop('sign') == '-' else 1
    if lexical.lstrip('+-') == 'P':
        raise ValueError('invalid duration')
    amounts = {key: Decimal(value.replace(',', '.')) if value else Decimal(0) for key, value in values.items()}
    fixed = timedelta(**{key: float(amounts[key]) for key in ('weeks', 'days', 'hours', 'minutes', 'seconds')})
    if not amounts['years'] and not amounts['months']:
        return sign * fixed
    return Duration(sign * amounts['years'], sign * amounts['months'], sign * fixed)


def format_duration(value):
    parts = []
    negative = False
    calendar = isinstance(value, Duration) and bool(value.years or value.months)
    if calendar:
        months = value.years * 12 + value.months
        negative = months < 0
        years, months = divmod(abs(months), 12)
        if years:
            parts.append(str(years) + 'Y')
        if value.months:
            parts.append(str(months) + 'M')
    fixed = value.tdelta if isinstance(value, Duration) else value
    microseconds = (fixed.days * 86400 + fixed.seconds) * 1000000 + fixed.microseconds
    if microseconds < 0:
        if calendar:
            raise ValueError('incompatible signs in calendar and fixed duration components')
        negative = True
    seconds, micros = divmod(abs(microseconds), 1000000)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if days:
        parts.append(str(days) + 'D')
    if hours or minutes or seconds or micros:
        parts.append('T')
        if hours:
            parts.append(str(hours) + 'H')
        if minutes:
            parts.append(str(minutes) + 'M')
        if seconds or micros:
            parts.append((f'{seconds}.{micros:06d}'.rstrip('0') if micros else str(seconds)) + 'S')
    return ('-P' if negative else 'P') + (''.join(parts) or '0D')


def binary(left, right, subtract=False):
    from .term import Literal, _INTEGER_DATATYPES, _STRING_DATATYPES
    if right is None:
        return left
    right = right if isinstance(right, Literal) else Literal(right)
    if left.direction is not None or right.direction is not None:
        raise TypeError('arithmetic on directional literals is unsupported')
    a, b = str(left.datatype), str(right.datatype)
    if subtract and not left.datatype:
        raise TypeError('Minuend Literal must have Numeric, Date, Datetime or Time datatype.')
    if subtract and not right.datatype:
        raise TypeError('Subtrahend Literal must have Numeric, Date, Datetime or Time datatype.')
    operation = (lambda x, y: x - y) if subtract else (lambda x, y: x + y)
    if a in DATES and b in ARITH_DURATIONS:
        native = left.toPython()
        if a == XSD + 'time':
            native = datetime.combine(date(2000, 1, 1), native)
        result = operation(native, right.toPython())
        return Literal(result.time() if a == XSD + 'time' else result, datatype=left.datatype)
    temporal = DATES | ARITH_DURATIONS
    if not subtract and ((a in temporal) != (b in temporal) or (a in ARITH_DURATIONS and a != b)):
        raise TypeError(f'Cannot add a Literal of datatype {right.datatype} to a Literal of datatype {left.datatype}')
    if left.datatype == right.datatype:
        lvalue, rvalue = left.toPython(), right.toPython()
        if subtract and a == XSD + 'time':
            lvalue, rvalue = datetime.combine(date.today(), lvalue), datetime.combine(date.today(), rvalue)
        result = operation(lvalue, rvalue)
        datatype = XSD + 'duration' if subtract and a in DATES else left.datatype
        return Literal(result, lang=left.language, datatype=datatype)
    numeric = _INTEGER_DATATYPES | {XSD + name for name in ('decimal', 'double', 'float')}
    if a in numeric and b in numeric:
        result = operation(Decimal(left.toPython()), Decimal(right.toPython()))
        lexical = f'{round(result, 15):f}'.rstrip('0').rstrip('.')
        return Literal(Decimal(lexical), datatype=XSD + 'decimal')
    if subtract:
        raise TypeError(f'Cannot subtract a Literal of datatype {right.datatype} from a Literal of datatype {left.datatype}')
    strings = {XSD + name for name in ('string', 'normalizedString', 'token')} | {'http://www.w3.org/1999/02/22-rdf-syntax-ns#XMLLiteral', 'http://www.w3.org/1999/02/22-rdf-syntax-ns#HTML'}
    datatype = left.datatype if a in strings else XSD + 'string'
    return Literal(str(left) + str(right), lang=left.language, datatype=datatype)
