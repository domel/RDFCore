"""Value-space constraints for explicit D-entailment, not Literal equality.

Semantics CRD 2026-09-24 §§7–9; Concepts CR 2026-04-07 §5/Appendix A;
XSD 1.1 Part 2 REC 2012-04-05 §2.2.1 and built-in type definitions.
HTML and XMLLiteral have the same DOM DocumentFragment value space, even
though their lexical mappings differ. XSD primitive spaces remain disjoint.
"""

import json
from base64 import b64encode

from .datatypes import (
    RDF, XSD, SUPPORTED_DATATYPES, DatatypeValue, InvalidLexicalForm,
    UnsupportedDatatype, datatype_value, lexical_value, _STRINGS,
)
from .term import Literal, _INTEGER_BOUNDS, _INTEGER_DATATYPES
from ._datatype_temporal import TEMPORAL_TYPES, DURATION_TYPES


def families(datatype):
    datatype = str(datatype)
    if datatype not in SUPPORTED_DATATYPES:
        raise UnsupportedDatatype(datatype)
    name = datatype.removeprefix(XSD)
    if datatype == RDF+'JSON':
        return {'JSON', 'string', 'boolean', 'double'}
    if datatype in {RDF+'HTML', RDF+'XMLLiteral'}:
        return {'markup'}
    if datatype.startswith(RDF):
        return {datatype[len(RDF):]}
    if datatype in _INTEGER_DATATYPES or name == 'decimal':
        return {'numeric'}
    if name in _STRINGS:
        return {'anyURI' if name == 'anyURI' else 'string'}
    if name in TEMPORAL_TYPES:
        return {'temporal-'+('dateTime' if name == 'dateTimeStamp' else name)}
    if name in DURATION_TYPES:
        return {'duration'}
    return {name}


def contains(value: DatatypeValue, datatype) -> bool:
    """Exact membership of a validated value in a supported datatype space."""
    datatype = str(datatype)
    space = families(datatype)
    name = datatype.removeprefix(XSD)
    if value.family == 'temporal':
        fields = value.key
        kind = {tuple(field is not None for field in fields[:6]): kind for kind, fields in (
            ('dateTime', (1, 1, 1, 1, 1, 1)), ('date', (1, 1, 1, None, None, None)),
            ('time', (None, None, None, 1, 1, 1)), ('gYear', (1, None, None, None, None, None)),
            ('gYearMonth', (1, 1, None, None, None, None)), ('gMonth', (None, 1, None, None, None, None)),
            ('gDay', (None, None, 1, None, None, None)), ('gMonthDay', (None, 1, 1, None, None, None)),
        )}.get(tuple(field is not None for field in fields[:6]))
        return ('temporal-'+str(kind) in space
                and (name != 'dateTimeStamp' or fields[6] is not None))
    if value.family not in space:
        return False
    if value.family == 'numeric':
        if datatype in _INTEGER_DATATYPES:
            lower, upper = _INTEGER_BOUNDS.get(datatype, (None, None))
            return (value.key.denominator == 1
                    and (lower is None or value.key >= lower)
                    and (upper is None or value.key <= upper))
        return True
    if value.family in {'string', 'anyURI'} and datatype != RDF+'JSON':
        try:
            return lexical_value(value.key, datatype) == value
        except InvalidLexicalForm:
            return False
    if value.family == 'duration':
        months, seconds = value.key
        return ((name != 'yearMonthDuration' or seconds == 0)
                and (name != 'dayTimeDuration' or months == 0))
    return True


_STRING_PARENTS = {
    'string': set(), 'normalizedString': {'string'},
    'token': {'normalizedString', 'string'},
    'NMTOKEN': {'token', 'normalizedString', 'string'},
    'Name': {'NMTOKEN', 'token', 'normalizedString', 'string'},
    'NCName': {'Name', 'NMTOKEN', 'token', 'normalizedString', 'string'},
    'language': {'NCName', 'Name', 'NMTOKEN', 'token', 'normalizedString', 'string'},
}


def subset(left, right) -> bool:
    """Space inclusion, not an inferred rdfs:subClassOf assertion."""
    left, right = str(left), str(right)
    a, b = families(left), families(right)
    if left == right:
        return True
    if not a <= b:
        return False
    ln, rn = left.removeprefix(XSD), right.removeprefix(XSD)
    if a == {'numeric'}:
        if rn == 'decimal':
            return True
        if left not in _INTEGER_DATATYPES:
            return False
        ll, lu = _INTEGER_BOUNDS.get(left, (None, None))
        rl, ru = _INTEGER_BOUNDS.get(right, (None, None))
        return ((rl is None or (ll is not None and ll >= rl))
                and (ru is None or (lu is not None and lu <= ru)))
    if a == {'string'} and right != RDF+'JSON':
        return rn in _STRING_PARENTS.get(ln, set())
    if a == {'temporal-dateTime'}:
        return rn == 'dateTime'
    if a == {'duration'}:
        return rn == 'duration'
    return True


_SAMPLES = {
    'boolean': [('true', XSD+'boolean'), ('false', XSD+'boolean')],
    'string': [('a', XSD+'string'), ('b', XSD+'string')],
    'anyURI': [('urn:a', XSD+'anyURI'), ('urn:b', XSD+'anyURI')],
    'float': [('0', XSD+'float'), ('1', XSD+'float')],
    'double': [('0', XSD+'double'), ('1', XSD+'double')],
    'markup': [('', RDF+'XMLLiteral'), ('text', RDF+'XMLLiteral')],
    'JSON': [('[]', RDF+'JSON'), ('{}', RDF+'JSON')],
    'duration': [('P0M', XSD+'duration'), ('P1M', XSD+'duration'), ('PT1S', XSD+'duration')],
    'hexBinary': [('', XSD+'hexBinary'), ('00', XSD+'hexBinary')],
    'base64Binary': [('', XSD+'base64Binary'), ('AA==', XSD+'base64Binary')],
}
for name, lexical in {
    'dateTime': '2026-10-22T00:00:00Z', 'date': '2026-10-22Z', 'time': '00:00:00Z',
    'gYear': '2026Z', 'gYearMonth': '2026-10Z', 'gMonth': '--10Z', 'gDay': '---22Z',
    'gMonthDay': '--10-22Z',
}.items():
    _SAMPLES['temporal-'+name] = [(lexical, XSD+name)]


def _recognized_witness(literal, datatypes):
    value = datatype_value(literal)
    for datatype in sorted(datatypes):
        text = str(literal)
        if datatype == RDF+'langString':
            candidate = Literal(text, lang=literal.language)
        elif datatype == RDF+'dirLangString':
            candidate = Literal(text, lang=literal.language, direction=literal.direction)
        else:
            if datatype == RDF+'JSON':
                if value.family == 'string':
                    text = json.dumps(value.key)
                elif value.family == 'boolean':
                    text = 'true' if value.key else 'false'
            if datatype == XSD+'dayTimeDuration' and value.family == 'duration':
                text = 'PT0S' if value.key[1] == 0 else text
            candidate = Literal(text, datatype=datatype, normalize=False)
        try:
            if datatype_value(candidate) == value:
                return candidate
        except InvalidLexicalForm:
            continue
    raise UnsupportedDatatype('no recognized lexical representation for intersection witness')


def witnesses(datatypes, *, enumerate_finite=False):
    """Return (witness literals, exhaustive).

    An empty list proves an empty intersection, not a failed sample search.
    Samples certify existence only. Boolean spaces, singleton integer
    intervals and the zero-duration intersection are exhaustive. With
    enumerate_finite=True, bounded integer intervals of up to 4096 values
    are also exhaustive. Larger spaces are never silently treated as finite
    collections of samples.
    """
    datatypes = set(map(str, datatypes))
    if not datatypes:
        raise ValueError('intersection requires at least one datatype')
    common = set.intersection(*(families(t) for t in datatypes))
    if not common:
        return [], True
    if common == {'numeric'}:
        lower = max((bound for t in datatypes for bound in [_INTEGER_BOUNDS.get(t, (None, None))[0]]
                     if bound is not None), default=None)
        upper = min((bound for t in datatypes for bound in [_INTEGER_BOUNDS.get(t, (None, None))[1]]
                     if bound is not None), default=None)
        if lower is not None and upper is not None and lower > upper:
            return [], True
        base = max(0, lower) if lower is not None else min(0, upper) if upper is not None else 0
        if upper is not None:
            base = min(base, upper)
        exhaustive = lower is not None and lower == upper
        if (enumerate_finite and any(t in _INTEGER_DATATYPES for t in datatypes)
                and lower is not None and upper is not None and upper-lower < 4096):
            numbers, exhaustive = range(lower, upper+1), True
        else:
            numbers = [base, base+1, base-1]
        samples = [Literal(str(n), datatype=XSD+'integer', normalize=False) for n in numbers]
        selected = [s for s in samples if all(contains(datatype_value(s), t) for t in datatypes)]
        return [_recognized_witness(s, datatypes) for s in selected], exhaustive
    samples = []
    for family in sorted(common):
        if family == 'langString':
            samples.append(Literal('value', lang='en'))
        elif family == 'dirLangString':
            samples.append(Literal('value', lang='en', direction='ltr'))
        else:
            samples.extend(Literal(text, datatype=datatype, normalize=False)
                           for text, datatype in _SAMPLES[family])
    selected = [s for s in samples if all(contains(datatype_value(s), t) for t in datatypes)]
    if not selected:
        # Every nonnumeric family intersection above has a known common
        # witness. A missing one is an implementation gap, never emptiness.
        raise UnsupportedDatatype('intersection witness is unavailable')
    exhaustive = (common == {'boolean'} or
                  {XSD+'yearMonthDuration', XSD+'dayTimeDuration'} <= datatypes)
    return [_recognized_witness(s, datatypes) for s in selected], exhaustive


def countermodel_witnesses(datatypes, recognized, occupied, *, step):
    """Facet-boundary and fresh values, never an exhaustive proof domain."""
    datatypes = set(map(str, datatypes))
    common = set.intersection(*(families(t) for t in datatypes))
    candidates = []
    if 'numeric' in common:
        numbers = {0, 1, -1}
        for datatype in recognized:
            for bound in _INTEGER_BOUNDS.get(str(datatype), ()):
                if bound is not None:
                    numbers.update((bound-1, bound, bound+1))
        candidates.extend(Literal(str(n), datatype=XSD+'integer', normalize=False) for n in sorted(numbers))
        candidates.append(Literal('0.5', datatype=XSD+'decimal', normalize=False))
    if 'string' in common:
        candidates.extend(Literal(s, datatype=XSD+'string', normalize=False)
                          for s in ('', 'a b', ' a', 'a  b', 'a\tb', '1', 'a:b', 'a_b', 'en-US'))
    if 'temporal-dateTime' in common:
        candidates.append(Literal('2026-10-22T00:00:00', datatype=XSD+'dateTime', normalize=False))

    selected = {}

    def include(sample):
        step()
        value = datatype_value(sample)
        if all(contains(value, t) for t in datatypes):
            sample = _recognized_witness(sample, datatypes)
            selected[value] = sample
            return value not in occupied
        return False

    for sample in candidates:
        include(sample)
    # A finite ordinary property extension cannot cover an infinite value
    # space. Seek a fresh value instead of assuming 0/1/-1 are representative.
    for index in range(min(len(occupied)+2, 4096)):
        for family in sorted(common):
            if family in {'langString', 'dirLangString'}:
                sample = Literal('value'+str(index), lang='en',
                                 direction='ltr' if family == 'dirLangString' else None)
                if include(sample):
                    return list(selected.values())
                continue
            if family == 'numeric':
                samples = [(str(index+1), XSD+'integer'), (str(-index-1), XSD+'integer')]
            elif family == 'string':
                samples = [('a'+'-a'*index, XSD+'string')]
            elif family == 'markup':
                samples = [('text'+str(index), RDF+'XMLLiteral')]
            elif family in {'float', 'double'}:
                samples = [(str(index+2), XSD+family)]
            elif family == 'anyURI':
                samples = [('urn:value:'+str(index), XSD+'anyURI')]
            elif family == 'duration':
                samples = [(f'P{index+2}M', XSD+'yearMonthDuration'),
                           (f'PT{index+2}S', XSD+'dayTimeDuration')]
            elif family.startswith('temporal-'):
                kind = family.removeprefix('temporal-')
                date = f'{2000+index:04d}'
                text = {'dateTime': date+'-01-01T00:00:00Z', 'date': date+'-01-01Z',
                        'gYear': date+'Z', 'gYearMonth': date+'-01Z',
                        'time': f'00:00:00.{index+1:04d}Z'}.get(kind)
                if kind in {'gMonth', 'gDay', 'gMonthDay'}:
                    period = 12 if kind == 'gMonth' else 31
                    cycle = index // period
                    offset = cycle-2-840
                    zone = ('' if cycle == 0 else 'Z' if cycle == 1
                            else f'{"-" if offset < 0 else "+"}{abs(offset)//60:02d}:{abs(offset)%60:02d}')
                    text = {'gMonth': '--', 'gDay': '---', 'gMonthDay': '--01-'}[kind]
                    text += f'{index%period+1:02d}'+zone
                samples = [(text, XSD+kind)] if text else []
            elif family == 'hexBinary':
                samples = [(f'{index:08x}', XSD+'hexBinary')]
            elif family == 'base64Binary':
                samples = [(b64encode(index.to_bytes(4, 'big')).decode(), XSD+'base64Binary')]
            else:
                samples = []
            for text, datatype in samples:
                if include(Literal(text, datatype=datatype, normalize=False)):
                    return list(selected.values())
    return list(selected.values())


def membership_regions(recognized, *, step):
    """One witness for every nonempty exact membership region of our D-set.

    This is a partition by datatype membership, NOT an enumeration of values.
    Integer facets change only at their inclusive bounds; noninteger decimals
    form the remaining numeric region. String facets form the normalization /
    token / NMTOKEN / Name / NCName / language chain. DateTimeStamp separates
    timezone-present dateTimes. Durations have four month/second profiles.
    All other supported primitive families have constant membership; JSON
    unions its own structural family with string, boolean and double, and
    HTML/XMLLiteral share a DOM family. These facts exhaust SUPPORTED_DATATYPES.
    No conclusion about arbitrary datatype extensions is made.
    """
    recognized = set(map(str, recognized))
    for datatype in recognized:
        families(datatype)  # Reject unimplemented spaces, not an empty region.
    samples = [sample for datatype in recognized for sample in witnesses({datatype})[0]]
    bounds = {0, 1, -1}
    for datatype in recognized:
        for bound in _INTEGER_BOUNDS.get(datatype, ()):
            if bound is not None:
                bounds.update((bound-1, bound, bound+1))
    samples.extend(Literal(str(n), datatype=XSD+'integer', normalize=False) for n in sorted(bounds))
    samples.append(Literal('0.5', datatype=XSD+'decimal', normalize=False))
    samples.extend(Literal(s, datatype=XSD+'string', normalize=False)
                   for s in ('a', '', ' a', 'a\tb', '1', 'a:b', 'a_b'))
    samples.extend((Literal('2026-10-22T00:00:00', datatype=XSD+'dateTime', normalize=False),
                    Literal('P1MT1S', datatype=XSD+'duration', normalize=False)))
    regions = {}
    for sample in samples:
        step()
        value = datatype_value(sample)
        profile = frozenset(d for d in recognized if contains(value, d))
        if profile and profile not in regions:
            regions[profile] = _recognized_witness(sample, profile)
    return tuple(regions.items())


def infinite_region(profile, recognized):
    """Cardinality of a nonempty exact membership region, not its samples."""
    profile, recognized = set(map(str, profile)), set(map(str, recognized))
    common = set.intersection(*(families(d) for d in profile))
    if common == {'numeric'}:
        integers = profile & _INTEGER_DATATYPES
        if not integers:
            return True  # Arbitrarily precise noninteger decimal values.
        lower = [b[0] for d in integers if (b := _INTEGER_BOUNDS.get(d, (None, None)))[0] is not None]
        upper = [b[1] for d in integers if (b := _INTEGER_BOUNDS.get(d, (None, None)))[1] is not None]
        excluded = [_INTEGER_BOUNDS.get(d, (None, None))
                    for d in (recognized-profile) & _INTEGER_DATATYPES]
        return ((not upper and not any(hi is None for _, hi in excluded))
                or (not lower and not any(lo is None for lo, _ in excluded)))
    if common <= {'boolean', 'float', 'double', 'temporal-gMonth',
                  'temporal-gDay', 'temporal-gMonthDay'}:
        return False
    if {XSD+'yearMonthDuration', XSD+'dayTimeDuration'} <= profile:
        return False
    return True


def fresh_image_witness(types, recognized, occupied, *, step):
    """Find an unused value in an infinite eligible membership region.

    Fast facet witnesses precede a fair ASCII lexical enumeration. Every
    infinite region of the supported spaces has infinitely many ASCII
    lexical representatives (language literals use fixed en/ltr metadata).
    Thus finite occupied values cannot exhaust this search. The caller's
    work budget still applies; exhaustion never means an empty space.
    """
    types = set(map(str, types))
    regions = membership_regions(recognized, step=step)
    if not any(types <= profile and infinite_region(profile, recognized) for profile, _ in regions):
        return None

    def eligible(sample):
        value = datatype_value(sample)
        profile = frozenset(str(d) for d in recognized if contains(value, d))
        return value not in occupied and types <= profile and infinite_region(profile, recognized)

    candidates = [sample for _, sample in regions]
    candidates += countermodel_witnesses(types, recognized, occupied, step=step)
    for sample in candidates:
        step()
        if eligible(sample):
            return sample
    numeric_base = max([0] + [abs(bound) for d in recognized
                             for bound in _INTEGER_BOUNDS.get(str(d), ()) if bound is not None]
                       + [int(abs(v.key))+1 for v in occupied if v.family == 'numeric'])+1
    index = 0
    while True:
        step()
        # Bijective base-128 enumeration: no queue or retained search history.
        code, text = index, ''
        while code:
            code, digit = divmod(code-1, 128)
            text = chr(digit)+text
        for datatype in sorted(types):
            name = datatype.removeprefix(XSD)
            year = str(2000+index)
            temporal = {'dateTime': year+'-01-01T00:00:00Z',
                        'dateTimeStamp': year+'-01-01T00:00:00Z',
                        'date': year+'-01-01Z', 'gYear': year+'Z',
                        'gYearMonth': year+'-01Z', 'time': f'00:00:00.{index+1}Z'}
            encoded = index.to_bytes(max(1, (index.bit_length()+7)//8), 'big')
            variants = [str(index), str(index)+'.1', str(numeric_base+index),
                        str(-numeric_base-index), 'a'+'-a'*index, text,
                        'urn:value:'+str(index), 'text'+str(index),
                        f'P{index+1}MT{index+1}S', f'P{index+1}M', f'PT{index+1}S',
                        json.dumps([index]), encoded.hex(), b64encode(encoded).decode()]
            if name in temporal:
                variants += [temporal[name], temporal[name].removesuffix('Z')]
            for lexical in variants:
                step()
                sample = (Literal(lexical, lang='en', direction='ltr' if datatype == RDF+'dirLangString' else None)
                          if datatype in {RDF+'langString', RDF+'dirLangString'}
                          else Literal(lexical, datatype=datatype, normalize=False))
                try:
                    if eligible(sample):
                        return sample
                except InvalidLexicalForm:
                    pass
        index += 1
