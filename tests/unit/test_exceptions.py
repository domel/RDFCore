import pytest

from rdfcore import BadSyntax, Error, ParserError, PluginException
from rdfcore.compat import binary_type, is_py3, iteritems, string_types, text_type


def test_parser_error_is_library_error():
    assert issubclass(ParserError, Error)
    assert issubclass(PluginException, Error)


def test_bad_syntax_is_distinct_parser_exception():
    assert issubclass(BadSyntax, Exception)
    assert not issubclass(BadSyntax, Error)


def test_python_compatibility_helpers():
    assert is_py3()
    assert text_type is str
    assert binary_type is bytes
    assert isinstance("x", string_types)
    assert list(iteritems({"x": 1})) == [("x", 1)]


def test_exceptions_can_be_raised():
    with pytest.raises(ParserError, match="invalid input"):
        raise ParserError("invalid input")
