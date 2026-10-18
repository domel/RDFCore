"""Versioned RDF media types and profile-preserving plugin adapters."""

import re
from functools import lru_cache

from .rdf_version import RDF_VERSIONS, required_rdf_version, version_allows

_FORMATS = {
    'text/turtle': ('turtle', 'turtle12'),
    'application/trig': ('trig', 'trig12'),
    'application/n-triples': ('nt', 'nt12'),
    'application/n-quads': ('nquads', 'nq12'),
    'application/rdf+xml': ('xml', 'xml12'),
}
_TOKEN = r"[!#$%&'*+.^_`|~0-9A-Za-z-]+"
_PARAM = re.compile(r'\s*;\s*(' + _TOKEN + r')\s*=\s*(' + _TOKEN + r'|"(?:[^"\\\r\n]|\\[^\r\n])*")\s*')


def resolve_format(name):
    if not isinstance(name, str) or ';' not in name:
        return name, None
    media, rest = name.split(';', 1)
    choices = _FORMATS.get(media.strip().lower())
    if choices is None:
        return name, None
    if '\r' in name or '\n' in name:
        raise ValueError('invalid media parameters')
    rest = ';' + rest
    position, version = 0, None
    while position < len(rest):
        match = _PARAM.match(rest, position)
        if match is None:
            raise ValueError('invalid media parameters')
        key, value = match.groups()
        if value.startswith('"'):
            value = re.sub(r'\\(.)', r'\1', value[1:-1])
        if key.lower() == 'version':
            if version is not None:
                raise ValueError('duplicate media version')
            if value not in RDF_VERSIONS:
                raise ValueError(f'unsupported media version {value!r}')
            version = value
        position = match.end()
    return choices[version is not None and version != '1.1'], version


def version_options(options, version):
    options = dict(options)
    if version is not None:
        if options.get('rdf_version', 'auto') not in ('auto', version):
            raise ValueError('media version and rdf_version conflict')
        options['rdf_version'] = version
    return options


class ProfileSink:
    def __init__(self, sink, version):
        self.sink, self.version = sink, version

    def __getattr__(self, name):
        return getattr(self.sink, name)

    def add(self, statement):
        if not version_allows(self.version, required_rdf_version((statement,))):
            raise ValueError(f'statement exceeds RDF {self.version} media profile')
        return self.sink.add(statement)


@lru_cache(maxsize=32)
def versioned_class(backend, kind, version):
    from .parser import Parser
    if kind is Parser:
        class VersionedParser(backend):
            def parse(self, source, sink, **kwargs):
                options = version_options(kwargs, version)
                wrapped = ProfileSink(sink, version) if version else sink
                result = super().parse(source, wrapped, **options)
                return sink if result is wrapped else result
        return VersionedParser

    class VersionedSerializer(backend):
        def serialize(self, stream=None, base=None, encoding=None, **kwargs):
            return super().serialize(stream, base=base, encoding=encoding,
                                     **version_options(kwargs, version))
    return VersionedSerializer
