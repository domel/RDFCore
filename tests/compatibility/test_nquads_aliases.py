"""RDFCore aliases use RDFLib 7.6.0's nquads as the executable oracle."""

from io import BytesIO

import pytest

from rdfcore import Dataset, Literal, URIRef, convert
from rdfcore.exceptions import ParserError

DATA = '<urn:s> <urn:p> "named"@EN <urn:g> .\n<urn:t> <urn:p> "default" .\n'


def records(dataset):
    return {
        tuple(
            (
                type(term).__name__,
                str(term),
                getattr(term, "language", None),
                str(getattr(term, "datatype", None)),
            )
            for term in quad
        )
        for quad in dataset.quads()
    }


@pytest.mark.parametrize("source", ["nq", "nq11"])
@pytest.mark.parametrize("target", ["nq", "nq11", "nq12"])
def test_convert_accepts_new_aliases_in_both_directions(source, target):
    output = BytesIO()
    convert(BytesIO(DATA.encode()), output, input_format=source, output_format=target)
    expected = Dataset().parse(data=DATA, format="nquads")
    assert records(Dataset().parse(data=output.getvalue(), format=target)) == records(
        expected
    )


@pytest.mark.parametrize("alias", ["nq", "nq11"])
def test_new_aliases_do_not_enable_rdf12(alias):
    errors = []
    for format in ("nquads", alias):
        with pytest.raises(Exception) as caught:
            Dataset().parse(data='<urn:s> <urn:p> "text"@en--rtl .\n', format=format)
        errors.append(type(caught.value))
    assert errors[0] is errors[1]
    graph = Dataset().add(
        (URIRef("urn:s"), URIRef("urn:p"), Literal("text", lang="en", direction="rtl"))
    )
    with pytest.raises(ValueError):
        graph.serialize(format=alias)
    with pytest.raises(ParserError) as caught:
        convert(
            BytesIO(b'VERSION "1.2"\n<urn:s> <urn:p> "text"@en--rtl .\n'),
            BytesIO(),
            input_format="nq12",
            output_format=alias,
        )
    assert isinstance(caught.value.__cause__, ValueError)
