"""Parser base classes and input normalization."""

from __future__ import annotations

from pathlib import Path, PurePath
from urllib.parse import urlparse
from urllib.request import urlopen


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
    if sum(value is not None for value in (source, location, file, data)) > 1:
        raise ValueError("source, location, file, and data are mutually exclusive")
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
            file = urlopen(str(location))
        else:
            path = Path(location)
            file = path.open("rb")
        return InputSource(data=data, location=location, file=file, publicID=publicID, auto_close=True)
    return InputSource(data=data, location=location, file=file, publicID=publicID)


class Parser:
    def __init__(self, store=None):
        self.store = store

    def parse(self, source, sink, **kwargs):
        raise NotImplementedError
