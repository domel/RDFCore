"""Executable shared-format contracts against the pinned RDFLib oracle.

These are scoped examples, not a complete syntax conformance suite. Known
differences remain ordinary failing assertions until resolved; no xfails.
"""

import platform
import subprocess

import pytest
import rdflib
import rdfcore


@pytest.fixture(scope="module", autouse=True)
def oracle_metadata(record_testsuite_property):
    assert rdflib.__version__ == "7.6.0"
    record_testsuite_property("rdflib", rdflib.__version__)
    record_testsuite_property("python", platform.python_version())
    record_testsuite_property(
        "rdfcore_revision",
        subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    )


def graph(module, fmt):
    return (module.Dataset if fmt in ("nquads", "trig") else module.Graph)()


@pytest.mark.parametrize("fmt", ("turtle12", "trig12"))
def test_rdf12_keeps_separate_eof_and_subject_validation(fmt):
    from rdfcore.exceptions import BadSyntax

    with pytest.raises(BadSyntax):
        graph(rdfcore, "trig" if fmt == "trig12" else "turtle").parse(
            data='<urn:s> <urn:p> "x"', format=fmt
        )
    with pytest.raises(ValueError, match="unterminated literal"):
        graph(rdfcore, "trig" if fmt == "trig12" else "turtle").parse(
            data='<urn:s> <urn:p> "unterminated', format=fmt
        )
    with pytest.raises(BadSyntax, match="subject"):
        graph(rdfcore, "trig" if fmt == "trig12" else "turtle").parse(
            data='"subject" <urn:p> "x" .', format=fmt
        )
