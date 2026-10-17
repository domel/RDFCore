"""Executable shared-format contracts against the pinned RDFLib oracle.

These are scoped examples, not a complete syntax conformance suite. Known
differences remain ordinary failing assertions until resolved; no xfails.
"""

import io
import platform
import subprocess
import warnings

import pytest
import rdflib
import rdfcore


FORMATS = ("nt", "ntriples", "nquads", "turtle", "ttl", "trig")
LINE = '<urn:s> <urn:p> "ż\\nquoted\\\""@en .\n'


@pytest.fixture(scope="module", autouse=True)
def oracle_metadata(record_testsuite_property):
    assert rdflib.__version__ == "7.6.0"
    record_testsuite_property("rdflib", rdflib.__version__)
    record_testsuite_property("python", platform.python_version())
    record_testsuite_property("rdfcore_revision", subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True).strip())


def graph(module, fmt):
    return (module.Dataset if fmt in ("nquads", "trig") else module.Graph)()


def term(value):
    # Keep class, lexical form, datatype, language and graph identity distinct.
    return (type(value).__name__, str(value),
            str(value.datatype) if getattr(value, "datatype", None) is not None else None,
            getattr(value, "language", None))


def statements(value, fmt):
    rows = value.quads((None, None, None, None)) if fmt in ("nquads", "trig") else value
    return {tuple(term(item) if item is not None else None for item in row) for row in rows}


@pytest.mark.parametrize("fmt", FORMATS)
@pytest.mark.parametrize("data", ("", "# comment\n", LINE, LINE * 2))
@pytest.mark.parametrize("source_kind", ("text", "bytes", "text_stream", "byte_stream"))
def test_parse_inputs_return_identity_and_repeat_calls(fmt, data, source_kind):
    observed = []
    for module in (rdflib, rdfcore):
        value = graph(module, fmt)
        closed = []
        for _ in range(2):
            source = {"text": lambda: data, "bytes": lambda: data.encode(),
                      "text_stream": lambda: io.StringIO(data),
                      "byte_stream": lambda: io.BytesIO(data.encode())}[source_kind]()
            kwargs = {"source" if "stream" in source_kind else "data": source}
            assert value.parse(format=fmt, **kwargs) is value
            if "stream" in source_kind:
                closed.append(source.closed)
        observed.append((statements(value, fmt), closed))
    assert observed[1] == observed[0]


@pytest.mark.parametrize("fmt", FORMATS)
@pytest.mark.parametrize("data", ('<urn:s> <urn:p> "x" . trailing',
                                  '<urn:s> <urn:p> "unterminated',
                                  '"subject" <urn:p> "x" .'))
def test_invalid_input_exception_class_and_partial_state(fmt, data):
    observed = []
    for module in (rdflib, rdfcore):
        value = graph(module, fmt)
        try:
            value.parse(data=data, format=fmt)
        except Exception as error:
            error_class = type(error).__name__
        else:
            error_class = None
        observed.append((error_class, statements(value, fmt)))
    assert observed[1] == observed[0]


@pytest.mark.parametrize("fmt", FORMATS)
@pytest.mark.parametrize("empty", (False, True))
@pytest.mark.parametrize("encoding", (None, "utf-8"))
def test_serialize_return_type_and_semantic_roundtrip(fmt, empty, encoding):
    observed = []
    for module in (rdflib, rdfcore):
        value = graph(module, fmt)
        if not empty:
            value.parse(data=LINE, format=fmt)
        output = value.serialize(format=fmt, encoding=encoding)
        assert type(output) is (str if encoding is None else bytes)
        parsed = graph(rdflib, fmt).parse(data=output, format=fmt)
        observed.append(statements(parsed, fmt))
    assert observed[1] == observed[0]


@pytest.mark.parametrize("fmt", FORMATS)
@pytest.mark.parametrize("empty", (False, True))
@pytest.mark.parametrize("encoding", (None, "utf-8"))
def test_binary_destination_return_identity_and_ownership(fmt, empty, encoding):
    observed = []
    for module in (rdflib, rdfcore):
        value = graph(module, fmt)
        if not empty:
            value.parse(data=LINE, format=fmt)
        stream = io.BytesIO()
        assert value.serialize(stream, format=fmt, encoding=encoding) is value
        assert not stream.closed
        parsed = graph(rdflib, fmt).parse(data=stream.getvalue(), format=fmt)
        observed.append(statements(parsed, fmt))
    assert observed[1] == observed[0]


@pytest.mark.parametrize("fmt", FORMATS)
def test_typed_literal_normalization(fmt):
    data = '<urn:s> <urn:p> "01"^^<http://www.w3.org/2001/XMLSchema#integer> .'
    observed = [statements(graph(module, fmt).parse(data=data, format=fmt), fmt)
                for module in (rdflib, rdfcore)]
    assert observed[1] == observed[0]


@pytest.mark.parametrize("fmt", ("turtle", "ttl", "trig"))
def test_missing_final_dot_exception(fmt):
    observed = []
    for module in (rdflib, rdfcore):
        with pytest.raises(Exception) as error:
            graph(module, fmt).parse(data='<urn:s> <urn:p> "x"', format=fmt)
        observed.append(type(error.value).__name__)
    assert observed[1] == observed[0]


@pytest.mark.parametrize("fmt", ("nquads", "trig"))
def test_named_and_default_graphs_roundtrip(fmt):
    observed = []
    for module in (rdflib, rdfcore):
        value = module.Dataset()
        triple = (module.URIRef("urn:s"), module.URIRef("urn:p"), module.Literal("x"))
        value.add(triple)
        value.graph(module.URIRef("urn:g")).add(triple)
        encoded = value.serialize(format=fmt)
        parsed = rdflib.Dataset().parse(data=encoded, format=fmt)
        observed.append(statements(parsed, fmt))
    assert observed[1] == observed[0]


@pytest.mark.parametrize("fmt", FORMATS)
def test_failed_parse_stream_ownership(fmt):
    observed = []
    for module in (rdflib, rdfcore):
        source = io.BytesIO(b'<urn:s> <urn:p> "x" . trailing')
        with pytest.raises(Exception):
            graph(module, fmt).parse(source=source, format=fmt)
        observed.append(source.closed)
    assert observed[1] == observed[0]


@pytest.mark.parametrize("fmt", FORMATS)
@pytest.mark.parametrize("encoding", ("utf-16", "ascii"))
def test_custom_encoding_binary_destination(fmt, encoding):
    observed = []
    for module in (rdflib, rdfcore):
        value = graph(module, fmt).parse(data=LINE, format=fmt)
        destination = io.BytesIO()
        try:
            value.serialize(destination, format=fmt, encoding=encoding)
        except Exception as error:
            observed.append((type(error).__name__, None))
        else:
            try:
                parsed = graph(rdflib, fmt).parse(data=destination.getvalue(), format=fmt)
            except Exception as error:
                observed.append((type(error).__name__, None))
            else:
                observed.append((None, statements(parsed, fmt)))
    assert observed[1] == observed[0]


@pytest.mark.parametrize("fmt", FORMATS)
@pytest.mark.parametrize("encoding", ("utf-16", "ascii"))
def test_custom_encoding_capture_and_warnings(fmt, encoding):
    observed = []
    for module in (rdflib, rdfcore):
        value = graph(module, fmt).parse(data=LINE, format=fmt)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", UserWarning)
            output = value.serialize(format=fmt, encoding=encoding)
        assert type(output) is bytes
        parsed = graph(rdflib, fmt).parse(data=output, format=fmt)
        observed.append((statements(parsed, fmt),
                         [str(item.message) for item in caught
                          if item.category is UserWarning]))
    assert observed[1] == observed[0]


@pytest.mark.parametrize("fmt", FORMATS)
def test_path_destination_and_autodetection(fmt, tmp_path):
    observed = []
    suffix = {"nt": "nt", "ntriples": "nt", "nquads": "nq",
              "turtle": "ttl", "ttl": "ttl", "trig": "trig"}[fmt]
    for module in (rdflib, rdfcore):
        value = graph(module, fmt).parse(data=LINE, format=fmt)
        path = tmp_path / f"{module.__name__}.{suffix}"
        assert value.serialize(path, format=fmt) is value
        observed.append(statements(graph(module, fmt).parse(path), fmt))
    assert observed[1] == observed[0]


@pytest.mark.parametrize("fmt", FORMATS)
@pytest.mark.parametrize("data", (None, 3))
def test_missing_or_wrong_data_exception(fmt, data):
    observed = []
    for module in (rdflib, rdfcore):
        with pytest.raises(Exception) as error:
            graph(module, fmt).parse(data=data, format=fmt)
        observed.append(type(error.value).__name__)
    assert observed[1] == observed[0]


@pytest.mark.parametrize("fmt", ("turtle", "ttl", "trig"))
@pytest.mark.parametrize("tail", ("", " ", "\n", "# comment", " # comment\n"))
def test_missing_dot_eof_boundaries(fmt, tail):
    observed = []
    for module in (rdflib, rdfcore):
        value = graph(module, fmt)
        with pytest.raises(Exception) as error:
            value.parse(data='<urn:s> <urn:p> "x"' + tail, format=fmt)
        observed.append((type(error.value).__name__, statements(value, fmt)))
    assert observed[1] == observed[0]


@pytest.mark.parametrize("fmt", ("turtle", "ttl", "trig"))
@pytest.mark.parametrize("obj", ('"unterminated', "'unterminated",
                                 '"""unterminated', '"unterminated\n', '<urn:o'))
def test_unterminated_token_exception(fmt, obj):
    observed = []
    for module in (rdflib, rdfcore):
        with pytest.raises(Exception) as error:
            graph(module, fmt).parse(data='<urn:s> <urn:p> ' + obj, format=fmt)
        observed.append(type(error.value).__name__)
    assert observed[1] == observed[0]


def test_literal_subject_in_named_graph():
    observed = []
    for module in (rdflib, rdfcore):
        value = module.Dataset().parse(
            data='<urn:g> { "subject" <urn:p> "x" . }', format="trig")
        observed.append(statements(value, "trig"))
    assert observed[1] == observed[0]


@pytest.mark.parametrize("fmt", FORMATS)
def test_bytearray_data(fmt):
    observed = [statements(graph(module, fmt).parse(
        data=bytearray(LINE.encode()), format=fmt), fmt) for module in (rdflib, rdfcore)]
    assert observed[1] == observed[0]


@pytest.mark.parametrize("fmt", ("turtle12", "trig12"))
def test_rdf12_keeps_separate_eof_and_subject_validation(fmt):
    from rdfcore.exceptions import BadSyntax

    with pytest.raises(BadSyntax):
        graph(rdfcore, "trig" if fmt == "trig12" else "turtle").parse(
            data='<urn:s> <urn:p> "x"', format=fmt)
    with pytest.raises(ValueError, match="unterminated literal"):
        graph(rdfcore, "trig" if fmt == "trig12" else "turtle").parse(
            data='<urn:s> <urn:p> "unterminated', format=fmt)
    with pytest.raises(BadSyntax, match='subject'):
        graph(rdfcore, "trig" if fmt == "trig12" else "turtle").parse(
            data='"subject" <urn:p> "x" .', format=fmt)
