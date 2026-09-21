"""Serializer base class."""


class Serializer:
    def __init__(self, store=None):
        self.store = store

    def serialize(self, stream=None, base=None, encoding=None, **kwargs):
        raise NotImplementedError
