"""Regression checks for the v3 label-free source reliability check."""
import json
import random

import pytest

from research.genetics import version2
from research.genetics.records import Record
from research.genetics.version2 import Calibration, Scores, checked_set
from research.genetics.version3 import (
    MIN_RECORDS, OUT, ROOT, SCENARIOS, Reference, agreement_residual, batches,
    digest, origin_claims, reliability_check, route_batch, scenario_records,
)

DNA = (.65,) + (.05,) * 7
DNA_CAL = Calibration("dna_only", (.99,) * 8)
FUSION_CAL = Calibration("complete_known_fusion", (0.,) * 8)


def test_v2_scenarios_reproduce_v2_record_draws_exactly():
    for scenario in ("clean_complete", "nominal_missing25", "missing70", "incorrect_A45_complete", "unknown_all_complete", "unknown_A_complete"):
        for truth in (1, 5, 8):
            for replicate in range(1, 60):
                assert scenario_records(truth, replicate, scenario) == version2.generated_records(truth, replicate, scenario)


def test_new_scenarios_were_declared_unseen_and_change_only_their_origin():
    unseen = {name for name, spec in SCENARIOS.items() if not spec["seen_before_design"]}
    assert unseen == {"incorrect_A25_complete", "incorrect_B_complete", "incorrect_A45_missing25", "better_A_complete"}
    for replicate in range(1, 200):
        clean = {r.origin: r for r in scenario_records(3, replicate, "clean_complete")}
        bad_b = {r.origin: r for r in scenario_records(3, replicate, "incorrect_B_complete")}
        assert clean["A"] == bad_b["A"]


def test_residual_is_centred_when_claims_follow_the_assumed_reliability():
    rng = random.Random(7)
    dna = (.4, .3, .1, .08, .05, .04, .02, .01)
    residuals = []
    for _ in range(40000):
        truth = rng.choices(range(1, 9), weights=dna)[0]
        claim = truth if rng.random() < .85 else rng.choice([c for c in range(1, 9) if c != truth])
        residuals.append(agreement_residual(dna, claim, .85))
    assert abs(sum(residuals) / len(residuals)) < 0.003


def test_check_rejects_worse_source_but_not_nominal_or_better_source():
    reference = Reference([-.1, .1] * 5000)
    assert reliability_check([0.0] * 400, reference)["status"] == "consistent"
    assert reliability_check([-.05] * 400, reference)["status"] == "rejected"
    assert reliability_check([.05] * 400, reference)["status"] == "consistent"  # one-sided
    assert reliability_check([-.5] * (MIN_RECORDS - 1), reference)["status"] == "insufficient_evidence"


def test_failed_check_routes_complete_bundles_to_exact_dna_fallback():
    reference = Reference([-.01, .01] * 5000)
    bundle = [Record("a", "A", 2, .85), Record("b", "B", 2, .7)]  # disagrees with DNA's favoured class 1
    rows = [(DNA, bundle)] * 50
    routed, checks = route_batch(rows, {"A": reference, "B": reference}, DNA_CAL, FUSION_CAL)
    assert checks["A"]["status"] == "rejected"
    expected = checked_set(Scores("dna_only", DNA), DNA_CAL)
    assert all(result == (expected, "dna_only", "reliability_A_rejected_B_rejected") for result in routed)


def test_passing_check_keeps_v2_routing():
    bundle = [Record("a", "A", 1, .85), Record("b", "B", 1, .7)]
    a, b = agreement_residual(DNA, 1, .85), agreement_residual(DNA, 1, .7)
    references = {"A": Reference([a - .01, a + .01] * 5000), "B": Reference([b - .01, b + .01] * 5000)}
    routed, checks = route_batch([(DNA, bundle)] * 50, references, DNA_CAL, FUSION_CAL)
    assert {c["status"] for c in checks.values()} == {"consistent"}
    assert routed[0] == version2.corrected_prediction(DNA, bundle, DNA_CAL, FUSION_CAL)


def test_unknown_or_conflicting_origins_never_contribute_evidence():
    assert origin_claims([Record("a", None, 1, .85), Record("b", "B", 1, .7)]) == {"B": (1, .7)}
    assert origin_claims([Record("a", "A", 1, .85), Record("c", "A", 2, .85)]) == {}


def test_batches_partition_every_row_once():
    for size in (25, 100, 400, "all"):
        seen = [i for batch in batches(1003, size) for i in batch]
        assert sorted(seen) == list(range(1003))


@pytest.mark.skipif(not (OUT / "comparison.json").exists(), reason="v3 evaluation not run yet")
def test_saved_v3_report_is_frozen_and_internally_consistent():
    protocol = json.loads((OUT / "frozen_protocol.json").read_text())
    assert digest(OUT / "frozen_protocol.json") == (OUT / "frozen_protocol.sha256").read_text().strip()
    assert digest(ROOT / "version3.py") == protocol["implementation_sha256"]
    assert digest(ROOT / "results/v2/comparison.json") == protocol["v2_comparison_sha256"]
    report = json.loads((OUT / "comparison.json").read_text())
    assert report["independent_fresh_source_data_claimed"] is False and report["calibrations_match_v2"] is True
    n = report["split_integrity"]["positive_evaluation_groups"]
    for result in report["scenarios"].values():
        for metric in result["metrics"].values():
            assert metric["overall"]["n"] == n
        for stats in result["batch_checks"].values():
            assert stats["fallback_set_disagreements_with_dna"] == 0
