"""Published evidence must distinguish current checks from historical pointers."""

from pathlib import Path

from tests.w3c.semantic_audit import audit_report


def test_normative_audit_identifies_current_and_historical_evidence(monkeypatch):
    report = audit_report()
    for item in report["obligations"] + report["discrepancies"]:
        assert item["verification_status"] in ("core-regression", "unverified")
        if item["evidence"] is not None:
            assert item["verification_status"] == "core-regression"
            assert Path(item["evidence"].split("::")[0]).is_file()
        else:
            assert item["historical_evidence"]

    from tests.w3c import semantic_coverage, semantic_requirements
    from tests.w3c.semantic_contract import (
        semantic_plan,
        BASE,
        SEMANTIC_11,
        SEMANTIC_12,
    )

    # Only report metadata is under test; reasoning has its own core cases.
    monkeypatch.setattr(
        semantic_requirements, "run_probe", lambda probe: {"status": "not-run"}
    )
    monkeypatch.setattr(
        semantic_coverage, "_probe", lambda *args, **kwargs: {"status": "not-run"}
    )
    coverage = semantic_coverage.coverage_report([])
    assert not coverage["full_profile_verified"]
    for item in coverage["schema_sections"] + coverage["semantic_conditions"]:
        assert Path(item["evidence"].split("::")[0]).is_file()
        assert item["evidence_kind"] in ("report-probe", "core-regression")
    for prefix, catalogue in (
        (BASE + "rdf11/rdf-mt/manifest.ttl#", SEMANTIC_11),
        (BASE + "rdf12/rdf-semantics#", SEMANTIC_12),
    ):
        for name in catalogue:
            plan = semantic_plan(prefix + name)
            if plan:
                assert plan["regression"] is None
                assert plan["regression_status"] == "unverified"
                assert plan["historical_regression"]


def test_evidence_resolves_only_collected_tests():
    from tests.w3c.evidence import regression_evidence

    helper = "tests/integration/test_roundtrip_properties.py::snapshot"
    assert regression_evidence("history", helper)["verification_status"] == "unverified"
    group = "tests/integration/test_rdflib_differential.py::test_four_rdf11_formats_match_upstream_statements"
    assert (
        regression_evidence("history", group)["verification_status"]
        == "core-regression"
    )
    assert (
        regression_evidence("history", group + "[missing-case]")["verification_status"]
        == "unverified"
    )
