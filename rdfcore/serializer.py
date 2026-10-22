"""Serializer base class."""

from io import BufferedIOBase, RawIOBase, TextIOBase
import codecs


class _IncrementalOutput:
    """Keep one codec state per document without taking ownership of a sink."""

    def __init__(self, stream, encoding, requested):
        self.stream, self.encoding, self.requested = stream, encoding, requested
        self.encoder = None
        self.finished = False

    def _binary(self, text):
        if self.encoder is None:
            self.encoder = codecs.getincrementalencoder(self.encoding)()
        self.finished = False
        self.stream.write(self.encoder.encode(text))

    def write(self, text):
        if self.requested is False:
            self._binary(text)
        elif self.requested is True:
            self.stream.write(text)
        else:
            # Preserve the direct push API's historical text-first fallback.
            try:
                self.stream.write(text)
            except TypeError:
                self._binary(text)

    def finish(self):
        if self.encoder is not None and not self.finished:
            self.finished = True
            tail = self.encoder.encode('', final=True)
            if tail:
                self.stream.write(tail)


def text_output(stream, encoding=None, requested=None):
    """Select the protocol without probing a possibly side-effecting write."""
    if requested is not None:
        if type(requested) is not bool:
            raise ValueError('text_output must be a boolean or None')
        return requested
    if isinstance(stream, TextIOBase):
        return True
    if isinstance(stream, (BufferedIOBase, RawIOBase)):
        return False
    mode = getattr(stream, 'mode', None)
    if isinstance(mode, str):
        return 'b' not in mode
    return encoding is None


def write_output(stream, value, encoding=None, requested=None):
    use_text = text_output(stream, encoding, requested)
    # Validate explicit codecs even when a text sink is selected.
    payload = value.encode(encoding or 'utf-8')
    stream.write(value if use_text else payload)


class Serializer:
    def __init__(self, store=None):
        self.store = store

    def serialize(self, stream=None, base=None, encoding=None, **kwargs):
        raise NotImplementedError
