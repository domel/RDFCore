"""Exceptions exposed by the RDFLib-compatible public API."""


class Error(Exception):
    """Base class for library errors."""


class ParserError(Error):
    """Raised when an RDF document cannot be parsed."""


class ObjectTypeError(Error):
    """Raised when an operation receives an invalid RDF object type."""


class UniquenessError(Error):
    """Raised when an operation requires a unique result but gets several."""


class ModificationException(Error):
    """Raised when a store cannot be modified."""


class StoreException(Error):
    """Raised for store-level failures."""


class PluginException(Error):
    """Raised when a plugin cannot be loaded or resolved."""


class BadSyntax(SyntaxError):
    """Syntax error used by Turtle and TriG parsers."""


class CompValueException(Exception):
    """Raised for invalid parser grammar values."""
