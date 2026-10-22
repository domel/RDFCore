"""Parser base classes and input normalization."""

from __future__ import annotations

from pathlib import Path, PurePath
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def _http_accept(format):
    # RDFLib 7.6.0 URLInputSource's shared short-name contract.
    legacy = {'xml': 'application/rdf+xml, */*;q=0.1',
              'turtle': 'text/turtle, application/x-turtle, */*;q=0.1',
              'ttl': 'text/turtle, application/x-turtle, */*;q=0.1',
              'nt': 'text/plain, */*;q=0.1', 'trig': 'application/trig, */*;q=0.1'}
    if format in legacy:
        return legacy[format]
    from .plugin import resolve_format, plugins
    resolved, version = resolve_format(format, Parser)
    if isinstance(format, str) and ';' in format and resolved == format:
        return format  # An exact custom registry entry takes precedence.
    explicit = {'nt12': 'application/n-triples', 'nq12': 'application/n-quads',
                'turtle12': 'text/turtle', 'trig12': 'application/trig',
                'xml12': 'application/rdf+xml', 'xmlrdf12': 'application/rdf+xml'}
    if resolved in explicit:
        return explicit[resolved]+'; version='+ (version or '1.2')
    if version is not None:
        return format
    return ', '.join(p.name for p in plugins(Parser) if '/' in p.name and ';' not in p.name)


class InputSource:
    def __init__(self, source=None, *, data=None, location=None, file=None, publicID=None, auto_close=False):
        self.publicID = publicID
        self.location = location
        self.file = file
        self.data = data
        self.content_type = None
        self.auto_close = auto_close

    def getByteStream(self):
        mode = getattr(self.file, "mode", "b") if self.file is not None else ""
        if self.file is not None and (not isinstance(mode, str) or "b" in mode):
            return self.file
        if isinstance(self.data, bytes):
            from io import BytesIO
            return BytesIO(self.data)
        return None

    def getCharacterStream(self):
        mode = getattr(self.file, "mode", "") if self.file is not None else ""
        if self.file is not None and isinstance(mode, str) and "b" not in mode:
            return self.file
        if isinstance(self.data, str):
            from io import StringIO
            return StringIO(self.data)
        return None

    def close(self):
        if self.auto_close and self.file is not None:
            self.file.close()


def create_input_source(source=None, publicID=None, location=None, file=None, data=None, format=None, **kwargs):
    if all(value is None for value in (source, location, file, data)):
        raise ValueError("exactly one of source, location, file or data must be given")
    if sum(value is not None for value in (source, location, file, data)) > 1:
        raise ValueError("source, location, file, and data are mutually exclusive")
    if data is not None and not isinstance(data, (str, bytes, bytearray)):
        raise RuntimeError("parse data can only be str, bytes or bytearray")
    if isinstance(data, bytearray):
        data = bytes(data)
    if source is not None:
        if hasattr(source, "read"):
            file = source
        elif isinstance(source, (str, bytes)) and isinstance(source, bytes):
            data = source
        elif isinstance(source, (str, PurePath)):
            location = str(source)
        else:
            raise TypeError("unsupported source type")
    if location is not None:
        parsed = urlparse(str(location))
        if parsed.scheme in ("http", "https"):
            accept = kwargs.get('http_accept', _http_accept(format))
            if not isinstance(accept, str) or '\r' in accept or '\n' in accept:
                raise ValueError('http_accept must be a single HTTP header value')
            file = urlopen(Request(str(location), headers={'Accept': accept}))
            try:
                final_url = file.geturl() if hasattr(file, 'geturl') else str(location)
                content_type = getattr(file, 'headers', {}).get('Content-Type')
                # RDFLib's explicit empty publicID falls back to the original
                # system ID, unlike None which uses the redirected public ID.
                base = final_url if publicID is None else str(location) if publicID == '' else publicID
                result = InputSource(location=final_url, file=file,
                                     publicID=base, auto_close=True)
                result.content_type = content_type
                return result
            except BaseException:
                file.close()
                raise
        else:
            path = Path(location)
            file = path.open("rb")
        result = InputSource(data=data, location=location, file=file, publicID=publicID, auto_close=True)
        return result
    return InputSource(data=data, location=location, file=file, publicID=publicID)


class Parser:
    def __init__(self, store=None):
        self.store = store

    def parse(self, source, sink, **kwargs):
        raise NotImplementedError
