"""Executable RDFLib 7.6.0 regressions for the 2026-10-18 review."""

import pytest
import rdflib
from rdflib.compare import isomorphic as reference_isomorphic

import rdfcore
from rdfcore.compare import isomorphic


@pytest.mark.parametrize("case", ["cycle", "split_cycles", "loop", "star"])
def test_exact_comparison_backtracks_like_reference(case):
    outcomes = []
    cycle = [(i, (i + 1) % 6) for i in range(6)]
    variants = {
        "cycle": cycle,
        "split_cycles": [(i, (i // 3) * 3 + (i + 1) % 3) for i in range(6)],
        "loop": [(i, i) for i in range(6)],
        "star": [(0, i) for i in range(6)],
    }
    for module, compare in ((rdflib, reference_isomorphic), (rdfcore, isomorphic)):
        a, b = module.Graph(), module.Graph()
        for source, edges, prefix in ((a, cycle, "a"), (b, variants[case], "b")):
            for s, o in edges:
                source.add(
                    (
                        module.BNode(prefix + str(s)),
                        module.URIRef("urn:p"),
                        module.BNode(prefix + str(o)),
                    )
                )
        outcomes.append(compare(a, b))
    assert outcomes[0] == outcomes[1]
