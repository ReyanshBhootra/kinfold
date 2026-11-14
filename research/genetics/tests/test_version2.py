"""Regression checks for matching fallback calibration and the frozen reanalysis."""
import csv
import gzip
import json

import pytest

from research.genetics.data import group_partition
from research.genetics.records import Record
from research.genetics.version2 import (
    Calibration, OUT, ROOT, Scores, checked_set, complete_bundle,
    corrected_prediction, digest, generated_records, partition_v2,
)

DNA = (.65,) + (.05,) * 7
DNA_CAL = Calibration("dna_only", (.99,) * 8)
FUSION_CAL = Calibration("complete_known_fusion", (0.,) * 8)


def test_score_and_threshold_families_cannot_be_interchanged():
    with pytest.raises(ValueError, match="family mismatch"):
        checked_set(Scores("dna_only", DNA), FUSION_CAL)
    with pytest.raises(ValueError, match="Eight supported"):
        checked_set(Scores("dna_only", DNA[:7]), DNA_CAL)


@pytest.mark.parametrize("records,reason", [
    ([], "no_records"),
    ([Record("a", "A", 1, .85)], "missing_required_origin"),
    ([Record("a", None, 1, .85), Record("b", "B", 1, .7)], "unknown_or_unsupported_origin"),
    ([Record("a", "unexpected", 1, .85), Record("b", "B", 1, .7)], "unknown_or_unsupported_origin"),
    ([Record("a", "A", 1, .85), Record("b", "B", 1, .7), Record("copy", "A", 2, .85)], "conflicting_origin_bundle"),
    ([Record("a", "A", 1, .6), Record("b", "B", 1, .7)], "unsupported_assertion_or_assumed_reliability"),
])
def test_incomplete_or_unsupported_evidence_uses_dna_scores_and_dna_thresholds(records, reason):
    expected = checked_set(Scores("dna_only", DNA), DNA_CAL)
    hypotheses, family, actual_reason = corrected_prediction(DNA, records, DNA_CAL, FUSION_CAL)
    assert hypotheses == expected == tuple(range(1, 9))
    assert family == "dna_only"
    assert actual_reason == reason
    # Retaining the fused thresholds would exclude every class in this case.
    assert not any(1 - value <= threshold for value, threshold in zip(DNA, FUSION_CAL.thresholds))


def test_complete_known_bundle_uses_its_own_calibration_and_counts_copies_once():
    bundle = [Record("a", "A", 1, .85), Record("b", "B", 2, .7)]
    original = corrected_prediction(DNA, bundle, DNA_CAL, FUSION_CAL)
    copied = corrected_prediction(DNA, bundle + [Record("a-copy", "A", 1, .85)] * 6, DNA_CAL, FUSION_CAL)
    assert original == copied
    assert original[1:] == ("complete_known_fusion", "complete_known_consistent_origins")
    with pytest.raises(ValueError, match="family mismatch"):
        corrected_prediction(DNA, bundle, DNA_CAL, DNA_CAL)


def test_record_seed_is_repeatable_and_missingness_keeps_the_same_surviving_assertions():
    for replicate in range(1, 100):
        clean = generated_records(4, replicate, "clean_complete")
        assert clean == generated_records(4, replicate, "clean_complete")
        assert complete_bundle(clean)[0]
        for scenario in ("nominal_missing25", "missing70"):
            assert all(record in clean for record in generated_records(4, replicate, scenario))
        assert all(record.origin is None for record in generated_records(4, replicate, "unknown_all_complete"))
        assert not complete_bundle(generated_records(4, replicate, "unknown_A_complete"))[0]


def test_frozen_split_keeps_matched_ids_together_and_excludes_all_v1_train_and_test():
    protocol = json.loads((OUT / "frozen_protocol.json").read_text())
    assert digest(OUT / "frozen_protocol.json") == (OUT / "frozen_protocol.sha256").read_text().strip()
    assert digest(OUT / "frozen_split.csv.gz") == protocol["split_sha256"]
    assert digest(ROOT / "version2.py") == protocol["implementation_sha256"]
    counts = {"v2_calibration": 0, "v2_evaluation": 0}
    seen = set()
    with gzip.open(OUT / "frozen_split.csv.gz", "rt") as handle:
        for row in csv.DictReader(handle):
            key = int(row["cousin"]), int(row["replicate"])
            assert key not in seen
            seen.add(key)
            assert row["v1_partition"] == group_partition(*key)
            assert row["v2_partition"] == partition_v2(*key)
            if row["v2_partition"] in counts:
                assert row["v1_partition"] == "calibration"
                counts[row["v2_partition"]] += 1
    assert len(seen) == 400000
    assert min(counts.values()) > 0
    for relative, expected in protocol["preserved_v1_sha256"].items():
        assert digest(ROOT / relative) == expected
        assert digest(ROOT / "results/v1_preserved" / relative.split("/")[-1]) == expected


def test_saved_reanalysis_reports_identical_rows_and_exact_dna_fallback():
    report = json.loads((OUT / "comparison.json").read_text())
    assert report["independent_fresh_source_data_claimed"] is False
    assert report["v1_preservation_verified"] is True
    integrity = report["split_integrity"]
    assert integrity["overlap"] == integrity["v1_test_groups_used"] == integrity["v1_training_groups_evaluated"] == 0
    reference_counts = None
    for scenario, result in report["scenarios"].items():
        assert result["fallback_dna_equality"]["set_disagreements_with_dna"] == 0
        for metric in result["metrics"].values():
            counts = tuple(row["n"] for row in metric["per_class"].values())
            if reference_counts is None:
                reference_counts = counts
            assert counts == reference_counts
            assert sum(counts) == metric["overall"]["n"] == integrity["positive_evaluation_groups"]
        if scenario.startswith("unknown_"):
            assert result["fallback_dna_equality"]["fallback_rows"] == integrity["positive_evaluation_groups"]
            assert result["metrics"]["corrected_matching_fallback"] == result["metrics"]["dna_only"]
