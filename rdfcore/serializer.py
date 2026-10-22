"""Serializer base class."""

from io import BufferedIOBase, RawIOBase, TextIOBase


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
